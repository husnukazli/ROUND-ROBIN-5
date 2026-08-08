import streamlit as st
import base64

def arkaplan_ekle(resim_yolu="arkaplan.jpg"):
    try:
        with open(resim_yolu, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpg;base64,{encoded_string}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        pass

def genel_css_yukle(admin_mi, kaptan_mi, hakem_mi):
    st.markdown("""
    <style>
        footer {visibility: hidden !important;}
        
        .dev-buton .stButton > button {
            border-radius: 12px;
            min-height: 80px !important; 
            font-size: 18px !important;
            font-weight: 600 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: all 0.2s ease-in-out;
        }
        .dev-buton .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
    </style>
    """, unsafe_allow_html=True)

    if not admin_mi and not kaptan_mi and not hakem_mi:
        st.markdown("""
        <style>
            [data-testid="stToolbar"] {visibility: hidden !important;}
        </style>
        """, unsafe_allow_html=True)

def hakem_mobil_css_yukle():
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
