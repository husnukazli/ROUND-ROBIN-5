import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Tenis Turnuva Otomasyonu", layout="wide")
st.title("🎾 Profesyonel Tenis Turnuva Yönetim Sistemi")

# ==============================================================================
# SİSTEM FONKSİYONLARI
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
        except Exception:
            pass 

# ==============================================================================
# HAFIZA BAŞLATMA
# ==============================================================================
if "admin_mi" not in st.session_state:
    st.session_state.admin_mi = False

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

# ==============================================================================
# YARDIMCI FONKSİYONLAR
# ==============================================================================
def set_gecerli_mi(t1, t2, is_set3=False):
    if t1 == 0 and t2 == 0: return True, ""
    if t1 < 0 or t2 < 0: return False, "Skorlar negatif olamaz."
    max_s, min_s = max(t1, t2), min(t1, t2)
    diff = max_s - min_s
    if is_set3 and (t1 >= 10 or t2 >= 10):
        if max_s == 10 and min_s <= 8: return True, ""
        elif max_s > 10 and diff == 2: return True, ""
        else: return False, "3. Set geçersiz!"
    if max_s < 6: return False, "Set bitmemiş."
    if max_s == 6 and diff >= 2: return True, ""
    if max_s == 7 and (diff == 2 or diff == 1): return True, ""
    return False, "Geçersiz set skoru."

def eslesmeleri_olustur(grup_adi, takimlar, grup_tipi):
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
            satir = m.copy()
            satir.update({"Branş": brans, "Grup": grup_adi, "T1_Oyuncu": "", "T2_Oyuncu": "", "1.Set T1": 0, "1.Set T2": 0, "2.Set T1": 0, "2.Set T2": 0, "3.Set T1": 0, "3.Set T2": 0})
            program.append(satir)
    return program

# ==============================================================================
# SİSTEM MENÜLERİ
# ==============================================================================
with st.sidebar:
    st.markdown("### 👨‍⚖️ Turnuva Yönetim Girişi")
    if not st.session_state.admin_mi:
        if st.text_input("Yönetici Şifresi:", type="password") == "zonguldak2026":
            if st.button("🔒 Giriş Yap"): st.session_state.admin_mi = True; st.rerun()
    else:
        if st.button("🔓 Çıkış Yap"): st.session_state.admin_mi = False; st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 1. Grup Ayarları", "✍️ 2. Skor Girişi", "🏆 3. Puan Durumu", "📅 4. Maç Programı", "⚙️ 5. Yönetim"])

# --- TAB 1, 2, 3 ve 5 mevcut yapıda kalmaya devam edecek ---
# (Buraya mevcut kodlarını olduğu gibi yapıştırmaya devam edebilirsin)
with tab1:
    st.subheader("Turnuva Grupları ve Kadrolar")
    if st.session_state.admin_mi:
        grup_tipi = st.radio("Grup Tipi:", ["4'lü Grup", "5'li Grup"], horizontal=True)
        grup_adi = st.text_input("Grup Adı")
        takim_listesi = st.text_area("Takım İsimleri (Satır satır):")
        takimlar = [t.strip() for t in takim_listesi.split('\n') if t.strip()]
        if st.button("🚀 Oluştur"):
            yeni_maclar = eslesmeleri_olustur(grup_adi, takimlar, grup_tipi)
            st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, pd.DataFrame(yeni_maclar)], ignore_index=True)
            ortak_veriyi_kaydet(); st.rerun()

# --- TAB 4: GÜNCELLENMİŞ MAÇ PROGRAMI (Tüm özellikleri içeren) ---
with tab4:
    st.subheader("📅 Maç Programı ve Fikstür Yönetimi")
    col_a, col_b = st.columns(2)
    tarih_secimi = col_a.date_input("Maç Tarihi:", value=pd.to_datetime("today"))
    secilen_grup = col_b.selectbox("Grup Filtresi:", ["Hepsi"] + list(st.session_state.skor_tablosu['Grup'].unique()))

    # Mükerrer Engelleme Mantığı
    def anahtar_olustur(row):
        return f"{row['Grup']}-{row['Gün']}-{row['Branş']}-{row['Eşleşme']}"

    tum_maclar = st.session_state.skor_tablosu.copy()
    tum_maclar['key'] = tum_maclar.apply(anahtar_olustur, axis=1)
    
    if not st.session_state.mac_programi.empty:
        program_anahtarlar = st.session_state.mac_programi.apply(anahtar_olustur, axis=1).tolist()
    else:
        program_anahtarlar = []

    kalan_maclar = tum_maclar[~tum_maclar['key'].isin(program_anahtarlar)]
    if secilen_grup != "Hepsi":
        kalan_maclar = kalan_maclar[kalan_maclar['Grup'] == secilen_grup]

    # Yeni Maç Ekleme
    if st.session_state.admin_mi:
        st.markdown("### ➕ Yeni Maç Ekle")
        mac_secenekleri = [f"{row['Grup']} | {row['Gün']} | {row['Branş']} | {row['Eşleşme']} ({row['Takım 1']} vs {row['Takım 2']})" for _, row in kalan_maclar.iterrows()]
        
        if mac_secenekleri:
            secilen_mac_idx = st.selectbox("Eklenecek Maçı Seç:", range(len(mac_secenekleri)), format_func=lambda x: mac_secenekleri[x])
            if st.button("Seçili Maçı Programa Ekle"):
                secilen_row = kalan_maclar.iloc[secilen_mac_idx]
                yeni_satir = {
                    "Maç Saati": "10:00", "Tarih": str(tarih_secimi), "Gün Adı": tarih_secimi.strftime("%A"),
                    "Kort": "Kort 1", "Grup": secilen_row['Grup'], "Gün": secilen_row['Gün'],
                    "Branş": secilen_row['Branş'], "Eşleşme": secilen_row['Eşleşme'],
                    "Takım 1": secilen_row['Takım 1'], "T1 Oyuncular": secilen_row['T1_Oyuncu'],
                    "Takım 2": secilen_row['Takım 2'], "T2 Oyuncular": secilen_row['T2_Oyuncu'],
                    "Canlı Skor": "Oynanmadı"
                }
                st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, pd.DataFrame([yeni_satir])], ignore_index=True)
                ortak_veriyi_kaydet(); st.rerun()

    # Günlük Program
    st.markdown(f"### 📋 {tarih_secimi} Tarihli Maçlar")
    gunluk_program = st.session_state.mac_programi[st.session_state.mac_programi['Tarih'] == str(tarih_secimi)]

    if not gunluk_program.empty:
        if st.session_state.admin_mi:
            edited_df = st.data_editor(gunluk_program, use_container_width=True, num_rows="dynamic")
            if st.button("💾 Değişiklikleri Kaydet / Maç Sil"):
                st.session_state.mac_programi = pd.concat([
                    st.session_state.mac_programi[st.session_state.mac_programi['Tarih'] != str(tarih_secimi)],
                    edited_df
                ])
                ortak_veriyi_kaydet(); st.rerun()
        else:
            st.table(gunluk_program[['Maç Saati', 'Kort', 'Grup', 'Branş', 'Takım 1', 'T1 Oyuncular', 'Takım 2', 'T2 Oyuncular', 'Canlı Skor']])
    else:
        st.write("Bu tarihte planlanmış maç bulunmamaktadır.")

# --- TAB 5 ---
with tab5:
    st.subheader("⚙️ Yönetim Paneli")
    # Mevcut yönetim paneli kodların buraya eklenecek

# --- TAB 5: YÖNETİM & DOSYA İŞLEMLERİ ---
with tab5:
    st.subheader("⚙️ Yönetim Paneli")

    if st.session_state.admin_mi:
        # 1. BÖLÜM: TAKIM VE OYUNCU DÜZENLEME (Esnek Modül)
        with st.expander("✍️ Takım İsmi ve Kadro Düzenle (Gelişmiş)"):
            if not st.session_state.skor_tablosu.empty:
                tum_gruplar = st.session_state.skor_tablosu['Grup'].unique()
                secilen_grup = st.selectbox("Düzenlemek İçin Grup Seç:", tum_gruplar, key="admin_edit_grup")
                
                mevcut_kadrolar = st.session_state.takim_kadrolari.get(secilen_grup, {})
                
                st.write(f"### 🎯 {secilen_grup} Takım ve Kadro Düzenleme")
                
                yeni_kadro_yapisi = {}
                takim_isim_degisiklikleri = {} 
                
                for eski_takim_adi, oyuncular in mevcut_kadrolar.items():
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        yeni_ad = st.text_input(f"Takım Adı", value=eski_takim_adi, key=f"ad_{eski_takim_adi}")
                        if yeni_ad != eski_takim_adi:
                            takim_isim_degisiklikleri[eski_takim_adi] = yeni_ad
                    with col2:
                        yeni_oyuncular_text = st.text_area(f"Oyuncular (Her satıra bir isim)", value="\n".join(oyuncular), key=f"oyuncu_{eski_takim_adi}", height=100)
                        yeni_kadro_yapisi[yeni_ad if yeni_ad else eski_takim_adi] = [o.strip() for o in yeni_oyuncular_text.split('\n') if o.strip()]

                if st.button("💾 Tüm Değişiklikleri Kaydet"):
                    st.session_state.takim_kadrolari[secilen_grup] = yeni_kadro_yapisi
                    if takim_isim_degisiklikleri:
                        for eski, yeni in takim_isim_degisiklikleri.items():
                            st.session_state.skor_tablosu.replace({eski: yeni}, inplace=True)
                            st.session_state.mac_programi.replace({eski: yeni}, inplace=True)
                            
                    ortak_veriyi_kaydet() # Takım/İsim değişimini sunucuya yaz
                    st.success("✅ Güncellemeler başarıyla kaydedildi!")
                    st.rerun()
            else:
                st.info("Düzenlenecek veri bulunamadı.")

        st.markdown("---")

        # 2. BÖLÜM: DOSYA YEDEKLEME VE YÜKLEME
        st.markdown("### 💾 Dosya İşlemleri")
        c_save, c_load = st.columns(2)
        
        with c_save:
            st.write("📋 **Mevcut Durumu Yedekle**")
            export_data = {
                "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
                "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
                "takim_kadrolari": st.session_state.takim_kadrolari
            }
            st.download_button(
                label="📥 Turnuvayı İndir (.json)",
                data=json.dumps(export_data, ensure_ascii=False, indent=4),
                file_name="tenis_turnuva_yedek.json",
                mime="application/json"
            )

        with c_load:
            st.write("📤 **Turnuvayı Geri Yükle**")
            uploaded_file = st.file_uploader("Yedek Dosyası (.json)", type=["json"])
            if uploaded_file is not None:
                if st.button("📥 Seçilen Dosyayı Yükle ve Uygula"):
                    try:
                        data = json.load(uploaded_file)
                        st.session_state.skor_tablosu = pd.DataFrame(data["skor_tablosu"])
                        st.session_state.mac_programi = pd.DataFrame(data["mac_programi"])
                        st.session_state.takim_kadrolari = data["takim_kadrolari"]
                        ortak_veriyi_kaydet() # Yüklenen yedeği sunucuya göm
                        st.success("✅ Veriler yüklendi! Sayfa yenileniyor...")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Dosya okuma hatası: {e}")

        st.markdown("---")
        
        # 3. BÖLÜM: GÜVENLİ SIFIRLAMA
        st.markdown("### 🚨 Tehlikeli Bölge (Sistem Sıfırlama)")
        onay_kutususu = st.checkbox("🚨 TÜM TURNUVAYI (Skorlar, Kadrolar, Program) SİLMEK İSTİYORUM.")
        
        if onay_kutususu:
            if st.button("⚠️ EMİNİM, HER ŞEYİ SIFIRLA"):
                st.session_state.skor_tablosu = pd.DataFrame(columns=[
                    "Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu",
                    "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"
                ])
                st.session_state.mac_programi = pd.DataFrame(columns=[
                    "Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor"
                ])
                st.session_state.takim_kadrolari = {}
                ortak_veriyi_kaydet() # Sunucudaki dosyayı da tamamen temizle
                st.rerun()
        else:
            st.warning("Sistemi tamamen sıfırlamak için yukarıdaki onay kutusunu işaretleyin.")
            
    else:
        st.warning("🔒 Bu alan dışarıdan erişime kapalıdır. Yönetim paneli sadece Başhakeme aittir.")
