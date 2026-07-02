import streamlit as st
import pandas as pd
import json
import os
import datetime

# --- GENEL SAYFA AYARLARI ---
st.set_page_config(page_title="Tenis Turnuva Otomasyonu", page_icon="🎾", layout="wide")
st.title("🎾 Profesyonel Tenis Turnuva Yönetim Sistemi")

VERI_DOSYASI = "turnuva_veri.json"

# ==============================================================================
# SİSTEM FONKSİYONLARI (ORTAK VERİ YAZMA VE OKUMA MOTORU)
# ==============================================================================
def ortak_veriyi_kaydet():
    """Tüm güncel tabloları tek bir JSON dosyasında kalıcı hale getirir."""
    data = {
        "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
        "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
        "takim_kadrolari": st.session_state.takim_kadrolari
    }
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def ortak_veriyi_yukle():
    """JSON dosyasından tüm turnuva geçmişini ve ayarlarını güvenle çeker."""
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.session_state.skor_tablosu = pd.DataFrame(data["skor_tablosu"])
            
            mp_df = pd.DataFrame(data["mac_programi"])
            if "T1 Oyuncu" not in mp_df.columns:
                mp_df["T1 Oyuncu"] = ""
                mp_df["T2 Oyuncu"] = ""
            st.session_state.mac_programi = mp_df
            st.session_state.takim_kadrolari = data["takim_kadrolari"]
        except Exception:
            pass 

# ==============================================================================
# HAFIZA (SESSION STATE) BAŞLATMA
# ==============================================================================
if "admin_mi" not in st.session_state:
    st.session_state.admin_mi = False

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
            "Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Canlı Skor"
        ])
        st.session_state.takim_kadrolari = {} 

if 'mac_programi' in st.session_state and "T1 Oyuncu" not in st.session_state.mac_programi.columns:
    st.session_state.mac_programi["T1 Oyuncu"] = ""
    st.session_state.mac_programi["T2 Oyuncu"] = ""

# ==============================================================================
# 👨‍⚖️ BAŞHAKEM YÖNETİM GİRİŞİ (SOL SIDEBAR)
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
    
    if is_set3 and (t1 >= 10 or t2 >= 10):
        if max_s == 10 and min_s <= 8: return True, ""
        elif max_s > 10 and diff == 2: return True, ""
        else: return False, "3. Set Süper Tie-Break kurallarına uymuyor!"
            
    if max_s < 6: return False, "Set en az 6 oyun olmalıdır."
    if max_s == 6 and diff >= 2: return True, ""
    if max_s == 7 and (diff == 2 or diff == 1): return True, ""
    return False, "Geçersiz set skoru (Örn: 6-5 olamaz, uzamalıdır)."

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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 1. Grup Ayarları", "✍️ 2. Skor Girişi", "🏆 3. Puan Durumu", "📅 4. Maç Programı", "⚙️ 5. Yönetim & Dosya"])

# --- TAB 1: GRUP AYARLARI ---
with tab1:
    st.subheader("Turnuva Grupları ve Kadrolar")
    if st.session_state.admin_mi:
        grup_tipi = st.radio("Grup Tipi:", ["4'lü Grup", "5'li Grup"], horizontal=True)
        grup_adi = st.text_input("Grup Adı:", placeholder="Örn: 65+ Erkekler A Grubu")
        beklenen_sayi = 4 if grup_tipi == "4'lü Grup" else 5
        takim_listesi = st.text_area(f"Takım İsimlerini Satır Satır Yazın (Tam olarak {beklenen_sayi} Takım):")
        takimlar = [t.strip() for t in takim_listesi.split('\n') if t.strip()]
        
        grup_kadrolari = {}
        kadro_hata = False
        if len(takimlar) == beklenen_sayi:
            st.markdown("### 👥 Oyuncu Kadroları (Her Satıra Bir Oyuncu, En Fazla 10)")
            cols = st.columns(beklenen_sayi)
            for i, t in enumerate(takimlar):
                with cols[i]:
                    oyuncular_raw = st.text_area(f"✍️ {t} Kadrosu", key=f"input_kadro_{t}", height=150)
                    oyuncu_listesi = [o.strip() for o in oyuncular_raw.split('\n') if o.strip()]
                    if len(oyuncu_listesi) > 10:
                        st.error("Maksimum 10 oyuncu sınırı aşıldı!")
                        kadro_hata = True
                    grup_kadrolari[t] = oyuncu_listesi if oyuncu_listesi else ["Belirtilmedi"]

        if st.button("🚀 Grubu ve Fikstürü Oluştur"):
            if not grup_adi or len(takimlar) != beklenen_sayi or kadro_hata:
                st.error("Lütfen tüm parametreleri eksiksiz ve kurallara uygun doldurun.")
            else:
                st.session_state.takim_kadrolari[grup_adi] = grup_kadrolari
                if not st.session_state.skor_tablosu.empty and grup_adi in st.session_state.skor_tablosu['Grup'].unique():
                    ortak_veriyi_kaydet()
                    st.success("Mevcut grup kadroları güncellendi, fikstür korundu.")
                else:
                    yeni_df = pd.DataFrame(eslesmeleri_olustur(grup_adi, takimlar, grup_tipi))
                    st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
                    ortak_veriyi_kaydet()
                    st.success("Grup ve fikstür başarıyla oluşturuldu!")
                st.rerun()
    else:
        st.info("ℹ️ Kadro ve grup tanımlama işlemleri sadece Başhakem yetkisindedir.")
        if st.session_state.takim_kadrolari: st.json(st.session_state.takim_kadrolari)

# --- TAB 2: SKOR GİRİŞİ ---
with tab2:
    st.subheader("Maç Skorları ve Oyuncu Seçim Girişleri")
    if st.session_state.admin_mi:
        if not st.session_state.skor_tablosu.empty:
            gruplar = st.session_state.skor_tablosu['Grup'].unique()
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
                
                # Sabit "Seçiniz" mantığı ile Tekler/Çiftler ayrımı (T1)
                if row['Branş'] == "Çiftler":
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
                
                # Sabit "Seçiniz" mantığı ile Tekler/Çiftler ayrımı (T2)
                if row['Branş'] == "Çiftler":
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
        seriler['T1_Win'] = (seriler['T1_Match_Win'] >= 2).astype(int)
        seriler['T2_Win'] = (seriler['T2_Match_Win'] >= 2).astype(int)
        
        t1 = seriler[['Grup', 'Takım 1', 'T1_Win', 'T1_Match_Win', 'T2_Match_Win', 'T1_Set_Skor', 'T2_Set_Skor', 'T1_Oyun', 'T2_Oyun']]
        t1.columns = ['Grup', 'Takım', 'Galibiyet', 'Aldığı Maç', 'Verdiği Maç', 'Aldığı Set', 'Verdiği Set', 'Aldığı Oyun', 'Verdiği Oyun']
        t2 = seriler[['Grup', 'Takım 2', 'T2_Win', 'T2_Match_Win', 'T1_Match_Win', 'T2_Set_Skor', 'T1_Set_Skor', 'T2_Oyun', 'T1_Oyun']]
        t2.columns = ['Grup', 'Takım', 'Galibiyet', 'Aldığı Maç', 'Verdiği Maç', 'Aldığı Set', 'Verdiği Set', 'Aldığı Oyun', 'Verdiği Oyun']
        
        tum_stats = pd.concat([t1, t2]).groupby(['Grup', 'Takım']).sum().reset_index()
        tum_stats['Maç Av.'] = tum_stats['Aldığı Maç'] - tum_stats['Verdiği Maç']
        tum_stats['Set Av.'] = tum_stats['Aldığı Set'] - tum_stats['Verdiği Set']
        tum_stats['Oyun Av.'] = tum_stats['Aldığı Oyun'] - tum_stats['Verdiği Oyun']
        
        for gp in tum_stats['Grup'].unique():
            st.markdown(f"### 🏆 {gp} Puan Durumu")
            grup_df = tum_stats[tum_stats['Grup'] == gp].drop(columns=['Grup']).sort_values(by=['Galibiyet', 'Maç Av.', 'Oyun Av.'], ascending=False)
            grup_df.index = range(1, len(grup_df) + 1)
            st.dataframe(grup_df, use_container_width=True)

# --- TAB 4: MAÇ PROGRAMI (HTML HATASI KESİNLİKLE ÇÖZÜLDÜ) ---
with tab4:
    st.subheader("📅 Canlı Maç Programı ve Fikstür")
    if not st.session_state.skor_tablosu.empty:
        turkce_gunler = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
        secilen_tarih = st.date_input("🗓️ Program Yapılacak / Görüntülenecek Tarih:", value=datetime.date.today())
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

                if int(m['1.Set T1']) != 0 or int(m['1.Set T2']) != 0:
                    skor_str = f"{int(m['1.Set T1'])}-{int(m['1.Set T2'])} | {int(m['2.Set T1'])}-{int(m['2.Set T2'])}"
                    if int(m['3.Set T1']) != 0 or int(m['3.Set T2']) != 0:
                        skor_str += f" | TB: {int(m['3.Set T1'])}-{int(m['3.Set T2'])}"
                    st.session_state.mac_programi.at[idx, "Canlı Skor"] = skor_str
                else:
                    st.session_state.mac_programi.at[idx, "Canlı Skor"] = "Oynanmadı"

        df_gunluk = st.session_state.mac_programi[st.session_state.mac_programi['Tarih'] == formatted_tarih].copy()

        # --- YÖNETİCİ MODU ---
        if st.session_state.admin_mi:
            st.markdown(f"### ➕ {formatted_tarih} Tarihine Maç Ekle")
            c1, c2, c3 = st.columns(3)
            gruplar_prog = st.session_state.skor_tablosu['Grup'].unique()
            sec_grup_prog = c1.selectbox("Grup Seç:", gruplar_prog, key="prog_grup")
            df_g_prog = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == sec_grup_prog]
            gunler_prog = sorted(df_g_prog['Gün'].unique(), key=lambda x: int(x.split('.')[0]) if '.' in x else 99)
            sec_gun_prog = c2.selectbox("Gün Seç:", gunler_prog, key="prog_gun")
            df_m_prog = df_g_prog[df_g_prog['Gün'] == sec_gun_prog]
            
            mevcut_mask = df_m_prog.apply(lambda r: not st.session_state.mac_programi[
                (st.session_state.mac_programi['Tarih'] == formatted_tarih) &
                (st.session_state.mac_programi['Grup'] == r['Grup']) &
                (st.session_state.mac_programi['Gün'] == r['Gün']) &
                (st.session_state.mac_programi['Branş'] == r['Branş']) &
                (st.session_state.mac_programi['Eşleşme'] == r['Eşleşme'])
            ].empty, axis=1)
            df_m_prog_eklenebilir = df_m_prog[~mevcut_mask]
            
            if df_m_prog_eklenebilir.empty:
                c3.info("✅ Fikstürdeki maçlar eklenmiş.")
            else:
                mac_listesi = [f"{row['Takım 1']} vs {row['Takım 2']} ({row['Branş']})" for idx, row in df_m_prog_eklenebilir.iterrows()]
                sec_mac_adi = c3.selectbox("Maç Seç:", mac_listesi, key="prog_mac")
                if st.button("➕ Akışa Ekle"):
                    secilen_row = df_m_prog_eklenebilir.iloc[mac_listesi.index(sec_mac_adi)]
                    yeni_kayit = pd.DataFrame([{
                        "Maç Saati": "10:00", "Tarih": formatted_tarih, "Gün Adı": gun_adi, "Kort": "Kort 1",
                        "Grup": secilen_row['Grup'], "Gün": secilen_row['Gün'], "Branş": secilen_row['Branş'], "Eşleşme": secilen_row['Eşleşme'],
                        "Takım 1": secilen_row['Takım 1'], "Takım 2": secilen_row['Takım 2'], "T1 Oyuncu": "", "T2 Oyuncu": "", "Canlı Skor": "Oynanmadı"
                    }])
                    st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, yeni_kayit], ignore_index=True)
                    ortak_veriyi_kaydet()
                    st.success("Maç eklendi!")
                    st.rerun()

            if not df_gunluk.empty:
                st.markdown("### 📋 Günlük Akış Editörü")
                guncel_program = st.data_editor(
                    df_gunluk, use_container_width=True, num_rows="dynamic",
                    disabled=["Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Canlı Skor"],
                    key=f"program_editor_{formatted_tarih}"
                )
                if st.button("💾 Değişiklikleri Kaydet"):
                    eski_indexler = df_gunluk.index
                    st.session_state.mac_programi.drop(index=eski_indexler, inplace=True)
                    guncel_program['Tarih'] = guncel_program['Tarih'].fillna(formatted_tarih)
                    guncel_program['Gün Adı'] = guncel_program['Gün Adı'].fillna(gun_adi)
                    st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, guncel_program]).reset_index(drop=True)
                    ortak_veriyi_kaydet()
                    st.success("Güncellendi!")
                    st.rerun()

                st.markdown("---")
                silme_havuzu = []
                for idx, row in df_gunluk.iterrows():
                    silme_havuzu.append((idx, f"{row['Maç Saati']} | {row['Kort']} | {row['Takım 1']} vs {row['Takım 2']} ({row['Branş']})"))
                
                secilen_silme_tanimi = st.selectbox("Silmek istediğiniz maçı seçin:", ["Seçiniz..."] + [m[1] for m in silme_havuzu])
                if secilen_silme_tanimi != "Seçiniz...":
                    if st.button("❌ Kaldır"):
                        hedef_idx = [m[0] for m in silme_havuzu if m[1] == secilen_silme_tanimi][0]
                        st.session_state.mac_programi.drop(index=hedef_idx, inplace=True)
                        st.session_state.mac_programi.reset_index(drop=True, inplace=True)
                        ortak_veriyi_kaydet()
                        st.success("Kaldırıldı!")
                        st.rerun()

       # --- MİSAFİR MODU (GÜNCEL & SABİT TASARIM) ---
        else:
            st.markdown(f"### 📋 {formatted_tarih} Tarihli Maç Akışı")
            if df_gunluk.empty:
                st.info("Bu tarihte planlanmış maç bulunmamaktadır.")
            else:
                # CSS'i daha kararlı hale getirdik
                html_css = """
                <style>
                    .ref-table { width: 100%; border-collapse: collapse; font-family: sans-serif; }
                    .ref-table th { background: #334155; color: white; padding: 10px; text-align: left; }
                    .ref-table td { padding: 12px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
                    .team-cell { font-weight: bold; font-size: 1.1rem; }
                    .player-cell { font-style: italic; color: #475569; font-size: 0.9rem; display: block; margin-top: 4px; }
                    .score-cell { font-weight: bold; color: #be123c; }
                    .waiting-cell { color: #059669; font-weight: bold; }
                </style>
                """
                
                html_rows = ""
                for _, row in df_gunluk.iterrows():
                    skor = str(row.get('Canlı Skor', 'Oynanmadı'))
                    skor_html = f"<span class='waiting-cell'>Bekleniyor</span>" if skor in ["Oynanmadı", ""] else f"<span class='score-cell'>{skor}</span>"
                    
                    # Oyuncu isimlerini çek
                    t1_o = str(row.get('T1 Oyuncu', '')).strip()
                    t2_o = str(row.get('T2 Oyuncu', '')).strip()
                    
                    t1_display = f"<div class='team-cell'>{row.get('Takım 1', '')}</div>" + (f"<div class='player-cell'>👤 {t1_o}</div>" if t1_o and t1_o != "nan" else "")
                    t2_display = f"<div class='team-cell'>{row.get('Takım 2', '')}</div>" + (f"<div class='player-cell'>👤 {t2_o}</div>" if t2_o and t2_o != "nan" else "")
                    
                    html_rows += f"<tr><td>{row.get('Maç Saati', '')}</td><td>{row.get('Kort', '')}</td><td>{row.get('Branş', '')}</td><td>{t1_display}</td><td>{t2_display}</td><td>{skor_html}</td></tr>"
                
                st.markdown(html_css + f"<table class='ref-table'><thead><tr><th>Saat</th><th>Kort</th><th>Branş</th><th>Takım 1</th><th>Takım 2</th><th>Skor</th></tr></thead><tbody>{html_rows}</tbody></table>", unsafe_allow_html=True)
    else:
        st.info("Gruplar oluşturulmadan maç programı aktif edilemez.")
# --- TAB 5: YÖNETİM & DOSYA İŞLEMLERİ ---
with tab5:
    st.subheader("⚙️ Gelişmiş Yönetim Paneli")
    if st.session_state.admin_mi:
        with st.expander("✍️ Takım İsimlerini ve Kadroları Revize Et"):
            if not st.session_state.skor_tablosu.empty:
                t_gruplar = st.session_state.skor_tablosu['Grup'].unique()
                sec_g = st.selectbox("Düzenlenecek Grup:", t_gruplar, key="admin_edit_grup")
                m_kadrolar = st.session_state.takim_kadrolari.get(sec_g, {})
                
                yeni_k_yapisi = {}
                isim_degisiklikleri = {}
                for esk_ad, oyuncular in m_kadrolar.items():
                    c_a, c_b = st.columns([1, 2])
                    with c_a:
                        y_ad = st.text_input(f"Takım Adı", value=esk_ad, key=f"ad_{esk_ad}")
                        if y_ad != esk_ad: isim_degisiklikleri[esk_ad] = y_ad
                    with c_b:
                        y_o_text = st.text_area(f"Oyuncular", value="\n".join(oyuncular), key=f"oyuncu_{esk_ad}", height=100)
                        yeni_k_yapisi[y_ad if y_ad else esk_ad] = [o.strip() for o in y_o_text.split('\n') if o.strip()]
                
                if st.button("💾 Yapılan Değişiklikleri Veritabanına Yaz"):
                    st.session_state.takim_kadrolari[sec_g] = yeni_k_yapisi
                    if isim_degisiklikleri:
                        for e_a, y_a in isim_degisiklikleri.items():
                            st.session_state.skor_tablosu.replace({e_a: y_a}, inplace=True)
                            st.session_state.mac_programi.replace({e_a: y_a}, inplace=True)
                    ortak_veriyi_kaydet()
                    st.success("Başarıyla güncellendi!")
                    st.rerun()

        st.markdown("### 💾 Yedekleme Paneli")
        c_sv, c_ld = st.columns(2)
        with c_sv:
            export_data = {
                "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
                "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
                "takim_kadrolari": st.session_state.takim_kadrolari
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
                    ortak_veriyi_kaydet()
                    st.success("Yedek başarıyla yüklendi!")
                    st.rerun()
                except Exception as ex: st.error(f"Hata: {ex}")

        st.markdown("### 🚨 Turnuva Sıfırlama")
        if st.checkbox("🚨 TÜM VERİLERİ KALICI OLARAK SİLMEK İSTİYORUM"):
            if st.button("⚠️ VERİTABANINI TAMAMEN SIFIRLA"):
                st.session_state.skor_tablosu = pd.DataFrame(columns=["Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu", "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"])
                st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Canlı Skor"])
                st.session_state.takim_kadrolari = {}
                ortak_veriyi_kaydet()
                st.rerun()
    else:
        st.warning("🔒 Yönetim sekmesi yetkisiz erişime kapalıdır.")
