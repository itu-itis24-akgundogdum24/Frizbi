import streamlit as st
import uuid
from main import build_graph

# --- Sayfa Ayarlari ---
st.set_page_config(
    page_title="AI Dropshipping Orchestrator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Kurumsal CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #121212;
        padding: 24px;
        border-radius: 8px;
        border-left: 4px solid #2563eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        border: 1px solid #333;
    }
    .product-title {
        color: #60a5fa;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .trust-high { color: #4ade80; font-weight: 600; }
    .trust-low { color: #f87171; font-weight: 600; }
    .section-header {
        font-size: 1.1rem;
        color: #9ca3af;
        border-bottom: 1px solid #333;
        padding-bottom: 5px;
        margin-bottom: 15px;
    }
    div[data-testid="stSidebar"] {
        background-color: #0a0a0a;
        border-right: 1px solid #222;
    }
</style>
""", unsafe_allow_html=True)


# --- YAN MENÜ ---
with st.sidebar:
    st.title("AI Kontrol Paneli")
    st.markdown(
        "Sosyal medya trendlerini analiz edip, pazar yerlerinden otonom "
        "ürün keşfeden ve SEO içerikleri üreten LangGraph operasyon merkezi."
    )
    st.divider()
    st.caption("Frizbi BTK Hackathon - 2026")


# --- ANA EKRAN ---
st.title("Akıllı Ürün Keşif ve Optimizasyon Motoru")
st.markdown("Hedef kategoriyi belirleyin, ajanlar küresel pazarı tarayıp operasyona hazır hale getirsin.")

# Kullanici Girisi
col1, col2 = st.columns([4, 1])
with col1:
    user_input = st.text_input("Hedef Kategori:", placeholder="Örn: kablosuz kulaklık...", value="kablosuz kulaklık", label_visibility="collapsed")
with col2:
    run_button = st.button("Sistemi Başlat", use_container_width=True, type="primary")

st.divider()

# --- GRAF ÇALIŞTIRMA MANTIĞI ---
if run_button:
    if not user_input:
        st.warning("Lütfen işlem yapılacak bir kategori girin.")
    else:
        session_id = str(uuid.uuid4())
        initial_state = {
            "session_id": session_id,
            "user_request": user_input,
            "trend_keywords": [],
            "raw_product_data": {},
            "optimized_content": {},
            "shipping_details": {},
            "is_data_valid": False,
            "retry_count": 0,
            "trust_scores": {},
            "data_source": "",
            "log_history": [],
        }

        with st.status("Ajanlar görevlendirildi. İşlem devam ediyor...", expanded=True) as status:
            st.write("Sinyal analizleri ve pazar yeri taraması yapılıyor...")
            
            try:
                graph = build_graph()
                final_state = graph.invoke(initial_state)
                
                status.update(label="Operasyon başarıyla tamamlandı.", state="complete", expanded=False)
                
                is_valid = final_state.get("is_data_valid", False)
                logs = final_state.get("log_history", [])
                
                if is_valid:
                    st.success("Tüm veriler doğrulandı. Ürünler panele aktarıldı.")
                else:
                    st.warning("Canlı ağ erişim kısıtlaması nedeniyle sistem Yüksek Erişilebilirlik (Mock) katmanından yanıt verdi.")
                        
            except Exception as e:
                status.update(label="Kritik Sistem Hatası", state="error", expanded=True)
                st.error(f"İşlem sırasında bir hata oluştu: {e}")
                st.stop()


        # --- SONUÇLARI GÖSTERME (SEKMELİ YAPI) ---
        tab1, tab2 = st.tabs(["Ürün Dashboard", "Sistem Logları"])
        
        content = final_state.get("optimized_content", {})
        shipping = final_state.get("shipping_details", {})
        trust_scores = final_state.get("trust_scores", {})
        raw_products_list = final_state.get("raw_product_data", {}).get("products", [])
        
        # Orijinal urun linklerini ID ile eslestirmek icin sozluk yapisi
        raw_product_map = {p["id"]: p for p in raw_products_list}
        
        with tab1:
            if not content:
                st.info("Ekrana basılacak onaylanmış ürün bulunamadı. Lütfen sistem loglarını inceleyin.")
            else:
                st.markdown("<div class='section-header'>Yayına Hazır Envanter</div>", unsafe_allow_html=True)
                
                # Urunleri listele
                for pid, ct in content.items():
                    sh = shipping.get(pid, {})
                    t_score = trust_scores.get(pid, 100)
                    raw_data = raw_product_map.get(pid, {})
                    
                    trust_class = "trust-high" if t_score >= 80 else "trust-low"
                    source_url = raw_data.get("source_url", "https://www.alibaba.com")
                    unit_cost = raw_data.get("unit_cost_usd", 0.0)
                    
                    with st.container():
                        st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
                        
                        c1, c2 = st.columns([2.5, 1])
                        
                        # Sol Kolon: SEO ve Icerik
                        with c1:
                            st.markdown(f'<div class="product-title">{ct.get("seo_title", "Başlık Bulunamadı")}</div>', unsafe_allow_html=True)
                            st.write(ct.get("seo_description", "Açıklama üretilemedi."))
                            st.caption(f"Meta Etiketleri: {', '.join(ct.get('meta_keywords', []))}")
                            
                        # Sag Kolon: Finans ve Aksiyon
                        with c2:
                            st.metric("Önerilen Satış Fiyatı", f"₺ {sh.get('suggested_sale_price_try', 0)}")
                            st.caption(f"Tedarik Maliyeti: ${unit_cost}")
                            st.write(f"Kargo: {sh.get('display_text', 'Veri yok')}")
                            st.markdown(f"Güvenilirlik Endeksi: <span class='{trust_class}'>{t_score}/100</span>", unsafe_allow_html=True)
                            
                            # Streamlit'in dogrudan link butonu (sayfa yenilemez, yeni sekmede acar)
                            st.link_button("Tedarikçi Sayfasına Git", source_url, use_container_width=True)
                            
                        st.markdown('</div>', unsafe_allow_html=True)
                        
        with tab2:
            st.markdown("<div class='section-header'>Ajan İşlem Kayıtları (Audit Trail)</div>", unsafe_allow_html=True)
            for log in logs:
                st.code(log, language="log")