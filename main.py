"""
Adım 2: Gemini API ve Yapay Zeka Entegrasyonu
"""

import os
import json
from typing import Annotated
import operator

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict

# Ortam değişkenleri ve API Key kontrolü
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY bulunamadı! "
        "Lütfen .env dosyasına veya ortam değişkenlerine ekleyin."
    )

# LLM (Gemini) Tanımı
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0.7,
    google_api_key=GEMINI_API_KEY,
)

# 1. Pydantic Şemaları (Yapılandırılmış Çıktılar)
class TrendOutput(BaseModel):
    """Trend & Talep Avcısı Agent çıktısı."""
    keywords: list[str] = Field(
        description="E-ticarette yükselen 5 trend alt ürün grubu / anahtar kelimesi"
    )


class SEOContent(BaseModel):
    """İçerik & Optimizasyon Agent çıktısı."""
    seo_title:       str       = Field(description="SEO uyumlu, çarpıcı ürün başlığı (Türkçe)")
    seo_description: str       = Field(description="Dürüst ve detaylı ürün açıklaması (Türkçe)")
    meta_keywords:   list[str] = Field(description="Google için 3-5 meta anahtar kelime")

# 2. Agent State (Ortak veri sözleşmesi)
class AgentState(TypedDict):
    user_request:       str
    trend_keywords:     list
    raw_product_data:   dict
    optimized_content:  dict
    shipping_details:   dict
    is_data_valid:      bool
    retry_count:        int
    log_history:        Annotated[list, operator.add]


# 3. Düğümler (Nodes)

# 3a. Trend & Talep Avcısı Agent (Gemini)
def trend_agent(state: AgentState) -> dict:
    """
    Gemini'ye kategori gönderir; yapılandırılmış 5 trend anahtar kelime alır.
    """
    user_req = state["user_request"]

    prompt = (
        f"Bir dropshipping uzmanı olarak, '{user_req}' ana kategorisinde "
        f"şu an küresel e-ticaret pazarlarında ve sosyal medyada "
        f"(TikTok, Reddit) hızla yükselen, satışı yüksek 5 adet spesifik "
        f"trend alt ürün grubu/anahtar kelimesi üret. "
        f"Sadece Türkçe kelimeler kullan."
    )

    structured_llm = llm.with_structured_output(TrendOutput)
    result: TrendOutput = structured_llm.invoke(prompt)

    log = (
        f"[Trend Agent] ✅ Gemini sosyal medya ve pazar trendi analizi tamamladı. "
        f"'{user_req}' için {len(result.keywords)} trend anahtar kelime üretildi: "
        f"{', '.join(result.keywords)}"
    )

    return {
        "trend_keywords": result.keywords,
        "log_history":    [log],
    }

# 3b. Ürün Avcısı Agent (Mock)
def product_hunter_agent(state: AgentState) -> dict:
    """
    Ham ürün verisi üretir. Adım 3'te Alibaba scraping ile değiştirilecek.
    """
    keywords = state["trend_keywords"]
    user_req = state["user_request"]

    simulated_products = {
        "products": [
            {
                "id":               "PRD-001",
                "name":             f"Premium {user_req.title()} Seti - Model A",
                "supplier":         "Guangzhou BabyWorld Co.",
                "supplier_rating":  4.8,
                "unit_cost_usd":    12.50,
                "moq":              10,
                "images":           ["img_001.jpg", "img_002.jpg"],
                "raw_description":  "high quality baby product made of safe materials, BPA free",
                "matched_keywords": keywords[:2] if len(keywords) >= 2 else keywords,
            },
            {
                "id":               "PRD-002",
                "name":             f"Organik {user_req.title()} - Model B",
                "supplier":         "Shenzhen EcoKids Ltd.",
                "supplier_rating":  4.6,
                "unit_cost_usd":    18.00,
                "moq":              5,
                "images":           ["img_003.jpg"],
                "raw_description":  "organic certified eco-friendly baby item, OEKO-TEX certified",
                "matched_keywords": keywords[2:4] if len(keywords) >= 4 else keywords,
            },
            {
                "id":               "PRD-003",
                "name":             f"{user_req.title()} Hediye Seti - Model C",
                "supplier":         "Yiwu GiftBaby Factory",
                "supplier_rating":  4.9,
                "unit_cost_usd":    25.00,
                "moq":              3,
                "images":           ["img_004.jpg", "img_005.jpg", "img_006.jpg"],
                "raw_description":  "complete premium gift set, best seller 2024, safe for newborns",
                "matched_keywords": keywords[1:3] if len(keywords) >= 3 else keywords,
            },
        ],
        "total_found":   3,
        "filtered_out":  7,
    }

    log = (
        f"[Ürün Avcısı Agent] ✅ Tedarikçiler tarandı (mock). "
        f"{simulated_products['total_found']} kaliteli ürün seçildi, "
        f"{simulated_products['filtered_out']} düşük kaliteli ürün elendi."
    )

    return {
        "raw_product_data": simulated_products,
        "log_history":      [log],
    }

# 3c. İçerik & Optimizasyon Agent (Gemini)
def content_agent(state: AgentState) -> dict:
    """
    Her ürün için Gemini'ye ham veri gönderir; Türkçe SEO içerik alır.
    """
    products         = state["raw_product_data"].get("products", [])
    trend_keywords   = state["trend_keywords"]
    structured_llm   = llm.with_structured_output(SEOContent)
    optimized        = {}

    for product in products:
        urun_verisi = {
            "urun_adi":         product["name"],
            "tedarikci":        product["supplier"],
            "tedarikci_puani":  product["supplier_rating"],
            "ham_aciklama":     product["raw_description"],
            "eslesen_trendler": product.get("matched_keywords", []),
            "guncel_trendler":  trend_keywords,
        }

        prompt = (
            f"Sen profesyonel bir e-ticaret metin yazarısın (copywriter). "
            f"Sana gelen şu ham ürün verilerini ve trend kelimeleri incele:\n\n"
            f"{json.dumps(urun_verisi, ensure_ascii=False, indent=2)}\n\n"
            f"Bu ürün için:\n"
            f"1. Tüketiciyi cezbedecek, dürüst ve Google aramalarında üst sıraya "
            f"çıkacak Türkçe, SEO uyumlu, çarpıcı bir başlık (seo_title) yaz. "
            f"Emoji kullanabilirsin. Maksimum 70 karakter.\n"
            f"2. Detaylı, samimi ve satış odaklı Türkçe ürün açıklaması "
            f"(seo_description) yaz. 100-150 kelime arası.\n"
            f"3. Google için 3-5 Türkçe meta_keywords belirle."
        )

        result: SEOContent = structured_llm.invoke(prompt)

        # Görsel isimlerini webp formatına güvenli dönüştür
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
        f"[İçerik Agent] ✅ Gemini, {len(optimized)} ürün için Türkçe SEO başlıkları "
        f"ve açıklamaları oluşturdu. Görseller webp formatına dönüştürüldü."
    )

    return {
        "optimized_content": optimized,
        "log_history":       [log],
    }

# 3d. Operasyon & Kargo Agent (Mock)
def operations_agent(state: AgentState) -> dict:
    """
    Kargo süresi ve maliyet hesabı yapar. Adım 3'te lojistik API ile değişecek.
    """
    products = state["raw_product_data"].get("products", [])
    shipping = {}

    for p in products:
        base_days  = 14
        unit_cost  = p["unit_cost_usd"]
        markup     = 2.8
        shipping[p["id"]] = {
            "origin_country":           "CN",
            "destination":              "TR",
            "estimated_delivery_days":  base_days,
            "estimated_delivery_label": f"{base_days}-{base_days + 5} iş günü",
            "shipping_cost_usd":        round(unit_cost * 0.15, 2),
            "suggested_sale_price_try": round(unit_cost * markup * 33, 2),
            "display_text":             f"🚚 Ücretsiz Kargo | Tahmini Teslimat: {base_days}-{base_days + 5} İş Günü",
        }

    log = (
        f"[Operasyon Agent] ✅ {len(shipping)} ürün için kargo süresi ve "
        f"maliyet hesabı tamamlandı (mock). Satış fiyatları belirlendi."
    )

    return {
        "shipping_details": shipping,
        "log_history":      [log],
    }

# 3e. Chief Orchestrator (Kontrolcü Baş Ajan)
def orchestrator_review(state: AgentState) -> dict:
    """
    İçerik ve Operasyon çıktılarını birleştirir, doğrular.
    Hata varsa ilgili ajanlara geri gönderir; kusursuzsa Site Agent'a yollar.
    """
    content  = state.get("optimized_content", {})
    shipping = state.get("shipping_details", {})
    retry    = state.get("retry_count", 0)
    errors   = []

    for pid in content:
        if pid not in shipping:
            errors.append(f"HATA: {pid} için kargo bilgisi eksik!")

    for pid, sh in shipping.items():
        if sh.get("estimated_delivery_days", 0) <= 0:
            errors.append(f"HATA: {pid} teslimat süresi geçersiz!")
        if sh.get("suggested_sale_price_try", 0) <= 0:
            errors.append(f"HATA: {pid} satış fiyatı sıfır veya negatif!")

    for pid, ct in content.items():
        if not ct.get("seo_title", "").strip():
            errors.append(f"HATA: {pid} SEO başlığı boş!")

    is_valid = len(errors) == 0

    if is_valid:
        log = (
            f"[Baş Ajan (Orchestrator)] ✅ Tüm veriler doğrulandı. "
            f"{len(content)} ürün onaylandı. Site Agent'a yönlendiriliyor."
        )
    else:
        log = (
            f"[Baş Ajan (Orchestrator)] ⚠️  {len(errors)} hata tespit edildi "
            f"(Deneme #{retry + 1}). İlgili ajanlara geri gönderiliyor.\n"
            + "\n".join(f"  → {e}" for e in errors)
        )

    return {
        "is_data_valid": is_valid,
        "retry_count":   retry + 1,
        "log_history":   [log],
    }

# 3f. Veri Tabanı & Site Agent
def site_agent(state: AgentState) -> dict:
    content  = state["optimized_content"]
    shipping = state["shipping_details"]

    listings = []
    for pid in content:
        listings.append({
            "product_id":    pid,
            "title":         content[pid]["seo_title"],
            "description":   content[pid]["seo_description"],
            "images":        content[pid]["formatted_images"],
            "price_try":     shipping[pid]["suggested_sale_price_try"],
            "shipping_text": shipping[pid]["display_text"],
            "status":        "LIVE",
        })

    log = (
        f"[Site Agent] ✅ {len(listings)} ürün mağazaya eklendi ve yayına alındı. "
        f"Dashboard güncellendi."
    )

    return {"log_history": [log]}

# 3g. Kullanıcı Asistanı Agent (Mentor)
def user_assistant_agent(state: AgentState) -> dict:
    total   = state["raw_product_data"].get("total_found", 0)
    request = state["user_request"]

    notification = (
        f"[Kullanıcı Asistanı] 🎉 Harika haber! '{request}' kategorisinde "
        f"{total} yeni ürün bulundu ve mağazana eklendi. "
        f"Dashboard'unda inceleyebilir, fiyatlarını düzenleyebilirsin. "
        f"İlk siparişin gelmesi için sabırsızlanıyoruz! 🚀"
    )

    return {"log_history": [notification]}

# 4. Koşullu Yönlendirme
def route_after_review(state: AgentState) -> str:
    MAX_RETRY = 3
    if state["is_data_valid"]:
        return "site_agent"
    elif state.get("retry_count", 0) >= MAX_RETRY:
        return "user_assistant_agent"   # Sonsuz döngü koruması
    else:
        return "content_agent"          # Hata → geri dön

# 5. Graf Kurulumu
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
            "content_agent":        "content_agent",
            "user_assistant_agent": "user_assistant_agent",
        },
    )

    workflow.add_edge("site_agent",           "user_assistant_agent")
    workflow.add_edge("user_assistant_agent", END)

    return workflow.compile()

# 6. Çalıştırma
if __name__ == "__main__":
    print("=" * 65)
    print("  Chief Orchestrator  |  Adım 2: Gemini Entegrasyonu")
    print("=" * 65)

    graph = build_graph()

    initial_state: AgentState = {
        "user_request":      "bebek ürünleri",
        "trend_keywords":    [],
        "raw_product_data":  {},
        "optimized_content": {},
        "shipping_details":  {},
        "is_data_valid":     False,
        "retry_count":       0,
        "log_history":       [],
    }

    print(f"\n📥 Gelen İstek: \"{initial_state['user_request']}\"\n")
    print(f"🤖 Gemini modeli hazır. Graf çalıştırılıyor...\n")
    print("-" * 65)

    final_state = graph.invoke(initial_state)

    # ── Log Akışı ──
    print("\n📋 AJAN LOG AKIŞI (Kronolojik Sıra):\n")
    for i, entry in enumerate(final_state["log_history"], 1):
        print(f"  [{i:02d}] {entry}")

    # ── Özet Rapor ──
    print("\n" + "=" * 65)
    print("  ÖZET RAPOR")
    print("=" * 65)
    print(f"  • Kategori          : {final_state['user_request']}")
    print(f"  • Trend Kelimeler   : {', '.join(final_state['trend_keywords'])}")
    print(f"  • Bulunan Ürünler   : {final_state['raw_product_data'].get('total_found', 0)} adet")
    print(f"  • SEO İçerik        : {len(final_state['optimized_content'])} ürün (Gemini tarafından)")
    print(f"  • Kargo Hesabı      : {len(final_state['shipping_details'])} ürün için tamamlandı")
    print(f"  • Veri Geçerliliği  : {'✅ ONAYLANDI' if final_state['is_data_valid'] else '❌ HATA'}")
    print("=" * 65)

    # ── Örnek Listeleme (İlk Ürün) ──
    if final_state["optimized_content"]:
        first_pid = list(final_state["optimized_content"].keys())[0]
        sample_output = {
            "product_id":    first_pid,
            "seo_title":     final_state["optimized_content"][first_pid]["seo_title"],
            "seo_description": final_state["optimized_content"][first_pid]["seo_description"][:120] + "...",
            "meta_keywords": final_state["optimized_content"][first_pid]["meta_keywords"],
            "price_try":     final_state["shipping_details"][first_pid]["suggested_sale_price_try"],
            "delivery":      final_state["shipping_details"][first_pid]["display_text"],
            "status":        "LIVE",
        }
        print("\n📦 ÖRNEK LİSTELEME VERİSİ — Gemini SEO Çıktısı (İlk Ürün):\n")
        print(json.dumps(sample_output, ensure_ascii=False, indent=2))
        print()