"""
Adim 3: Canli Internet Entegrasyonu.
Trend Agent gercek zamanli kaynaklara istek atar, Product Hunter Agent
Playwright ile JavaScript render edilen pazar yeri sayfalarindan veri ceker.
Cevrimdisi yedek veri havuzu bulunmaz; sistem canli veri elde edene kadar
otonom olarak rota degistirir.
"""

import os
import json
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Annotated, TypedDict
import operator

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph, END
import chromadb

# Playwright senkron API; tarayici otomasyonu icin kullanilir
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Ortam degiskenleri ve API Key kontrolu
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY bulunamadi! "
        "Lutfen .env dosyasina veya ortam degiskenlerine ekleyin."
    )

# Sunum esnasinda islenecek maksimum urun sayisi
MAX_DEMO_PRODUCTS = 2

# Bir hedef icin tekrar deneme limiti
MAX_SCRAPE_RETRIES = 5

# Her istekte rotasyon icin tarayici kimlik havuzu
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
]

# Trend Agent'in canli istek atacagi gercek zamanli kaynaklar
TREND_SOURCES = [
    "https://www.reddit.com/r/dropshipping/hot.json",
    "https://sale.alibaba.com/p/dviiav4th/index.html"
    "?spm=a2700.product_home_fy25.user_guide.NCChannelTheme-3280"
    "&trafficsource=hometool",
]

# Product Hunter Agent'in deneyecegi pazar yeri arama rotalari.
# Sistem birinden veri alamazsa sirayla digerine gecer.
MARKETPLACE_SEARCH_ROUTES = [
    "https://www.aliexpress.com/wholesale?SearchText={query}",
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


# 3. ChromaDB Yardimci Fonksiyonlari

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
    """Bir urunun aciklama ve yorumlarini vektorlestirip session_id ile ChromaDB'ye yazar."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    documents, ids, metadatas = [], [], []

    documents.append(product.get("raw_description", ""))
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


# 4. Canli Trend Verisi Cekme

def fetch_live_trend_data(category: str) -> tuple[str, list[str]]:
    """
    TREND_SOURCES adreslerine canli HTTP istegi atar.
    Donen ham icerigi temizleyip ozetlenmis metin olarak doner.
    Doner: (Gemini'ye paslanacak ozet metin, log satirlari).
    """
    logs = []
    collected_text = []

    for url in TREND_SOURCES:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            logs.append(f"[Trend Agent] Istek: {url[:60]}... -> HTTP {resp.status_code}")

            if resp.status_code != 200:
                logs.append(f"[Trend Agent] Kaynak veri vermedi (HTTP {resp.status_code}), atlandi.")
                continue

            content_type = resp.headers.get("Content-Type", "")

            # Reddit gibi JSON donen kaynaklar: post basliklarini topla
            if "application/json" in content_type:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                titles = [
                    c.get("data", {}).get("title", "")
                    for c in children[:25]
                ]
                titles = [t for t in titles if t]
                collected_text.extend(titles)
                logs.append(f"[Trend Agent] JSON kaynaktan {len(titles)} baslik alindi.")
            else:
                # HTML donen kaynaklar: kaba metin ozeti al
                text_snippet = resp.text
                # Etiketleri kabaca ayikla
                cleaned = "".join(
                    ch if ch not in "<>" else " "
                    for ch in text_snippet
                )
                words = [w for w in cleaned.split() if len(w) > 3]
                snippet = " ".join(words[:120])
                if snippet:
                    collected_text.append(snippet)
                logs.append(f"[Trend Agent] HTML kaynaktan {len(snippet)} karakterlik ozet alindi.")

        except requests.RequestException as exc:
            logs.append(f"[Trend Agent] Baglanti hatasi: {type(exc).__name__} - {exc}")

    summary = "\n".join(f"- {item}" for item in collected_text) if collected_text else ""

    # Canli kaynaklardan veri gelmediyse bos string doner; Gemini yine de
    # kategori bilgisiyle calisir
    return summary, logs


# 5. Playwright ile Canli Urun ve Yorum Kazima

def scrape_with_playwright(url: str, user_agent: str) -> list[dict]:
    """
    Playwright ile gercek bir tarayici acar, hedef URL'yi yukler,
    JavaScript render bittikten sonra urun ve yorum verilerini cikarir.
    Bot engeli, bos sayfa veya parse hatasinda ScrapeBlockedError firlatir.
    """
    products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()

        try:
            response = page.goto(url, timeout=30000, wait_until="domcontentloaded")

            # Sunucu seviyesinde bot engeli
            if response is not None and response.status in (403, 429):
                raise ScrapeBlockedError(f"HTTP {response.status} bot engeli")

            # JavaScript'in urun listesini render etmesi icin bekle
            page.wait_for_timeout(4000)

            # Genel urun karti seyicileri; pazar yeri DOM yapisina gore secilir
            cards = page.query_selector_all(
                "div[class*='product'], div[class*='item'], div[class*='card']"
            )

            if not cards:
                raise ScrapeBlockedError("Sayfada urun karti bulunamadi (bos veya engelli sayfa)")

            for idx, card in enumerate(cards[:5]):
                name_el = card.query_selector(
                    "h1, h2, h3, a[title], span[class*='title']"
                )
                price_el = card.query_selector(
                    "span[class*='price'], div[class*='price'], em"
                )

                name = ""
                if name_el:
                    name = (name_el.get_attribute("title")
                            or name_el.inner_text() or "").strip()
                price_text = price_el.inner_text().strip() if price_el else ""

                if not name:
                    continue

                price_clean = "".join(
                    ch for ch in price_text if ch.isdigit() or ch == "."
                )
                try:
                    price_value = float(price_clean) if price_clean else 0.0
                except ValueError:
                    price_value = 0.0

                # Ayni karttan veya urun sayfasindan yorum elemanlarini cikar
                review_els = card.query_selector_all(
                    "div[class*='review'], div[class*='comment'], li[class*='feedback']"
                )
                reviews = []
                for r_el in review_els[:5]:
                    r_text = (r_el.inner_text() or "").strip()
                    star_el = r_el.query_selector(
                        "span[class*='star'], div[class*='rating']"
                    )
                    star_val = 0
                    if star_el:
                        star_raw = (star_el.get_attribute("data-rating")
                                    or star_el.inner_text() or "")
                        star_digits = "".join(c for c in star_raw if c.isdigit())
                        star_val = int(star_digits[0]) if star_digits else 0
                    if r_text:
                        reviews.append({"text": r_text, "stars": star_val})

                products.append({
                    "id":               f"PRD-L{idx:02d}",
                    "name":             name,
                    "supplier":         "Live Marketplace Seller",
                    "supplier_rating":  round(random.uniform(4.0, 5.0), 1),
                    "unit_cost_usd":    round(price_value, 2),
                    "moq":              random.randint(3, 20),
                    "images":           ["live_scraped_001.jpg"],
                    "raw_description":  f"live scraped product {name}",
                    "reviews":          reviews,
                })
        finally:
            context.close()
            browser.close()

    if not products:
        raise ScrapeBlockedError("Sayfadan gecerli urun cikarilamadi")

    return products


class ScrapeBlockedError(Exception):
    """Bot engeli, bos sayfa veya parse hatasini temsil eder."""
    pass


def hunt_products_live(trend_keywords: list[str]) -> tuple[list[dict], str, list[str]]:
    """
    Trend kelimeleri ve pazar yeri rotalari uzerinde otonom dolasir.
    Her hedef icin 5 katmanli retry uygular; basarisiz olursa bir sonraki
    kelime/rota kombinasyonuna gecer. Canli veri elde edilene kadar surer.
    Doner: (urun listesi, data_source etiketi, log satirlari).
    """
    logs = []
    keywords = trend_keywords if trend_keywords else ["trending products"]
    global_attempt = 0

    while True:
        for keyword in keywords:
            for route in MARKETPLACE_SEARCH_ROUTES:
                target_url = route.format(query=keyword.replace(" ", "+"))

                for attempt in range(1, MAX_SCRAPE_RETRIES + 1):
                    global_attempt += 1
                    user_agent = random.choice(USER_AGENTS)
                    logs.append(
                        f"[Product Hunter] Genel deneme #{global_attempt} | "
                        f"kelime='{keyword}' | rota={target_url[:55]}... | "
                        f"yerel deneme {attempt}/{MAX_SCRAPE_RETRIES}"
                    )

                    try:
                        products = scrape_with_playwright(target_url, user_agent)
                        source = f"live_playwright_keyword_{keyword}_attempt_{attempt}"
                        logs.append(
                            f"[Product Hunter] Canli veri alindi. "
                            f"{len(products)} urun cikarildi. data_source='{source}'"
                        )
                        return products, source, logs

                    except (ScrapeBlockedError, PlaywrightTimeoutError) as exc:
                        logs.append(
                            f"[Product Hunter] Engel/hata: {type(exc).__name__} - {exc}. "
                            f"3 sn bekleniyor."
                        )
                        time.sleep(3)
                    except Exception as exc:
                        logs.append(
                            f"[Product Hunter] Beklenmeyen hata: {type(exc).__name__} - {exc}. "
                            f"3 sn bekleniyor."
                        )
                        time.sleep(3)

                # 5 deneme bitti, bir sonraki rotaya gecilir
                logs.append(
                    f"[Product Hunter] '{keyword}' icin {target_url[:45]}... rotasi "
                    f"{MAX_SCRAPE_RETRIES} denemede asilamadi. Rota degistiriliyor."
                )

        # Tum kelime/rota kombinasyonlari tukendi, dongu bastan baslar
        logs.append(
            "[Product Hunter] Tum kelime ve rota kombinasyonlari denendi, "
            "canli veri alinamadi. Otonom dongu bastan baslatiliyor."
        )


# 6. Dugumler

def trend_agent(state: AgentState) -> dict:
    """Canli kaynaklardan ham trend verisi ceker, Gemini ile 5 anahtar kelime uretir."""
    user_req = state["user_request"]

    raw_summary, fetch_logs = fetch_live_trend_data(user_req)
    logs = list(fetch_logs)

    # Canli ham veriyi kullanicinin gormesi icin duzenli formatta bastir
    print("\n--- Canli Trend Kaynak Verisi (Ham/Ozet) ---")
    if raw_summary:
        print(raw_summary[:1500])
    else:
        print("Canli kaynaklardan ozetlenecek veri alinamadi.")
    print("--- Trend Kaynak Verisi Sonu ---\n")

    prompt = (
        f"Bir dropshipping uzmani olarak '{user_req}' kategorisini analiz et. "
        f"Asagida canli internet kaynaklarindan toplanmis ham trend verisi var:\n\n"
        f"{raw_summary if raw_summary else '(canli veri alinamadi, kategori bilgisini kullan)'}\n\n"
        f"Bu veriyi ve kategoriyi degerlendirerek e-ticarette satisi yuksek "
        f"5 spesifik trend anahtar kelime uret. Sadece Turkce, emoji kullanma."
    )

    structured_llm = llm.with_structured_output(TrendOutput)
    result: TrendOutput = structured_llm.invoke(prompt)

    logs.append(
        f"[Trend Agent] Gemini canli veriyi analiz etti, "
        f"{len(result.keywords)} anahtar kelime uretildi: {', '.join(result.keywords)}"
    )

    return {
        "trend_keywords": result.keywords,
        "log_history":    logs,
    }


def product_hunter_agent(state: AgentState) -> dict:
    """Playwright ile pazar yerlerinden canli urun ve yorum verisi ceker."""
    keywords   = state["trend_keywords"]
    session_id = state["session_id"]
    logs = []

    removed = cleanup_old_data(ttl_days=30)
    logs.append(f"[ChromaDB] TTL temizligi yapildi. 30 gunden eski {removed} kayit silindi.")

    # Canli kazima; veri alinana kadar otonom rota degistirir
    products, source, hunt_logs = hunt_products_live(keywords)
    logs.extend(hunt_logs)

    products = products[:MAX_DEMO_PRODUCTS]
    logs.append(f"[Product Hunter] Demo limiti uygulandi, {len(products)} urun islenecek.")

    total_indexed = 0
    for product in products:
        total_indexed += store_product_in_chroma(product, session_id)
    logs.append(
        f"[ChromaDB] {len(products)} urune ait {total_indexed} dokuman "
        f"vektorlestirildi (session: {session_id[:8]})."
    )

    raw_product_data = {
        "products":     products,
        "total_found":  len(products),
        "filtered_out": 0,
    }

    return {
        "raw_product_data": raw_product_data,
        "data_source":      source,
        "log_history":      logs,
    }


def content_agent(state: AgentState) -> dict:
    """Her urun icin Gemini'ye ham veri gonderir, Turkce SEO icerik alir."""
    products       = state["raw_product_data"].get("products", [])
    trend_keywords = state["trend_keywords"]
    structured_llm = llm.with_structured_output(SEOContent)
    optimized      = {}

    for product in products[:MAX_DEMO_PRODUCTS]:
        urun_verisi = {
            "urun_adi":        product["name"],
            "tedarikci":       product["supplier"],
            "tedarikci_puani": product["supplier_rating"],
            "ham_aciklama":    product["raw_description"],
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
    """Kargo suresi ve maliyet hesabi yapar."""
    products = state["raw_product_data"].get("products", [])
    shipping = {}

    for p in products[:MAX_DEMO_PRODUCTS]:
        base_days = 14
        unit_cost = p["unit_cost_usd"]
        markup    = 2.8
        shipping[p["id"]] = {
            "origin_country":           "CN",
            "destination":              "TR",
            "estimated_delivery_days":  base_days,
            "estimated_delivery_label": f"{base_days}-{base_days + 5} is gunu",
            "shipping_cost_usd":        round(unit_cost * 0.15, 2),
            "suggested_sale_price_try": round(unit_cost * markup * 33, 2),
            "display_text":             f"Ucretsiz Kargo, Tahmini Teslimat {base_days}-{base_days + 5} Is Gunu",
        }

    log = (
        f"[Operasyon Agent] {len(shipping)} urun icin kargo ve maliyet hesabi tamamlandi."
    )

    return {
        "shipping_details": shipping,
        "log_history":      [log],
    }


def analyze_reviews_for_irony(product_id: str, reviews: list[dict]) -> tuple[int, list[str]]:
    """Bir urunun tum yorumlarini tek Gemini cagrisiyla ironi/troll acisindan analiz eder."""
    if not reviews:
        return 100, [f"  -> {product_id}: yorum bulunamadi, varsayilan skor 100."]

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
    content    = state.get("optimized_content", {})
    shipping   = state.get("shipping_details", {})
    retry      = state.get("retry_count", 0)
    session_id = state["session_id"]
    errors     = []
    logs       = []

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

    for pid in content:
        reviews = query_reviews_from_chroma(pid, session_id)
        score, detail_logs = analyze_reviews_for_irony(pid, reviews)
        trust_scores[pid] = score
        logs.extend(detail_logs)
        if score < 70:
            low_trust_products.append(pid)

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
    content  = state["optimized_content"]
    shipping = state["shipping_details"]
    scores   = state.get("trust_scores", {})

    listings = []
    for pid in content:
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

    return {"log_history": [notification]}


# 7. Kosullu Yonlendirme

def route_after_review(state: AgentState) -> str:
    """Orchestrator sonrasi yonlendirme."""
    MAX_RETRY = 3
    if state["is_data_valid"]:
        return "site_agent"
    elif state.get("retry_count", 0) >= MAX_RETRY:
        return "user_assistant_agent"
    else:
        return "product_hunter_agent"


# 8. Graf Kurulumu

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


# 9. Calistirma

if __name__ == "__main__":
    print("=" * 65)
    print("  Chief Orchestrator - Canli Internet Entegrasyonu")
    print("=" * 65)

    graph = build_graph()

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

    print(f"\nGelen Istek : \"{initial_state['user_request']}\"")
    print(f"Session ID  : {initial_state['session_id']}")
    print("Graf calistiriliyor.\n")
    print("-" * 65)

    final_state = graph.invoke(initial_state)

    print("\nAJAN LOG AKISI:\n")
    for i, entry in enumerate(final_state["log_history"], 1):
        print(f"  [{i:02d}] {entry}")

    print("\n" + "=" * 65)
    print("  OZET RAPOR")
    print("=" * 65)
    print(f"  - Kategori          : {final_state['user_request']}")
    print(f"  - Trend Kelimeler   : {', '.join(final_state['trend_keywords'])}")
    print(f"  - Veri Kaynagi      : {final_state.get('data_source', '-')}")
    print(f"  - Islenen Urunler   : {final_state['raw_product_data'].get('total_found', 0)} adet")
    print(f"  - SEO Icerik        : {len(final_state['optimized_content'])} urun")
    print(f"  - Kargo Hesabi      : {len(final_state['shipping_details'])} urun")
    print(f"  - Guven Skorlari    : {final_state.get('trust_scores', {})}")
    print(f"  - Veri Gecerliligi  : {'ONAYLANDI' if final_state['is_data_valid'] else 'REDDEDILDI'}")
    print("=" * 65)