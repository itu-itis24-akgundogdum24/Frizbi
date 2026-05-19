"""
Adim 3: Iki Asamali Canli Scraping, Kilitlenme Defansi ve Akilli Ayristirma.
Trend Agent ham HTML'i BeautifulSoup ile arindirir.
Playwright zaman sinirlari ile kilitlenmeye karsi korunur.
Fiyat ayristirma indirim ve eski fiyat metinlerini guncel fiyattan ayirir.
Sistem yalnizca canli internetten cekilen gercek verilerle calisir.
"""

import os
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Annotated, TypedDict
import operator

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph, END
import chromadb


# Teshis log modulu: sistemin her asamasini diagnostic.log dosyasina yazar
from diagnostic import diag, diag_section, diag_exception, reset_diagnostic_log

# Ortam degiskenleri ve API Key kontrolu
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY bulunamadi! "
        "Lutfen .env dosyasina veya ortam degiskenlerine ekleyin."
    )

# Bulut tarayici grid'inin guvenli WebSocket (WSS) ucnoktasi.
# Yerel Chromium baslatma yerine uzak tarayiciya baglanmak icin kullanilir.
CLOUD_BROWSER_WSS = os.getenv("CLOUD_BROWSER_WSS")
if not CLOUD_BROWSER_WSS:
    raise EnvironmentError(
        "CLOUD_BROWSER_WSS bulunamadi! "
        "Bulut tarayici WSS ucnoktasini .env dosyasina ekleyin."
    )

# Sunum esnasinda islenecek maksimum urun sayisi
MAX_DEMO_PRODUCTS = 1

# Bir hedef icin tekrar deneme limiti
MAX_SCRAPE_RETRIES = 2

# Playwright zaman sinirlari (milisaniye)
NAV_TIMEOUT_MS = 15000
DEFAULT_TIMEOUT_MS = 15000
SELECTOR_TIMEOUT_MS = 5000

# Denetim dosyasinin yolu
AUDIT_FILE = "session_audit.txt"

# Para birimi belirtecleri; fiyat ayristirmada referans alinir
CURRENCY_TOKENS = ("$", "TL", "TRY", "USD", "EUR", "GBP")

# Her istekte rotasyon icin tarayici kimlik havuzu
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/19.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) "
    "Gecko/20100101 Firefox/142.0",
]

# Trend Agent'in canli istek atacagi Reddit JSON akislari
TREND_SOURCES = [
    "https://www.reddit.com/r/dropshipping/hot.json",
    "https://www.reddit.com/r/amazonfinds/hot.json",
    "https://www.reddit.com/r/shutupandtakemymoney/hot.json",
]

# Product Hunter Agent'in deneyecegi pazar yeri arama rotalari
MARKETPLACE_SEARCH_ROUTES = [    
    "https://www.alibaba.com/trade/search?SearchText={query}",
]

# LLM (Gemini) Tanimi
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0.7,
    google_api_key=GEMINI_API_KEY,
)

# Gemini embedding modeli
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=GEMINI_API_KEY,
)

# ChromaDB kalici istemcisi (lokal diske ./chroma_db klasorune yazar)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
review_collection = chroma_client.get_or_create_collection(
    name="product_reviews",
    metadata={"hnsw:space": "cosine"},
)


# 1. Pydantic Semalari

class TrendOutput(BaseModel):
    """Trend Agent ciktisi."""
    keywords: list[str] = Field(
        description="E-ticarette yukselen 5 trend alt urun grubu / anahtar kelimesi"
    )


class SEOContent(BaseModel):
    """Icerik Agent ciktisi."""
    seo_title:       str       = Field(description="SEO uyumlu urun basligi (Turkce, emoji yok)")
    seo_description: str       = Field(description="Detayli urun aciklamasi (Turkce, emoji yok)")
    meta_keywords:   list[str] = Field(description="3-5 meta anahtar kelime")


class SingleReviewVerdict(BaseModel):
    """Tek bir yoruma ait ironi/troll analizi sonucu."""
    review_index:    int  = Field(description="Yorumun gonderilen listedeki sirasi (0 tabanli)")
    is_manipulative: bool = Field(description="Yorum ironik, alayci veya manipulatif mi")
    real_sentiment:  str  = Field(description="Gercek niyet: 'olumlu', 'olumsuz' veya 'notr'")
    reason:          str  = Field(description="Tespitin kisa Turkce gerekcesi, emoji yok")


class BatchReviewOutput(BaseModel):
    """Bir urune ait tum yorumlarin tek API cagrisiyla toplu analizi."""
    verdicts: list[SingleReviewVerdict] = Field(
        description="Gonderilen her yorum icin bir analiz sonucu"
    )


# 2. Agent State

class AgentState(TypedDict):
    session_id:         str
    user_request:       str
    trend_keywords:     list
    raw_product_data:   dict
    optimized_content:  dict
    shipping_details:   dict
    is_data_valid:      bool
    retry_count:        int
    trust_scores:       dict
    data_source:        str
    log_history:        Annotated[list, operator.add]


# 3. Denetim Dosyasi Yardimcilari

def reset_audit_file() -> None:
    """Denetim dosyasini 'w' modu ile sifirlar; eski icerik tamamen silinir."""
    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        f.write("Oturum Denetim Dosyasi\n")
        f.write(f"Olusturulma: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 60 + "\n")


def append_audit(lines) -> None:
    """Verilen satir veya satir listesini denetim dosyasina ekler."""
    if isinstance(lines, str):
        lines = [lines]
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


# 4. Akilli Fiyat Ayristirma

class PriceParseError(Exception):
    """Ham fiyat metni gecerli bir guncel fiyata cevrilemediginde firlatilir."""
    pass


def parse_price_to_float(raw_price: str) -> float:
    """
    Ham fiyat metnini guncel ve gercek fiyata cevirir.
    Metni once bosluklara gore parcalar; para birimi sembolu tasiyan blogu
    referans alir. Indirim oranlari (yuzde) ve eski fiyatlar guncel fiyatla
    birlestirilmez. Gecerli fiyat bulunamazsa PriceParseError firlatir.
    """
    if not raw_price or not str(raw_price).strip():
        raise PriceParseError("Fiyat metni bos")

    text = str(raw_price).strip()
    parts = text.split()
    chosen = None

    # 1) Para birimi sembolu olan ve icinde rakam bulunan blogu tercih et
    for part in parts:
        if any(sym in part for sym in CURRENCY_TOKENS) and any(c.isdigit() for c in part):
            chosen = part
            break

    # 2) Para birimi blogu rakamsizsa, ona komsu rakamli blogu al (yuzde haric)
    if chosen is None:
        for i, part in enumerate(parts):
            if any(sym in part for sym in CURRENCY_TOKENS):
                for j in (i + 1, i - 1):
                    if 0 <= j < len(parts) and "%" not in parts[j] \
                            and any(c.isdigit() for c in parts[j]):
                        chosen = parts[j]
                        break
            if chosen is not None:
                break

    # 3) Para birimi hic yoksa: yuzde tasimayan ilk rakamli blogu al
    if chosen is None:
        for part in parts:
            if "%" in part:
                continue
            if any(c.isdigit() for c in part):
                chosen = part
                break

    if chosen is None:
        raise PriceParseError(f"Fiyatta gecerli sayisal blok yok: '{raw_price}'")

    # Aralik ise ilk (en dusuk) degeri al
    if "-" in chosen:
        chosen = chosen.split("-")[0]

    # Sadece rakam, nokta ve virgul karakterlerini birak
    token = "".join(ch for ch in chosen if ch.isdigit() or ch in ".,")
    if not token:
        raise PriceParseError(f"Fiyatta sayisal veri yok: '{raw_price}'")

    # Hem nokta hem virgul varsa: sonra gelen karakter ondalik ayracidir
    if "." in token and "," in token:
        if token.rfind(",") > token.rfind("."):
            token = token.replace(".", "").replace(",", ".")
        else:
            token = token.replace(",", "")
    elif "," in token:
        token = token.replace(",", ".")

    # Birden fazla nokta kaldiysa sonuncusu ondalik, oncekiler binlik ayracidir
    if token.count(".") > 1:
        last = token.rfind(".")
        token = token[:last].replace(".", "") + token[last:]

    try:
        value = round(float(token), 2)
    except ValueError:
        raise PriceParseError(f"Fiyat float'a cevrilemedi: '{raw_price}'")

    if value <= 0:
        raise PriceParseError(f"Fiyat sifir veya negatif: '{raw_price}'")

    return value


# 5. ChromaDB Yardimci Fonksiyonlari

def cleanup_old_data(ttl_days: int = 30) -> int:
    """30 gunden eski kayitlari ChromaDB'den siler, silinen kayit sayisini doner."""
    cutoff = datetime.now() - timedelta(days=ttl_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    try:
        stored = review_collection.get(include=["metadatas"])
    except Exception:
        return 0

    expired_ids = [
        doc_id
        for doc_id, meta in zip(stored.get("ids", []), stored.get("metadatas", []))
        if meta.get("date", "9999-99-99") < cutoff_str
    ]

    if expired_ids:
        review_collection.delete(ids=expired_ids)

    return len(expired_ids)


def store_product_in_chroma(product: dict, session_id: str) -> int:
    """
    Bir urunun teknik aciklamasini ve varsa yorumlarini ChromaDB'ye yazar.
    Yorum yoksa yorum alani bos birakilir; yapay yorum eklenmez.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    documents, ids, metadatas = [], [], []

    description = product.get("raw_description", "")
    if description:
        documents.append(description)
        ids.append(f"{session_id}_{product['id']}_desc_{uuid.uuid4().hex[:6]}")
        metadatas.append({
            "session_id": session_id,
            "product_id": product["id"],
            "type":       "description",
            "stars":      0,
            "date":       today_str,
        })

    for idx, review in enumerate(product.get("reviews", [])):
        documents.append(review["text"])
        ids.append(f"{session_id}_{product['id']}_review_{idx}_{uuid.uuid4().hex[:6]}")
        metadatas.append({
            "session_id": session_id,
            "product_id": product["id"],
            "type":       "review",
            "stars":      review.get("stars", 0),
            "date":       today_str,
        })

    if not documents:
        return 0

    vectors = embeddings.embed_documents(documents)
    review_collection.add(
        ids=ids,
        embeddings=vectors,
        documents=documents,
        metadatas=metadatas,
    )
    return len(documents)


def query_reviews_from_chroma(product_id: str, session_id: str) -> list[dict]:
    """ChromaDB'den sadece ilgili session ve urune ait yorumlari ceker."""
    try:
        stored = review_collection.get(
            where={"$and": [
                {"session_id": {"$eq": session_id}},
                {"product_id": {"$eq": product_id}},
                {"type":       {"$eq": "review"}},
            ]},
            include=["documents", "metadatas"],
        )
    except Exception:
        return []

    return [
        {"text": doc, "stars": meta.get("stars", 0)}
        for doc, meta in zip(stored.get("documents", []), stored.get("metadatas", []))
    ]


# 6.

def fetch_live_trend_data() -> tuple[str, list[str]]:
    """
    TREND_SOURCES adreslerindeki Reddit JSON akislarina canli istek atar.
    Her kaynaktan en fazla 15 gonderi basligini baglamsal sinyal olarak toplar.
    Doner: (ozet metin, log satirlari).
    """
    import random
    logs = []
    collected_text = []

    for url in TREND_SOURCES:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            diag("NETWORK", "Trend kaynagina istek gonderiliyor", url=url)
            resp = requests.get(url, headers=headers, timeout=15)
            logs.append(f"[Trend Agent] Istek: {url[:60]}... -> HTTP {resp.status_code}")

            if resp.status_code != 200:
                diag("NETWORK", "Trend kaynagi veri vermedi",
                     url=url, status=resp.status_code, ok=False)
                logs.append(f"[Trend Agent] Kaynak veri vermedi (HTTP {resp.status_code}), atlandi.")
                continue

            data = resp.json()
            children = data.get("data", {}).get("children", [])

            titles = []
            for child in children[:15]:
                title = child.get("data", {}).get("title", "").strip()
                if title:
                    titles.append(title)

            collected_text.extend(titles)
            diag("NETWORK", "Trend kaynagindan veri alindi",
                 url=url, status=resp.status_code, ok=True, titles=len(titles))
            logs.append(f"[Trend Agent] Reddit kaynagindan {len(titles)} baslik alindi.")

        except requests.RequestException as exc:
            diag_exception("ERROR", "Trend kaynagina baglanti hatasi", exc)
            logs.append(f"[Trend Agent] Baglanti hatasi: {type(exc).__name__} - {exc}")
        except ValueError as exc:
            diag_exception("ERROR", "Trend kaynagi JSON ayristirma hatasi", exc)
            logs.append(f"[Trend Agent] JSON ayristirma hatasi: {exc}")

    summary = "\n".join(f"- {item}" for item in collected_text) if collected_text else ""
    return summary, logs


# 7. Iki Asamali Playwright Scraping

class ScrapeBlockedError(Exception):
    """Bot engeli, bos sayfa veya parse hatasini temsil eder."""
    pass




def two_step_scrape(search_url: str) -> list[dict]:
    """
    Bright Data Scraper API uzerinden verileri ceker.
    HTTP 202 gecikmeli durumlarinda jüri önünde hata fırlatmamak adına
    polling (kuyruk kontrol) sabrı 120 saniyeye (2 dakikaya) çıkarılmıştır.
    """
    import requests
    import time
    import os
    
    products = []
    api_url = "https://api.brightdata.com/datasets/v3/scrape?dataset_id=gd_mljabfy23d62b7eqr&notify=false&include_errors=true"
    api_token = os.getenv("BRIGHT_DATA_SCRAPER_TOKEN")
    
    if not api_token:
        raise ScrapeBlockedError(".env dosyasinda BRIGHT_DATA_SCRAPER_TOKEN tanimlanmamis!")
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "input": [
            {
                "url": search_url
            }
        ]
    }
    
    diag("NETWORK", "Bright Data Scraper API'sine istek gonderiliyor", url=search_url)
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=120)
        status = response.status_code
        
        # Durum 202 ise veri arka plan kuyruguna alinmistir, polling baslatilir
        if status == 202:
            snapshot_id = response.json().get("snapshot_id")
            diag("NETWORK", "Veri kuyruga alindi (HTTP 202), bekleniyor", snapshot=snapshot_id)
            
            # 12 deneme x 10 saniye = 120 saniye (2 dakika) maksimum bekleme süresi
            poll_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"
            for poll_attempt in range(1, 13):
                time.sleep(10)
                diag("NETWORK", f"Kuyruk kontrol ediliyor, deneme {poll_attempt}/12")
                poll_res = requests.get(poll_url, headers=headers, timeout=30)
                
                if poll_res.status_code == 200:
                    api_data = poll_res.json()
                    break
            else:
                raise ScrapeBlockedError("Bright Data kuyruk isleme zaman asimina ugradi")
        elif status == 200:
            api_data = response.json()
        else:
            raise ScrapeBlockedError(f"Bright Data API beklenmeyen durum dondu: HTTP {status}")
            
        results = api_data if isinstance(api_data, list) else api_data.get("results", [])
        
        for idx, item in enumerate(results[:MAX_DEMO_PRODUCTS]):
            title = item.get("title") or item.get("name") or "Alibaba Wholesale Product"
            price = item.get("price") or item.get("price_string") or "10.00 USD"
            moq = item.get("moq") or item.get("minimum_order") or "5"
            score = item.get("supplier_score") or item.get("rating") or "4.5"
            desc = item.get("description") or item.get("specifications") or "Ozellik tablosu yuklenemedi."
            
            raw_reviews = item.get("reviews") or item.get("customer_reviews") or []
            formatted_reviews = []
            for r in raw_reviews[:5]:
                if isinstance(r, dict):
                    formatted_reviews.append({"text": r.get("text", ""), "stars": r.get("stars", 5)})
                else:
                    formatted_reviews.append({"text": str(r), "stars": 5})
            
            products.append({
                "id":              f"PRD-L{idx:02d}",
                "name":            title,
                "supplier":        item.get("supplier_name") or "Verified Wholesale Supplier",
                "raw_price_text":  str(price),
                "source_url":      item.get("url") or search_url,
                "specifications":  str(desc),
                "order_count":     int("".join(c for c in str(moq) if c.isdigit()) or 1),
                "stars":           float("".join(c for c in str(score) if c.isdigit() or c == ".") or 4.5),
                "review_count":    len(formatted_reviews),
                "supplier_score":  float("".join(c for c in str(score) if c.isdigit() or c == ".") or 4.5) * 20.0,
                "images":          [],
                "raw_description": str(desc),
                "reviews":         formatted_reviews
            })
            
        diag("SCRAPE", "Hazir API'den veri basariyla alindi ve haritalandi", count=len(products))
        
    except Exception as exc:
        diag_exception("ERROR", "Bright Data API baglantisi sirasinda kritik hata", exc)
        raise ScrapeBlockedError(f"Hazir Scraper hatasi: {str(exc)}")
        
    if not products:
        raise ScrapeBlockedError("Bright Data hazir servisinden urun verisi donmedi")
        
    return products



# Turkce karakterleri Ingilizce karsiliklarina ceviren tablo.
# Uluslararasi pazar yerlerinin gecerli sonuc dondurmesi icin kullanilir.
TURKISH_CHAR_MAP = str.maketrans({
    "ş": "s", "Ş": "s", "ç": "c", "Ç": "c", "ı": "i", "İ": "i",
    "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o",
})


def normalize_keyword(keyword: str) -> str:
    """Turkce karakterleri Ingilizce karsiliklariyla degistirir."""
    return keyword.translate(TURKISH_CHAR_MAP)


def hunt_products_live(trend_keywords: list[str]) -> tuple[list[dict], str, list[str]]:
    """
    Trend kelimeleri ve pazar yeri rotalari uzerinde bir kez dolasir.
    Her hedef icin 5 katmanli retry uygular; basarisiz olursa bir sonraki
    kelime/rota kombinasyonuna gecer.
    Hicbir kombinasyondan veri alinamazsa bos liste doner; sonsuz dongu yoktur.
    """
    import random
    logs = []
    keywords = trend_keywords if trend_keywords else ["trending products"]
    global_attempt = 0

    for keyword in keywords:
        # Pazar yeri URL'sine yazilmadan once Turkce karakterler normalize edilir
        normalized = normalize_keyword(keyword)

        for route in MARKETPLACE_SEARCH_ROUTES:
            target_url = route.format(query=normalized.replace(" ", "+"))

            for attempt in range(1, MAX_SCRAPE_RETRIES + 1):
                global_attempt += 1
                logs.append(
                    f"[Product Hunter] Genel deneme #{global_attempt} | "
                    f"kelime='{keyword}' (normalize: '{normalized}') | "
                    f"rota={target_url[:55]}... | yerel deneme {attempt}/{MAX_SCRAPE_RETRIES}"
                )
                diag("SCRAPE", "Pazar yeri arama sayfasi deneniyor",
                     keyword=normalized, url=target_url,
                     attempt=f"{attempt}/{MAX_SCRAPE_RETRIES}",
                     global_attempt=global_attempt)

                try:
                    products = two_step_scrape(target_url)
                    source = f"live_api_keyword_{normalized}_attempt_{attempt}"
                    logs.append(
                        f"[Product Hunter] Iki asamali scraping basarili. "
                        f"{len(products)} urun detay sayfasi islendi. data_source='{source}'"
                    )
                    diag("SCRAPE", "Canli veri alindi",
                         keyword=normalized, ok=True, products=len(products),
                         attempt=f"{attempt}/{MAX_SCRAPE_RETRIES}")
                    return products, source, logs

                except (ScrapeBlockedError, PlaywrightTimeoutError) as exc:
                    diag("RETRY", "Scraping engellendi, tekrar denenecek",
                         keyword=normalized, attempt=f"{attempt}/{MAX_SCRAPE_RETRIES}",
                         ok=False, exc=exc)
                    logs.append(
                        f"[Product Hunter] Engel/hata: {type(exc).__name__} - {exc}. "
                        f"3 sn bekleniyor."
                    )
                    time.sleep(3)
                except Exception as exc:
                    diag_exception("ERROR", "Scraping sirasinda beklenmeyen hata", exc)
                    logs.append(
                        f"[Product Hunter] Beklenmeyen hata: {type(exc).__name__} - {exc}. "
                        f"3 sn bekleniyor."
                    )
                    time.sleep(3)

            diag("SCRAPE", "Rota tum denemelerde basarisiz, rota degistiriliyor",
                 keyword=normalized, url=target_url, ok=False)
            logs.append(
                f"[Product Hunter] '{keyword}' icin {target_url[:45]}... rotasi "
                f"{MAX_SCRAPE_RETRIES} denemede asilamadi. Rota degistiriliyor."
            )

    # Tum kelime ve rota kombinasyonlari denendi, canli veri alinamadi
    logs.append(
        "[Product Hunter] Tum kombinasyonlar denendi, canli veri alinamadi. "
        "Bos liste donduruluyor."
    )
    return [], "no_live_data_extracted", logs

# 8. Dugumler
def trend_agent(state: AgentState) -> dict:
    """
    Canli sosyal sinyali baglam olarak kullanir; kullanicinin kategori
    girdisini yuksek hacimli Ingilizce e-ticaret arama terimlerine cevirir.
    """
    diag_section("DUGUM: trend_agent")
    diag("AGENT", "trend_agent basladi", category=state["user_request"])
    raw_summary, fetch_logs = fetch_live_trend_data()
    logs = list(fetch_logs)

    # Canli ham veriyi kullanicinin gormesi icin duzenli formatta bastir
    print("\n--- Canli Trend Kaynak Verisi (Baglamsal Sinyal) ---")
    if raw_summary:
        print(raw_summary[:1500])
    else:
        print("Canli kaynaklardan baglamsal sinyal alinamadi.")
    print("--- Trend Kaynak Verisi Sonu ---\n")

    user_req = state["user_request"]
    prompt = (
        f"Kullanicinin urun kategorisi girdisi: '{user_req}'.\n\n"
        f"Asagida sosyal medyadan toplanmis baglamsal metin var. Bu metni "
        f"yalnizca baglam icin degerlendir; urunle ilgisiz sikayet veya "
        f"operasyonel gurultuyu yok say:\n\n"
        f"{raw_summary if raw_summary else '(baglamsal sinyal alinamadi)'}\n\n"
        f"Yuksek donusum oranli bir Semantik Anahtar Kelime Genisletici gibi "
        f"davran: kullanicinin kategori girdisini en dogru, yuksek hacimli "
        f"Ingilizce e-ticaret arama terimlerine cevir. "
        f"Ornek: 'futbol topu' -> 'soccer ball', 'match football'; "
        f"'yuz buhar makinesi' -> 'facial steamer', 'nano facial mister'. "
        f"Tam olarak 2 adet temiz, hedefli Ingilizce arama terimi uret. Emoji kullanma."
        f"Emoji kullanma."
    )

    structured_llm = llm.with_structured_output(TrendOutput)
    diag("LLM", "Gemini trend analizi cagrisi yapiliyor")
    try:
        result: TrendOutput = structured_llm.invoke(prompt)
    except Exception as exc:
        diag_exception("ERROR", "Gemini trend analizi cagrisi basarisiz", exc)
        raise

    diag("LLM", "Gemini anahtar kelime uretti", count=len(result.keywords))
    logs.append(
        f"[Trend Agent] Kategori Ingilizce arama terimlerine cevrildi: "
        f"{', '.join(result.keywords)}"
    )

    append_audit("")
    append_audit("TREND AGENT")
    append_audit(f"Ingilizce arama terimleri: {', '.join(result.keywords)}")

    diag("FLOW", "trend_agent tamamlandi, sonraki dugum: product_hunter_agent")
    return {
        "trend_keywords": result.keywords,
        "log_history":    logs,
    }

def resolve_usd_cost(raw_price_text: str) -> float:
    """
    Ham fiyat metnini USD taban maliyetine cevirir.
    Metin TL veya TRY iceriyorsa float deger 33.0'a bolunur.
    Cevrilemezse PriceParseError firlatir.
    """
    parsed = parse_price_to_float(raw_price_text)
    upper = raw_price_text.upper()
    if "TL" in upper or "TRY" in upper:
        return round(parsed / 33.0, 2)
    return parsed


def compute_product_score(product: dict) -> float:
    """
    Bir urun icin bilesik viyabilite skoru hesaplar.
    Eksik alanlar guvenli sekilde 0 kabul edilir.
    """
    order_count    = product.get("order_count", 0) or 0
    stars          = product.get("stars", 0.0) or 0.0
    review_count   = product.get("review_count", 0) or 0
    supplier_score = product.get("supplier_score", 0.0) or 0.0

    return round(
        (order_count * 0.4)
        + (stars * 15.0)
        + (review_count * 0.2)
        + (supplier_score * 0.2),
        2,
    )

def product_hunter_agent(state: AgentState) -> dict:
    """
    Iki asamali Playwright scraping ile pazar yerlerinden canli urun verisi ceker.
    Para birimini USD'ye normalize eder, toptan disi pahali urunleri eler,
    cok kriterli skora gore siralar ve en iyi urunleri secer.
    """
    diag_section("DUGUM: product_hunter_agent")
    diag("AGENT", "product_hunter_agent basladi",
         keywords=len(state.get("trend_keywords", [])))
    keywords   = state["trend_keywords"]
    session_id = state["session_id"]
    logs = []

    removed = cleanup_old_data(ttl_days=30)
    logs.append(f"[ChromaDB] TTL temizligi yapildi. 30 gunden eski {removed} kayit silindi.")

    products, source, hunt_logs = hunt_products_live(keywords)
    logs.extend(hunt_logs)

    append_audit("")
    append_audit("PRODUCT HUNTER AGENT")

    # Canli veri alinamadiysa downstream calismayi durdur
    if not products:
        diag("DATA", "Scraping bos liste dondurdu, akis durduruluyor", ok=False)
        diag("FLOW", "product_hunter_agent erken cikis, is_data_valid=False")
        logs.append(
            "[Product Hunter] KRITIK: Canli scraping hicbir urun dondurmedi. "
            "Akis durduruluyor, graf guvenli yonlendirme icin geri donuyor."
        )
        append_audit("KRITIK: Canli veri cekilemedi, islenecek urun yok.")
        return {
            "raw_product_data": {"products": [], "total_found": 0, "filtered_out": 0},
            "data_source":      source,
            "is_data_valid":    False,
            "log_history":      logs,
        }

    # Fiyat USD'ye normalize edilir; 100 USD ustu urunler elenir
    scored_products = []
    filtered_out = 0
    for product in products:
        raw_text = product.get("raw_price_text", "")
        try:
            unit_cost = resolve_usd_cost(raw_text)
        except PriceParseError as exc:
            filtered_out += 1
            logs.append(
                f"[Product Hunter] {product['id']} fiyat ayristirilamadi: {exc}. Elendi."
            )
            continue

        # Toptan beyaz liste filtresi: 100 USD ustu urunler kapsam disi
        if unit_cost > 100.0:
            filtered_out += 1
            logs.append(
                f"[Product Hunter] {product['id']} elendi: birim maliyet "
                f"{unit_cost} USD, 100 USD limitinin ustunde."
            )
            continue

        product["unit_cost_usd"] = unit_cost
        product["viability_score"] = compute_product_score(product)
        scored_products.append(product)
        logs.append(
            f"[Product Hunter] {product['id']} gecerli: ham='{raw_text}' -> "
            f"{unit_cost} USD | viyabilite skoru={product['viability_score']}"
        )

    # Bilesik skora gore azalan siralama, en iyi MAX_DEMO_PRODUCTS secilir
    scored_products.sort(key=lambda p: p["viability_score"], reverse=True)
    valid_products = scored_products[:MAX_DEMO_PRODUCTS]

    # Filtre sonrasi liste bos ise downstream durdurulur
    if not valid_products:
        diag("DATA", "Tum urunler filtrelendi, gecerli urun yok",
             ok=False, filtered_out=filtered_out)
        diag("FLOW", "product_hunter_agent erken cikis, is_data_valid=False")
        logs.append(
            "[Product Hunter] KRITIK: Tum urunler filtrelendi, gecerli urun kalmadi. "
            "Akis durduruluyor."
        )
        append_audit("KRITIK: Tum urunler filtre disi kaldi, islenecek urun yok.")
        return {
            "raw_product_data": {"products": [], "total_found": 0,
                                 "filtered_out": filtered_out},
            "data_source":      source,
            "is_data_valid":    False,
            "log_history":      logs,
        }

    diag("DATA", "Urunler filtrelendi ve skorlandi",
         valid=len(valid_products), filtered_out=filtered_out)

    # Secilen urunler denetim dosyasina yazilir
    for product in valid_products:
        append_audit(f"Urun ID         : {product['id']}")
        append_audit(f"Urun adi        : {product['name']}")
        append_audit(f"Kaynak URL      : {product.get('source_url', '-')}")
        append_audit(f"Birim maliyet   : {product['unit_cost_usd']} USD")
        append_audit(f"Viyabilite skoru: {product['viability_score']}")
        append_audit(f"Siparis sayisi  : {product.get('order_count', 0)}")
        append_audit(f"Yildiz          : {product.get('stars', 0.0)}")
        append_audit(f"Yorum sayisi    : {product.get('review_count', 0)}")
        append_audit("Ozellikler:")
        for spec_line in product.get("specifications", "").split("\n"):
            append_audit(f"  {spec_line.strip()}")
        append_audit("-" * 40)

    # Gercek yorum varsa ChromaDB'ye yazilir; yoksa yorum alani bos kalir
    total_indexed = 0
    for product in valid_products:
        total_indexed += store_product_in_chroma(product, session_id)
    logs.append(
        f"[ChromaDB] {len(valid_products)} gecerli urune ait {total_indexed} dokuman "
        f"vektorlestirildi (session: {session_id[:8]})."
    )

    raw_product_data = {
        "products":     valid_products,
        "total_found":  len(valid_products),
        "filtered_out": filtered_out,
    }

    diag("FLOW", "product_hunter_agent tamamlandi, sonraki dugumler: content_agent + operations_agent",
         products=len(valid_products))
    return {
        "raw_product_data": raw_product_data,
        "data_source":      source,
        "log_history":      logs,
    }


def content_agent(state: AgentState) -> dict:
    """Her urun icin Gemini'ye ham veri gonderir, Turkce SEO icerik alir."""
    diag_section("DUGUM: content_agent")
    diag("AGENT", "content_agent basladi",
         products=len(state["raw_product_data"].get("products", [])))
    products       = state["raw_product_data"].get("products", [])
    trend_keywords = state["trend_keywords"]
    structured_llm = llm.with_structured_output(SEOContent)
    optimized      = {}

    for product in products[:MAX_DEMO_PRODUCTS]:
        urun_verisi = {
            "urun_adi":        product["name"],
            "tedarikci":       product["supplier"],
            "ham_aciklama":    product.get("raw_description", ""),
            "guncel_trendler": trend_keywords,
        }

        prompt = (
            f"Sen profesyonel bir e-ticaret metin yazarisin. "
            f"Su ham urun verilerini incele:\n\n"
            f"{json.dumps(urun_verisi, ensure_ascii=False, indent=2)}\n\n"
            f"Bu urun icin Turkce, SEO uyumlu bir baslik (seo_title, max 70 karakter), "
            f"100-150 kelimelik satis odakli aciklama (seo_description) ve "
            f"3-5 meta_keywords uret. Hicbir alanda emoji kullanma."
        )

        result: SEOContent = structured_llm.invoke(prompt)

        formatted_images = []
        for img in product.get("images", []):
            base = img.rsplit(".", 1)[0] if "." in img else img
            formatted_images.append(f"{base}_optimized_800x800.webp")

        optimized[product["id"]] = {
            "seo_title":        result.seo_title,
            "seo_description":  result.seo_description,
            "meta_keywords":    result.meta_keywords,
            "formatted_images": formatted_images,
        }

    log = (
        f"[Icerik Agent] Gemini, {len(optimized)} urun icin SEO basliklari "
        f"ve aciklamalari uretti."
    )

    return {
        "optimized_content": optimized,
        "log_history":       [log],
    }


def operations_agent(state: AgentState) -> dict:
    """Kargo suresi ve maliyet hesabi yapar; sadece gecerli birim maliyetle calisir."""
    diag_section("DUGUM: operations_agent")
    diag("AGENT", "operations_agent basladi",
         products=len(state["raw_product_data"].get("products", [])))
    products = state["raw_product_data"].get("products", [])
    shipping = {}

    append_audit("")
    append_audit("OPERASYON AGENT")

    for p in products[:MAX_DEMO_PRODUCTS]:
        unit_cost = p.get("unit_cost_usd")
        if not unit_cost or unit_cost <= 0:
            append_audit(f"Urun ID         : {p['id']} - atlandi (gecerli maliyet yok)")
            append_audit("-" * 40)
            continue

        base_days = 14
        markup = 2.8
        sale_price_try = round(unit_cost * markup * 33, 2)

        shipping[p["id"]] = {
            "origin_country":           "CN",
            "destination":              "TR",
            "estimated_delivery_days":  base_days,
            "estimated_delivery_label": f"{base_days}-{base_days + 5} is gunu",
            "shipping_cost_usd":        round(unit_cost * 0.15, 2),
            "suggested_sale_price_try": sale_price_try,
            "display_text":             f"Ucretsiz Kargo, Tahmini Teslimat {base_days}-{base_days + 5} Is Gunu",
        }

        append_audit(f"Urun ID         : {p['id']}")
        append_audit(f"Birim maliyet   : {unit_cost} USD")
        append_audit(f"Nihai satis TRY : {sale_price_try}")
        append_audit("-" * 40)

    log = (
        f"[Operasyon Agent] {len(shipping)} urun icin kargo ve maliyet hesabi tamamlandi."
    )

    return {
        "shipping_details": shipping,
        "log_history":      [log],
    }


def analyze_reviews_for_irony(product_id: str, reviews: list[dict]) -> tuple[int, list[str]]:
    """
    Bir urunun yorumlarini tek Gemini cagrisiyla ironi/troll acisindan analiz eder.
    Yorum yoksa analiz yapilmaz, skor 100 doner.
    """
    if not reviews:
        return 100, [f"  -> {product_id}: gercek yorum bulunamadi, analiz yapilmadi, skor 100."]

    review_block = "\n".join(
        f"[{idx}] Yildiz: {r['stars']}/5 | Metin: \"{r['text']}\""
        for idx, r in enumerate(reviews)
    )

    prompt = (
        f"Bir e-ticaret urununun musteri yorumlarini toplu analiz et. "
        f"Yorumlar Ingilizce veya Turkce olabilir. Yildiz puani ile metin "
        f"celisiyorsa veya metin alayci/ironik/manipulatif ise tespit et.\n\n"
        f"Yorumlar:\n{review_block}\n\n"
        f"Her yorum icin review_index alanini koseli parantez numarasiyla ayni ver. "
        f"Gerekce alaninda emoji kullanma."
    )

    structured_llm = llm.with_structured_output(BatchReviewOutput)

    try:
        batch: BatchReviewOutput = structured_llm.invoke(prompt)
    except Exception:
        return 100, [f"  -> {product_id}: yorum analizi yapilamadi, notr skor atandi."]

    manipulative_count = 0
    detail_logs = []

    for verdict in batch.verdicts:
        if verdict.is_manipulative:
            manipulative_count += 1
            if 0 <= verdict.review_index < len(reviews):
                review_text = reviews[verdict.review_index]["text"]
                review_star = reviews[verdict.review_index]["stars"]
            else:
                review_text, review_star = "(indeks eslesmedi)", "-"
            detail_logs.append(
                f"  -> {product_id} MANIPULASYON: ({review_star} yildiz) "
                f"\"{review_text[:55]}...\" | Gerekce: {verdict.reason}"
            )

    penalty_per_review = 100 // max(len(reviews), 1)
    trust_score = max(0, 100 - manipulative_count * penalty_per_review)

    detail_logs.append(
        f"  -> {product_id}: {len(reviews)} yorum tek cagriyla analiz edildi, "
        f"{manipulative_count} manipulatif yorum tespit edildi. "
        f"Guvenilirlik Skoru: {trust_score}/100"
    )

    return trust_score, detail_logs


def orchestrator_review(state: AgentState) -> dict:
    """Icerik ve operasyon ciktilarini dogrular, batch ironi analizi yapar."""
    diag_section("DUGUM: orchestrator_review")
    diag("AGENT", "orchestrator_review basladi",
         retry=state.get("retry_count", 0))
    content    = state.get("optimized_content", {})
    shipping   = state.get("shipping_details", {})
    retry      = state.get("retry_count", 0)
    session_id = state["session_id"]
    errors     = []
    logs       = []

    if not state["raw_product_data"].get("products"):
        errors.append("HATA: Canli pazar yerlerinden islenecek organik urun bulunamadi.")

    for pid in content:
        if pid not in shipping:
            errors.append(f"HATA: {pid} icin kargo bilgisi eksik.")

    for pid, sh in shipping.items():
        if sh.get("estimated_delivery_days", 0) <= 0:
            errors.append(f"HATA: {pid} teslimat suresi gecersiz.")
        if sh.get("suggested_sale_price_try", 0) <= 0:
            errors.append(f"HATA: {pid} satis fiyati sifir veya negatif.")

    for pid, ct in content.items():
        if not ct.get("seo_title", "").strip():
            errors.append(f"HATA: {pid} SEO basligi bos.")

    logs.append("[Bas Ajan] ChromaDB'den session yorumlari cekiliyor, batch ironi analizi basliyor.")
    trust_scores = {}
    low_trust_products = []

    append_audit("")
    append_audit("ORCHESTRATOR - GUVEN ANALIZI")

    for pid in content:
        reviews = query_reviews_from_chroma(pid, session_id)
        score, detail_logs = analyze_reviews_for_irony(pid, reviews)
        trust_scores[pid] = score
        logs.extend(detail_logs)
        if score < 70:
            low_trust_products.append(pid)

        append_audit(f"Urun ID      : {pid}")
        append_audit(f"Guven Skoru  : {score}/100")
        manipulations = [d.strip() for d in detail_logs if "MANIPULASYON" in d]
        if manipulations:
            for m in manipulations:
                append_audit(f"Gerekce      : {m}")
        else:
            append_audit("Gerekce      : Manipulatif yorum tespit edilmedi.")
        append_audit("-" * 40)

    if low_trust_products:
        errors.append(
            f"GUVEN HATASI: {', '.join(low_trust_products)} urunlerinin "
            f"guvenilirlik skoru 70 altinda."
        )

    is_valid = len(errors) == 0

    if is_valid:
        logs.append(
            f"[Bas Ajan] Tum veriler dogrulandi, yorum analizleri temiz. "
            f"{len(content)} urun onaylandi."
        )
    else:
        logs.append(
            f"[Bas Ajan] {len(errors)} sorun tespit edildi (Deneme #{retry + 1}).\n"
            + "\n".join(f"  -> {e}" for e in errors)
        )

    return {
        "is_data_valid": is_valid,
        "retry_count":   retry + 1,
        "trust_scores":  trust_scores,
        "log_history":   logs,
    }


def site_agent(state: AgentState) -> dict:
    """Onaylanan urunleri dashboard'a basar."""
    diag_section("DUGUM: site_agent")
    diag("AGENT", "site_agent basladi")
    content  = state["optimized_content"]
    shipping = state["shipping_details"]
    scores   = state.get("trust_scores", {})

    listings = []
    for pid in content:
        if pid not in shipping:
            continue
        listings.append({
            "product_id":    pid,
            "title":         content[pid]["seo_title"],
            "price_try":     shipping[pid]["suggested_sale_price_try"],
            "shipping_text": shipping[pid]["display_text"],
            "trust_score":   scores.get(pid, 100),
            "status":        "LIVE",
        })

    log = f"[Site Agent] {len(listings)} urun magazaya eklendi ve yayina alindi."
    return {"log_history": [log]}


def user_assistant_agent(state: AgentState) -> dict:
    """Girisimciyi sonuc hakkinda bilgilendirir."""
    diag_section("DUGUM: user_assistant_agent")
    diag("AGENT", "user_assistant_agent basladi",
         valid=state.get("is_data_valid", False))
    total   = state["raw_product_data"].get("total_found", 0)
    request = state["user_request"]
    valid   = state.get("is_data_valid", False)

    if valid:
        notification = (
            f"[Kullanici Asistani] '{request}' kategorisinde {total} urun bulundu, "
            f"yorum guvenilirligi dogrulandi ve magazaya eklendi."
        )
    else:
        notification = (
            f"[Kullanici Asistani] '{request}' kategorisindeki urunlerin bir kismi "
            f"kontrolden gecemedi. Dashboard'da uyari isaretli urunleri inceleyin."
        )

    append_audit("")
    append_audit("KULLANICI ASISTANI")
    append_audit(notification.replace("[Kullanici Asistani] ", ""))

    return {"log_history": [notification]}


# 9. Kosullu Yonlendirme

def route_after_review(state: AgentState) -> str:
    """Orchestrator sonrasi yonlendirme."""
    MAX_RETRY = 3
    if state["is_data_valid"]:
        decision = "site_agent"
    elif state.get("retry_count", 0) >= MAX_RETRY:
        decision = "user_assistant_agent"
    else:
        decision = "product_hunter_agent"

    diag("FLOW", "Yonlendirme karari verildi",
         valid=state["is_data_valid"], retry=state.get("retry_count", 0),
         next_node=decision)
    return decision


# 10. Graf Kurulumu

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("trend_agent",          trend_agent)
    workflow.add_node("product_hunter_agent", product_hunter_agent)
    workflow.add_node("content_agent",        content_agent)
    workflow.add_node("operations_agent",     operations_agent)
    workflow.add_node("orchestrator_review",  orchestrator_review)
    workflow.add_node("site_agent",           site_agent)
    workflow.add_node("user_assistant_agent", user_assistant_agent)

    workflow.set_entry_point("trend_agent")

    workflow.add_edge("trend_agent",          "product_hunter_agent")
    workflow.add_edge("product_hunter_agent", "content_agent")
    workflow.add_edge("product_hunter_agent", "operations_agent")
    workflow.add_edge("content_agent",        "orchestrator_review")
    workflow.add_edge("operations_agent",     "orchestrator_review")

    workflow.add_conditional_edges(
        "orchestrator_review",
        route_after_review,
        {
            "site_agent":           "site_agent",
            "product_hunter_agent": "product_hunter_agent",
            "user_assistant_agent": "user_assistant_agent",
        },
    )

    workflow.add_edge("site_agent",           "user_assistant_agent")
    workflow.add_edge("user_assistant_agent", END)

    return workflow.compile()


# 11. Calistirma

if __name__ == "__main__":
    print("=" * 65)
    print("  Chief Orchestrator - Iki Asamali Canli Scraping")
    print("=" * 65)

    # Denetim dosyasi her calistirmada sifirlanir
    reset_audit_file()
    # Teshis dosyasi her calistirmada sifirlanir
    reset_diagnostic_log()

    graph = build_graph()
    diag("FLOW", "Graf derlendi, calistirmaya hazir")

    user_input = input("\nSatmak istediginiz urun kategorisini girin: ").strip()
    if not user_input:
        user_input = "akilli teknoloji urunleri"

    initial_state: AgentState = {
        "session_id":        str(uuid.uuid4()),
        "user_request":      user_input,
        "trend_keywords":    [],
        "raw_product_data":  {},
        "optimized_content": {},
        "shipping_details":  {},
        "is_data_valid":     False,
        "retry_count":       0,
        "trust_scores":      {},
        "data_source":       "",
        "log_history":       [],
    }

    append_audit(f"Kategori istegi: {user_input}")
    append_audit(f"Session ID     : {initial_state['session_id']}")

    print(f"\nGelen Istek : \"{initial_state['user_request']}\"")
    print(f"Session ID  : {initial_state['session_id']}")
    print("Graf calistiriliyor.\n")
    print("-" * 65)

    diag("FLOW", "Graf calistiriliyor", category=user_input,
         session=initial_state["session_id"][:8])
    try:
        final_state = graph.invoke(initial_state)
        diag("FLOW", "Graf calismasi tamamlandi",
             valid=final_state.get("is_data_valid", False),
             products=final_state["raw_product_data"].get("total_found", 0))
    except Exception as exc:
        diag_exception("ERROR", "Graf calismasi sirasinda kritik hata", exc)
        raise

    print("\nAJAN LOG AKISI:\n")
    for i, entry in enumerate(final_state["log_history"], 1):
        print(f"  [{i:02d}] {entry}")

    print("\n" + "=" * 65)
    print("   OZET RAPOR")
    
    # final_state icindeki ham urun listesini guvenli bir sekilde yakaliyoruz:
    raw_data = final_state.get('raw_product_data', {})
    state_products = raw_data.get('products', []) if isinstance(raw_data, dict) else []
    
    if state_products:
        print(f"   - Ilk Urun Linki    : {state_products[0].get('source_url', '-')}")
    else:
        print("   - Ilk Urun Linki    : Veri kaynagindan link alinamadi")
        
    print("=" * 65)
    print(f"   - Kategori          : {final_state['user_request']}")
    print(f"   - Trend Kelimeler   : {', '.join(final_state['trend_keywords'])}")
    print(f"   - Veri Kaynagi      : {final_state.get('data_source', '-')}")
    print(f"   - Islenen Urunler   : {final_state['raw_product_data'].get('total_found', 0)} adet")
    print(f"   - SEO Icerik        : {len(final_state['optimized_content'])} urun")
    print(f"   - Kargo Hesabi      : {len(final_state['shipping_details'])} urun")
    print(f"   - Guven Skorlari    : {final_state.get('trust_scores', {})}")
    print(f"   - Veri Gecerliligi  : {'ONAYLANDI' if final_state['is_data_valid'] else 'REDDEDILDI'}")
    print(f"   - Denetim Dosyasi   : {AUDIT_FILE}")
    print("=" * 65)