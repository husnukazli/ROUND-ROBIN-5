import streamlit as st
import pandas as pd
import json

# ==============================================================================
# 1. BÖLÜM: SESSION STATE (HAFIZA) BAŞLATMA
# ==============================================================================
# (Sizin kodunuzun en üstündeki st.session_state tanımlamaları aynen burada kalacak)
if "skor_tablosu" not in st.session_state:
    st.session_state.skor_tablosu = pd.DataFrame(columns=[
        "Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu",
        "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"
    ])
if "mac_programi" not in st.session_state:
    st.session_state.mac_programi = pd.DataFrame(columns=[
        "Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor"
    ])
if "takim_kadrolari" not in st.session_state:
    st.session_state.takim_kadrolari = {}

# ==============================================================================
# 2. BÖLÜM: GİZLİ BAŞHAKEM ŞİFRE PANELİ (SOL MENÜ)
# ==============================================================================
with st.sidebar:
    st.markdown("### 👨‍⚖️ Turnuva Yönetim Girişi")
    girilen_sifre = st.text_input("Yönetici Şifresi:", type="password")
    
    # Şifreyi burayı değiştirerek güncelleyebilirsiniz
    if girilen_sifre == "zonguldak2026":
        st.session_state.admin_mi = True
        st.success("✅ Başhakem Yetkisi Aktif!")
    else:
        st.session_state.admin_mi = False
        st.info("👀 İzleyici Modu: Sadece sonuçları ve programı görebilirsiniz.")

# ==============================================================================
# 3. BÖLÜM: SEKMELERİN TANIMLANMASI
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
    
    # 🔓 HERKESİN GÖREBİLECEĞİ KISIM (Okuma Modu)
    # --- BURAYA MEVCUT KODUNUZDAKİ GRUPLARI/TAKIMLARI LİSTELEYEN TABLO KODLARINI KOYUN ---
    st.write("Mevcut gruplar ve oyuncu listeleri burada listelenecek.")


    # 🔒 SADECE BAŞHAKEMİN GÖREBİLECEĞİ KISIM (Grup Oluşturma Alanı)
    st.markdown("---")
    if st.session_state.admin_mi:
        st.markdown("### 🛠️ Yeni Grup & Fikstür Oluşturma (Sadece Başhakem)")
        # --- BURAYA MEVCUT KODUNUZDAKİ "GRUP ADI GİR", "TAKIM SAYISI SEÇ", "FİKSTÜR OLUŞTUR" BUTONLARINI KOYUN ---
    else:
        st.info("ℹ️ Yeni grup oluşturma ve ilk kurulum alanları sadece Başhakeme açıktır.")

# ==============================================================================
# TAB 2: MAÇ PROGRAMI
# ==============================================================================
with tab2:
    st.subheader("📅 Canlı Maç Programı / Fikstür")
    # 🔓 HERKESİN GÖREBİLECEĞİ KISIM (Okuma Modu)
    # --- BURAYA MEVCUT KODUNUZDAKİ MAÇ PROGRAMI TABLOSUNU GÖSTEREN KODLARI KOYUN ---
    st.dataframe(st.session_state.mac_programi)

# ==============================================================================
# TAB 3: PUAN DURUMU & SONUÇLAR
# ==============================================================================
with tab3:
    st.subheader("📊 Canlı Puan Durumu ve Maç Sonuçları")
    # 🔓 HERKESİN GÖREBİLECEĞİ KISIM (Okuma Modu)
    # --- BURAYA MEVCUT KODUNUZDAKİ PUAN DURUMU HESAPLAYAN VE TABLOLARI GÖSTEREN KODLARI KOYUN ---
    st.write("Puan durumları ve tamamlanan maç sonuçları burada görüntülenecek.")

# ==============================================================================
# TAB 4: SKOR GİRİŞİ
# ==============================================================================
with tab4:
    st.subheader("🎾 Maç Skoru Girme Paneli")
    
    # 🔒 SADECE BAŞHAKEMİN GÖREBİLECEĞİ KISIM
    if st.session_state.admin_mi:
        # --- BURAYA MEVCUT KODUNUZDAKİ "MAÇ SEÇ", "SKORLARI YAZ", "KAYDET" KODLARINIZI KOYUN ---
        st.write("Skor giriş formları yetki dahilinde burada çalışacak.")
    else:
        st.warning("🔒 Bu alan dışarıdan erişime kapalıdır. Skorları sadece Başhakem girebilir.")

# ==============================================================================
# TAB 5: YÖNETİM & DOSYA İŞLEMLERİ (Son Birleştirdiğimiz Güvenli Bölüm)
# ==============================================================================
with tab5:
    st.subheader("⚙️ Yönetim Paneli")

    # 🔒 SADECE BAŞHAKEMİN GÖREBİLECEĞİ KISIM
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
                    if  takim_isim_degisiklikleri:
                        for eski, yeni in takim_isim_degisiklikleri.items():
                            st.session_state.skor_tablosu.replace({eski: yeni}, inplace=True)
                            st.session_state.mac_programi.replace({eski: yeni}, inplace=True)
                    st.success("✅ Güncellemeler başarıyla kaydedildi!")
                    st.rerun()
            else:
                st.info("Düzenlenecek veri bulunamadı.")

        st.markdown("---")

        # B) DOSYA İŞLEMLERİ
        st.markdown("### 💾 Dosya İşlemleri")
        c_save, c_load = st.columns(2)
        with c_save:
            st.write("📋 **Mevcut Durumu Yedekle**")
            export_data = {"skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"), "mac_programi": st.session_state.mac_programi.to_dict(orient="records"), "takim_kadrolari": st.session_state.takim_kadrolari}
            st.download_button(label="📥 Turnuvayı İndir (.json)", data=json.dumps(export_data, ensure_ascii=False, indent=4), file_name="tenis_turnuva_yedek.json", mime="application/json")
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
                        st.success("✅ Veriler yüklendi! Sayfa yenileniyor...")
                        st.rerun()
                    except Exception as e: st.error(f"Dosya okuma hatası: {e}")

        st.markdown("---")
        
        # C) GÜVENLİ SIFIRLAMA
        st.markdown("### 🚨 Tehlikeli Bölge (Sistem Sıfırlama)")
        onay_kutususu = st.checkbox("🚨 TÜM TURNUVAYI SİLMEK İSTİYORUM.")
        if onay_kutususu:
            if st.button("⚠️ EMİNİM, HER ŞEYİ SIFIRLA"):
                st.session_state.skor_tablosu = pd.DataFrame(columns=["Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu", "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"])
                st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor"])
                st.session_state.takim_kadrolari = {}
                st.rerun()
        else:
            st.warning("Sistemi tamamen sıfırlamak için yukarıdaki onay kutusunu işaretleyin.")
            
    else:
        st.warning("🔒 Bu alan dışarıdan erişime kapalıdır. Yetkiniz bulunmamaktadır.")
