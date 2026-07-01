import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Tenis Turnuva Otomasyonu", layout="wide")
st.title("🎾 Profesyonel Tenis Turnuva Yönetim Sistemi")

# ==============================================================================
# SİSTEM FONKSİYONLARI VE HAFIZA BAŞLATMA
# ==============================================================================
VERI_DOSYASI = "turnuva_veri.json"

def ortak_veriyi_kaydet():
    data = {
        "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
        "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
        "takim_kadrolari": st.session_state.takim_kadrolari
    }
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def ortak_veriyi_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.session_state.skor_tablosu = pd.DataFrame(data["skor_tablosu"])
            st.session_state.mac_programi = pd.DataFrame(data["mac_programi"])
            st.session_state.takim_kadrolari = data["takim_kadrolari"]
        except:
            pass 

if "admin_mi" not in st.session_state: st.session_state.admin_mi = False

if 'skor_tablosu' not in st.session_state:
    if os.path.exists(VERI_DOSYASI):
        ortak_veriyi_yukle()
    else:
        st.session_state.skor_tablosu = pd.DataFrame(columns=[
            "Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", 
            "T1_Oyuncu", "T2_Oyuncu", "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"
        ])
        st.session_state.mac_programi = pd.DataFrame(columns=[
            "Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", 
            "Takım 1", "T1 Oyuncular", "Takım 2", "T2 Oyuncular", "Canlı Skor"
        ])
        st.session_state.takim_kadrolari = {} 

# --- YARDIMCI FONKSİYONLAR ---
def set_gecerli_mi(t1, t2, is_set3=False):
    if t1 == 0 and t2 == 0: return True, ""
    if t1 < 0 or t2 < 0: return False, "Skorlar negatif olamaz."
    max_s, min_s = max(t1, t2), min(t1, t2)
    diff = max_s - min_s
    if is_set3 and (t1 >= 10 or t2 >= 10):
        return (max_s == 10 and min_s <= 8) or (max_s > 10 and diff == 2), "3. Set skoru hatalı"
    if max_s < 6: return False, "Set henüz bitmemiş."
    return (max_s == 6 and diff >= 2) or (max_s == 7 and (diff == 2 or diff == 1)), "Geçersiz set skoru."

def eslesmeleri_olustur(grup_adi, takimlar, grup_tipi):
    base_matches = []
    if grup_tipi == "4'lü Grup":
        base_matches = [
            {"Gün": "1. Gün", "Eşleşme": "1 ve 4", "Takım 1": takimlar[0], "Takım 2": takimlar[3]},
            {"Gün": "1. Gün", "Eşleşme": "2 ve 3", "Takım 1": takimlar[1], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "1 ve 3", "Takım 1": takimlar[0], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "2 ve 4", "Takım 1": takimlar[1], "Takım 2": takimlar[3]},
            {"Gün": "3. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]},
            {"Gün": "3. Gün", "Eşleşme": "3 ve 4", "Takım 1": takimlar[2], "Takım 2": takimlar[3]},
        ]
    else:
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
    program = []
    for m in base_matches:
        for brans in ["1. Tekler", "2. Tekler", "Çiftler"]:
            satir = m.copy(); satir.update({"Branş": brans, "Grup": grup_adi, "T1_Oyuncu": "", "T2_Oyuncu": "", "1.Set T1": 0, "1.Set T2": 0, "2.Set T1": 0, "2.Set T2": 0, "3.Set T1": 0, "3.Set T2": 0})
            program.append(satir)
    return program

# ==============================================================================
# GİRİŞ PANELİ VE DİNAMİK SEKMELER
# ==============================================================================
with st.sidebar:
    st.markdown("### 👨‍⚖️ Turnuva Yönetim Girişi")
    if not st.session_state.admin_mi:
        if st.text_input("Yönetici Şifresi:", type="password") == "zonguldak2026":
            if st.button("🔒 Giriş Yap"): st.session_state.admin_mi = True; st.rerun()
    else:
        st.write("🟢 **Mod:** Başhakem")
        if st.button("🔓 Çıkış Yap"): st.session_state.admin_mi = False; st.rerun()

if st.session_state.admin_mi:
    tabs = st.tabs(["👥 1. Grup Ayarları", "✍️ 2. Skor Girişi", "🏆 3. Puan Durumu", "📅 4. Maç Programı", "⚙️ 5. Yönetim & Dosya"])
    t1, t2, t3, t4, t5 = tabs
else:
    tabs = st.tabs(["👥 1. Grup Ayarları", "🏆 3. Puan Durumu", "📅 4. Maç Programı"])
    t1, t3, t4 = tabs
    t2, t5 = None, None

# ==============================================================================
# TAB 1: GRUP AYARLARI
# ==============================================================================
with t1:
    st.subheader("Turnuva Grupları ve Kadrolar")
    if st.session_state.admin_mi:
        grup_tipi = st.radio("Kurulacak Grup Tipini Seçin:", ["4'lü Grup", "5'li Grup"], horizontal=True)
        grup_adi = st.text_input("Grup Adı")
        beklenen_sayi = 4 if grup_tipi == "4'lü Grup" else 5
        takim_listesi = st.text_area(f"Takım İsimleri (Her satıra 1 tane, toplam {beklenen_sayi} adet):")
        takimlar = [t.strip() for t in takim_listesi.split('\n') if t.strip()]
        if len(takimlar) == beklenen_sayi:
            cols = st.columns(beklenen_sayi)
            grup_kadrolari = {}
            for i, t in enumerate(takimlar):
                with cols[i]:
                    raw = st.text_area(f"{t} Kadrosu", key=f"kadro_{t}", height=100)
                    grup_kadrolari[t] = [o.strip() for o in raw.split('\n') if o.strip()]
            if st.button("🚀 Eşleşmeleri ve Kadroları Oluştur"):
                st.session_state.takim_kadrolari[grup_adi] = grup_kadrolari
                yeni_maclar = eslesmeleri_olustur(grup_adi, takimlar, grup_tipi)
                st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, pd.DataFrame(yeni_maclar)], ignore_index=True)
                ortak_veriyi_kaydet(); st.rerun()
    else:
        if st.session_state.takim_kadrolari: st.json(st.session_state.takim_kadrolari)
        else: st.info("Henüz grup veya kadro girilmedi.")

# ==============================================================================
# TAB 2: SKOR GİRİŞİ (Sadece Admin)
# ==============================================================================
if t2:
    with t2:
        st.subheader("Maç Skorları")
        if not st.session_state.skor_tablosu.empty:
            gruplar = st.session_state.skor_tablosu['Grup'].unique()
            secilen_grup = st.selectbox("Grup Seç:", gruplar)
            df_grup = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == secilen_grup]
            # ... (Buraya senin orjinal Tab 2 skor giriş formunu ekleyebilirsin) ...
            st.write("Skor giriş arayüzü burada çalışır.")

# ==============================================================================
# TAB 3: PUAN DURUMU
# ==============================================================================
with t3:
    st.subheader("Canlı Puan Durumu")
    if not st.session_state.skor_tablosu.empty:
        # Puan durumu hesaplama kodların buraya...
        st.write("Puan durumu tablosu burada görünür.")

# ==============================================================================
# TAB 4: MAÇ PROGRAMI (Gelişmiş)
# ==============================================================================
with t4:
    st.subheader("📅 Maç Programı ve Fikstür Yönetimi")
    col_a, col_b = st.columns(2)
    tarih_secimi = col_a.date_input("Maç Tarihi:", value=pd.to_datetime("today"))
    secilen_grup = col_b.selectbox("Grup Filtresi:", ["Hepsi"] + list(st.session_state.skor_tablosu['Grup'].unique()))

    def anahtar_olustur(row): return f"{row['Grup']}-{row['Gün']}-{row['Branş']}-{row['Eşleşme']}"
    
    tum_maclar = st.session_state.skor_tablosu.copy()
    tum_maclar['key'] = tum_maclar.apply(anahtar_olustur, axis=1)
    program_anahtarlar = st.session_state.mac_programi.apply(anahtar_olustur, axis=1).tolist()
    kalan_maclar = tum_maclar[~tum_maclar['key'].isin(program_anahtarlar)]

    if st.session_state.admin_mi and not kalan_maclar.empty:
        mac_secenekleri = [f"{r['Grup']} | {r['Gün']} | {r['Branş']} ({r['Takım 1']} vs {r['Takım 2']})" for _, r in kalan_maclar.iterrows()]
        secilen_mac_idx = st.selectbox("Eklenecek Maçı Seç:", range(len(mac_secenekleri)), format_func=lambda x: mac_secenekleri[x])
        if st.button("➕ Maçı Programa Ekle"):
            s = kalan_maclar.iloc[secilen_mac_idx]
            yeni = {"Maç Saati": "10:00", "Tarih": str(tarih_secimi), "Gün Adı": tarih_secimi.strftime("%A"), "Kort": "Kort 1", 
                    "Grup": s['Grup'], "Gün": s['Gün'], "Branş": s['Branş'], "Eşleşme": s['Eşleşme'], 
                    "Takım 1": s['Takım 1'], "T1 Oyuncular": s['T1_Oyuncu'], "Takım 2": s['Takım 2'], "T2 Oyuncular": s['T2_Oyuncu'], "Canlı Skor": "Oynanmadı"}
            st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, pd.DataFrame([yeni])], ignore_index=True)
            ortak_veriyi_kaydet(); st.rerun()

    mask = st.session_state.mac_programi['Tarih'] == str(tarih_secimi)
    gunluk_program = st.session_state.mac_programi[mask]
    if st.session_state.admin_mi:
        edited_df = st.data_editor(gunluk_program, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Değişiklikleri Kaydet"):
            diger = st.session_state.mac_programi[st.session_state.mac_programi['Tarih'] != str(tarih_secimi)]
            st.session_state.mac_programi = pd.concat([diger, edited_df], ignore_index=True)
            ortak_veriyi_kaydet(); st.rerun()
    else:
        st.table(gunluk_program[['Maç Saati', 'Kort', 'Grup', 'Branş', 'Takım 1', 'T1 Oyuncular', 'Takım 2', 'T2 Oyuncular', 'Canlı Skor']])

# ==============================================================================
# TAB 5: YÖNETİM (Sadece Admin)
# ==============================================================================
if t5:
    with t5:
        st.subheader("⚙️ Yönetim Paneli")
        # Yönetim kodların buraya...
