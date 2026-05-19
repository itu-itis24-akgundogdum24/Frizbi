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

# ==============================================================