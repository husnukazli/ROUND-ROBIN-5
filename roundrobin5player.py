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

# --- SABİTLER ---
VERI_DOSYASI = "turnuva_verileri.json"
FORMAT_SECENEKLERI = {
    "Tekli Maç Formatı": ["Genel"],
    "3'lü Takım Serisi (1. Tek, 2. Tek, Çiftler)": ["1. Tekler", "2. Tekler", "Çiftler"],
    "5'li Takım Serisi (1. Tek, 2. Tek, 3. Tek, 1. Çift, 2. Çift)": ["1. Tekler", "2. Tekler", "3. Tekler", "1. Çiftler", "2. Çiftler"]
}

def tablo_eksiklerini_tamamla(df, tur):
    """Eski JSON dosyalarından gelen eksik sütunları onarır."""
    if df.empty:
        return df
        
    if "Alt Maç" not in df.columns:
        df.insert(3, "Alt Maç", "Genel")
        
    if tur == "skor":
        if "Oynandı" not in df.columns:
            df["Oynandı"] = False
        if "Skor 1" not in df.columns:
            df["Skor 1"] = 0
        if "Skor 2" not in df.columns:
            df["Skor 2"] = 0
            
    elif tur == "mac":
        if "Tarih/Saat" not in df.columns:
            df["Tarih/Saat"] = ""
        if "Kort" not in df.columns:
            df["Kort"] = ""
            
    return df

def ortak_veriyi_yukle():
    if os.path.exists(VERI_DOSYASI):
        with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                
                if "skor_tablosu" in data:
                    df_skor = pd.DataFrame(data["skor_tablosu"])
                    st.session_state.skor_tablosu = tablo_eksiklerini_tamamla(df_skor, "skor")
                    
                if "mac_programi" in data:
                    df_mac = pd.DataFrame(data["mac_programi"])
                    st.session_state.mac_programi = tablo_eksiklerini_tamamla(df_mac, "mac")
                    
                if "takim_kadrolari" in data:
                    st.session_state.takim_kadrolari = data["takim_kadrolari"]
                    
                if "grup_formatlari" in data:
                    st.session_state.grup_formatlari = data["grup_formatlari"]
                else:
                    # Eski veriler için varsayılan format oluştur
                    st.session_state.grup_formatlari = {g: "Tekli Maç Formatı" for g in st.session_state.takim_kadrolari.keys()}
            except:
                pass

def ortak_veriyi_kaydet():
    data = {
        "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
        "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
        "takim_kadrolari": st.session_state.takim_kadrolari,
        "grup_formatlari": st.session_state.grup_formatlari
    }
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- SESSION STATE BAŞLANGIÇ ---
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False
if "skor_tablosu" not in st.session_state:
    st.session_state.skor_tablosu = pd.DataFrame(columns=["Grup", "Takım 1", "Takım 2", "Alt Maç", "Skor 1", "Skor 2", "Oynandı"])
if "mac_programi" not in st.session_state:
    st.session_state.mac_programi = pd.DataFrame(columns=["Grup", "Takım 1", "Takım 2", "Alt Maç", "Tarih/Saat", "Kort"])
if "takim_kadrolari" not in st.session_state:
    st.session_state.takim_kadrolari = {}
if "grup_formatlari" not in st.session_state:
    st.session_state.grup_formatlari = {}

ortak_veriyi_yukle()

# --- YAN MENÜ ---
with st.sidebar:
    st.title("🎾 Turnuva Yönetimi")
    if not st.session_state.giris_yapildi:
        sifre = st.text_input("Başhakem Şifresi:", type="password")
        if st.button("Giriş Yap"):
            if sifre == "admin":  
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
        
        col_form, col_liste = st.columns([5, 5], gap="large")
        
        with col_form:
            st.subheader("➕ Yeni Grup Ekle")
            grup_adi = st.text_input("Yeni Grup Adı Ekle (Örn: 35 Kadınlar):")
            secili_format = st.selectbox("Grubun Maç Formatı:", list(FORMAT_SECENEKLERI.keys()))
            
            if st.button("Grup Ekle"):
                if grup_adi and grup_adi not in st.session_state.takim_kadrolari:
                    st.session_state.takim_kadrolari[grup_adi] = {}
                    st.session_state.grup_formatlari[grup_adi] = secili_format
                    ortak_veriyi_kaydet()
                    st.success(f"{grup_adi} ({secili_format}) oluşturuldu!")
                    st.rerun()
            
            st.divider()
            if st.session_state.takim_kadrolari:
                st.subheader("👕 Takım Ekle")
                secili_grup = st.selectbox("İşlem Yapılacak Grup Seçin:", list(st.session_state.takim_kadrolari.keys()))
                st.info(f"Bu grubun formatı: **{st.session_state.grup_formatlari.get(secili_grup, 'Bilinmiyor')}**")
                
                takim_adi = st.text_input("Takım Adı Girin (Örn: İzmir):")
                oyuncular = st.text_area("Oyuncular (Her satıra bir isim):", height=150)
                
                if st.button("Takım Ekle"):
                    if takim_adi and oyuncular:
                        oyuncu_listesi = [o.strip() for o in oyuncular.split("\n") if o.strip()]
                        st.session_state.takim_kadrolari[secili_grup][takim_adi] = oyuncu_listesi
                        ortak_veriyi_kaydet()
                        st.success(f"{takim_adi} takımı eklendi!")
                        st.rerun()
        
        with col_liste:
            st.subheader("📋 Mevcut Gruplar ve Kadrolar")
            if not st.session_state.takim_kadrolari:
                st.info("Henüz sisteme eklenmiş bir grup bulunmuyor.")
            else:
                for g_adi, takimlar in st.session_state.takim_kadrolari.items():
                    format_bilgisi = st.session_state.grup_formatlari.get(g_adi, "Format Belirtilmemiş")
                    with st.expander(f"📁 {g_adi} - [{format_bilgisi}]"):
                        if not takimlar:
                            st.write("*Bu grupta henüz takım yok.*")
                        else:
                            for t_adi, o_listesi in takimlar.items():
                                with st.expander(f"👕 {t_adi}"):
                                    if not o_listesi:
                                        st.write("*Oyuncu eklenmemiş.*")
                                    else:
                                        for oyuncu in o_listesi:
                                            st.markdown(f"- 👤 {oyuncu}")

# --- SEKME 2: MAÇ PROGRAMI OLUŞTURMA ---
with t2:
    if not st.session_state.giris_yapildi:
        st.warning("🔒 Bu sekme sadece Başhakem içindir.")
    else:
        st.header("Maç Programı Oluşturma")
        if st.session_state.takim_kadrolari:
            m_grup = st.selectbox("Grup Seç:", list(st.session_state.takim_kadrolari.keys()), key="m_grup")
            takimlar = list(st.session_state.takim_kadrolari[m_grup].keys())
            grup_formati = st.session_state.grup_formatlari.get(m_grup, "Tekli Maç Formatı")
            alt_mac_listesi = FORMAT_SECENEKLERI.get(grup_formati, ["Genel"])
            
            if len(takimlar) >= 2:
                c1, c2 = st.columns(2)
                t_1 = c1.selectbox("1. Takım:", takimlar)
                t_2 = c2.selectbox("2. Takım:", [t for t in takimlar if t != t_1])
                tarih = st.text_input("Tarih / Saat (Örn: 10 Mayıs 14:00):")
                kort = st.text_input("Kort (Örn: Kort 1):")
                
                st.info(f"💡 Eşleşme eklendiğinde takım serisi formatı gereği **{len(alt_mac_listesi)} adet alt maç** ({', '.join(alt_mac_listesi)}) otomatik olarak oluşturulacaktır.")
                
                if st.button("➕ Maç Serisini Ekle"):
                    yeni_maclar = []
                    yeni_skorlar = []
                    
                    for alt_mac in alt_mac_listesi:
                        yeni_maclar.append({
                            "Grup": m_grup, "Takım 1": t_1, "Takım 2": t_2, "Alt Maç": alt_mac,
                            "Tarih/Saat": tarih, "Kort": kort
                        })
                        yeni_skorlar.append({
                            "Grup": m_grup, "Takım 1": t_1, "Takım 2": t_2, "Alt Maç": alt_mac,
                            "Skor 1": 0, "Skor 2": 0, "Oynandı": False
                        })
                        
                    st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, pd.DataFrame(yeni_maclar)], ignore_index=True)
                    st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, pd.DataFrame(yeni_skorlar)], ignore_index=True)
                    ortak_veriyi_kaydet()
                    st.success(f"{t_1} - {t_2} serisi programa başarıyla eklendi!")
                    st.rerun()
            else:
                st.info("Eşleşme yapabilmek için bu grupta en az 2 takım olmalı.")
        
        st.divider()
        st.subheader("📅 Mevcut Maç Programı")
        st.dataframe(st.session_state.mac_programi, use_container_width=True)
        
        if not st.session_state.mac_programi.empty:
            st.divider()
            st.markdown("### 🗑️ Programdan Maç Sil")
            maclar_listesi = []
            for idx, row in st.session_state.mac_programi.iterrows():
                maclar_listesi.append(f"{idx}:: {row['Grup']} | {row['Takım 1']} vs {row['Takım 2']} ({row['Alt Maç']})")
                
            secilen_silinecek = st.selectbox("Silinecek alt maçı seçin:", maclar_listesi)
            
            if st.button("🗑️ Seçili Maçı Sil", type="primary"):
                gercek_idx = int(secilen_silinecek.split("::")[0])
                satir = st.session_state.mac_programi.loc[gercek_idx]
                g_adi, t1_adi, t2_adi, alt_adi = satir["Grup"], satir["Takım 1"], satir["Takım 2"], satir["Alt Maç"]
                
                st.session_state.mac_programi = st.session_state.mac_programi.drop(gercek_idx).reset_index(drop=True)
                
                skor_sil_idx = st.session_state.skor_tablosu[
                    (st.session_state.skor_tablosu['Grup'] == g_adi) & 
                    (st.session_state.skor_tablosu['Takım 1'] == t1_adi) & 
                    (st.session_state.skor_tablosu['Takım 2'] == t2_adi) &
                    (st.session_state.skor_tablosu['Alt Maç'] == alt_adi)
                ].index
                
                if not skor_sil_idx.empty:
                    st.session_state.skor_tablosu = st.session_state.skor_tablosu.drop(skor_sil_idx[0]).reset_index(drop=True)

                ortak_veriyi_kaydet()
                st.success("Seçtiğiniz maç programdan ve skor listesinden başarıyla silindi!")
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
                lambda x: f"{x['Grup']} | {x['Takım 1']} vs {x['Takım 2']} ({x['Alt Maç']})", axis=1
            ).tolist()
            secilen_mac_str = st.selectbox("Skoru Girilecek Maçı Seçin:", mac_secim_listesi)
            secilen_idx = mac_secim_listesi.index(secilen_mac_str)
            gercek_idx = oynanmamis_maclar.index[secilen_idx]
            
            satir = oynanmamis_maclar.iloc[secilen_idx]
            c1, c2 = st.columns(2)
            s1 = c1.number_input(f"{satir['Takım 1']} Skoru (Set/Oyun):", min_value=0, step=1)
            s2 = c2.number_input(f"{satir['Takım 2']} Skoru (Set/Oyun):", min_value=0, step=1)
            
            if st.button("💾 Skoru Kaydet ve Oynandı Olarak İşaretle"):
                st.session_state.skor_tablosu.at[gercek_idx, "Skor 1"] = s1
                st.session_state.skor_tablosu.at[gercek_idx, "Skor 2"] = s2
                st.session_state.skor_tablosu.at[gercek_idx, "Oynandı"] = True
                ortak_veriyi_kaydet()
                st.success("Skor başarıyla kaydedildi!")
                st.rerun()
        else:
            st.info("Skoru girilecek bekleyen alt maç bulunmuyor.")

# --- SEKME 4: MİSAFİR MODU (KİLİTLİ TABLOLAR) ---
with t4:
    st.header("🏆 Turnuva Görünümü (Misafir Modu)")
    
    st.subheader("📊 Puan Durumu (Seri Usulü)")
    for g in st.session_state.takim_kadrolari.keys():
        grup_maclari = st.session_state.skor_tablosu[(st.session_state.skor_tablosu["Grup"] == g) & (st.session_state.skor_tablosu["Oynandı"] == True)]
        
        puan_tablosu = {t: {"O": 0, "G": 0, "M": 0, "Alt Maç Av.": 0, "Puan": 0} for t in st.session_state.takim_kadrolari[g].keys()}
        
        seriler = {}
        for _, mac in grup_maclari.iterrows():
            t1, t2 = mac["Takım 1"], mac["Takım 2"]
            s1, s2 = mac["Skor 1"], mac["Skor 2"]
            
            if t1 < t2:
                key, tA, tB, skorA, skorB = f"{t1}-{t2}", t1, t2, s1, s2
            else:
                key, tA, tB, skorA, skorB = f"{t2}-{t1}", t2, t1, s2, s1
                
            if key not in seriler:
                seriler[key] = {"TeamA": tA, "TeamB": tB, "A_Wins": 0, "B_Wins": 0}
                
            if skorA > skorB: seriler[key]["A_Wins"] += 1
            elif skorB > skorA: seriler[key]["B_Wins"] += 1

        for key, data in seriler.items():
            tA, tB = data["TeamA"], data["TeamB"]
            a_w, b_w = data["A_Wins"], data["B_Wins"]
            
            if tA in puan_tablosu: puan_tablosu[tA]["Alt Maç Av."] += (a_w - b_w)
            if tB in puan_tablosu: puan_tablosu[tB]["Alt Maç Av."] += (b_w - a_w)
            
            if a_w > b_w:
                if tA in puan_tablosu:
                    puan_tablosu[tA]["O"] += 1; puan_tablosu[tA]["G"] += 1; puan_tablosu[tA]["Puan"] += 2
                if tB in puan_tablosu:
                    puan_tablosu[tB]["O"] += 1; puan_tablosu[tB]["M"] += 1; puan_tablosu[tB]["Puan"] += 1
            elif b_w > a_w:
                if tB in puan_tablosu:
                    puan_tablosu[tB]["O"] += 1; puan_tablosu[tB]["G"] += 1; puan_tablosu[tB]["Puan"] += 2
                if tA in puan_tablosu:
                    puan_tablosu[tA]["O"] += 1; puan_tablosu[tA]["M"] += 1; puan_tablosu[tA]["Puan"] += 1
            else:
                if tA in puan_tablosu:
                    puan_tablosu[tA]["O"] += 1; puan_tablosu[tA]["Puan"] += 1
                if tB in puan_tablosu:
                    puan_tablosu[tB]["O"] += 1; puan_tablosu[tB]["Puan"] += 1
        
        df_puan = pd.DataFrame.from_dict(puan_tablosu, orient="index").reset_index()
        df_puan.rename(columns={"index": "Takım"}, inplace=True)
        df_puan = df_puan.sort_values(by=["Puan", "G", "Alt Maç Av."], ascending=False).reset_index(drop=True)
        
        st.markdown(f"#### {g}")
        st.markdown(df_puan.to_html(index=False, classes="custom-table"), unsafe_allow_html=True)

    st.divider()
    st.subheader("📅 Maç Programı ve Alınan Skorlar")
    if not st.session_state.mac_programi.empty:
        gorunum_df = st.session_state.mac_programi.copy()
        
        def takim_ve_oyunculari_getir(grup, takim):
            oyun_listesi = st.session_state.takim_kadrolari.get(grup, {}).get(takim, [])
            if oyun_listesi:
                oyuncular_str = "<br>".join(oyun_listesi)
                return f"<b>{takim}</b><br><span style='font-size:0.85em; color:gray;'>{oyuncular_str}</span>"
            return f"<b>{takim}</b>"

        gorunum_df["Takım 1"] = gorunum_df.apply(lambda x: takim_ve_oyunculari_getir(x["Grup"], x["Takım 1"]), axis=1)
        gorunum_df["Takım 2"] = gorunum_df.apply(lambda x: takim_ve_oyunculari_getir(x["Grup"], x["Takım 2"]), axis=1)
        
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
                if yeni_grup_adi != sec_g:
                    st.session_state.skor_tablosu.loc[st.session_state.skor_tablosu['Grup'] == sec_g, 'Grup'] = yeni_grup_adi
                    st.session_state.mac_programi.loc[st.session_state.mac_programi['Grup'] == sec_g, 'Grup'] = yeni_grup_adi
                    
                    st.session_state.takim_kadrolari[yeni_grup_adi] = st.session_state.takim_kadrolari.pop(sec_g)
                    if sec_g in st.session_state.grup_formatlari:
                        st.session_state.grup_formatlari[yeni_grup_adi] = st.session_state.grup_formatlari.pop(sec_g)
                    sec_g = yeni_grup_adi 
                
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
        st.markdown("### 💾 Yedekleme, Geri Yükleme ve Sıfırlama")
        
        c_yedek, c_yukle, c_sil = st.columns(3)
        
        with c_yedek:
            st.markdown("#### 📥 Dışa Aktar")
            if os.path.exists(VERI_DOSYASI):
                with open(VERI_DOSYASI, "rb") as f:
                    st.download_button(
                        label="💾 Turnuva Verisini İndir", 
                        data=f, 
                        file_name=f"turnuva_yedek_{datetime.date.today().strftime('%Y%m%d')}.json", 
                        mime="application/json"
                    )
            else:
                st.info("Henüz yedeklenecek veri yok.")
                
        with c_yukle:
            st.markdown("#### 📤 İçe Aktar (Geri Yükle)")
            yuklenen_dosya = st.file_uploader("Yedek JSON Dosyası Seç:", type=['json'], label_visibility="collapsed")
            if yuklenen_dosya is not None:
                if st.button("📂 Yükle ve Uygula"):
                    try:
                        data = json.load(yuklenen_dosya)
                        
                        if "skor_tablosu" in data:
                            df_skor = pd.DataFrame(data["skor_tablosu"])
                            st.session_state.skor_tablosu = tablo_eksiklerini_tamamla(df_skor, "skor")
                            
                        if "mac_programi" in data:
                            df_mac = pd.DataFrame(data["mac_programi"])
                            st.session_state.mac_programi = tablo_eksiklerini_tamamla(df_mac, "mac")
                            
                        if "takim_kadrolari" in data:
                            st.session_state.takim_kadrolari = data["takim_kadrolari"]
                            
                        if "grup_formatlari" in data:
                            st.session_state.grup_formatlari = data["grup_formatlari"]
                        else:
                            st.session_state.grup_formatlari = {g: "Tekli Maç Formatı" for g in st.session_state.takim_kadrolari.keys()}
                            
                        ortak_veriyi_kaydet()
                        st.success("Veriler başarıyla geri yüklendi ve eksik kolonlar onarıldı!")
                        st.rerun()
                    except Exception as e:
                        st.error("Dosya yüklenirken hata oluştu. Geçerli bir JSON dosyası olduğundan emin olun.")
                        
        with c_sil:
            st.markdown("#### 🚨 Sistemi Sıfırla")
            onayi_ver = st.checkbox("Turnuvayı sıfırlamayı onaylıyorum.")
            if st.button("🗑️ Tüm Sistemi Sıfırla", type="primary", disabled=not onayi_ver):
                st.session_state.clear()
                if os.path.exists(VERI_DOSYASI):
                    os.remove(VERI_DOSYASI)
                st.rerun()
