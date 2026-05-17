"""
DropAI - Chief Orchestrator LangGraph İskeleti
Adım 1: State Yönetimi, Düğümler ve Graf Akışı
"""

import json
from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END


# ─────────────────────────────────────────────
# 1. AGENT STATE — Tüm ajanların ortak veri sözleşmesi
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    user_request:       str           # Kullanıcının kategori isteği
    trend_keywords:     list          # Trend ajanının bulduğu kelimeler
    raw_product_data:   dict          # Ürün avcısının ham verisi
    optimized_content:  dict          # İçerik ajanının SEO çıktısı
    shipping_details:   dict          # Operasyon ajanının kargo/maliyet çıktısı
    is_data_valid:      bool          # Baş Ajan onay durumu
    retry_count:        int           # Hata döngüsü sayacı (sonsuz döngü koruması)
    log_history:        Annotated[list, operator.add]  # Terminal logları (otomatik birleştir)


# ─────────────────────────────────────────────
# 2. DÜĞÜMLER (NODES) — 6 Uzman Ajan
# ─────────────────────────────────────────────

def trend_agent(state: AgentState) -> dict:
    """
    Trend & Talep Avcısı Agent
    Görev: X, Reddit, TikTok, Amazon Bestsellers'ı tarar; trend kelimeler üretir.
    """
    user_req = state["user_request"]

    # SIMÜLE — Gerçek implementasyonda scraping API'leri buraya gelecek
    simulated_keywords = [
        f"{user_req} 2025 trend",
        f"en çok satan {user_req}",
        f"{user_req} hediye seti",
        f"organik {user_req}",
        f"{user_req} premium",
    ]

    log = f"[Trend Agent] ✅ Sosyal medya ve pazar yerleri tarandı. " \
          f"'{user_req}' için {len(simulated_keywords)} trend anahtar kelime belirlendi."

    return {
        "trend_keywords": simulated_keywords,
        "log_history": [log],
    }


def product_hunter_agent(state: AgentState) -> dict:
    """
    Ürün Avcısı Agent
    Görev: Alibaba/üreticilerden ham ürün verisi, foto, puan, yorumları çeker.
    """
    keywords = state["trend_keywords"]

    # SIMÜLE — Gerçek implementasyonda Alibaba API / scraper buraya gelecek
    simulated_products = {
        "products": [
            {
                "id": "PRD-001",
                "name": f"Premium {state['user_request'].title()} Seti - Model A",
                "supplier": "Guangzhou BabyWorld Co.",
                "supplier_rating": 4.8,
                "unit_cost_usd": 12.50,
                "moq": 10,
                "images": ["img_001.jpg", "img_002.jpg"],
                "raw_description": "high quality baby product made of safe materials",
                "matched_keywords": keywords[:2],
            },
            {
                "id": "PRD-002",
                "name": f"Organik {state['user_request'].title()} - Model B",
                "supplier": "Shenzhen EcoKids Ltd.",
                "supplier_rating": 4.6,
                "unit_cost_usd": 18.00,
                "moq": 5,
                "images": ["img_003.jpg"],
                "raw_description": "organic certified eco-friendly baby item",
                "matched_keywords": keywords[2:4],
            },
            {
                "id": "PRD-003",
                "name": f"{state['user_request'].title()} Hediye Seti - Model C",
                "supplier": "Yiwu GiftBaby Factory",
                "supplier_rating": 4.9,
                "unit_cost_usd": 25.00,
                "moq": 3,
                "images": ["img_004.jpg", "img_005.jpg", "img_006.jpg"],
                "raw_description": "complete gift set for babies best seller 2024",
                "matched_keywords": keywords[1:3],
            },
        ],
        "total_found": 3,
        "filtered_out": 7,  # Düşük puanlı ürünler elendi
    }

    log = f"[Ürün Avcısı Agent] ✅ Tedarikçiler tarandı. " \
          f"{simulated_products['total_found']} kaliteli ürün seçildi, " \
          f"{simulated_products['filtered_out']} düşük kaliteli ürün elendi."

    return {
        "raw_product_data": simulated_products,
        "log_history": [log],
    }


def content_agent(state: AgentState) -> dict:
    """
    İçerik & Optimizasyon Agent
    Görev: SEO uyumlu başlık/açıklama yazar, görselleri formatlar.
    """
    products = state["raw_product_data"].get("products", [])

    # SIMÜLE — Gerçek implementasyonda LLM SEO yazımı + görsel işleme buraya
    optimized = {}
    for p in products:
        optimized[p["id"]] = {
            "seo_title": f"🌟 {p['name']} | Güvenli & Kaliteli | Ücretsiz Kargo",
            "seo_description": (
                f"En sevilen {state['user_request']} modellerinden biri! "
                f"{p['supplier']} tarafından üretilen bu ürün, "
                f"yüksek kalite standartlarını karşılamaktadır. "
                f"Aile dostu tasarım, güvenli malzeme."
            ),
            "meta_keywords": state["trend_keywords"][:3],
            "formatted_images": [img.replace(".jpg", "_optimized_800x800.webp")
                                  for img in p["images"]],
        }

    log = f"[İçerik Agent] ✅ {len(optimized)} ürün için SEO başlıkları ve " \
          f"açıklamaları oluşturuldu. Görseller webp formatına dönüştürüldü."

    return {
        "optimized_content": optimized,
        "log_history": [log],
    }


def operations_agent(state: AgentState) -> dict:
    """
    Operasyon & Kargo Agent
    Görev: Teslimat süresi, kargo maliyeti hesaplar; site için formatlar.
    """
    products = state["raw_product_data"].get("products", [])

    # SIMÜLE — Gerçek implementasyonda lojistik API'leri buraya
    shipping = {}
    for p in products:
        # Tedarikçi Çin'de → Türkiye'ye standart e-ticaret hesabı
        base_days = 14
        unit_cost  = p["unit_cost_usd"]
        markup     = 2.8  # %180 kâr marjı

        shipping[p["id"]] = {
            "origin_country": "CN",
            "destination": "TR",
            "estimated_delivery_days": base_days,
            "estimated_delivery_label": f"{base_days}-{base_days + 5} iş günü",
            "shipping_cost_usd": round(unit_cost * 0.15, 2),  # Birim başı kargo ~%15
            "suggested_sale_price_try": round(unit_cost * markup * 33, 2),  # USD→TRY
            "display_text": f"🚚 Ücretsiz Kargo | Tahmini Teslimat: {base_days}-{base_days+5} İş Günü",
        }

    log = f"[Operasyon Agent] ✅ {len(shipping)} ürün için kargo süresi ve " \
          f"maliyet hesabı tamamlandı. Satış fiyatları belirlendi."

    return {
        "shipping_details": shipping,
        "log_history": [log],
    }


def orchestrator_review(state: AgentState) -> dict:
    """
    Chief Orchestrator — Kontrolcü Baş Ajan
    Görev: İçerik ve Operasyon ajanlarının çıktısını birleştirir, doğrular.
    Hata varsa ilgili ajana geri gönderir; kusursuzsa Site Agent'a yönlendirir.
    """
    content  = state.get("optimized_content", {})
    shipping = state.get("shipping_details", {})
    retry    = state.get("retry_count", 0)

    errors = []

    # — Validasyon Kuralları —
    for pid in content:
        if pid not in shipping:
            errors.append(f"HATA: {pid} için kargo bilgisi eksik!")

    for pid, sh in shipping.items():
        if sh.get("estimated_delivery_days", 0) <= 0:
            errors.append(f"HATA: {pid} için teslimat süresi geçersiz ({sh['estimated_delivery_days']} gün)!")
        if sh.get("suggested_sale_price_try", 0) <= 0:
            errors.append(f"HATA: {pid} için satış fiyatı sıfır veya negatif!")

    for pid, ct in content.items():
        if not ct.get("seo_title"):
            errors.append(f"HATA: {pid} için SEO başlığı boş!")

    # Simülasyon: İlk çalışmada kasıtlı hata YOK (retry_count 0'da geçerli veri)
    # Test etmek için: retry_count == 99 gibi bir koşulla hata inject edebilirsin
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
        "retry_count": retry + 1,
        "log_history": [log],
    }


def site_agent(state: AgentState) -> dict:
    """
    Veri Tabanı & Site Agent
    Görev: Onaylanmış ürünleri Dashboard ve canlı siteye aktarır.
    """
    content  = state["optimized_content"]
    shipping = state["shipping_details"]

    listings = []
    for pid in content:
        listings.append({
            "product_id":   pid,
            "title":        content[pid]["seo_title"],
            "description":  content[pid]["seo_description"],
            "images":       content[pid]["formatted_images"],
            "price_try":    shipping[pid]["suggested_sale_price_try"],
            "shipping_text":shipping[pid]["display_text"],
            "status":       "LIVE",
        })

    log = (
        f"[Site Agent] ✅ {len(listings)} ürün mağazaya eklendi ve yayına alındı. "
        f"Dashboard güncellendi."
    )

    return {"log_history": [log]}


def user_assistant_agent(state: AgentState) -> dict:
    """
    Kullanıcı Asistanı Agent (Mentor)
    Görev: Dropshipper'a işlem özeti bildirir.
    """
    total   = state["raw_product_data"].get("total_found", 0)
    request = state["user_request"]

    notification = (
        f"[Kullanıcı Asistanı] 🎉 Harika haber! '{request}' kategorisinde "
        f"{total} yeni ürün bulundu ve mağazana eklendi. "
        f"Dashboard'unda inceleyebilir, fiyatlarını düzenleyebilirsin. "
        f"İlk siparişin gelmesi için sabırsızlanıyoruz! 🚀"
    )

    return {"log_history": [notification]}


# ─────────────────────────────────────────────
# 3. KOŞULLu YÖNLENDİRME (CONDITIONAL EDGE)
# ─────────────────────────────────────────────

def route_after_review(state: AgentState) -> str:
    """
    Orchestrator'ın kararına göre akışı yönlendir.
    - Geçerliyse   → 'site_agent'
    - Hatalıysa    → 'content_agent' (yeniden dene)
    - Max retry'a  → 'user_assistant_agent' (hatayı bildir ve bitir)
    """
    MAX_RETRY = 3

    if state["is_data_valid"]:
        return "site_agent"
    elif state.get("retry_count", 0) >= MAX_RETRY:
        # Sonsuz döngü koruması
        return "user_assistant_agent"
    else:
        return "content_agent"   # İçerik/kargo ajanlarını yeniden tetikle


# ─────────────────────────────────────────────
# 4. GRAF KURULUMU
# ─────────────────────────────────────────────

def build_graph():
    workflow = StateGraph(AgentState)

    # Düğümleri ekle
    workflow.add_node("trend_agent",          trend_agent)
    workflow.add_node("product_hunter_agent", product_hunter_agent)
    workflow.add_node("content_agent",        content_agent)
    workflow.add_node("operations_agent",     operations_agent)
    workflow.add_node("orchestrator_review",  orchestrator_review)
    workflow.add_node("site_agent",           site_agent)
    workflow.add_node("user_assistant_agent", user_assistant_agent)

    # ── Başlangıç noktası ──
    workflow.set_entry_point("trend_agent")

    # ── Sıralı akış ──
    workflow.add_edge("trend_agent", "product_hunter_agent")

    # ── Paralel dallanma: Ürün Avcısı → İçerik + Operasyon aynı anda ──
    workflow.add_edge("product_hunter_agent", "content_agent")
    workflow.add_edge("product_hunter_agent", "operations_agent")

    # ── Paralel kollar Orchestrator'da birleşir ──
    workflow.add_edge("content_agent",    "orchestrator_review")
    workflow.add_edge("operations_agent", "orchestrator_review")

    # ── Koşullu yönlendirme ──
    workflow.add_conditional_edges(
        "orchestrator_review",
        route_after_review,
        {
            "site_agent":           "site_agent",
            "content_agent":        "content_agent",   # Hata → geri dön
            "user_assistant_agent": "user_assistant_agent",
        },
    )

    # ── Bitiş akışları ──
    workflow.add_edge("site_agent", "user_assistant_agent")
    workflow.add_edge("user_assistant_agent", END)

    return workflow.compile()


# ─────────────────────────────────────────────
# 5. ÇALIŞTIRMA & LOG ÇIKTISI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  DropAI — Chief Orchestrator  |  Adım 1: Graf İskeleti")
    print("=" * 65)

    graph = build_graph()

    # Başlangıç state'i
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
    print("-" * 65)

    # Grafı çalıştır
    final_state = graph.invoke(initial_state)

    # Log akışını terminale bas
    print("\n📋 AJAN LOG AKIŞI (Kronolojik Sıra):\n")
    for i, entry in enumerate(final_state["log_history"], 1):
        print(f"  [{i:02d}] {entry}")

    print("\n" + "=" * 65)
    print("  ÖZET RAPOR")
    print("=" * 65)
    print(f"  • Kategori          : {final_state['user_request']}")
    print(f"  • Trend Kelimeler   : {len(final_state['trend_keywords'])} adet")
    print(f"  • Bulunan Ürünler   : {final_state['raw_product_data'].get('total_found', 0)} adet")
    print(f"  • SEO İçerik        : {len(final_state['optimized_content'])} ürün optimize edildi")
    print(f"  • Kargo Hesabı      : {len(final_state['shipping_details'])} ürün için tamamlandı")
    print(f"  • Veri Geçerliliği  : {'✅ ONAYLANDI' if final_state['is_data_valid'] else '❌ HATA'}")
    print(f"  • Yeniden Deneme    : {final_state['retry_count']} kez")
    print("=" * 65)

    print("\n📦 ÖRNEK LİSTELEME VERISI (İlk Ürün JSON):\n")
    first_pid = list(final_state["optimized_content"].keys())[0]
    sample_output = {
        "product_id":    first_pid,
        "seo_title":     final_state["optimized_content"][first_pid]["seo_title"],
        "price_try":     final_state["shipping_details"][first_pid]["suggested_sale_price_try"],
        "delivery":      final_state["shipping_details"][first_pid]["display_text"],
        "status":        "LIVE",
    }
    print(json.dumps(sample_output, ensure_ascii=False, indent=2))
    print()