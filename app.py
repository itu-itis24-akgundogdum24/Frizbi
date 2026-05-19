import streamlit as st
import uuid
from main import build_graph

# --- Kurumsal Sayfa Ayarları ---
st.set_page_config(
    page_title="Frizbi Enterprise B2B & Pazaryeri",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GLOBAL DİNAMİK STYLING & SİBER IZGARA TASARIM MOTORU ---
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet">

<style>
    /* 1. SİBER IZGARA (CYBER-GRID) VE DİNAMİK ARKA PLAN MATRİSİ */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #060913 !important;
        background-image: 
            linear-gradient(rgba(96, 165, 250, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(96, 165, 250, 0.03) 1px, transparent 1px),
            radial-gradient(circle at 50% 50%, #141033 0%, #060913 100%) !important;
        background-size: 40px 40px, 40px 40px, 100% 100% !important;
        background-attachment: fixed !important;
        animation: gridPulse 20s infinite alternate ease-in-out;
    }
    
    @keyframes gridPulse {
        0% { background-position: 0px 0px, 0px 0px, 50% 50%; }
        100% { background-position: 20px 20px, 20px 20px, 50% 50%; }
    }

    /* 2. TÜM SAYFADA TEK TİP ELEGANT FONT YÖNETİMİ */
    html, body, p, label, input, button, select, textarea, h1, h2, h3, h4, 
    [data-testid="stMetricLabel"], .main-title, .product-title-box {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #f3f4f6 !important;
    }
    
    /* İKONLARIN METNE DÖNÜŞMESİNİ (keyboard_double_right) KESİN ENGELLEME */
    [data-testid="stSidebarCollapseButton"] span, 
    [data-testid="collapsedControl"] span,
    [class*="Icon"], 
    svg,
    .st-emotion-cache-1sc780p,
    [data-testid="stIcon"] {
        font-family: "Material Symbols Outlined", "Segoe UI Symbol", sans-serif !important;
        display: inline-block !important;
    }
    
    .main-title {
        font-size: 2.6rem;
        font-weight: 700;
        background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
        letter-spacing: -0.03em;
    }
    
    .subtitle {
        font-size: 1.05rem;
        color: #9ca3af;
        margin-bottom: 30px;
        font-weight: 300;
    }
    
    /* MOUSE GELİNCE PARLAMA EFEKTİ */
    .product-master-card, .login-box, .stButton>button {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .product-master-card:hover, .stButton>button:hover {
        box-shadow: 0 0 30px rgba(96, 165, 250, 0.15) !important;
        border-color: #60a5fa !important;
        transform: translateY(-2px);
    }
    
    /* 3. BÖLMELİ TEK KUTU ÜRÜN TASARIMI */
    .product-master-card {
        background: rgba(13, 17, 28, 0.85);
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #1e293b;
        margin-bottom: 25px;
        backdrop-filter: blur(12px);
    }
    
    /* Ürün Adı İçin Üst Bölme Kutucuğu */
    .product-title-box {
        background: rgba(30, 41, 59, 0.5);
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 4px solid #60a5fa;
        font-size: 1.2rem;
        font-weight: 600;
        color: #60a5fa !important;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
    }
    
    /* Ürün Açıklaması İçin Alt Bölme Kutucuğu */
    .product-desc-box {
        background: rgba(15, 23, 42, 0.6);
        padding: 14px 16px;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.03);
        color: #d1d5db !important;
        font-size: 0.9rem;
        font-weight: 300;
        line-height: 1.5;
        margin-bottom: 12px;
        min-height: 80px;
    }
    
    /* Lojistik Bilgi Şeridi */
    .product-meta-strip {
        font-size: 0.82rem;
        color: #a78bfa;
        padding-left: 4px;
        margin-bottom: 4px;
    }
    
    /* 4. GİRİŞ EKRANI KUTU TASARIMI (Sadeleştirildi) */
    .login-box {
        background: rgba(13, 17, 28, 0.8);
        padding: 32px;
        border-radius: 16px;
        border: 1px solid #1e293b;
        position: relative;
        z-index: 2;
        overflow: visible; 
        backdrop-filter: blur(12px);
    }
    
    .login-box:hover {
        border-color: #a78bfa !important;
        box-shadow: 0 0 35px rgba(167, 139, 250, 0.15);
    }

    /* Rozetler */
    .trust-badge-high {
        background-color: rgba(6, 95, 70, 0.4);
        color: #34d399;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(52, 211, 153, 0.2);
        white-space: nowrap;
    }
    .trust-badge-low {
        background-color: rgba(127, 29, 29, 0.4);
        color: #f87171;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(248, 113, 113, 0.2);
        white-space: nowrap;
    }
    .depo-header-badge {
        background-color: #1e1b4b;
        color: #c7d2fe;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        border: 1px solid #312e81;
        white-space: nowrap;
    }
    .sidebar-inventory-item {
        background-color: #0f172a;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 3px solid #6366f1;
        border: 1px solid #1e293b;
    }
    
    /* Kontroller Paneli Stili */
    .control-panel-bar {
        background: rgba(30, 41, 59, 0.2);
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid #1e293b;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Durum Yönetimi ---
if "role" not in st.session_state:
    st.session_state.role = None
if "depo_name" not in st.session_state:
    st.session_state.depo_name = ""
if "depo" not in st.session_state:
    st.session_state.depo = []
if "sepet" not in st.session_state:
    st.session_state.sepet = []
if "last_search_results" not in st.session_state:
    st.session_state.last_search_results = None
if "page" not in st.session_state:
    st.session_state.page = "main"

@st.cache_resource
def get_compiled_graph():
    return build_graph()

graph = get_compiled_graph()

# --- 1. ADIM: PROFİL VE GİRİŞ EKRANI ---
if st.session_state.role is None:
    st.markdown('<div class="main-title">Frizbi E-Tedarik ve Pazaryeri Hub</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Kurumsal B2B tedarik lojistik otomasyonu ve entegre dijital pazar yönetim altyapısı.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.subheader("Mağaza Yönetim Modülü")
        st.caption("Veri hatlarını analiz ederek yerel envanterinizi güncel ve rekabetçi ürünlerle ölçeklendirin.")
        
        input_depo = st.text_input(
            "Kurulacak Depo / Mağaza Adı", 
            placeholder="Örn: Efe Lojistik, Global Tedarik...",
            key="setup_depo_name"
        )
        
        if st.button("Mağaza Yöneticisi Yetkisiyle Giriş Yap", use_container_width=True, type="primary"):
            if not input_depo.strip():
                st.error("Giriş yapmak için geçerli bir organizasyon veya depo adı tanımlamalısınız.")
            else:
                st.session_state.depo_name = input_depo.strip()
                st.session_state.role = "Mağaza"
                st.session_state.page = "main"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
                
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.subheader("Genel Alışveriş Modülü")
        st.caption("Sistem üzerindeki doğrulanmış depolardan doğrudan sipariş geçin ve lojistik hatlarını izleyin.")
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("Müşteri Kimliği ile Bağlantı Kur", use_container_width=True):
            st.session_state.role = "Kullanıcı"
            st.session_state.page = "main"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# --- SOL DENETİM PANELİ (SIDEBAR) ---
with st.sidebar:
    st.markdown("### ⬡ Yönetim Konsolu")
    st.write(f"Mevcut Rol: **{st.session_state.role}**")
    
    if st.session_state.role == "Mağaza":
        st.write(f"Aktif Depo: **{st.session_state.depo_name}**")
        aktif_depo_urunleri = [i for i in st.session_state.depo if i.get("source_depo") == st.session_state.depo_name]
        st.metric("Depodaki Güncel Ürün", f"{len(aktif_depo_urunleri)} Kalem")
        
        st.markdown("---")
        st.markdown("#### 📦 Canlı Depo Envanteri")
        if not aktif_depo_urunleri:
            st.caption("Envanter boş. Lütfen sağ panelden veri çekip ürün ekleyin.")
        else:
            for item in aktif_depo_urunleri:
                try:
                    price_val = float(item['price'])
                except:
                    price_val = 0.0
                st.markdown(f"""
                <div class="sidebar-inventory-item">
                    <div style="font-size:0.85rem; font-weight:600; color:#f3f4f6;">{item['title'][:28]}...</div>
                    <div style="font-size:0.75rem; color:#4ade80;">💰 ₺{price_val:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
    else:
        st.write("🛒 **Aktif Sepetiniz**")
        if not st.session_state.sepet:
            st.caption("Sepetiniz boş, pazaryerinden ürün ekleyebilirsiniz.")
        else:
            try:
                toplam = sum(float(i["price"]) for i in st.session_state.sepet)
            except:
                toplam = 0.0
            for i in st.session_state.sepet:
                try:
                    p_i = float(i['price'])
                except:
                    p_i = 0.0
                st.caption(f"• {i['title'][:25]}... (₺{p_i:.2f})")
            st.markdown(f"**Toplam Tutar: ₺{toplam:.2f}**")
            
            if st.button("💳 Alışverişi Güvenli Tamamla", use_container_width=True, type="primary"):
                st.session_state.page = "checkout"
                st.rerun()
                
    st.markdown("---")
    if st.button("🔄 Güvenli Çıkış / Rol Değiştir", use_container_width=True):
        st.session_state.role = None
        st.session_state.last_search_results = None
        st.session_state.page = "main"
        st.rerun()

# =====================================================================
#  SAYFA KONTROL VE YÖNLENDİRME AKIŞLARI
# =====================================================================

if st.session_state.role == "Kullanıcı" and st.session_state.page == "checkout":
    st.title("💳 Güvenli Ödeme ve Sipariş İletim Merkezi")
    st.write("Siparişinizi tamamlamak için lojistik sevkiyat ve fatura verilerini kontrol edin.")
    
    col_pay1, col_pay2 = st.columns([2, 1], gap="large")
    
    with col_pay1:
        st.subheader("1. Sevkiyat ve Konsolidasyon Bilgileri")
        c_adr1, c_adr2 = st.columns(2)
        with c_adr1:
            st.text_input("Müşteri Adı Soyadı", value="Efe")
            st.text_input("İletişim Hattı", placeholder="+90 5xx ...")
        with c_adr2:
            st.text_input("Fatura Başlığı", placeholder="Şahıs / Kurum Bilgisi")
            st.selectbox("Lojistik Dağıtım Ortağı", ["DHL Express", "FedEx Entegrasyonu", "Yurtiçi Lojistik"])
            
        st.text_area("Açık Teslimat Adresi", placeholder="Sevkiyatın yapılacağı açık adres detayları...")
        
        st.subheader("2. Finansal Ödeme Geçidi")
        st.text_input("Kart Sahibi Adı", value="EFE")
        cc_col1, cc_col2, cc_col3 = st.columns([2, 1, 1])
        with cc_col1:
            st.text_input("Kredi Kartı Numarası", placeholder="4543 •••• •••• 1290", max_chars=19)
        with cc_col2:
            st.text_input("Son Tüketim (AA/YY)", placeholder="12/29", max_chars=5)
        with cc_col3:
            st.text_input("Güvenlik Kodu (CVV)", placeholder="•••", max_chars=3)
            
    with col_pay2:
        st.subheader("Fatura Kalemleri Özeti")
        try:
            total_checkout_price = sum(float(i["price"]) for i in st.session_state.sepet)
        except:
            total_checkout_price = 0.0
        
        for item in st.session_state.sepet:
            try:
                p_val = float(item['price'])
            except:
                p_val = 0.0
            st.markdown(f"""
            <div style="background-color:#0d111c; padding:12px; border-radius:8px; margin-bottom:10px; border:1px solid #1e293b;">
                <span style="font-size:0.9rem; font-weight:500; color:#f3f4f6;">{item['title']}</span><br>
                <span style="color:#a78bfa; font-size:0.85rem;">Kaynak Depo: {item.get('source_depo','Ana Dağıtım')}</span>
                <div style="text-align:right; font-weight:600; color:#4ade80;">₺{p_val:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"### Toplam Ödeme: ₺{total_checkout_price:.2f}")
        st.caption("Fiyatlandırmaya lojistik transfer, gümrükleme ve yasal vergiler dahildir.")
        
        if st.button("🔒 İşlemi Onayla ve Ödemeyi Kapat", use_container_width=True, type="primary"):
            with st.spinner("Finansal mutabakat ve iş emri akışları tetikleniyor..."):
                import time
                time.sleep(1.2)
            st.success("Ödeme başarıyla doğrulandı! Ürün tedarik emirleri ilgili mağaza depolarına iletildi.")
            st.balloons()
            st.session_state.sepet = []
            st.session_state.page = "main"
                
    if st.button("← Pazaryerine Geri Dön"):
        st.session_state.page = "main"
        st.rerun()

elif st.session_state.page == "main":
    
    if st.session_state.role == "Mağaza":
        st.title(f"🏪 {st.session_state.depo_name} — Kontrol Masası")
        st.write("Analiz edilecek ürün grubunu tanımlayın ve yapay zeka çalışma stratejisini belirleyin.")
        
        if "SESSION_ID" not in st.session_state:
            st.session_state.SESSION_ID = str(uuid.uuid4())
            
        col_inp, col_strat = st.columns([3, 2])
        with col_inp:
            user_input = st.text_input("Aranacak Ürün Grubu / Kategori Verisi", placeholder="Örn: custom mechanical keyboard...")
        with col_strat:
            ai_strategy = st.selectbox(
                "🧠 Yapay Zeka Operasyon Stratejisi",
                [
                    "Premium Markalama & Kurumsal Dil",
                    "Sosyal Medya ve Trend Odaklı",
                    "Maksimum Kârlılık ve Fiyat Optimizasyonu",
                    "Teknik Standartlar ve Mühendislik Odaklı",
                    "Dengeli Standart Dağıtım"
                ]
            )
            
        search_triggered = st.button("Tedarik Hatlarını Çözümle", type="primary", use_container_width=True)
            
        if search_triggered:
            if not user_input.strip():
                st.warning("İşlem başlatabilmek için geçerli bir kategori verisi girmelisiniz.")
            else:
                with st.spinner("Tedarik ağları taranıyor, özgün ürün içerikleri yapılandırılıyor..."):
                    refined_request = f"{user_input} [İŞLETİM STRATEJİSİ: {ai_strategy}. Yapay zeka kalıplarından uzak, tamamen özgün, vurucu ve teknik veriye dayalı metinler üret.]"
                    
                    initial_state = {
                        "session_id": st.session_state.SESSION_ID,
                        "user_request": refined_request,
                        "trend_keywords": [],
                        "raw_product_data": {},
                        "optimized_content": {},
                        "shipping_details": {},
                        "is_data_valid": False,
                        "retry_count": 0,
                        "trust_scores": {},
                        "data_source": "",
                        "log_history": []
                    }
                    try:
                        final_state = graph.invoke(initial_state)
                        raw_data = final_state.get('raw_product_data', {})
                        state_products = raw_data.get('products', []) if isinstance(raw_data, dict) else []
                        
                        st.session_state.last_search_results = {
                            "products": state_products,
                            "optimized": final_state.get("optimized_content", {}),
                            "shipping": final_state.get("shipping_details", {}),
                            "trust_scores": final_state.get("trust_scores", {}),
                            "logs": final_state.get("log_history", [])
                        }
                    except Exception as e:
                        st.error(f"Sistem Grafik Hatası: {str(e)}")

        if st.session_state.last_search_results:
            res = st.session_state.last_search_results
            tab1, tab2 = st.tabs(["🔍 Çözümlenen Ürün Listesi", "📄 Sistem İşlem Günlüğü"])
            
            with tab1:
                if not res["products"]:
                    st.info("Kriterlere uygun herhangi bir ürün verisi bulunamadı.")
                else:
                    st.markdown('<div class="control-panel-bar">', unsafe_allow_html=True)
                    ctrl_col1, ctrl_col2 = st.columns(2)
                    with ctrl_col1:
                        sort_m = st.selectbox(
                            "Sıralama Seçenekleri",
                            ["Önerilen Sıralama", "Fiyat: Düşükten Yükseğe", "Fiyat: Yüksekten Düşüğe"],
                            key="magaza_sort"
                        )
                    with ctrl_col2:
                        layout_m = st.radio(
                            "📐 Görünüm Formatı",
                            ["Klasik Liste", "Izgara (Grid)"],
                            horizontal=True,
                            key="magaza_layout"
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                    display_products = list(res["products"])
                    
                    def get_price_for_sorting(prod):
                        p_id = prod.get("id")
                        sh_data = res["shipping"].get(p_id, {})
                        try:
                            return float(sh_data.get('suggested_sale_price_try', 0))
                        except:
                            return 0.0

                    if sort_m == "Fiyat: Düşükten Yükseğe":
                        display_products.sort(key=get_price_for_sorting)
                    elif sort_m == "Fiyat: Yüksekten Düşüğe":
                        display_products.sort(key=get_price_for_sorting, reverse=True)

                    if layout_m == "Izgara (Grid)":
                        grid_cols = st.columns(3)
                        for index, p in enumerate(display_products):
                            p_id = p.get("id")
                            ct = res["optimized"].get(p_id, {})
                            sh = res["shipping"].get(p_id, {})
                            t_score = res["trust_scores"].get(p_id, 100)
                            
                            try:
                                s_price = float(sh.get('suggested_sale_price_try', 0))
                            except:
                                s_price = 0.0
                                
                            is_stored = any(item["id"] == p_id and item.get("source_depo") == st.session_state.depo_name for item in st.session_state.depo)
                            
                            with grid_cols[index % 3]:
                                st.markdown(f"""
                                <div class="product-master-card">
                                    <div class="product-title-box" style="font-size:1.05rem; flex-direction:column; align-items:flex-start;">
                                        <div style="font-weight:700;">{ct.get('seo_title', p.get('name'))[:40]}...</div>
                                        <span class="{ 'trust-badge-high' if t_score >= 70 else 'trust-badge-low' }">Güven: {t_score}/100</span>
                                    </div>
                                    <div class="product-desc-box" style="font-size:0.85rem; min-height:120px;">
                                        {ct.get('seo_description', 'İçerik verisi işlenemedi.')[:140]}...
                                    </div>
                                    <div class="product-meta-strip">
                                        🚀 {sh.get('display_text', 'Hesaplanıyor')[:30]}...
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                st.markdown(f"**Satış:** <span style='color:#4ade80;font-weight:600;'>₺{s_price:.2f}</span>", unsafe_allow_html=True)
                                
                                if is_stored:
                                    st.button("✅ İşlendi", key=f"grid_btn_added_{p_id}_{index}", disabled=True, use_container_width=True)
                                else:
                                    if st.button("📥 Kaydet", key=f"grid_btn_add_{p_id}_{index}", use_container_width=True, type="primary"):
                                        st.session_state.depo.append({
                                            "id": p_id,
                                            "title": ct.get("seo_title", p.get("name")),
                                            "description": ct.get("seo_description", ""),
                                            "price": s_price,
                                            "shipping": sh.get("display_text", ""),
                                            "trust_score": t_score,
                                            "source_depo": st.session_state.depo_name
                                        })
                                        st.toast(f"Ürün envantere eklendi.")
                                        st.rerun()
                                st.markdown("<br>", unsafe_allow_html=True)
                    else:
                        for p in display_products:
                            p_id = p.get("id")
                            ct = res["optimized"].get(p_id, {})
                            sh = res["shipping"].get(p_id, {})
                            t_score = res["trust_scores"].get(p_id, 100)
                            
                            try:
                                s_price = float(sh.get('suggested_sale_price_try', 0))
                            except:
                                s_price = 0.0
                                
                            is_stored = any(item["id"] == p_id and item.get("source_depo") == st.session_state.depo_name for item in st.session_state.depo)
                            
                            st.markdown(f"""
                            <div class="product-master-card">
                                <div class="product-title-box">
                                    <span>{ct.get('seo_title', p.get('name'))}</span>
                                    <span class="{ 'trust-badge-high' if t_score >= 70 else 'trust-badge-low' }">Güven: {t_score}/100</span>
                                </div>
                                <div class="product-desc-box">
                                    {ct.get('seo_description', 'İçerik verisi işlenemedi.')}
                                </div>
                                <div class="product-meta-strip">
                                    🚀 Lojistik Rotası: {sh.get('display_text', 'Hesaplanıyor')}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            col_price, col_action = st.columns([1, 1])
                            with col_price:
                                st.markdown(f"**Önerilen Satış:** <span style='color:#4ade80;font-weight:600;font-size:1.2rem;'>₺{s_price:.2f}</span>", unsafe_allow_html=True)
                                
                            with col_action:
                                if is_stored:
                                    st.button("✅ Envantere İşlendi", key=f"btn_added_{p_id}", disabled=True, use_container_width=True)
                                else:
                                    if st.button("📥 Ürünü Depoma Kaydet", key=f"btn_add_{p_id}", use_container_width=True, type="primary"):
                                        st.session_state.depo.append({
                                            "id": p_id,
                                            "title": ct.get("seo_title", p.get("name")),
                                            "description": ct.get("seo_description", ""),
                                            "price": s_price,
                                            "shipping": sh.get("display_text", ""),
                                            "trust_score": t_score,
                                            "source_depo": st.session_state.depo_name
                                        })
                                        st.toast(f"Ürün, {st.session_state.depo_name} envanter hattına işlendi.")
                                        st.rerun()
                            st.markdown("<br>", unsafe_allow_html=True)
                        
            with tab2:
                st.markdown("<div style='background-color: #09090b; border: 1px solid #1e293b; padding: 18px; border-radius: 10px; max-height: 350px; overflow-y: auto; font-family: monospace;'>", unsafe_allow_html=True)
                for log in res["logs"]:
                    if "HATA" in log.upper() or "ERROR" in log.upper():
                        st.markdown(f"<div style='color: #f87171; margin: 4px 0;'>❌ {log}</div>", unsafe_allow_html=True)
                    elif "BAŞARI" in log.upper() or "SUCCESS" in log.upper():
                        st.markdown(f"<div style='color: #4ade80; margin: 4px 0;'>✅ {log}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='color: #a1a1aa; margin: 4px 0;'>🔹 {log}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state.role == "Kullanıcı":
        st.title("🛒 Frizbi Dağıtık Pazaryeri Havuzu")
        st.write("Sistemdeki bağımsız ticari depolar tarafından onaylanıp arz edilen güncel konsolide ürünler.")
        
        if not st.session_state.depo:
            st.warning("Şu anda sistem genelinde aktif ürün arzı bulunmuyor. Rol değiştirerek mağaza modundan ürün ekleyebilirsiniz.")
        else:
            st.markdown('<div class="control-panel-bar">', unsafe_allow_html=True)
            cust_col1, cust_col2 = st.columns(2)
            with cust_col1:
                sort_c = st.selectbox(
                    "Sıralama Seçenekleri",
                    ["Önerilen Sıralama", "Fiyat: Düşükten Yükseğe", "Fiyat: Yüksekten Düşüğe"],
                    key="kullanici_sort"
                )
            with cust_col2:
                layout_c = st.radio(
                    "📐 Görünüm Formatı",
                    ["Klasik Liste", "Izgara (Grid)"],
                    horizontal=True,
                    key="kullanici_layout"
                )
            st.markdown('</div>', unsafe_allow_html=True)

            display_depo = list(st.session_state.depo)
            
            if sort_c == "Fiyat: Düşükten Yükseğe":
                display_depo.sort(key=lambda x: float(x.get('price', 0)))
            elif sort_c == "Fiyat: Yüksekten Düşüğe":
                display_depo.sort(key=lambda x: float(x.get('price', 0)), reverse=True)

            if layout_c == "Izgara (Grid)":
                grid_cols_c = st.columns(3)
                for index, item in enumerate(display_depo):
                    try:
                        i_price = float(item['price'])
                    except:
                        i_price = 0.0
                        
                    with grid_cols_c[index % 3]:
                        st.markdown(f"""
                        <div class="product-master-card">
                            <div class="product-title-box" style="font-size:1.05rem; flex-direction:column; align-items:flex-start;">
                                <div style="font-weight:700;">{item['title'][:40]}...</div>
                                <span class="depo-header-badge">🏪 {item.get('source_depo', 'Ana Depo')[:15]}...</span>
                            </div>
                            <div class="product-desc-box" style="font-size:0.85rem; min-height:120px;">
                                {item['description'][:140]}...
                            </div>
                            <div class="product-meta-strip">
                                📦 {item['shipping'][:30]}...
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"**Birim Fiyatı:** <span style='font-size: 1.1rem; color: #4ade80;'>₺{i_price:.2f}</span>", unsafe_allow_html=True)
                        stable_btn_key = f"grid_cust_buy_{item['id']}_{index}_{item.get('source_depo', '').replace(' ', '_')}"
                        if st.button("Sepete Ekle", key=stable_btn_key, use_container_width=True, type="primary"):
                            st.session_state.sepet.append(item)
                            st.toast(f"✓ Ürün sepetinize eklendi.")
                            st.rerun()
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                for item in display_depo:
                    try:
                        i_price = float(item['price'])
                    except:
                        i_price = 0.0

                    st.markdown(f"""
                    <div class="product-master-card">
                        <div class="product-title-box">
                            <span>{item['title']}</span>
                            <span class="depo-header-badge">🏪 Satıcı: {item.get('source_depo', 'Ana Depo')}</span>
                        </div>
                        <div class="product-desc-box">
                            {item['description']}
                        </div>
                        <div class="product-meta-strip">
                            📦 Lojistik Durumu: {item['shipping']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c_inf, c_buy = st.columns([3, 1])
                    with c_inf:
                        st.markdown(f"**Birim Satış Fiyatı:** <span style='font-size: 1.3rem; color: #4ade80;'>₺{i_price:.2f}</span>", unsafe_allow_html=True)
                    with c_buy:
                        stable_btn_key = f"customer_buy_{item['id']}_{item.get('source_depo', '').replace(' ', '_')}"
                        if st.button("Sepete Ekle", key=stable_btn_key, use_container_width=True, type="primary"):
                            st.session_state.sepet.append(item)
                            st.toast(f"✓ Ürün sepetinize eklendi.")
                            st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)