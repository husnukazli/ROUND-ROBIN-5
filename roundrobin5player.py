import streamlit as st
import pandas as pd
import json
import os

# Ortak veri dosyasının adı (Veritabanımız)
VERI_DOSYASI = "turnuva_veri.json"

# ==============================================================================
# SİSTEM FONKSİYONLARI (ORTAK VERİ YAZMA VE OKUMA)
# ==============================================================================
def ortak_veriyi_kaydet():
    """Adminin yaptığı tüm değişiklikleri sunucudaki ortak dosyaya yazar."""
    data = {
        "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
        "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
        "takim_kadrolari": st.session_state.takim_kadrolari
    }
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def ortak_veriyi_yukle():
    """Siteyi açan herkesin ortak dosyadan güncel verileri çekmesini sağlar."""
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.session_state.skor_tablosu = pd.DataFrame(data["skor_tablosu"])
            st.session_state.mac_programi = pd.DataFrame(data["mac_programi"])
            st.session_state.takim_kadrolari = data["takim_kadrolari"]
        except Exception as e:
            pass # Dosya okunamazsa boş başlatır

# ==============================================================================
# HAFIZA (SESSION STATE) İLKLENDİRME
# ==============================================================================
if "admin_mi" not in st.session_state:
    st.session_state.admin_mi = False

# Eğer hafızada tablolar yoksa önce ortak dosyadan yükle, dosya da yoksa boş oluştur
if "skor_tablosu" not in st.session_state:
    if os.path.exists(VERI_DOSYASI):
        ortak_veriyi_yukle()
    else:
        st.session_state.skor_tablosu = pd.DataFrame(columns=[
            "Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu",
            "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"
        ])
        st.session_state.mac_programi = pd.DataFrame(columns=[
            "Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor"
        ])
        st.session_state.takim_kadrolari = {}

# ==============================================================================
# GÜVENLİ BAŞHAKEM GİRİŞ PANELİ (SOL MENÜ)
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
                st.error("❌ Hatalı Şifre girdiniz!")
    else:
        st.write("🟢 **Mod:** Başhakem (Yönetici)")
        if st.button("🔓 Çıkış Yap (İzleyici Moduna Dön)"):
            st.session_state.admin_mi = False
            st.rerun()

# ==============================================================================
# SEKMELERİN TANIMLANMASI
# ==============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "👥 Gruplar & Kadrolar", 
    "📅 Maç Programı", 
    "📊 Puan Durumu & Sonuçlar", 
    "🎾 Skor Girişi", 
    "⚙️ Yönetim Paneli"
])

# ==============================================================================
# TAB 1: GRUPLAR & KADROLAR
# ==============================================================================
with tab1:
    st.subheader("👥 Turnuva Grupları ve Oyuncu Kadroları")
    
    # 🔓 İZLEYİCİ GÖRÜNTÜLEME ALANI
    # --- BURAYA MEVCUT KODUNUZDAKİ GRUPLARI EKİPLERİ EKRAna BASAN TABLOLARI KOYUN ---
    st.write("Mevcut gruplar ve oyuncular burada herkes tarafından görülecek.")

    # 🔒 SADECE BAŞHAKEMİN GÖREBİLECEĞİ KISIM (Grup Kurma)
    st.markdown("---")
    if st.session_state.admin_mi:
        st.markdown("### 🛠️ Yeni Grup & Fikstür Oluşturma (Sadece Başhakem)")
        # --- BURAYA ESKİ GRUP OLUŞTURMA BUTONLARINIZI KOYUN ---
        # ÖNEMLİ: Grup oluşturma butonunun kod bloğunun en sonuna 
        # `ortak_veriyi_kaydet()` fonksiyonunu ekleyin ki oluşturulan gruplar ortak dosyaya yazılsın!
    else:
        st.info("ℹ️ Yeni grup oluşturma ve ilk kurulum alanları sadece Başhakeme açıktır.")

# ==============================================================================
# TAB 2: MAÇ PROGRAMI
# ==============================================================================
with tab2:
    st.subheader("📅 Canlı Maç Programı / Fikstür")
    # 🔓 HERKESİN GÖREBİLECEĞİ KISIM (Okuma Modu)
    st.dataframe(st.session_state.mac_programi, use_container_width=True)

# ==============================================================================
# TAB 3: PUAN DURUMU & SONUÇLAR
# ==============================================================================
with tab3:
    st.subheader("📊 Canlı Puan Durumu ve Maç Sonuçları")
    # 🔓 HERKESİN GÖREBİLECEĞİ KISIM (Okuma Modu)
    # --- BURAYA MEVCUT KODUNUZDAKİ PUAN DURUMU HESAPLAMA VE GÖSTERME TABLOLARINI KOYUN ---
    st.write("Puan durumları ve tamamlanan maç sonuçları burada canlı görüntülenecek.")

# ==============================================================================
# TAB 4: SKOR GİRİŞİ
# ==============================================================================
with tab4:
    st.subheader("🎾 Maç Skoru Girme Paneli")
    
    # 🔒 SADECE BAŞHAKEMİN GÖREBİLECEĞİ KISIM
    if st.session_state.admin_mi:
        st.markdown("### ✍️ Skor Girişi Yapın")
        # --- BURAYA MEVCUT SKOR GİRİŞ FORMLARINIZI VE BUTONUNUZU KOYUN ---
        
        # ÖNEMLİ ÖRNEK: Skor Kaydet butonunuzun tetiklendiği yer tam olarak şöyle olmalı:
        # if st.button("Skorları Kaydet"):
        #     st.session_state.skor_tablosu = ... (skorları işleyen kodunuz)
        #     ortak_veriyi_kaydet() # <--- BU SATIRI EKLEYİN Kİ DÜNYA GÖREBİLSİN!
        #     st.success("Skor kaydedildi ve yayınlandı!")
        #     st.rerun()
    else:
        st.warning("🔒 Bu alan dışarıdan erişime kapalıdır. Skorları sadece Başhakem girebilir.")

# ==============================================================================
# TAB 5: YÖNETİM & DOSYA İŞLEMLERİ (Gelişmiş Takım/Oyuncu Düzenleme Modülü)
# ==============================================================================
with tab5:
    st.subheader("⚙️ Yönetim Paneli")

    if st.session_state.admin_mi:
        # A) TAKIM VE OYUNCU DÜZENLEME MODÜLÜ
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
                    
                    # Ortak dosyaya kaydetmeyi tetikliyoruz
                    ortak_veriyi_kaydet()
                    st.success("✅ Güncellemeler kaydedildi ve canlıya aktarıldı!")
                    st.rerun()
            else:
                st.info("Düzenlenecek veri bulunamadı.")

        st.markdown("---")

        # B) DOSYA İŞLEMLERİ
        st.markdown("### 💾 Yedekleme İşlemleri")
        c_save, c_load = st.columns(2)
        with c_save:
            export_data = {"skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"), "mac_programi": st.session_state.mac_programi.to_dict(orient="records"), "takim_kadrolari": st.session_state.takim_kadrolari}
            st.download_button(label="📥 Turnuva Verisini Bilgisayara İndir (.json)", data=json.dumps(export_data, ensure_ascii=False, indent=4), file_name="tenis_turnuva_yedek.json", mime="application/json")
        with c_load:
            uploaded_file = st.file_uploader("Yedek Dosyası Yükle (.json)", type=["json"])
            if uploaded_file is not None:
                if st.button("📥 Yedekten Geri Yükle ve Canlıya Al"):
                    try:
                        data = json.load(uploaded_file)
                        st.session_state.skor_tablosu = pd.DataFrame(data["skor_tablosu"])
                        st.session_state.mac_programi = pd.DataFrame(data["mac_programi"])
                        st.session_state.takim_kadrolari = data["takim_kadrolari"]
                        ortak_veriyi_kaydet() # Yüklenen yedeği ortak dosyaya yaz
                        st.success("✅ Veriler yedekten yüklendi ve canlıya aktarıldı!")
                        st.rerun()
                    except Exception as e: st.error(f"Hata: {e}")

        st.markdown("---")
        
        # C) GÜVENLİ SIFIRLAMA
        st.markdown("### 🚨 Tehlikeli Bölge (Sistem Sıfırlama)")
        onay_kutususu = st.checkbox("🚨 TÜM TURNUVA VERİLERİNİ SİLMEK İSTİYORUM.")
        if onay_kutususu:
            if st.button("⚠️ EMİNİM, HER ŞEYİ SIFIRLA"):
                st.session_state.skor_tablosu = pd.DataFrame(columns=["Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu", "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"])
                st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor"])
                st.session_state.takim_kadrolari = {}
                ortak_veriyi_kaydet() # Ortak dosyayı da sıfırla
                st.success("Sistem tamamen sıfırlandı!")
                st.rerun()
            
    else:
        st.warning("🔒 Bu alan dışarıdan erişime kapalıdır. Yetkiniz bulunmamaktadır.")
