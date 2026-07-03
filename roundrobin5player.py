import streamlit as st
import pandas as pd
import json
import os
import datetime

# --- SAYFA AYARLARI VE CSS ---
st.set_page_config(page_title="Tenis Turnuva Yönetimi", layout="wide")
st.markdown("""
<style>
.custom-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
.custom-table th, .custom-table td { border: 1px solid #ddd; padding: 10px; text-align: center; }
.custom-table th { background-color: #f2f2f2; color: black; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- VERİ DOSYASI VE FONKSİYONLAR ---
VERI_DOSYASI = "turnuva_verileri.json"

def ortak_veriyi_yukle():
    if os.path.exists(VERI_DOSYASI):
        with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if "skor_tablosu" in data:
                    st.session_state.skor_tablosu = pd.DataFrame(data["skor_tablosu"])
                if "mac_programi" in data:
                    st.session_state.mac_programi = pd.DataFrame(data["mac_programi"])
                if "takim_kadrolari" in data:
                    st.session_state.takim_kadrolari = data["takim_kadrolari"]
            except:
                pass

def ortak_veriyi_kaydet():
    data = {
        "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
        "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
        "takim_kadrolari": st.session_state.takim_kadrolari
    }
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- SESSION STATE BAŞLANGIÇ ---
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False
if "skor_tablosu" not in st.session_state:
    st.session_state.skor_tablosu = pd.DataFrame(columns=["Grup", "Takım 1", "Takım 2", "Skor 1", "Skor 2", "Oynandı"])
if "mac_programi" not in st.session_state:
    st.session_state.mac_programi = pd.DataFrame(columns=["Grup", "Takım 1", "Takım 2", "Tarih/Saat", "Kort"])
if "takim_kadrolari" not in st.session_state:
    st.session_state.takim_kadrolari = {}

ortak_veriyi_yukle()

# --- YAN MENÜ (BAŞHAKEM GİRİŞİ) ---
with st.sidebar:
    st.title("🎾 Turnuva Yönetimi")
    if not st.session_state.giris_yapildi:
        sifre = st.text_input("Başhakem Şifresi:", type="password")
        if st.button("Giriş Yap"):
            if sifre == "admin":  # Şifrenizi buradan değiştirebilirsiniz
                st.session_state.giris_yapildi = True
                st.success("Giriş başarılı!")
                st.rerun()
            else:
                st.error("Hatalı şifre!")
    else:
        st.success("Başhakem Yetkisi Aktif")
        if st.button("Çıkış Yap"):
            st.session_state.giris_yapildi = False
            st.rerun()

# --- ANA SEKMELER ---
t1, t2, t3, t4, t5 = st.tabs([
    "👥 Gruplar & Takımlar", 
    "📅 Maç Programı Düzenle", 
    "✍️ Skor Girişi", 
    "🏆 Misafir Modu & Puan", 
    "⚙️ Yönetim Paneli"
])

# --- SEKME 1: GRUP VE TAKIM OLUŞTURMA ---
with t1:
    if not st.session_state.giris_yapildi:
        st.warning("🔒 Bu sekme sadece Başhakem içindir.")
    else:
        st.header("Grup ve Takım İşlemleri")
        grup_adi = st.text_input("Yeni Grup Adı Ekle (Örn: A Grubu):")
        if st.button("Grup Ekle"):
            if grup_adi and grup_adi not in st.session_state.takim_kadrolari:
                st.session_state.takim_kadrolari[grup_adi] = {}
                ortak_veriyi_kaydet()
                st.success(f"{grup_adi} oluşturuldu!")
                st.rerun()
        
        st.divider()
        if st.session_state.takim_kadrolari:
            secili_grup = st.selectbox("İşlem Yapılacak Grup Seçin:", list(st.session_state.takim_kadrolari.keys()))
            c_takim, c_oyuncu = st.columns(2)
            with c_takim:
                takim_adi = st.text_input("Takım Adı Girin:")
            with c_oyuncu:
                oyuncular = st.text_area("Oyuncular (Her satıra bir isim):")
            
            if st.button("Takım Ekle"):
                if takim_adi and oyuncular:
                    oyuncu_listesi = [o.strip() for o in oyuncular.split("\n") if o.strip()]
                    st.session_state.takim_kadrolari[secili_grup][takim_adi] = oyuncu_listesi
                    ortak_veriyi_kaydet()
                    st.success(f"{takim_adi} takımı kadrosuyla birlikte eklendi!")
                    st.rerun()

# --- SEKME 2: MAÇ PROGRAMI OLUŞTURMA & GERİ ALMA ---
with t2:
    if not st.session_state.giris_yapildi:
        st.warning("🔒 Bu sekme sadece Başhakem içindir.")
    else:
        st.header("Maç Programı Oluşturma")
        if st.session_state.takim_kadrolari:
            m_grup = st.selectbox("Grup Seç:", list(st.session_state.takim_kadrolari.keys()), key="m_grup")
            takimlar = list(st.session_state.takim_kadrolari[m_grup].keys())
            
            if len(takimlar) >= 2:
                c1, c2 = st.columns(2)
                t_1 = c1.selectbox("1. Takım:", takimlar)
                t_2 = c2.selectbox("2. Takım:", [t for t in takimlar if t != t_1])
                tarih = st.text_input("Tarih / Saat (Örn: 10 Mayıs 14:00):")
                kort = st.text_input("Kort (Örn: Kort 1):")
                
                if st.button("➕ Maçı Ekle"):
                    yeni_mac = pd.DataFrame([{
                        "Grup": m_grup, "Takım 1": t_1, "Takım 2": t_2, 
                        "Tarih/Saat": tarih, "Kort": kort
                    }])
                    st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, yeni_mac], ignore_index=True)
                    
                    # Skor tablosuna da maçı kaydet (Oynanmadı olarak)
                    yeni_skor = pd.DataFrame([{
                        "Grup": m_grup, "Takım 1": t_1, "Takım 2": t_2, 
                        "Skor 1": 0, "Skor 2": 0, "Oynandı": False
                    }])
                    st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_skor], ignore_index=True)
                    ortak_veriyi_kaydet()
                    st.success("Maç programa başarıyla eklendi!")
                    st.rerun()
            else:
                st.info("Eşleşme yapabilmek için bu grupta en az 2 takım olmalı.")
        
        st.divider()
        st.subheader("Mevcut Maç Programı")
        st.dataframe(st.session_state.mac_programi, use_container_width=True)
        
        # SATIR GERİ ALMA (UNDO) İŞLEMİ
        if not st.session_state.mac_programi.empty:
            if st.button("↩️ Son Eklenen Maçı Geri Al (Sil)", type="primary"):
                st.session_state.mac_programi = st.session_state.mac_programi.iloc[:-1]
                st.session_state.skor_tablosu = st.session_state.skor_tablosu.iloc[:-1]
                ortak_veriyi_kaydet()
                st.warning("Yanlışlıkla eklenen son maç programdan ve skor listesinden silindi.")
                st.rerun()

# --- SEKME 3: SKOR GİRİŞİ ---
with t3:
    if not st.session_state.giris_yapildi:
        st.warning("🔒 Bu sekme sadece Başhakem içindir.")
    else:
        st.header("Skor Girişi")
        oynanmamis_maclar = st.session_state.skor_tablosu[st.session_state.skor_tablosu["Oynandı"] == False]
        
        if not oynanmamis_maclar.empty:
            mac_secim_listesi = oynanmamis_maclar.apply(
                lambda x: f"{x['Grup']} | {x['Takım 1']} vs {x['Takım 2']}", axis=1
            ).tolist()
            secilen_mac_str = st.selectbox("Skoru Girilecek Maçı Seçin:", mac_secim_listesi)
            secilen_idx = mac_secim_listesi.index(secilen_mac_str)
            gercek_idx = oynanmamis_maclar.index[secilen_idx]
            
            satir = oynanmamis_maclar.iloc[secilen_idx]
            c1, c2 = st.columns(2)
            s1 = c1.number_input(f"{satir['Takım 1']} Skoru:", min_value=0, step=1)
            s2 = c2.number_input(f"{satir['Takım 2']} Skoru:", min_value=0, step=1)
            
            if st.button("💾 Skoru Kaydet ve Oynandı Olarak İşaretle"):
                st.session_state.skor_tablosu.at[gercek_idx, "Skor 1"] = s1
                st.session_state.skor_tablosu.at[gercek_idx, "Skor 2"] = s2
                st.session_state.skor_tablosu.at[gercek_idx, "Oynandı"] = True
                ortak_veriyi_kaydet()
                st.success("Skor başarıyla kaydedildi!")
                st.rerun()
        else:
            st.info("Skoru girilecek bekleyen maç bulunmuyor.")

# --- SEKME 4: MİSAFİR MODU (KİLİTLİ TABLOLAR & TAKIM ALTINDA OYUNCULAR) ---
with t4:
    st.header("🏆 Turnuva Görünümü (Misafir Modu)")
    
    st.subheader("📊 Puan Durumu")
    for g in st.session_state.takim_kadrolari.keys():
        grup_maclari = st.session_state.skor_tablosu[(st.session_state.skor_tablosu["Grup"] == g) & (st.session_state.skor_tablosu["Oynandı"] == True)]
        puan_tablosu = {t: {"O": 0, "G": 0, "M": 0, "Puan": 0} for t in st.session_state.takim_kadrolari[g].keys()}
        
        for _, mac in grup_maclari.iterrows():
            t1, t2 = mac["Takım 1"], mac["Takım 2"]
            s1, s2 = mac["Skor 1"], mac["Skor 2"]
            if t1 in puan_tablosu and t2 in puan_tablosu:
                puan_tablosu[t1]["O"] += 1
                puan_tablosu[t2]["O"] += 1
                if s1 > s2:
                    puan_tablosu[t1]["G"] += 1
                    puan_tablosu[t1]["Puan"] += 2
                    puan_tablosu[t2]["M"] += 1
                    puan_tablosu[t2]["Puan"] += 1
                elif s2 > s1:
                    puan_tablosu[t2]["G"] += 1
                    puan_tablosu[t2]["Puan"] += 2
                    puan_tablosu[t1]["M"] += 1
                    puan_tablosu[t1]["Puan"] += 1
        
        df_puan = pd.DataFrame.from_dict(puan_tablosu, orient="index").reset_index()
        df_puan.rename(columns={"index": "Takım"}, inplace=True)
        df_puan = df_puan.sort_values(by=["Puan", "G"], ascending=False).reset_index(drop=True)
        
        st.markdown(f"#### {g}")
        # Kilitli (Kolon değiştirilemeyen) HTML Tablosu
        st.markdown(df_puan.to_html(index=False, classes="custom-table"), unsafe_allow_html=True)

    st.divider()
    st.subheader("📅 Maç Programı")
    if not st.session_state.mac_programi.empty:
        gorunum_df = st.session_state.mac_programi.copy()
        
        # Takım ismi altına oyuncu isimlerini gri fontla ekleyen fonksiyon
        def takim_ve_oyunculari_getir(grup, takim):
            oyuncular = st.session_state.takim_kadrolari.get(grup, {}).get(takim, [])
            if oyuncular:
                oyuncular_str = "<br>".join(oyuncular)
                return f"<b>{takim}</b><br><span style='font-size:0.85em; color:gray;'>{oyuncular_str}</span>"
            return f"<b>{takim}</b>"

        gorunum_df["Takım 1"] = gorunum_df.apply(lambda x: takim_ve_oyunculari_getir(x["Grup"], x["Takım 1"]), axis=1)
        gorunum_df["Takım 2"] = gorunum_df.apply(lambda x: takim_ve_oyunculari_getir(x["Grup"], x["Takım 2"]), axis=1)
        
        # Kilitli (Kolon değiştirilemeyen) HTML Tablosu (escape=False ile HTML etiketleri aktif)
        st.markdown(gorunum_df.to_html(escape=False, index=False, classes="custom-table"), unsafe_allow_html=True)
    else:
        st.info("Henüz maç programı oluşturulmamış.")

# --- SEKME 5: YÖNETİM VE VERİ DÜZELTME PANELİ ---
with t5:
    if not st.session_state.giris_yapildi:
        st.info("🔒 Bu panele yalnızca Başhakem erişebilir.")
    else:
        st.header("⚙️ Yönetim ve Veri Düzeltme Paneli")
        st.markdown("### ✏️ Grup, Takım ve Kadro Düzeltme")
        
        if st.session_state.takim_kadrolari:
            sec_g = st.selectbox("Düzenlenecek Grubu Seçin:", list(st.session_state.takim_kadrolari.keys()))
            yeni_grup_adi = st.text_input("Grup Adını Güncelle:", value=sec_g)
            
            st.write("#### Takım İsimleri ve Kadrolarını Güncelle")
            yeni_k_yapisi = {}
            isim_degisiklikleri = {}
            
            for esk_ad, oyuncular in st.session_state.takim_kadrolari[sec_g].items():
                c_a, c_b = st.columns(2)
                with c_a:
                    y_ad = st.text_input(f"Takım Adı ({esk_ad})", value=esk_ad, key=f"t_{esk_ad}")
                    if y_ad != esk_ad:
                        isim_degisiklikleri[esk_ad] = y_ad
                with c_b:
                    y_oyuncular = st.text_area(f"Kadro (Satır Satır)", value="\n".join(oyuncular), height=100, key=f"o_{esk_ad}")
                    yeni_k_yapisi[y_ad] = [o.strip() for o in y_oyuncular.split("\n") if o.strip()]
                    
            if st.button("💾 Değişiklikleri Kaydet (Tüm Geçmişe Yansır)"):
                # Grup adı değişikliği
                if yeni_grup_adi != sec_g:
                    st.session_state.skor_tablosu.loc[st.session_state.skor_tablosu['Grup'] == sec_g, 'Grup'] = yeni_grup_adi
                    st.session_state.mac_programi.loc[st.session_state.mac_programi['Grup'] == sec_g, 'Grup'] = yeni_grup_adi
                    st.session_state.takim_kadrolari[yeni_grup_adi] = st.session_state.takim_kadrolari.pop(sec_g)
                    sec_g = yeni_grup_adi 
                
                # Takım adı değişiklikleri
                for e_ad, y_ad in isim_degisiklikleri.items():
                    st.session_state.skor_tablosu.loc[(st.session_state.skor_tablosu['Grup'] == sec_g) & (st.session_state.skor_tablosu['Takım 1'] == e_ad), 'Takım 1'] = y_ad
                    st.session_state.skor_tablosu.loc[(st.session_state.skor_tablosu['Grup'] == sec_g) & (st.session_state.skor_tablosu['Takım 2'] == e_ad), 'Takım 2'] = y_ad
                    st.session_state.mac_programi.loc[(st.session_state.mac_programi['Grup'] == sec_g) & (st.session_state.mac_programi['Takım 1'] == e_ad), 'Takım 1'] = y_ad
                    st.session_state.mac_programi.loc[(st.session_state.mac_programi['Grup'] == sec_g) & (st.session_state.mac_programi['Takım 2'] == e_ad), 'Takım 2'] = y_ad
                
                st.session_state.takim_kadrolari[sec_g] = yeni_k_yapisi
                ortak_veriyi_kaydet()
                st.success("✅ Veriler her yerde geçmişe dönük olarak güncellendi!")
                st.rerun()

        st.divider()
        st.markdown("### 🗑️ Yedekleme ve Sıfırlama")
        c_yedek, c_sil = st.columns(2)
        with c_yedek:
            if os.path.exists(VERI_DOSYASI):
                with open(VERI_DOSYASI, "rb") as f:
                    st.download_button(
                        label="📥 Turnuva Verisini Yedekle (JSON)", 
                        data=f, 
                        file_name=f"turnuva_yedek_{datetime.date.today().strftime('%Y%m%d')}.json", 
                        mime="application/json"
                    )
        with c_sil:
            onayi_ver = st.checkbox("Turnuvayı tamamen sıfırlamayı onaylıyorum.")
            if st.button("🚨 Tüm Sistemi Sıfırla", type="primary", disabled=not onayi_ver):
                st.session_state.clear()
                if os.path.exists(VERI_DOSYASI):
                    os.remove(VERI_DOSYASI)
                st.rerun()
