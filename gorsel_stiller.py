import streamlit as st
import base64

def get_base64_of_bin_file(bin_file):
    """Görselleri HTML/CSS içinde kullanabilmek için Base64 formatına çevirir."""
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def arka_plani_yukle(bg_image_path="arkaplan.jpg"):
    """arkaplan.jpg dosyasını okuyup uygulamanın tüm sayfalarına arka plan olarak döşer."""
    try:
        bin_str = get_base64_of_bin_file(bg_image_path)
        page_bg_img = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except FileNotFoundError:
        # Eğer resim bulunamazsa sistem çökmesin, standart arka planla devam etsin
        pass

def genel_css_ayarlarini_yukle():
    """Uygulamanın genel kalabalıklarını (Streamlit menüleri vb.) gizler ve tabloları şıklaştırır."""
    st.markdown("""
    <style>
    /* Streamlit üst menüsünü ve alt bilgiyi gizle (Daha mobil/profesyonel görünüm) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Genel tablo köşe yuvarlamaları */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

def hakem_mobil_css_yukle():
    """Gözlemci Hakem Panelindeki devasa, kesilmeyen mobil skor butonlarının CSS kodları."""
    st.markdown("""
    <style>
    /* Kapsayıcının yüksekliğini artırarak butonların yarım kalmasını (kesilmesini) engelle */
    div[data-testid="stNumberInput"] {
        min-height: 75px !important;
    }
    div[data-testid="stNumberInput"] > div {
        min-height: 55px !important;
        align-items: center !important;
    }
    
    /* + ve - butonlarını devasa ve estetik yap */
    button[data-testid="stNumberInputStepDown"], 
    button[data-testid="stNumberInputStepUp"] {
        width: 50px !important;
        height: 50px !important;
        background-color: #e6ecef !important;
        border-radius: 12px !important;
        border: 1px solid #cbd5e1 !important;
    }
    
    /* Butonlar ile ortadaki kutu arasına boşluk bırak */
    button[data-testid="stNumberInputStepUp"] {
        margin-left: 10px !important;
    }
    button[data-testid="stNumberInputStepDown"] {
        margin-right: 10px !important;
    }

    /* Buton içindeki ok işaretlerini büyüt */
    button[data-testid="stNumberInputStepDown"] svg, 
    button[data-testid="stNumberInputStepUp"] svg {
        width: 22px !important;
        height: 22px !important;
        fill: #0B3B24 !important;
    }
    
    /* Ortadaki skor rakamını ve kutu yüksekliğini eşitle */
    input[type="number"] {
        font-size: 26px !important;
        font-weight: bold !important;
        text-align: center !important;
        height: 50px !important;
    }
    </style>
    """, unsafe_allow_html=True)
