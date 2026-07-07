import streamlit as st
import sys
import subprocess
import pandas as pd
import json
import os
import datetime
import base64
import shutil
import re
from fpdf import FPDF

# --- GENEL SAYFA AYARLARI ---
st.set_page_config(page_title="Tenis Turnuva Otomasyonu", page_icon="🎾", layout="wide")
st.title("🎾 Tenis Turnuva Yönetim Sistemi")

VERI_DOSYASI = "turnuva_veri.json"
BELGELER_KLASORU = "turnuva_belgeleri"

# Belgeler klasörü yoksa oluştur
if not os.path.exists(BELGELER_KLASORU):
    os.makedirs(BELGELER_KLASORU)

# ==============================================================================
# SİSTEM FONKSİYONLARI (ORTAK VERİ YAZMA, OKUMA VE PDF)
# ==============================================================================

# Doğal sıralama fonksiyonu (Grup isimlerindeki rakamları ve harfleri doğru sıralamak için)
def dogal_sirala(liste):
    def _natural_keys(text):
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]
    return sorted(liste, key=_natural_keys)

# Türkçe karakter font kontrolü
FONT_YUKLENDI = os.path.exists("arial.ttf")

def to_pdf_text(text):
    if FONT_YUKLENDI:
        return str(text)
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def generate_pdf(df, baslik):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    if FONT_YUKLENDI:
        try:
            pdf.add_font("ArialTR", "", "arial.ttf", uni=True)
            pdf.set_font("ArialTR", "", 14)
        except:
            pdf.set_font("Arial", 'B', 14)
    else:
        pdf.set_font("Arial", 'B', 14)
        
    pdf.cell(0, 10, to_pdf_text(baslik), ln=True, align='C')
    pdf.ln(5)
    
    if FONT_YUKLENDI:
        pdf.set_font("ArialTR", "", 10)
    else:
        pdf.set_font("Arial", '', 10)

    if len(df.columns) > 0:
        col_width = 270 / len(df.columns)
        for col in df.columns:
            pdf.cell(col_width, 10, to_pdf_text(col), border=1)
        pdf.ln()
        
        if FONT_YUKLENDI:
            pdf.set_font("ArialTR", "", 9)
        else:
            pdf.set_font("Arial", '', 9)
            
        for _, row in df.iterrows():
            for item in row:
                pdf.cell(col_width, 8, to_pdf_text(str(item)), border=1)
            pdf.ln()
    
    return bytes(pdf.output())

def generate_combined_standings_pdf(gruplar_dict):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    for grup_adi, df in gruplar_dict.items():
        if FONT_YUKLENDI:
            try:
                pdf.add_font("ArialTR", "", "arial.ttf", uni=True)
                pdf.set_font("ArialTR", "", 12)
            except:
                pdf.set_font("Arial", 'B', 12)
        else:
            pdf.set_font("Arial", 'B', 12)
            
        pdf.cell(0, 10, to_pdf_text(grup_adi + " Puan Durumu"), ln=True, align='L')
        
        if len(df.columns) > 0:
            if FONT_YUKLENDI:
                pdf.set_font("ArialTR", "", 10)
            else:
                pdf.set_font("Arial", 'B', 10)
                
            col_width = 270 / len(df.columns)
            for col in df.columns:
                pdf.cell(col_width, 8, to_pdf_text(col), border=1)
            pdf.ln()
            
            if FONT_YUKLENDI:
                pdf.set_font("ArialTR", "", 9)
            else:
                pdf.set_font("Arial", '', 9)
                
            for _, row in df.iterrows():
                for item in row:
                    pdf.cell(col_width, 8, to_pdf_text(str(item)), border=1)
                pdf.ln()
        pdf.ln(5)
    return bytes(pdf.output())

def ortak_veriyi_kaydet():
    data = {
        "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
        "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
        "takim_kadrolari": st.session_state.takim_kadrolari,
        "grup_formatlari": st.session_state.get("grup_formatlari", {}),
        "grup_kategorileri": st.session_state.get("grup_kategorileri", {}),
        "duyuru_metni": st.session_state.get("duyuru_metni", ""),
        "takim_havuzu": st.session_state.get("takim_havuzu", {})
    }
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def ortak_veriyi_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.session_state.skor_tablosu = pd.DataFrame(data["skor_tablosu"])
            
            mp_df = pd.DataFrame(data["mac_programi"])
            if "T1 Oyuncu" not in mp_df.columns:
                mp_df["T1 Oyuncu"] = ""
                mp_df["T2 Oyuncu"] = ""
            if "Kazanan" not in mp_df.columns:
                mp_df["Kazanan"] = ""
            st.session_state.mac_programi = mp_df
            st.session_state.takim_kadrolari = data["takim_kadrolari"]
            st.session_state.grup_formatlari = data.get("grup_formatlari", {})
            st.session_state.grup_kategorileri = data.get("grup_kategorileri", {})
            st.session_state.duyuru_metni = data.get("duyuru_metni", "")
            st.session_state.takim_havuzu = data.get("takim_havuzu", {})
        except Exception:
            pass 

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# ==============================================================================
# HAFIZA (SESSION STATE) BAŞLATMA
# ==============================================================================
if "admin_mi" not in st.session_state:
    st.session_state.admin_mi = False

if "expand_all" not in st.session_state:
    st.session_state.expand_all = False

if "selected_date_filter" not in st.session_state:
    st.session_state.selected_date_filter = datetime.date.today()

if "grup_formatlari" not in st.session_state:
    st.session_state.grup_formatlari = {}
    
if "grup_kategorileri" not in st.session_state:
    st.session_state.grup_kategorileri = {}
    
if "duyuru_metni" not in st.session_state:
    st.session_state.duyuru_metni = ""

if "takim_havuzu" not in st.session_state:
    st.session_state.takim_havuzu = {}

if 'skor_tablosu' not in st.session_state:
    if os.path.exists(VERI_DOSYASI):
        ortak_veriyi_yukle()
    else:
        st.session_state.skor_tablosu = pd.DataFrame(columns=[
            "Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", 
            "T1_Oyuncu", "T2_Oyuncu", 
            "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"
        ])
        st.session_state.mac_programi = pd.DataFrame(columns=[
            "Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Canlı Skor", "Kazanan"
        ])
        st.session_state.takim_kadrolari = {} 
        st.session_state.grup_formatlari = {}
        st.session_state.grup_kategorileri = {}

if 'mac_programi' in st.session_state:
    if "T1 Oyuncu" not in st.session_state.mac_programi.columns:
        st.session_state.mac_programi["T1 Oyuncu"] = ""
        st.session_state.mac_programi["T2 Oyuncu"] = ""
    if "Kazanan" not in st.session_state.mac_programi.columns:
        st.session_state.mac_programi["Kazanan"] = ""

# ==============================================================================
# BAŞHAKEM YÖNETİM GİRİŞİ (SOL SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.markdown("### 👨‍⚖️ Turnuva Yönetim Girişi")
    if not st.session_state.admin_mi:
        girilen_sifre = st.text_input("Yönetici Şifresi:", type="password")
        if st.button("🔒 Giriş Yap"):
            if girilen_sifre == "zonguldak2026":
                st.session_state.admin_mi = True
                st.success("✅ Başhakem Yetkisi Aktif!")
                st.rerun()
            else:
                st.error("❌ Hatalı Şifre!")
    else:
        st.write("🟢 **Mod:** Başhakem (Yönetici)")
        if st.button("🔓 Çıkış Yap (İzleyici Modu)"):
            st.session_state.admin_mi = False
            st.rerun()

# ==============================================================================
# SİLBAŞTAN SKOR DOĞRULAMA VE FİKSTÜR ÜRETECİ MOTORU
# ==============================================================================
def set_gecerli_mi(t1, t2, is_set3=False):
    if t1 == 0 and t2 == 0:
        return True, ""
    if t1 < 0 or t2 < 0:
        return False, "Skorlar negatif olamaz."
    
    max_s, min_s = max(t1, t2), min(t1, t2)
    diff = max_s - min_s
    
    if is_set3:
        if max_s >= 10:
            if max_s == 10 and min_s <= 8: return True, ""
            elif max_s > 10 and diff == 2: return True, ""
            else: return False, "Süper Tie-Break kurallarına uymuyor (Örn: 10-8 veya 12-10 olmalıdır)."
        else:
            if max_s < 6: return False, "Set en az 6 oyun olmalıdır."
            if max_s == 6 and diff >= 2: return True, ""
            if max_s == 7 and (diff == 2 or diff == 1): return True, ""
            return False, "Geçersiz normal set skoru."
    else:
        if max_s < 6: return False, "Set en az 6 oyun olmalıdır."
        if max_s == 6 and diff >= 2: return True, ""
        if max_s == 7 and (diff == 2 or diff == 1): return True, ""
        return False, "Geçersiz set skoru."

def eslesmeleri_olustur(grup_adi, takimlar, grup_tipi, format_secimi):
    if grup_tipi == "3'lü Grup":
        base_matches = [
            {"Gün": "1. Gün", "Eşleşme": "2 ve 3", "Takım 1": takimlar[1], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "1 ve 3", "Takım 1": takimlar[0], "Takım 2": takimlar[2]},
            {"Gün": "3. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]},
        ]
    elif grup_tipi == "4'lü Grup":
        base_matches = [
            {"Gün": "1. Gün", "Eşleşme": "1 ve 4", "Takım 1": takimlar[0], "Takım 2": takimlar[3]},
            {"Gün": "1. Gün", "Eşleşme": "2 ve 3", "Takım 1": takimlar[1], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "1 ve 3", "Takım 1": takimlar[0], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "2 ve 4", "Takım 1": takimlar[1], "Takım 2": takimlar[3]},
            {"Gün": "3. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]},
            {"Gün": "3. Gün", "Eşleşme": "3 ve 4", "Takım 1": takimlar[2], "Takım 2": takimlar[3]},
        ]
    elif grup_tipi == "5'li Grup":
        base_matches = [
            {"Gün": "1. Gün", "Eşleşme": "2 ve 5", "Takım 1": takimlar[1], "Takım 2": takimlar[4]},
            {"Gün": "1. Gün", "Eşleşme": "3 ve 4", "Takım 1": takimlar[2], "Takım 2": takimlar[3]},
            {"Gün": "2. Gün", "Eşleşme": "1 ve 5", "Takım 1": takimlar[0], "Takım 2": takimlar[4]},
            {"Gün": "2. Gün", "Eşleşme": "2 ve 3", "Takım 1": takimlar[1], "Takım 2": takimlar[2]},
            {"Gün": "3. Gün", "Eşleşme": "1 ve 4", "Takım 1": takimlar[0], "Takım 2": takimlar[3]},
            {"Gün": "3. Gün", "Eşleşme": "3 ve 5", "Takım 1": takimlar[2], "Takım 2": takimlar[4]},
            {"Gün": "4. Gün", "Eşleşme": "1 ve 3", "Takım 1": takimlar[0], "Takım 2": takimlar[2]},
            {"Gün": "4. Gün", "Eşleşme": "2 ve 4", "Takım 1": takimlar[1], "Takım 2": takimlar[3]},
            {"Gün": "5. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]},
            {"Gün": "5. Gün", "Eşleşme": "4 ve 5", "Takım 1": takimlar[3], "Takım 2": takimlar[4]},
        ]
    else: 
        base_matches = [
            {"Gün": "1. Gün", "Eşleşme": "1 ve 6", "Takım 1": takimlar[0], "Takım 2": takimlar[5]},
            {"Gün": "1. Gün", "Eşleşme": "2 ve 5", "Takım 1": takimlar[1], "Takım 2": takimlar[4]},
            {"Gün": "1. Gün", "Eşleşme": "3 ve 4", "Takım 1": takimlar[2], "Takım 2": takimlar[3]},
            {"Gün": "2. Gün", "Eşleşme": "1 ve 5", "Takım 1": takimlar[0], "Takım 2": takimlar[4]},
            {"Gün": "2. Gün", "Eşleşme": "2 ve 3", "Takım 1": takimlar[1], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "4 ve 6", "Takım 1": takimlar[3], "Takım 2": takimlar[5]},
            {"Gün": "3. Gün", "Eşleşme": "1 ve 4", "Takım 1": takimlar[0], "Takım 2": takimlar[3]},
            {"Gün": "3. Gün", "Eşleşme": "5 ve 3", "Takım 1": takimlar[4], "Takım 2": takimlar[2]},
            {"Gün": "3. Gün", "Eşleşme": "2 ve 6", "Takım 1": takimlar[1], "Takım 2": takimlar[5]},
            {"Gün": "4. Gün", "Eşleşme": "1 ve 3", "Takım 1": takimlar[0], "Takım 2": takimlar[2]},
            {"Gün": "4. Gün", "Eşleşme": "4 ve 2", "Takım 1": takimlar[3], "Takım 2": takimlar[1]},
            {"Gün": "4. Gün", "Eşleşme": "5 ve 6", "Takım 1": takimlar[4], "Takım 2": takimlar[5]},
            {"Gün": "5. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]},
            {"Gün": "5. Gün", "Eşleşme": "4 ve 5", "Takım 1": takimlar[3], "Takım 2": takimlar[4]},
            {"Gün": "5. Gün", "Eşleşme": "3 ve 6", "Takım 1": takimlar[2], "Takım 2": takimlar[5]},
        ]
    
    if format_secimi == "5 Maçlık (3 Tek, 2 Çift)":
        branslar = ["1. Tekler", "2. Tekler", "3. Tekler", "1. Çiftler", "2. Çiftler"]
    else:
        branslar = ["1. Tekler", "2. Tekler", "Çiftler"]

    program = []
    for m in base_matches:
        for brans in branslar:
            satir = m.copy()
            satir["Branş"] = brans
            satir["Grup"] = grup_adi
            satir.update({
                "T1_Oyuncu": "", "T2_Oyuncu": "",
                "1.Set T1": 0, "1.Set T2": 0, "2.Set T1": 0, "2.Set T2": 0, "3.Set T1": 0, "3.Set T2": 0
            })
            program.append(satir)
    return program

# ==============================================================================
# SEKME STRÜKTÜRÜ
# ==============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👥 1. Grup Ayarları", "✍️ 2. Skor Girişi", "🏆 3. Puan Durumu", "📅 4. Maç Programı", "📢 5. Duyurular", "⚙️ 6. Yönetim & Dosya"])

# --- TAB 1: GRUP Ayarları ---
with tab1:
    st.subheader("Turnuva Grupları ve Kadrolar")
    st.info("ℹ️ İpucu: Excel'de sütun başlıklarına 'Takım Adı', altındaki satırlara o takımın oyuncularını yazarak dosya yükleyebilirsiniz.")
    
    if st.session_state.admin_mi:
        # --- EXCEL/CSV YÜKLEME ALANI ---
        with st.expander("📥 Excel / CSV'den Takım ve Oyuncu Havuzu Yükle", expanded=False):
            uploaded_file = st.file_uploader("Takım listesini yükleyin (.xlsx veya .csv)", type=["csv", "xlsx"])
            if uploaded_file:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_havuz = pd.read_csv(uploaded_file)
                    else:
                        df_havuz = pd.read_excel(uploaded_file)
                    
                    yeni_havuz = {}
                    for col in df_havuz.columns:
                        if not "Unnamed" in str(col): # Boş sütunları atla
                            oyuncular = df_havuz[col].dropna().astype(str).tolist()
                            yeni_havuz[str(col).strip()] = [o.strip() for o in oyuncular if o.strip()]
                    
                    st.session_state.takim_havuzu.update(yeni_havuz)
                    ortak_veriyi_kaydet()
                    st.success(f"✅ Başarılı! {len(yeni_havuz)} takım sisteme kaydedildi.")
                except Exception as e:
                    st.error(f"Dosya okuma hatası: {e}. Lütfen formatın doğru olduğundan emin olun.")
            
            if st.session_state.takim_havuzu:
                st.write(f"📊 Sistemde şu an **{len(st.session_state.takim_havuzu)}** hazır takım bulunuyor.")
                if st.button("🗑️ Takım Havuzunu Temizle"):
                    st.session_state.takim_havuzu = {}
                    ortak_veriyi_kaydet()
                    st.rerun()

        st.markdown("---")
        
        # --- GRUP OLUŞTURMA ALANI ---
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            kategori_secimi = st.radio("Kategori:", ["Erkekler", "Kadınlar"], horizontal=True)
        with col_t2:
            grup_tipi = st.radio("Grup Tipi:", ["3'lü Grup", "4'lü Grup", "5'li Grup", "6'lı Grup"], horizontal=True)
        with col_t3:
            format_secimi = st.radio("Müsabaka Maç Formatı:", ["3 Maçlık (2 Tek, 1 Çift)", "5 Maçlık (3 Tek, 2 Çift)"], horizontal=True)
        
        grup_adi = st.text_input("Grup Adı:", placeholder="Örn: 65+ Erkekler A Grubu")
        grup_adi_temiz = grup_adi.strip()
        
        # Kategori Bazlı Çakışma Kontrolü
        baska_gruplardaki_takimlar = {}
        for g_n, g_k in st.session_state.takim_kadrolari.items():
            g_kat = st.session_state.grup_kategorileri.get(g_n, "Erkekler") # Eski kayıtlar varsayılan Erkekler kabul edilir
            if g_n != grup_adi_temiz and g_kat == kategori_secimi:
                for t_n in g_k.keys():
                    baska_gruplardaki_takimlar[t_n] = g_n
                    
        # Havuzu filtrele (Sadece aynı kategoride boşta olan takımları doğal sıralı göster)
        musait_havuz = dogal_sirala([t for t in st.session_state.takim_havuzu.keys() if t not in baska_gruplardaki_takimlar])
        havuz_isimleri = ["✏️ Yeni / Listede Olmayan Takım (Elle Gir)"] + musait_havuz
        
        if grup_tipi == "3'lü Grup": beklenen_sayi = 3
        elif grup_tipi == "4'lü Grup": beklenen_sayi = 4
        elif grup_tipi == "5'li Grup": beklenen_sayi = 5
        else: beklenen_sayi = 6
        
        st.markdown(f"### 🛡️ Takım ve Kadro Seçimi ({beklenen_sayi} Takım)")
        
        takimlar = []
        grup_kadrolari = {}
        kadro_hata = False
        
        cols = st.columns(beklenen_sayi)
        for i in range(beklenen_sayi):
            with cols[i]:
                st.markdown(f"**{i+1}. Takım**")
                secim = st.selectbox(f"{i+1}. Takım Seçimi", options=havuz_isimleri, key=f"sec_takim_{i}", label_visibility="collapsed")
                
                if secim == "✏️ Yeni / Listede Olmayan Takım (Elle Gir)":
                    t_isim = st.text_input("Takım Adı:", key=f"isim_t_{i}", placeholder="Takım Adı Yazın")
                    def_kadro = ""
                else:
                    t_isim = secim
                    def_kadro = "\n".join(st.session_state.takim_havuzu[secim])
                
                oyuncular_raw = st.text_area(f"✍️ Kadro (Her satıra bir kişi)", value=def_kadro, key=f"input_kadro_{i}_{secim}", height=150)
                oyuncu_listesi = [o.strip() for o in oyuncular_raw.split('\n') if o.strip()]
                
                if len(oyuncu_listesi) > 10:
                    st.error("Maksimum 10 oyuncu sınırı aşıldı!")
                    kadro_hata = True
                
                if t_isim:
                    takimlar.append(t_isim)
                    grup_kadrolari[t_isim] = oyuncu_listesi if oyuncu_listesi else ["Belirtilmedi"]

        if st.button("🚀 Grubu ve Fikstürü Oluştur / Güncelle"):
            # Çakışma kontrolü
            cakisan_takimlar = [t for t in takimlar if t in baska_gruplardaki_takimlar]
            
            if cakisan_takimlar:
                hata_detay = ", ".join([f"'{t}' ({baska_gruplardaki_takimlar[t]})" for t in cakisan_takimlar])
                st.error(f"⚠️ Hata: Girdiğiniz takım(lar) {kategori_secimi} kategorisinde zaten başka bir grupta kayıtlı! Bir takım aynı kategoride iki farklı grupta olamaz.\nÇakışanlar: {hata_detay}")
            elif not grup_adi or len(takimlar) != beklenen_sayi or kadro_hata or len(set(takimlar)) != beklenen_sayi:
                st.error("Lütfen grup adını girin, tüm takımları eksiksiz/farklı doldurun ve kurallara uyun.")
            else:
                st.session_state.takim_kadrolari[grup_adi_temiz] = grup_kadrolari
                st.session_state.grup_formatlari[grup_adi_temiz] = format_secimi
                st.session_state.grup_kategorileri[grup_adi_temiz] = kategori_secimi
                
                if not st.session_state.skor_tablosu.empty and grup_adi_temiz in st.session_state.skor_tablosu['Grup'].unique():
                    ortak_veriyi_kaydet()
                    st.success("Mevcut grup bulundu! Kadrolar başarıyla güncellendi, eski fikstür korundu.")
                else:
                    yeni_df = pd.DataFrame(eslesmeleri_olustur(grup_adi_temiz, takimlar, grup_tipi, format_secimi))
                    if st.session_state.skor_tablosu.empty:
                        st.session_state.skor_tablosu = yeni_df
                    else:
                        st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
                    ortak_veriyi_kaydet()
                    st.success("Grup ve fikstür başarıyla oluşturuldu!")
                
        if st.session_state.takim_kadrolari:
            st.markdown("---")
            st.markdown("### 📁 Mevcut Kayıtlı Gruplar ve Kadrolar")
            # KLASÖR LİSTESİ DOĞAL SIRALANDI
            for g_isim in dogal_sirala(list(st.session_state.takim_kadrolari.keys())):
                f_turu = st.session_state.grup_formatlari.get(g_isim, "3 Maçlık (2 Tek, 1 Çift)")
                f_kat = st.session_state.grup_kategorileri.get(g_isim, "Erkekler")
                with st.expander(f"📁 {g_isim} ({f_kat} | {f_turu})"):
                    g_kadro = st.session_state.takim_kadrolari[g_isim]
                    for t_isim in dogal_sirala(list(g_kadro.keys())):
                        st.markdown(f"**🛡️ {t_isim}**")
                        st.write(", ".join(g_kadro[t_isim]) if g_kadro[t_isim] else "Oyuncu yok")
    else:
        st.info("ℹ️ Kadro ve grup tanımlama işlemleri sadece Başhakem yetkisindedir.")
        if st.session_state.takim_kadrolari:
            st.markdown("### 📁 Mevcut Kayıtlı Gruplar ve Kadrolar")
            for g_isim in dogal_sirala(list(st.session_state.takim_kadrolari.keys())):
                f_turu = st.session_state.grup_formatlari.get(g_isim, "3 Maçlık (2 Tek, 1 Çift)")
                f_kat = st.session_state.grup_kategorileri.get(g_isim, "Erkekler")
                with st.expander(f"📁 {g_isim} ({f_kat} | {f_turu})"):
                    g_kadro = st.session_state.takim_kadrolari[g_isim]
                    for t_isim in dogal_sirala(list(g_kadro.keys())):
                        st.markdown(f"**🛡️ {t_isim}**")
                        st.write(", ".join(g_kadro[t_isim]) if g_kadro[t_isim] else "Oyuncu yok")

# --- TAB 2: SKOR GİRİŞİ ---
with tab2:
    st.subheader("Maç Skorları ve Oyuncu Seçim Girişleri")
    if st.session_state.admin_mi:
        if not st.session_state.skor_tablosu.empty:
            # SKOR GİRİŞİ GRUPLAR DOĞAL SIRALANDI
            gruplar = dogal_sirala(list(st.session_state.skor_tablosu['Grup'].unique()))
            secilen_grup = st.selectbox("Grup Seç:", gruplar, key="skor_grup_sec")
            df_grup = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == secilen_grup].copy()
            aktif_gunler = sorted(df_grup['Gün'].unique(), key=lambda x: int(x.split('.')[0]) if '.' in x else 99)
            secilen_gun = st.selectbox("Müsabaka Günü:", aktif_gunler)
            df_gun = df_grup[df_grup['Gün'] == secilen_gun]
            
            form_verileri = {}
            for idx, row in df_gun.iterrows():
                st.markdown(f"**🔹 {row['Branş']} ({row['Eşleşme']})**")
                r_cols = st.columns([1.5, 2.0, 1.5, 2.0, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7])
                
                t1_isim, t2_isim = row['Takım 1'], row['Takım 2']
                grup_kadro_dict = st.session_state.takim_kadrolari.get(secilen_grup, {})
                t1_havuz = grup_kadro_dict.get(t1_isim, ["Belirtilmedi"])
                t2_havuz = grup_kadro_dict.get(t2_isim, ["Belirtilmedi"])
                
                r_cols[0].write(f"**{t1_isim}**")
                
                if "Çiftler" in str(row['Branş']):
                    eski_kayit1 = str(row['T1_Oyuncu'])
                    for char in ["[", "]", "'", '"']: eski_kayit1 = eski_kayit1.replace(char, "")
                    ayirici1 = ' - ' if ' - ' in eski_kayit1 else ','
                    eski_oyuncular1 = [o.strip() for o in eski_kayit1.split(ayirici1) if o.strip() and o.strip() in t1_havuz and o.strip() != "Seçiniz"]
                    t1_oyuncu = r_cols[1].multiselect("T1 Oyuncular", options=t1_havuz, default=eski_oyuncular1, max_selections=2, key=f"t1_o_{idx}", label_visibility="collapsed")
                    t1_oyuncu_str = " - ".join(t1_oyuncu)
                else:
                    opts1 = ["Seçiniz"] + [o for o in t1_havuz if o != "Belirtilmedi"]
                    eski_veri1 = str(row['T1_Oyuncu']).strip()
                    for char in ["[", "]", "'", '"']: eski_veri1 = eski_veri1.replace(char, "")
                    eski_o1 = eski_veri1 if eski_veri1 and eski_veri1 not in ["nan", "None", ""] else "Seçiniz"
                    idx1 = opts1.index(eski_o1) if eski_o1 in opts1 else 0
                    t1_secim_raw = r_cols[1].selectbox("T1 Oyuncu", options=opts1, index=idx1, key=f"t1_o_{idx}", label_visibility="collapsed")
                    t1_oyuncu_str = t1_secim_raw if t1_secim_raw != "Seçiniz" else ""
                
                r_cols[2].write(f"**{t2_isim}**")
                
                if "Çiftler" in str(row['Branş']):
                    eski_kayit2 = str(row['T2_Oyuncu'])
                    for char in ["[", "]", "'", '"']: eski_kayit2 = eski_kayit2.replace(char, "")
                    ayirici2 = ' - ' if ' - ' in eski_kayit2 else ','
                    eski_oyuncular2 = [o.strip() for o in eski_kayit2.split(ayirici2) if o.strip() and o.strip() in t2_havuz and o.strip() != "Seçiniz"]
                    t2_oyuncu = r_cols[3].multiselect("T2 Oyuncular", options=t2_havuz, default=eski_oyuncular2, max_selections=2, key=f"t2_o_{idx}", label_visibility="collapsed")
                    t2_oyuncu_str = " - ".join(t2_oyuncu)
                else:
                    opts2 = ["Seçiniz"] + [o for o in t2_havuz if o != "Belirtilmedi"]
                    eski_veri2 = str(row['T2_Oyuncu']).strip()
                    for char in ["[", "]", "'", '"']: eski_veri2 = eski_veri2.replace(char, "")
                    eski_o2 = eski_veri2 if eski_veri2 and eski_veri2 not in ["nan", "None", ""] else "Seçiniz"
                    idx2 = opts2.index(eski_o2) if eski_o2 in opts2 else 0
                    t2_secim_raw = r_cols[3].selectbox("T2 Oyuncu", options=opts2, index=idx2, key=f"t2_o_{idx}", label_visibility="collapsed")
                    t2_oyuncu_str = t2_secim_raw if t2_secim_raw != "Seçiniz" else ""
                
                s1t1 = r_cols[4].number_input("S1T1", min_value=0, value=int(row['1.Set T1']), step=1, key=f"s1t1_{idx}", label_visibility="collapsed")
                s1t2 = r_cols[5].number_input("S1T2", min_value=0, value=int(row['1.Set T2']), step=1, key=f"s1t2_{idx}", label_visibility="collapsed")
                s2t1 = r_cols[6].number_input("S2T1", min_value=0, value=int(row['2.Set T1']), step=1, key=f"s2t1_{idx}", label_visibility="collapsed")
                s2t2 = r_cols[7].number_input("S2T2", min_value=0, value=int(row['2.Set T2']), step=1, key=f"s2t2_{idx}", label_visibility="collapsed")
                s3t1 = r_cols[8].number_input("S3T1", min_value=0, value=int(row['3.Set T1']), step=1, key=f"s3t1_{idx}", label_visibility="collapsed")
                s3t2 = r_cols[9].number_input("S3T2", min_value=0, value=int(row['3.Set T2']), step=1, key=f"s3t2_{idx}", label_visibility="collapsed")
                
                form_verileri[idx] = {
                    "T1_Oyuncu": t1_oyuncu_str, "T2_Oyuncu": t2_oyuncu_str,
                    "1.Set T1": s1t1, "1.Set T2": s1t2, "2.Set T1": s2t1, "2.Set T2": s2t2, "3.Set T1": s3t1, "3.Set T2": s3t2
                }
                st.divider()

            # --- ESAME HİYERARŞİSİ UYARI KONTROLÜ ---
            eslesme_dict = {}
            for idx, g_row in form_verileri.items():
                row_data = df_gun.loc[idx]
                eslesme = row_data["Eşleşme"]
                brans = row_data["Branş"]
                
                if eslesme not in eslesme_dict:
                    eslesme_dict[eslesme] = {
                        "T1": {"isim": row_data["Takım 1"], "secimler": {}}, 
                        "T2": {"isim": row_data["Takım 2"], "secimler": {}}
                    }
                
                eslesme_dict[eslesme]["T1"]["secimler"][brans] = g_row["T1_Oyuncu"]
                eslesme_dict[eslesme]["T2"]["secimler"][brans] = g_row["T2_Oyuncu"]
            
            grup_kadro_dict = st.session_state.takim_kadrolari.get(secilen_grup, {})
            for eslesme, data in eslesme_dict.items():
                for team_key in ["T1", "T2"]:
                    takim_ismi = data[team_key]["isim"]
                    havuz = grup_kadro_dict.get(takim_ismi, [])
                    secimler = data[team_key]["secimler"]
                    
                    o1 = secimler.get("1. Tekler")
                    o2 = secimler.get("2. Tekler")
                    o3 = secimler.get("3. Tekler")

                    r1 = havuz.index(o1) if o1 in havuz else -1
                    r2 = havuz.index(o2) if o2 in havuz else -1
                    r3 = havuz.index(o3) if o3 in havuz else -1
                    
                    uyarilar = []
                    
                    if r1 != -1 and r2 != -1 and r1 <= r2:
                        uyarilar.append(f"**2. Tekler** oyuncusu ({o2}), **1. Tekler** oyuncusundan ({o1}) daha üst bir esame sırasına sahip olmalıdır.")
                    if r2 != -1 and r3 != -1 and r2 <= r3:
                        uyarilar.append(f"**3. Tekler** oyuncusu ({o3}), **2. Tekler** oyuncusundan ({o2}) daha üst bir esame sırasına sahip olmalıdır.")
                    if r1 != -1 and r3 != -1 and r2 == -1 and r1 <= r3:
                        uyarilar.append(f"**3. Tekler** oyuncusu ({o3}), **1. Tekler** oyuncusundan ({o1}) daha üst bir esame sırasına sahip olmalıdır.")
                        
                    if uyarilar:
                        st.warning(f"⚠️ **Takım İçi Sıralama Uyarısı ({takim_ismi} | Eşleşme: {eslesme}):**\n\n" + "\n".join([f"- {u}" for u in uyarilar]) + "\n\n*(Kayıt işlemi yapılabilir, bu sadece bilgi uyarısıdır.)*")

            if st.button("✅ Tüm Skorları ve Esameleri Kaydet"):
                hata_mesajlari = []
                for idx, guncel_row in form_verileri.items():
                    mac_tanimi = f"{secilen_gun} - {st.session_state.skor_tablosu.loc[idx]['Branş']}"
                    ok1, msg1 = set_gecerli_mi(guncel_row["1.Set T1"], guncel_row["1.Set T2"])
                    ok2, msg2 = set_gecerli_mi(guncel_row["2.Set T1"], guncel_row["2.Set T2"])
                    ok3, msg3 = set_gecerli_mi(guncel_row["3.Set T1"], guncel_row["3.Set T2"], is_set3=True)
                    if not ok1: hata_mesajlari.append(f"{mac_tanimi} Set 1: {msg1}")
                    if not ok2: hata_mesajlari.append(f"{mac_tanimi} Set 2: {msg2}")
                    if not ok3: hata_mesajlari.append(f"{mac_tanimi} Set 3: {msg3}")
                
                if hata_mesajlari:
                    for h in hata_mesajlari: st.error(h)
                else:
                    for idx, guncel_row in form_verileri.items():
                        for k, v in guncel_row.items():
                            st.session_state.skor_tablosu.at[idx, k] = v
                    ortak_veriyi_kaydet()
                    st.success("Veriler başarıyla işlendi ve kaydedildi!")
                    st.rerun()
        else:
            st.info("Aktif grup bulunamadı.")
    else:
        st.warning("🔒 Skor ve esame giriş paneli dışarıya kapalıdır. Lütfen giriş yapınız.")

# --- TAB 3: PUAN DURUMU ---
with tab3:
    st.subheader("Canlı Puan Durumu")
    if not st.session_state.skor_tablosu.empty:
        df = st.session_state.skor_tablosu.copy()
        def satir_hesapla(row):
            s1_t1, s1_t2 = int(row['1.Set T1']), int(row['1.Set T2'])
            s2_t1, s2_t2 = int(row['2.Set T1']), int(row['2.Set T2'])
            s3_t1, s3_t2 = int(row['3.Set T1']), int(row['3.Set T2'])
            if s1_t1 == 0 and s1_t2 == 0 and s2_t1 == 0 and s2_t2 == 0 and s3_t1 == 0 and s3_t2 == 0:
                return pd.Series([0, 0, 0, 0])
            t1_set = int(s1_t1 > s1_t2) + int(s2_t1 > s2_t2)
            t2_set = int(s1_t2 > s1_t1) + int(s2_t2 > s2_t1)
            t1_oyun = s1_t1 + s2_t1
            t2_oyun = s1_t2 + s2_t2
            
            if s3_t1 > 0 or s3_t2 > 0:
                if s3_t1 >= 10 or s3_t2 >= 10: 
                    if s3_t1 > s3_t2: t1_set += 1; t1_oyun += 1
                    else: t2_set += 1; t2_oyun += 1
                else: 
                    t1_set += int(s3_t1 > s3_t2); t2_set += int(s3_t2 > s3_t1)
                    t1_oyun += s3_t1; t2_oyun += s3_t2
            return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])

        df[['T1_Oyun', 'T2_Oyun', 'T1_Set_Skor', 'T2_Set_Skor']] = df.apply(satir_hesapla, axis=1)
        df['T1_Match_Win'] = (df['T1_Set_Skor'] > df['T2_Set_Skor']).astype(int)
        df['T2_Match_Win'] = (df['T2_Set_Skor'] > df['T1_Set_Skor']).astype(int)
        
        seriler = df.groupby(['Grup', 'Gün', 'Eşleşme', 'Takım 1', 'Takım 2']).agg({'T1_Match_Win': 'sum', 'T2_Match_Win': 'sum', 'T1_Set_Skor': 'sum', 'T2_Set_Skor': 'sum', 'T1_Oyun': 'sum', 'T2_Oyun': 'sum'}).reset_index()
        
        seriler['T1_Win'] = (seriler['T1_Match_Win'] > seriler['T2_Match_Win']).astype(int)
        seriler['T2_Win'] = (seriler['T2_Match_Win'] > seriler['T1_Match_Win']).astype(int)
        
        t1 = seriler[['Grup', 'Takım 1', 'T1_Win', 'T1_Match_Win', 'T2_Match_Win', 'T1_Set_Skor', 'T2_Set_Skor', 'T1_Oyun', 'T2_Oyun']]
        t1.columns = ['Grup', 'Takım', 'Galibiyet', 'Aldığı Maç', 'Verdiği Maç', 'Aldığı Set', 'Verdiği Set', 'Aldığı Oyun', 'Verdiği Oyun']
        t2 = seriler[['Grup', 'Takım 2', 'T2_Win', 'T2_Match_Win', 'T1_Match_Win', 'T2_Set_Skor', 'T1_Set_Skor', 'T2_Oyun', 'T1_Oyun']]
        t2.columns = ['Grup', 'Takım', 'Galibiyet', 'Aldığı Maç', 'Verdiği Maç', 'Aldığı Set', 'Verdiği Set', 'Aldığı Oyun', 'Verdiği Oyun']
        
        tum_stats = pd.concat([t1, t2]).groupby(['Grup', 'Takım']).sum().reset_index()
        tum_stats['Maç Av.'] = tum_stats['Aldığı Maç'] - tum_stats['Verdiği Maç']
        tum_stats['Set Av.'] = tum_stats['Aldığı Set'] - tum_stats['Verdiği Set']
        tum_stats['Oyun Av.'] = tum_stats['Aldığı Oyun'] - tum_stats['Verdiği Oyun']
        
        # PUAN DURUMU GRUPLARI DOĞAL SIRALANDI
        mevcut_gruplar = dogal_sirala(list(tum_stats['Grup'].unique()))
        secim_opsiyonlari = ["Tümünü Göster"] + mevcut_gruplar
        secilen_gruplar = st.multiselect("🔍 Görüntülenecek Grupları Seçin (Karşılaştırmak istediklerinizi ekleyebilirsiniz):", options=secim_opsiyonlari, default=["Tümünü Göster"])
        
        gosterilecek_gruplar = mevcut_gruplar if "Tümünü Göster" in secilen_gruplar or len(secilen_gruplar) == 0 else [g for g in secilen_gruplar if g != "Tümünü Göster"]

        pdf_gruplar_data = {}

        for gp in gosterilecek_gruplar:
            if gp in mevcut_gruplar:
                g_kat = st.session_state.grup_kategorileri.get(gp, "Erkekler")
                st.markdown(f"### 🏆 {gp} Puan Durumu ({g_kat})")
                grup_df = tum_stats[tum_stats['Grup'] == gp].drop(columns=['Grup']).sort_values(by=['Galibiyet', 'Maç Av.', 'Oyun Av.'], ascending=False)
                grup_df.index = range(1, len(grup_df) + 1)
                
                pdf_df = grup_df.reset_index().rename(columns={"index": "Sıra"})
                pdf_gruplar_data[gp] = pdf_df
                
                st.dataframe(grup_df, use_container_width=True)

        if pdf_gruplar_data:
            st.divider()
            combined_pdf_bytes = generate_combined_standings_pdf(pdf_gruplar_data)
            st.download_button(
                label="📥 Seçili Grupların Puan Durumunu Tek PDF Olarak İndir",
                data=combined_pdf_bytes,
                file_name="puan_durumu_toplu.pdf",
                mime="application/pdf",
                key="pdf_puan_toplu"
            )

# --- TAB 4: MAÇ PROGRAMI ---
with tab4:
    st.subheader("📅 Maç Programı ve Fikstür")
    
    st.markdown("### 📅 Maç Olan Günler (Filtre)")
    if not st.session_state.mac_programi.empty:
        unique_dates = sorted(st.session_state.mac_programi['Tarih'].unique())
        cols = st.columns(min(len(unique_dates), 5) if len(unique_dates) > 0 else 1)
        for i, d_str in enumerate(unique_dates):
            match_count = len(st.session_state.mac_programi[st.session_state.mac_programi['Tarih'] == d_str])
            d_obj = datetime.datetime.strptime(d_str, "%d.%m.%Y").date()
            with cols[i % len(cols)]:
                if st.button(f"🗓️ {d_str} ({match_count})", key=f"btn_date_{d_str}"):
                    st.session_state.selected_date_filter = d_obj
                    st.rerun()
    else:
        st.info("Henüz maç planlanmadı.")

    st.markdown("---")

    if 'expand_all' not in st.session_state:
        st.session_state.expand_all = False

    if st.button("🔄 Arayüzde Bireysel Maçları Göster/ Gizle"):
        st.session_state.expand_all = not st.session_state.expand_all
        st.rerun()

    if not st.session_state.skor_tablosu.empty:
        turkce_gunler = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
        
        secilen_tarih = st.date_input("🗓️ Program Yapılacak / Görüntülenecek Tarih:", value=st.session_state.selected_date_filter)
        st.session_state.selected_date_filter = secilen_tarih
        
        formatted_tarih = secilen_tarih.strftime("%d.%m.%Y")
        gun_adi = turkce_gunler[secilen_tarih.weekday()]

        for idx in st.session_state.mac_programi.index:
            row = st.session_state.mac_programi.loc[idx]
            eslesen_mac = st.session_state.skor_tablosu[
                (st.session_state.skor_tablosu['Grup'] == row['Grup']) &
                (st.session_state.skor_tablosu['Gün'] == row['Gün']) &
                (st.session_state.skor_tablosu['Branş'] == row['Branş']) &
                (st.session_state.skor_tablosu['Eşleşme'] == row['Eşleşme'])
            ]
            if not eslesen_mac.empty:
                m = eslesen_mac.iloc[0]
                t1_o = str(m['T1_Oyuncu']).strip() if pd.notna(m['T1_Oyuncu']) and str(m['T1_Oyuncu']).strip() not in ["", "nan", "Seçiniz", "None"] else ""
                t2_o = str(m['T2_Oyuncu']).strip() if pd.notna(m['T2_Oyuncu']) and str(m['T2_Oyuncu']).strip() not in ["", "nan", "Seçiniz", "None"] else ""
                st.session_state.mac_programi.at[idx, "T1 Oyuncu"] = t1_o
                st.session_state.mac_programi.at[idx, "T2 Oyuncu"] = t2_o
                s1t1, s1t2 = int(m['1.Set T1']), int(m['1.Set T2'])
                s2t1, s2t2 = int(m['2.Set T1']), int(m['2.Set T2'])
                s3t1, s3t2 = int(m['3.Set T1']), int(m['3.Set T2'])
                if s1t1 != 0 or s1t2 != 0:
                    skor_str = f"{s1t1}-{s1t2} | {s2t1}-{s2t2}"
                    if s3t1 != 0 or s3t2 != 0: skor_str += f" | {s3t1}-{s3t2}" 
                    st.session_state.mac_programi.at[idx, "Canlı Skor"] = skor_str
                    t1_set_sayisi = (s1t1 > s1t2) + (s2t1 > s2t2) + (s3t1 > s3t2)
                    t2_set_sayisi = (s1t2 > s1t1) + (s2t2 > s2t1) + (s3t2 > s3t1)
                    st.session_state.mac_programi.at[idx, "Kazanan"] = "T1" if t1_set_sayisi >= 2 else ("T2" if t2_set_sayisi >= 2 else "")
                else:
                    st.session_state.mac_programi.at[idx, "Canlı Skor"] = "Oynanmadı"
                    st.session_state.mac_programi.at[idx, "Kazanan"] = ""

        df_gunluk = st.session_state.mac_programi[st.session_state.mac_programi['Tarih'] == formatted_tarih].copy()
        
        if st.session_state.admin_mi:
            st.markdown("### 📥 PDF İndirme Ayarları")
            bireysel_pdf_goster = st.checkbox("📄 PDF'te Bireysel Maçları (Tekler/Çiftler vb.) Göster", value=True)
            
            tum_kolonlar = ["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor", "Kazanan"]
            secilen_pdf_cols = st.multiselect("PDF'e eklenecek sütunları seçin:", options=tum_kolonlar, default=["Maç Saati", "Kort", "Grup", "Branş", "Takım 1", "Takım 2", "Canlı Skor"])

            df_pdf_export = df_gunluk.copy()
            if not bireysel_pdf_goster and not df_pdf_export.empty:
                df_pdf_export = df_pdf_export.drop_duplicates(subset=["Maç Saati", "Kort", "Grup", "Takım 1", "Takım 2"]).copy()
                if "Branş" in df_pdf_export.columns:
                    df_pdf_export["Branş"] = "Takım Karşılaşması"
                if "Canlı Skor" in df_pdf_export.columns:
                    df_pdf_export["Canlı Skor"] = "-"
                if "T1 Oyuncu" in df_pdf_export.columns:
                    df_pdf_export["T1 Oyuncu"] = "-"
                if "T2 Oyuncu" in df_pdf_export.columns:
                    df_pdf_export["T2 Oyuncu"] = "-"

            st.markdown(f"### ➕ {formatted_tarih} Tarihine Maç Ekle")
            c1, c2, c3 = st.columns(3)
            # MAÇ EKLE KISMINDAKİ GRUPLAR DOĞAL SIRALANDI
            gruplar_prog = dogal_sirala(list(st.session_state.skor_tablosu['Grup'].unique()))
            sec_grup_prog = c1.selectbox("Grup Seç:", gruplar_prog, key="prog_grup")
            df_g_prog = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == sec_grup_prog]
            gunler_prog = sorted(df_g_prog['Gün'].unique(), key=lambda x: int(x.split('.')[0]) if '.' in x else 99)
            sec_gun_prog = c2.selectbox("Gün Seç:", gunler_prog, key="prog_gun")
            df_m_prog = df_g_prog[df_g_prog['Gün'] == sec_gun_prog]
            
            mevcut_mask = df_m_prog.apply(lambda r: not st.session_state.mac_programi[
                (st.session_state.mac_programi['Tarih'] == formatted_tarih) & (st.session_state.mac_programi['Grup'] == r['Grup']) &
                (st.session_state.mac_programi['Gün'] == r['Gün']) & (st.session_state.mac_programi['Branş'] == r['Branş']) &
                (st.session_state.mac_programi['Eşleşme'] == r['Eşleşme'])
            ].empty, axis=1)
            df_m_prog_eklenebilir = df_m_prog[~mevcut_mask]
            
            if df_m_prog_eklenebilir.empty: c3.info("✅ Fikstürdeki maçlar eklenmiş.")
            else:
                mac_listesi = [f"{row['Takım 1']} vs {row['Takım 2']} ({row['Branş']})" for idx, row in df_m_prog_eklenebilir.iterrows()]
                sec_mac_adi = c3.selectbox("Maç Seç:", mac_listesi, key="prog_mac")
                if st.button("➕ Akışa Ekle"):
                    secilen_row = df_m_prog_eklenebilir.iloc[mac_listesi.index(sec_mac_adi)]
                    yeni_kayit = pd.DataFrame([{
                        "Maç Saati": "10:00", "Tarih": formatted_tarih, "Gün Adı": gun_adi, "Kort": "Kort 1",
                        "Grup": secilen_row['Grup'], "Gün": secilen_row['Gün'], "Branş": secilen_row['Branş'], "Eşleşme": secilen_row['Eşleşme'],
                        "Takım 1": secilen_row['Takım 1'], "Takım 2": secilen_row['Takım 2'], "T1 Oyuncu": "", "T2 Oyuncu": "", "Canlı Skor": "Oynanmadı", "Kazanan": ""
                    }])
                    st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, yeni_kayit], ignore_index=True)
                    ortak_veriyi_kaydet(); st.success("Maç eklendi!"); st.rerun()

            if not df_gunluk.empty:
                st.markdown("### 📋 Günlük Akış Editörü")
                mac_sil_secenekler = ["Seçiniz"] + [f"{r['Maç Saati']} - {r['Kort']} | {r['Grup']} | {r['Takım 1']} vs {r['Takım 2']} ({r['Branş']})" for idx, r in df_gunluk.iterrows()]
                secilen_program_mac = st.selectbox("⛔ Programdan Kaldırılacak Maçı Seçin:", mac_sil_secenekler, key="program_mac_sil_selectbox")
                if secilen_program_mac != "Seçiniz":
                    secilen_idx_in_df = mac_sil_secenekler.index(secilen_program_mac) - 1
                    actual_match_idx = df_gunluk.index[secilen_idx_in_df]
                    if st.button("❌ Seçilen Maçı Programdan Kaldır"):
                        st.session_state.mac_programi.drop(index=actual_match_idx, inplace=True); st.session_state.mac_programi.reset_index(drop=True, inplace=True); ortak_veriyi_kaydet(); st.rerun()
                st.divider()
                
                if not df_pdf_export.empty and secilen_pdf_cols:
                    pdf_bytes_admin = generate_pdf(df_pdf_export[secilen_pdf_cols], f"Mac Programi - {formatted_tarih}")
                    st.download_button("📥 Programı PDF Olarak İndir", data=pdf_bytes_admin, file_name=f"mac_programi_{formatted_tarih}.pdf", mime="application/pdf", key="pdf_admin")
                
                edited_dfs = []
                for (grup_adi, eslesme_adi), grup_df in df_gunluk.groupby(['Grup', 'Eşleşme']):
                    kort = grup_df.iloc[0]['Kort']
                    tarih = grup_df.iloc[0]['Tarih']
                    gun_adi_val = grup_df.iloc[0]['Gün Adı']
                    takim1 = grup_df.iloc[0]['Takım 1']
                    takim2 = grup_df.iloc[0]['Takım 2']
                    
                    expander_title = f"{kort} | {tarih} | {gun_adi_val} | {grup_adi} | {takim1} - {takim2}"
                    
                    with st.expander(expander_title, expanded=st.session_state.expand_all):
                        e_df = st.data_editor(
                            grup_df, 
                            use_container_width=True, 
                            num_rows="dynamic", 
                            disabled=["Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Canlı Skor", "Kazanan"], 
                            key=f"editor_{grup_adi}_{eslesme_adi}_{formatted_tarih}"
                        )
                        edited_dfs.append(e_df)

                if st.button("💾 Değişiklikleri Kaydet"):
                    if edited_dfs:
                        guncel_program = pd.concat(edited_dfs)
                        st.session_state.mac_programi.drop(index=df_gunluk.index, inplace=True)
                        guncel_program['Tarih'] = guncel_program['Tarih'].fillna(formatted_tarih)
                        st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, guncel_program]).reset_index(drop=True)
                        ortak_veriyi_kaydet()
                        st.success("Güncellendi!")
                        st.rerun()

        else:
            st.markdown(f"### 📋 {formatted_tarih} Tarihli Maç Akışı")
            if df_gunluk.empty:
                st.info("Bu tarihte planlanmış maç bulunmamaktadır.")
            else:
                st.divider()
                
                for (grup_adi, eslesme_adi), grup_df in df_gunluk.groupby(['Grup', 'Eşleşme']):
                    kort = grup_df.iloc[0]['Kort']
                    tarih = grup_df.iloc[0]['Tarih']
                    gun_adi_val = grup_df.iloc[0]['Gün Adı']
                    takim1 = grup_df.iloc[0]['Takım 1']
                    takim2 = grup_df.iloc[0]['Takım 2']
                    
                    expander_title = f"{kort} | {tarih} | {gun_adi_val} | {grup_adi} | {takim1} - {takim2}"
                    
                    with st.expander(expander_title, expanded=st.session_state.expand_all):
                        html_rows = ""
                        for _, row in grup_df.iterrows():
                            skor = str(row.get('Canlı Skor', 'Oynanmadı'))
                            skor_html = f"<span style='color:green; font-weight:bold;'>{skor}</span>" if skor not in ["Oynanmadı", ""] else "<i>Bekleniyor</i>"
                            t1_o = str(row.get('T1 Oyuncu', '')).strip()
                            t2_o = str(row.get('T2 Oyuncu', '')).strip()
                            html_rows += f"<tr><td>{row['Branş']}</td><td>{t1_o} / {t2_o}</td><td>{skor_html}</td></tr>"
                        
                        st.markdown(f"""
                        <table style="width:100%; border-collapse: collapse; font-family: sans-serif;">
                            <tr style="background:#f1f1f1;"><th style="padding:5px;">Branş</th><th style="padding:5px;">Oyuncular</th><th style="padding:5px;">Skor</th></tr>
                            {html_rows}
                        </table>
                        """, unsafe_allow_html=True)
    else:
        st.info("Gruplar oluşturulmadan maç programı aktif edilemez.")

# --- TAB 5: DUYURULAR ---
with tab5:
    st.subheader("📢 Turnuva Duyuruları ve Belgeler")
    
    if st.session_state.admin_mi:
        st.markdown("### ✍️ Duyuru Düzenleme (Sadece Başhakem)")
        yeni_duyuru = st.text_area("Duyuru Metni:", value=st.session_state.duyuru_metni, height=150)
        if st.button("💾 Duyuruyu Kaydet"):
            st.session_state.duyuru_metni = yeni_duyuru
            ortak_veriyi_kaydet()
            st.success("Duyuru metni başarıyla güncellendi!")
        
        st.markdown("---")
        st.markdown("### 📄 Turnuva Belgeleri Ekle (Çoklu Yükleme)")
        st.info("Kural kitapçığı veya yönetmelik gibi PDF dosyalarını sisteme buradan yükleyebilirsiniz.")
        
        uploaded_pdfs = st.file_uploader("PDF Dosyalarını Seçin:", type=["pdf"], accept_multiple_files=True)
        
        if uploaded_pdfs:
            if st.button("📤 Seçilen PDF'leri Sisteme Yükle"):
                for pdf_file in uploaded_pdfs:
                    file_path = os.path.join(BELGELER_KLASORU, pdf_file.name)
                    with open(file_path, "wb") as f:
                        f.write(pdf_file.getbuffer())
                st.success("Belgeler başarıyla yüklendi!")
                st.rerun()
        
        pdf_dosyalari = [f for f in os.listdir(BELGELER_KLASORU) if f.endswith('.pdf')]
        if pdf_dosyalari:
            st.markdown("### 🗑️ Yüklü Belgeleri Yönet")
            for pdf in pdf_dosyalari:
                col1, col2 = st.columns([4, 1])
                col1.write(f"📄 **{pdf}**")
                if col2.button("Sil", key=f"del_{pdf}"):
                    os.remove(os.path.join(BELGELER_KLASORU, pdf))
                    st.success(f"{pdf} başarıyla silindi!")
                    st.rerun()

    else:
        st.markdown("### 📝 Güncel Duyurular")
        if st.session_state.duyuru_metni:
            st.info(st.session_state.duyuru_metni)
        else:
            st.write("Şu an için aktif bir turnuva duyurusu bulunmamaktadır.")
            
        st.markdown("---")
        st.markdown("### 📄 Turnuva Belgeleri")
        
        pdf_dosyalari = [f for f in os.listdir(BELGELER_KLASORU) if f.endswith('.pdf')]
        
        if pdf_dosyalari:
            st.write("Aşağıdaki belgelere tıklayarak sayfadan ayrılmadan doğrudan okuyabilirsiniz:")
            for pdf in pdf_dosyalari:
                dosya_yolu = os.path.join(BELGELER_KLASORU, pdf)
                
                with st.expander(f"📖 {pdf} - Görüntülemek İçin Tıklayın"):
                    show_pdf(dosya_yolu)
                    
                    with open(dosya_yolu, "rb") as f:
                        st.download_button(
                            label=f"📥 {pdf} Dosyasını İndir",
                            data=f.read(),
                            file_name=pdf,
                            mime="application/pdf",
                            key=f"dl_btn_{pdf}"
                        )
        else:
            st.write("Sisteme henüz herhangi bir belge yüklenmemiş.")

# --- TAB 6: YÖNETİM & DOSYA İŞLEMLERİ ---
with tab6:
    st.subheader("⚙️ Gelişmiş Yönetim Paneli")
    if st.session_state.admin_mi:
        with st.expander("✍️ Grup Tipi, Format, İsim ve Kadroları Revize Et", expanded=True):
            if not st.session_state.skor_tablosu.empty:
                # Yönetim panelindeki grupları doğal sırala
                t_gruplar = dogal_sirala(list(st.session_state.skor_tablosu['Grup'].unique()))
                sec_g = st.selectbox("Düzenlenecek Grup Seç:", ["Seçiniz"] + t_gruplar, key="admin_edit_grup")
                
                if sec_g != "Seçiniz":
                    yeni_grup_adi = st.text_input("Grup Adını Güncelle:", value=sec_g, key="yeni_g_adi")
                    
                    st.markdown("---")
                    
                    m_kadrolar = st.session_state.takim_kadrolari.get(sec_g, {})
                    mevcut_takim_sayisi = len(m_kadrolar)
                    tip_liste = ["3'lü Grup", "4'lü Grup", "5'li Grup", "6'lı Grup"]
                    
                    if mevcut_takim_sayisi == 3: tip_idx = 0
                    elif mevcut_takim_sayisi == 4: tip_idx = 1
                    elif mevcut_takim_sayisi == 5: tip_idx = 2
                    elif mevcut_takim_sayisi == 6: tip_idx = 3
                    else: tip_idx = 0
                    
                    mevcut_format = st.session_state.grup_formatlari.get(sec_g, "3 Maçlık (2 Tek, 1 Çift)")
                    format_liste = ["3 Maçlık (2 Tek, 1 Çift)", "5 Maçlık (3 Tek, 2 Çift)"]
                    format_idx = format_liste.index(mevcut_format) if mevcut_format in format_liste else 0

                    mevcut_kategori = st.session_state.grup_kategorileri.get(sec_g, "Erkekler")
                    kategori_liste = ["Erkekler", "Kadınlar"]
                    kategori_idx = kategori_liste.index(mevcut_kategori) if mevcut_kategori in kategori_liste else 0

                    c_f1, c_f2, c_f3 = st.columns(3)
                    with c_f1:
                        yeni_kategori = st.radio("🔄 Kategori Değiştir:", kategori_liste, index=kategori_idx, horizontal=True, key="edit_kategori")
                    with c_f2:
                        yeni_grup_tipi = st.radio("🔄 Grup Tipi Değiştir:", tip_liste, index=tip_idx, horizontal=True, key="edit_grup_tipi")
                    with c_f3:
                        yeni_format = st.radio("🔄 Müsabaka Formatı Değiştir:", format_liste, index=format_idx, horizontal=True, key="edit_format")
                    
                    fikstur_sifirlanacak_mi = (yeni_grup_tipi != tip_liste[tip_idx]) or (yeni_format != mevcut_format)
                    if fikstur_sifirlanacak_mi:
                        st.warning("⚠️ DİKKAT: Grup tipini veya maç formatını değiştirdiniz! Kaydettiğinizde bu grubun eski fikstürü ve skorları TAMAMEN SİLİNİP, yeni ayarlarla baştan oluşturulacaktır.")

                    st.markdown("---")
                    
                    mevcut_takim_isimleri = list(m_kadrolar.keys())
                    beklenen_yeni_sayi = int(yeni_grup_tipi[0])
                    
                    yeni_k_yapisi = {}
                    isim_degisiklikleri = {}
                    
                    for i in range(beklenen_yeni_sayi):
                        esk_ad = mevcut_takim_isimleri[i] if i < len(mevcut_takim_isimleri) else f"Yeni Takım {i+1}"
                        oyuncular = m_kadrolar.get(esk_ad, ["Belirtilmedi"])
                        
                        c_a, c_b = st.columns([1, 2])
                        with c_a:
                            y_ad = st.text_input(f"{i+1}. Takım Adı", value=esk_ad, key=f"ad_{sec_g}_{i}")
                            if i < len(mevcut_takim_isimleri) and y_ad != esk_ad: 
                                isim_degisiklikleri[esk_ad] = y_ad
                        with c_b:
                            y_o_text = st.text_area(f"Oyuncular", value="\n".join(oyuncular), key=f"oyuncu_{sec_g}_{i}", height=100)
                            yeni_k_yapisi[y_ad if y_ad else esk_ad] = [o.strip() for o in y_o_text.split('\n') if o.strip()]
                    
                    if st.button("💾 Yapılan Değişiklikleri Veritabanına Yaz"):
                        # Yönetim ekranında Çakışma kontrolü
                        kullanilan_baska_takimlar_tab6 = {}
                        for g_n, g_k in st.session_state.takim_kadrolari.items():
                            g_kat = st.session_state.grup_kategorileri.get(g_n, "Erkekler")
                            if g_n != sec_g and g_kat == yeni_kategori: # Şu an düzenlenen grup hariç diğer aynı kategorilere bak
                                for t_n in g_k.keys():
                                    kullanilan_baska_takimlar_tab6[t_n] = g_n
                        
                        cakisanlar_tab6 = [t for t in list(yeni_k_yapisi.keys()) if t in kullanilan_baska_takimlar_tab6]
                        if cakisanlar_tab6:
                            hata_msj = ", ".join([f"'{t}' ({kullanilan_baska_takimlar_tab6[t]})" for t in cakisanlar_tab6])
                            st.error(f"⚠️ Hata: Eklemek veya değiştirmek istediğiniz takım(lar) {yeni_kategori} kategorisinde zaten başka gruplarda kayıtlı!\nÇakışanlar: {hata_msj}")
                        else:
                            g_hedef = yeni_grup_adi if yeni_grup_adi.strip() != "" else sec_g
                            
                            if fikstur_sifirlanacak_mi:
                                st.session_state.skor_tablosu = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] != sec_g]
                                st.session_state.mac_programi = st.session_state.mac_programi[st.session_state.mac_programi['Grup'] != sec_g]
                                
                                st.session_state.takim_kadrolari[g_hedef] = yeni_k_yapisi
                                st.session_state.grup_formatlari[g_hedef] = yeni_format
                                st.session_state.grup_kategorileri[g_hedef] = yeni_kategori
                                
                                if sec_g != g_hedef:
                                    if sec_g in st.session_state.takim_kadrolari: del st.session_state.takim_kadrolari[sec_g]
                                    if sec_g in st.session_state.grup_formatlari: del st.session_state.grup_formatlari[sec_g]
                                    if sec_g in st.session_state.grup_kategorileri: del st.session_state.grup_kategorileri[sec_g]
                                    
                                yeni_takim_listesi = list(yeni_k_yapisi.keys())
                                yeni_df = pd.DataFrame(eslesmeleri_olustur(g_hedef, yeni_takim_listesi, yeni_grup_tipi, yeni_format))
                                if st.session_state.skor_tablosu.empty:
                                    st.session_state.skor_tablosu = yeni_df
                                else:
                                    st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
                                
                                ortak_veriyi_kaydet()
                                st.success("Grup ayarları güncellendi ve yeni fikstür başarıyla oluşturuldu!")
                                
                            else:
                                st.session_state.takim_kadrolari[sec_g] = yeni_k_yapisi
                                st.session_state.grup_kategorileri[sec_g] = yeni_kategori
                                
                                if isim_degisiklikleri:
                                    for e_a, y_a in isim_degisiklikleri.items():
                                        st.session_state.skor_tablosu.replace({e_a: y_a}, inplace=True)
                                        st.session_state.mac_programi.replace({e_a: y_a}, inplace=True)
                                
                                if g_hedef != sec_g:
                                    st.session_state.skor_tablosu.loc[st.session_state.skor_tablosu['Grup'] == sec_g, 'Grup'] = g_hedef
                                    st.session_state.mac_programi.loc[st.session_state.mac_programi['Grup'] == sec_g, 'Grup'] = g_hedef
                                    st.session_state.takim_kadrolari[g_hedef] = st.session_state.takim_kadrolari.pop(sec_g)
                                    if sec_g in st.session_state.grup_formatlari:
                                        st.session_state.grup_formatlari[g_hedef] = st.session_state.grup_formatlari.pop(sec_g)
                                    if sec_g in st.session_state.grup_kategorileri:
                                        st.session_state.grup_kategorileri[g_hedef] = st.session_state.grup_kategorileri.pop(sec_g)
                                
                                ortak_veriyi_kaydet()
                                st.success("Takım ve kadro bilgileri başarıyla güncellendi!")
                            
                            st.rerun()

        st.markdown("### 🗑️ Grup Silme İşlemleri")
        if not st.session_state.skor_tablosu.empty:
            silinecek_gruplar = dogal_sirala(list(st.session_state.skor_tablosu['Grup'].unique()))
            secilen_sil_grup = st.selectbox("Silinecek Grubu Seçin:", ["Seçiniz"] + silinecek_gruplar, key="grup_sil_secim")
            
            if secilen_sil_grup != "Seçiniz":
                st.warning(f"⚠️ DİKKAT: '{secilen_sil_grup}' grubunu ve bu gruba ait tüm fikstür/kadro kayıtlarını kalıcı olarak sileceksiniz!")
                
                if st.button(f"🚨 '{secilen_sil_grup}' Grubunu Tamamen Sil"):
                    st.session_state.skor_tablosu = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] != secilen_sil_grup]
                    st.session_state.mac_programi = st.session_state.mac_programi[st.session_state.mac_programi['Grup'] != secilen_sil_grup]
                    
                    if secilen_sil_grup in st.session_state.takim_kadrolari: del st.session_state.takim_kadrolari[secilen_sil_grup]
                    if secilen_sil_grup in st.session_state.grup_formatlari: del st.session_state.grup_formatlari[secilen_sil_grup]
                    if secilen_sil_grup in st.session_state.grup_kategorileri: del st.session_state.grup_kategorileri[secilen_sil_grup]
                    
                    ortak_veriyi_kaydet()
                    st.success(f"'{secilen_sil_grup}' grubu sistemden başarıyla silindi!")
                    st.rerun()
        else:
            st.info("Sistemde silinecek herhangi bir grup bulunmuyor.")

        st.markdown("---")

        st.markdown("### 💾 Yedekleme Paneli")
        c_sv, c_ld = st.columns(2)
        with c_sv:
            export_data = {
                "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
                "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
                "takim_kadrolari": st.session_state.takim_kadrolari,
                "grup_formatlari": st.session_state.get("grup_formatlari", {}),
                "grup_kategorileri": st.session_state.get("grup_kategorileri", {}),
                "duyuru_metni": st.session_state.duyuru_metni,
                "takim_havuzu": st.session_state.get("takim_havuzu", {})
            }
            st.download_button("📥 Turnuva Veritabanını İndir (.json)", data=json.dumps(export_data, ensure_ascii=False, indent=4), file_name="turnuva_yedek.json", mime="application/json")
        with c_ld:
            up_file = st.file_uploader("Geri Yüklemek İçin Yedek Dosyası Seçin:", type=["json"])
            if up_file is not None and st.button("📤 Seçilen Yedeği Sisteme Entegre Et"):
                try:
                    d = json.load(up_file)
                    st.session_state.skor_tablosu = pd.DataFrame(d["skor_tablosu"])
                    st.session_state.mac_programi = pd.DataFrame(d["mac_programi"])
                    st.session_state.takim_kadrolari = d["takim_kadrolari"]
                    st.session_state.grup_formatlari = d.get("grup_formatlari", {})
                    st.session_state.grup_kategorileri = d.get("grup_kategorileri", {})
                    st.session_state.duyuru_metni = d.get("duyuru_metni", "")
                    st.session_state.takim_havuzu = d.get("takim_havuzu", {})
                    ortak_veriyi_kaydet()
                    st.success("Yedek başarıyla yüklendi!")
                    st.rerun()
                except Exception as ex: st.error(f"Hata: {ex}")
        st.markdown("---")
        st.markdown("### ⚠️ Sistem Sıfırlama (Tehlikeli İşlem)")
        
        if "confirm_reset" not in st.session_state:
            st.session_state.confirm_reset = False

        if not st.session_state.confirm_reset:
            if st.button("🗑️ Tüm Turnuva Verilerini Kalıcı Olarak Sıfırla"):
                st.session_state.confirm_reset = True
                st.rerun()
        else:
            st.warning("⚠️ DİKKAT: Tüm turnuva verileri (maçlar, kadrolar, skorlar, yüklenen belgeler) kalıcı olarak silinecektir. Bu işlem geri alınamaz!")
            col_evet, col_hayir = st.columns(2)
            if col_evet.button("✅ Evet, Tüm Verileri Sil"):
                if os.path.exists(VERI_DOSYASI):
                    os.remove(VERI_DOSYASI)
                if os.path.exists(BELGELER_KLASORU):
                    shutil.rmtree(BELGELER_KLASORU)
                
                st.session_state.clear()
                st.session_state.confirm_reset = False
                st.success("Tüm veritabanı başarıyla temizlendi!")
                st.rerun()
            if col_hayir.button("❌ Vazgeç"):
                st.session_state.confirm_reset = False
                st.rerun()
