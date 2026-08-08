import streamlit as st
import base64


@st.cache_data
def _resmi_base64_oku(resim_yolu):
    """Arkaplan görselini bir kez okuyup base64'e çevirir ve önbelleğe alır.
    Bunu cache'lemezsek, Streamlit'in her rerun'unda (ki bu uygulamada çok sık
    oluyor) disk okuma + base64 encode işlemi tekrar tekrar yapılır; mobil
    bağlantılarda bu gecikme özellikle hissedilir. Cache sayesinde sadece
    ilk seferde okunur."""
    with open(resim_yolu, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


def arkaplan_ekle(resim_yolu="arkaplan.jpg"):
    try:
        encoded_string = _resmi_base64_oku(resim_yolu)

        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpg;base64,{encoded_string}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}

            /* iOS Safari'de background-attachment: fixed düzgün çalışmaz; bazı
               cihazlarda kaymaya/takılmaya sebep olur. Mobilde scroll'a dönüyoruz. */
            @media (max-width: 768px) {{
                .stApp {{
                    background-attachment: scroll;
                }}
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

        /* Dokunmatik ekranlarda varsayılan gri/mavi "tap flash" efektini kaldırıp
           kendi :active stilimizle daha "native app" hissi veriyoruz. */
        button, [role="button"] {
            -webkit-tap-highlight-color: transparent;
        }

        /* Aşağı çekip yenileme (pull-to-refresh) ve kenar sekmesi (overscroll bounce)
           mobil tarayıcılarda kazara tetiklenip sayfayı yenileyebiliyor; kapatıyoruz. */
        html, body {
            overscroll-behavior-y: contain;
        }

        /* iOS Safari, font-size 16px'in altındaki bir input'a dokunulduğunda sayfayı
           otomatik yakınlaştırır (can sıkıcı bir "zıplama" hissi verir). Aksi
           belirtilmedikçe tüm form elemanlarını güvenli sınırın üstünde tutuyoruz. */
        input, select, textarea {
            font-size: 16px !important;
        }

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
        .dev-buton .stButton > button:active {
            transform: translateY(0px) scale(0.97);
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
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
    """Gözlemci hakemin maç esnasında sahada, genelde tek elle ve güneş altında
    kullandığı skor giriş ekranı için dokunmatik-öncelikli stil.
    Sadece bu ekran render edilirken çağrılmalı (genel_css_yukle ile karıştırıp
    tüm uygulamaya uygulamayın; masaüstü admin skor tablosundaki dar sütunları bozar).
    """
    st.markdown("""
    <style>
    /* Kapsayıcının yüksekliğini artırarak butonların yarım kalmasını (kesilmesini) engelle */
    div[data-testid="stNumberInput"] {
        min-height: 82px !important;
    }
    div[data-testid="stNumberInput"] div {
        align-items: center !important;
    }

    /* Tarayıcının kendi (spinner) ok tuşlarını gizle: bazı masaüstü tarayıcılarda
       Streamlit'in büyük butonlarının yanına bir de küçücük native ok ikonu
       ekleniyor - tam da şikayet edilen "küçük ve karıştırıcı" tuş bu olabiliyor. */
    input[type="number"]::-webkit-outer-spin-button,
    input[type="number"]::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    input[type="number"] {
        -moz-appearance: textfield;
        font-size: 28px !important;
        font-weight: 800 !important;
        text-align: center !important;
        height: 56px !important;
        user-select: none;
    }

    /* + ve - butonlarını devasa, birbirinden renkle ayrılan, parmak dostu yap.
       Kırmızı/yeşil ayrımı güneş altında bile hangisinin hangisi olduğunu
       düşünmeden anlamayı sağlıyor; ayrıca aralarında bariz boşluk var. */
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"] {
        width: 56px !important;
        height: 56px !important;
        min-width: 56px !important;
        border-radius: 14px !important;
        border: none !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.18) !important;
        transition: transform 0.08s ease-in-out, box-shadow 0.08s ease-in-out !important;
        touch-action: manipulation !important;
        cursor: pointer !important;
        -webkit-tap-highlight-color: transparent !important;
    }

    button[data-testid="stNumberInputStepDown"] {
        background-color: #dc2626 !important;   /* kırmızı: azalt */
        margin-right: 12px !important;
    }
    button[data-testid="stNumberInputStepUp"] {
        background-color: #16a34a !important;   /* yeşil: artır */
        margin-left: 12px !important;
    }

    /* Basılı tutulduğunda hafif küçülme -> dokunsal geri bildirim yerine geçen
       görsel "bastım" hissi (telefonda haptic yoksa bu önemli). */
    button[data-testid="stNumberInputStepDown"]:active,
    button[data-testid="stNumberInputStepUp"]:active {
        transform: scale(0.90) !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.15) !important;
    }

    button[data-testid="stNumberInputStepDown"]:disabled,
    button[data-testid="stNumberInputStepUp"]:disabled {
        background-color: #cbd5e1 !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
    }

    /* Ok/artı-eksi ikonlarını büyüt ve beyaz yap ki renkli zemin üstünde net görünsün */
    button[data-testid="stNumberInputStepDown"] svg,
    button[data-testid="stNumberInputStepUp"] svg {
        width: 24px !important;
        height: 24px !important;
        fill: #ffffff !important;
    }

    /* Çok dar ekranlarda (ör. iPhone SE) 3 set sütunu yan yana sıkışabilir;
       buton boyutunu biraz kısıp okunurluğu koruyoruz. */
    @media (max-width: 400px) {
        button[data-testid="stNumberInputStepDown"],
        button[data-testid="stNumberInputStepUp"] {
            width: 46px !important;
            height: 46px !important;
            min-width: 46px !important;
        }
        button[data-testid="stNumberInputStepDown"] { margin-right: 6px !important; }
        button[data-testid="stNumberInputStepUp"] { margin-left: 6px !important; }
        input[type="number"] {
            font-size: 22px !important;
            height: 46px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
