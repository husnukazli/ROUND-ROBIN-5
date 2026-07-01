import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Tenis Turnuva Otomasyonu", layout="wide")
st.title("🎾 Profesyonel Tenis Turnuva Yönetim Sistemi (Dosya Destekli)")

# --- 0. HAFIZA BAŞLATMA ---
if 'skor_tablosu' not in st.session_state:
    st.session_state.skor_tablosu = pd.DataFrame(columns=[
        "Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", 
        "T1_Oyuncu", "T2_Oyuncu", 
        "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"
    ])

if 'mac_programi' not in st.session_state:
    st.session_state.mac_programi = pd.DataFrame(columns=[
        "Maç Saati", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor"
    ])

if 'takim_kadrolari' not in st.session_state:
    st.session_state.takim_kadrolari = {} 

# --- TENİS KURALLARI VE DOĞRULAMA MOTORU ---
def set_gecerli_mi(t1, t2, is_set3=False):
    if t1 == 0 and t2 == 0:
        return True, ""
    if t1 < 0 or t2 < 0:
        return False, "Skorlar negatif olamaz."
        
    max_s = max(t1, t2)
    min_s = min(t1, t2)
    diff = max_s - min_s
    
    if is_set3 and (t1 >= 10 or t2 >= 10):
        if max_s == 10 and min_s <= 8:
            return True, ""
        elif max_s > 10 and diff == 2:
            return True, ""
        else:
            return False, "3. Set Süper Tie-Break skoru geçersiz! (En az 10'a ulaşılmalı ve fark 2 olmalıdır)"
            
    if max_s < 6:
        return False, "Set henüz bitmemiş (En az 6 oyun olmalı)."
    if max_s == 6 and diff >= 2:
        return True, ""
    if max_s == 7 and (diff == 2 or diff == 1):
        return True, ""
    if max_s > 7:
        return False, f"Normal set skoru {max_s} olamaz (En fazla 7-5 veya 7-6 olabilir)."
        
    return False, "Geçersiz set skoru (Örn: 6-5 olamaz, setin uzaması gerekir)."

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

# --- SEKMELER ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 1. Grup Ayarları", "✍️ 2. Skor Girişi", "🏆 3. Puan Durumu", "📅 4. Maç Programı", "⚙️ 5. Yönetim & Dosya"])

# --- TAB 1: GRUP AYARLARI ---
with tab1:
    st.subheader("Grup Takımlarını Seç, Kadroları Gir ve Eşleşmeleri Oluştur")
    grup_tipi = st.radio("Kurulacak Grup Tipini Seçin:", ["4'lü Grup", "5'li Grup"], horizontal=True)
    grup_adi = st.text_input("Grup Adı", placeholder="Örn: A Grubu")
    
    beklenen_sayi = 4 if grup_tipi == "4'lü Grup" else 5
    takim_listesi = st.text_area(f"Takım İsimlerini Alt Alta Yazın (Tam olarak {beklenen_sayi} Takım Olmalı)")
    
    # Hizalaması milimetrik olarak düzeltilen 102. satır burasıdır:
    takimlar = [t.strip() for t in takim_listesi.split('\n') if t.strip()]
    
    grup_kadrolari = {}
    kadro_hata = False
    
    if len(takimlar) == beklenen_sayi:
        st.markdown("---")
        st.markdown("### 👥 Oyuncu Kadrolarını Girin (En Fazla 10 Oyuncu, Her Satıra Bir İsim)")
        cols = st.columns(beklenen_sayi)
        for i, t in enumerate(takimlar):
            with cols[i]:
                oyuncular_raw = st.text_area(f"✍️ {t} Kadrosu", key=f"input_kadro_{t}", height=150, placeholder="Oyuncu 1\nOyuncu 2")
                oyuncu_listesi = [o.strip() for o in oyuncular_raw.split('\n') if o.strip()]
                if len(oyuncu_listesi) > 10:
                    st.error(f"❌ {t} takımı 10 oyuncuyu aşamaz! ({len(oyuncu_listesi)} girildi)")
                    kadro_hata = True
                grup_kadrolari[t] = oyuncu_listesi if oyuncu_listesi else ["Belirtilmedi"]

    if st.button("🚀 Eşleşmeleri ve Kadroları Oluştur"):
        if not grup_adi:
            st.error("Lütfen bir grup adı girin.")
        elif not st.session_state.skor_tablosu.empty and grup_adi in st.session_state.skor_tablosu['Grup'].unique():
            st.error(f"❌ Hata: '{grup_adi}' isminde bir grup zaten mevcut!")
        elif len(takimlar) != beklenen_sayi:
            st.error(f"Hata: {beklenen_sayi} takım girmelisiniz. (Şu an: {len(takimlar)})")
        elif kadro_hata:
            st.error("Lütfen 10 oyuncu sınırını aşan takımları düzeltin.")
        else:
            if grup_adi not in st.session_state.takim_kadrolari:
                st.session_state.takim_kadrolari[grup_adi] = grup_kadrolari
            
            yeni_maclar = eslesmeleri_olustur(grup_adi, takimlar, grup_tipi)
            yeni_df = pd.DataFrame(yeni_maclar)
            st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
            st.session_state.skor_tablosu.index = range(1, len(st.session_state.skor_tablosu) + 1)
            st.success(f"{grup_adi} ve oyuncu kadroları başarıyla oluşturuldu!")
            st.rerun()
# --- TAB 2: SKOR GİRİŞİ ---
with tab2:
    st.subheader("Maç Skorları ve Oyuncu Esame Girişi")
    if not st.session_state.skor_tablosu.empty:
        gruplar = st.session_state.skor_tablosu['Grup'].unique()
        secilen_grup = st.selectbox("Düzenlemek İçin Grup Seç:", gruplar, key="skor_grup_sec")
        df_grup = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == secilen_grup].copy()
        
        def gun_sirala(gun_adi):
            try: return int(gun_adi.split('.')[0])
            except: return 99
            
        aktif_gunler = sorted(df_grup['Gün'].unique(), key=gun_sirala)
        secilen_gun = st.selectbox("Gün Seçin:", aktif_gunler)
        df_gun = df_grup[df_grup['Gün'] == secilen_gun]
        
        st.markdown(f"### 🗓️ {secilen_grup} - {secilen_gun} Maçları")
        
        h_cols = st.columns([1.5, 2.0, 1.5, 2.0, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7])
        h_cols[0].markdown("**Takım 1**")
        h_cols[1].markdown("**Takım 1 Oyuncu(lar)**")
        h_cols[2].markdown("**Takım 2**")
        h_cols[3].markdown("**Takım 2 Oyuncu(lar)**")
        h_cols[4].markdown("**S1 T1**")
        h_cols[5].markdown("**S1 T2**")
        h_cols[6].markdown("**S2 T1**")
        h_cols[7].markdown("**S2 T2**")
        h_cols[8].markdown("**S3 T1**")
        h_cols[9].markdown("**S3 T2**")
        
        form_verileri = {}
        
        for idx, row in df_gun.iterrows():
            st.markdown(f"**🔹 {row['Branş']} ({row['Eşleşme']})**")
            r_cols = st.columns([1.5, 2.0, 1.5, 2.0, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7])
            
            t1_isim = row['Takım 1']
            t2_isim = row['Takım 2']
            
            grup_kadro_dict = st.session_state.takim_kadrolari.get(secilen_grup, {})
            t1_havuz = grup_kadro_dict.get(t1_isim, ["Belirtilmedi"])
            t2_havuz = grup_kadro_dict.get(t2_isim, ["Belirtilmedi"])
            
            r_cols[0].write(f"**{t1_isim}**")
            
            if row['Branş'] == "Çiftler":
                eski_oyuncular = [o.strip() for o in str(row['T1_Oyuncu']).split(',') if o.strip() and o in t1_havuz]
                t1_oyuncu = r_cols[1].multiselect("T1 Oyuncular", options=t1_havuz, default=eski_oyuncular, max_selections=2, key=f"t1_o_{idx}", label_visibility="collapsed")
                t1_oyuncu_str = ", ".join(t1_oyuncu)
            else:
                eski_oyuncu = str(row['T1_Oyuncu']) if str(row['T1_Oyuncu']) in t1_havuz else t1_havuz[0]
                idx_default = t1_havuz.index(eski_oyuncu) if eski_oyuncu in t1_havuz else 0
                t1_oyuncu_str = r_cols[1].selectbox("T1 Oyuncu", options=t1_havuz, index=idx_default, key=f"t1_o_{idx}", label_visibility="collapsed")
            
            r_cols[2].write(f"**{t2_isim}**")
            
            if row['Branş'] == "Çiftler":
                eski_oyuncular2 = [o.strip() for o in str(row['T2_Oyuncu']).split(',') if o.strip() and o in t2_havuz]
                t2_oyuncu = r_cols[3].multiselect("T2 Oyuncular", options=t2_havuz, default=eski_oyuncular2, max_selections=2, key=f"t2_o_{idx}", label_visibility="collapsed")
                t2_oyuncu_str = ", ".join(t2_oyuncu)
            else:
                eski_oyuncu2 = str(row['T2_Oyuncu']) if str(row['T2_Oyuncu']) in t2_havuz else t2_havuz[0]
                idx_default2 = t2_havuz.index(eski_oyuncu2) if eski_oyuncu2 in t2_havuz else 0
                t2_oyuncu_str = r_cols[3].selectbox("T2 Oyuncu", options=t2_havuz, index=idx_default2, key=f"t2_o_{idx}", label_visibility="collapsed")
            
            s1t1 = r_cols[4].number_input("S1T1", min_value=0, value=int(row['1.Set T1']), step=1, key=f"s1t1_{idx}", label_visibility="collapsed")
            s1t2 = r_cols[5].number_input("S1T2", min_value=0, value=int(row['1.Set T2']), step=1, key=f"s1t2_{idx}", label_visibility="collapsed")
            s2t1 = r_cols[6].number_input("S2T1", min_value=0, value=int(row['2.Set T1']), step=1, key=f"s2t1_{idx}", label_visibility="collapsed")
            s2t2 = r_cols[7].number_input("S2T2", min_value=0, value=int(row['2.Set T2']), step=1, key=f"s2t2_{idx}", label_visibility="collapsed")
            s3t1 = r_cols[8].number_input("S3T1", min_value=0, value=int(row['3.Set T1']), step=1, key=f"s3t1_{idx}", label_visibility="collapsed")
            s3t2 = r_cols[9].number_input("S3T2", min_value=0, value=int(row['3.Set T2']), step=1, key=f"s3t2_{idx}", label_visibility="collapsed")
            
            form_verileri[idx] = {
                "T1_Oyuncu": t1_oyuncu_str, "T2_Oyuncu": t2_oyuncu_str,
                "1.Set T1": s1t1, "1.Set T2": s1t2,
                "2.Set T1": s2t1, "2.Set T2": s2t2,
                "3.Set T1": s3t1, "3.Set T2": s3t2
            }
            st.divider()

        if st.button("✅ Tüm Skorları ve Kadroları Kaydet"):
            hata_mesajlari = []
            uzerine_yazilanlar = []
            
            for idx, guncel_row in form_verileri.items():
                eski_row = st.session_state.skor_tablosu.loc[idx]
                mac_tanimi = f"{eski_row['Gün']} - {eski_row['Branş']} ({eski_row['Takım 1']} vs {eski_row['Takım 2']})"
                
                ok1, msg1 = set_gecerli_mi(guncel_row["1.Set T1"], guncel_row["1.Set T2"], is_set3=False)
                ok2, msg2 = set_gecerli_mi(guncel_row["2.Set T1"], guncel_row["2.Set T2"], is_set3=False)
                ok3, msg3 = set_gecerli_mi(guncel_row["3.Set T1"], guncel_row["3.Set T2"], is_set3=True)
                
                if not ok1: hata_mesajlari.append(f"❌ {mac_tanimi} -> 1. Set: {msg1}")
                if not ok2: hata_mesajlari.append(f"❌ {mac_tanimi} -> 2. Set: {msg2}")
                if not ok3: hata_mesajlari.append(f"❌ {mac_tanimi} -> 3. Set: {msg3}")
                
                eski_dolu = (eski_row['1.Set T1'] != 0 or eski_row['1.Set T2'] != 0)
                yeni_farkli = (eski_row['1.Set T1'] != guncel_row['1.Set T1'] or eski_row['1.Set T2'] != guncel_row['1.Set T2'])
                if eski_dolu and yeni_farkli:
                    uzerine_yazilanlar.append(mac_tanimi)
            
            if hata_mesajlari:
                for h in hata_mesajlari: st.error(h)
                st.error("Kayıt bloke edildi. Lütfen hatalı skorları düzeltin.")
            else:
                if uzerine_yazilanlar:
                    st.warning("⚠️ Güncelleme: Şu maçların skorları yenilendi:\n" + "\n".join([f"- {m}" for m in uzerine_yazilanlar]))
                for idx, guncel_row in form_verileri.items():
                    for k, v in guncel_row.items():
                        st.session_state.skor_tablosu.at[idx, k] = v
                st.success("Tüm oyuncu listeleri ve skorlar başarıyla kaydedildi!")
                st.rerun()
    else:
        st.info("Henüz grup oluşturmadınız.")

# --- TAB 3: PUAN DURUMU ---
with tab3:
    st.subheader("Otomatik Puan Durumu")
    if not st.session_state.skor_tablosu.empty:
        df = st.session_state.skor_tablosu.copy()
        
        def satir_istatistiklerini_hesapla(row):
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
                    if s3_t1 > s3_t2:
                        t1_set += 1
                        t1_oyun += 1
                    else:
                        t2_set += 1
                        t2_oyun += 1
                else:
                    t1_set += int(s3_t1 > s3_t2)
                    t2_set += int(s3_t2 > s3_t1)
                    t1_oyun += s3_t1
                    t2_oyun += s3_t2
            return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])

        df[['T1_Oyun', 'T2_Oyun', 'T1_Set_Skor', 'T2_Set_Skor']] = df.apply(satir_istatistiklerini_hesapla, axis=1)
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
        
        for grup in tum_stats['Grup'].unique():
            st.markdown(f"### 🏆 {grup} Puan Durumu")
            grup_df = tum_stats[tum_stats['Grup'] == grup].drop(columns=['Grup']).sort_values(by=['Galibiyet', 'Maç Av.', 'Oyun Av.'], ascending=False)
            grup_df.index = range(1, len(grup_df) + 1)
            st.dataframe(grup_df, use_container_width=True)

# --- TAB 4: MAÇ PROGRAMI (GELİŞMİŞ VE CANLI) ---
with tab4:
    st.subheader("📅 Canlı Maç Programı Oluşturucu")
    if not st.session_state.skor_tablosu.empty:
        c1, c2, c3 = st.columns(3)
        gruplar_prog = st.session_state.skor_tablosu['Grup'].unique()
        sec_grup_prog = c1.selectbox("Grup Seç:", gruplar_prog, key="prog_grup")
        df_g_prog = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == sec_grup_prog]
        
        gunler_prog = sorted(df_g_prog['Gün'].unique(), key=lambda x: int(x.split('.')[0]) if '.' in x else 99)
        sec_gun_prog = c2.selectbox("Gün Seç:", gunler_prog, key="prog_gun")
        df_m_prog = df_g_prog[df_g_prog['Gün'] == sec_gun_prog]
        
        mac_listesi = [f"{row['Takım 1']} vs {row['Takım 2']} ({row['Branş']})" for idx, row in df_m_prog.iterrows()]
        sec_mac_adi = c3.selectbox("Maç Seç:", mac_listesi, key="prog_mac")
        
        if st.button("➕ Günlük Programa Ekle"):
            secilen_row = df_m_prog.iloc[mac_listesi.index(sec_mac_adi)]
            yeni_kayit = pd.DataFrame([{
                "Maç Saati": "10:00",
                "Kort": "Kort 1",
                "Grup": secilen_row['Grup'],
                "Gün": secilen_row['Gün'],
                "Branş": secilen_row['Branş'],
                "Eşleşme": secilen_row['Eşleşme'],
                "Takım 1": secilen_row['Takım 1'],
                "Takım 2": secilen_row['Takım 2'],
                "Canlı Skor": "Oynanmadı"
            }])
            st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, yeni_kayit], ignore_index=True)
            st.success("Maç programa eklendi! Saat ve Kort bilgisini tablodan güncelleyebilirsiniz.")
            st.rerun()
            
        st.divider()
        
        if not st.session_state.mac_programi.empty:
            st.markdown("### 📋 Güncel Maç Akışı (Skorlar Canlı Güncellenir)")
            
            # CANLI SKORLARI ARKA PLANDAN ÇEKME
            for idx, row in st.session_state.mac_programi.iterrows():
                eslesen_mac = st.session_state.skor_tablosu[
                    (st.session_state.skor_tablosu['Grup'] == row['Grup']) &
                    (st.session_state.skor_tablosu['Gün'] == row['Gün']) &
                    (st.session_state.skor_tablosu['Branş'] == row['Branş']) &
                    (st.session_state.skor_tablosu['Eşleşme'] == row['Eşleşme'])
                ]
                if not eslesen_mac.empty:
                    m = eslesen_mac.iloc[0]
                    if int(m['1.Set T1']) != 0 or int(m['1.Set T2']) != 0:
                        skor_str = f"{int(m['1.Set T1'])}-{int(m['1.Set T2'])} | {int(m['2.Set T1'])}-{int(m['2.Set T2'])}"
                        if int(m['3.Set T1']) != 0 or int(m['3.Set T2']) != 0:
                            skor_str += f" | TB: {int(m['3.Set T1'])}-{int(m['3.Set T2'])}"
                        
                        # Oyuncu isimlerini de yanına iliştirelim
                        t1_o = f" [{m['T1_Oyuncu']}]" if m['T1_Oyuncu'] else ""
                        t2_o = f" [{m['T2_Oyuncu']}]" if m['T2_Oyuncu'] else ""
                        st.session_state.mac_programi.at[idx, "Canlı Skor"] = skor_str
                    else:
                        st.session_state.mac_programi.at[idx, "Canlı Skor"] = "Oynanmadı"
            
            guncel_program = st.data_editor(
                st.session_state.mac_programi, 
                use_container_width=True, 
                num_rows="dynamic",
                disabled=["Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor"],
                key="program_editor_v2"
            )
            if st.button("💾 Saat ve Kort Değişikliklerini Kaydet"):
                st.session_state.mac_programi = guncel_program
                st.success("Maç saatleri ve kortlar güncellendi!")
                st.rerun()
    else:
        st.info("Henüz grup oluşturulmadığı için program yapılamaz.")

# --- TAB 5: YÖNETİM & DOSYA İŞLEMLERİ ---
with tab5:
    st.subheader("⚙️ Yönetim Paneli & Turnuva Yedekleme")
    
    # 💾 DOSYA KAYDETME VE YÜKLEME ALANI
    st.markdown("### 💾 Turnuva Veri Yönetimi (Dosya Kaydet / Yükle)")
    c_save, c_load = st.columns(2)
    
    with c_save:
        st.write("📋 **Mevcut Durumu Bilgisayara Yedekle**")
        export_data = {
            "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
            "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
            "takim_kadrolari": st.session_state.takim_kadrolari
        }
        json_str = json.dumps(export_data, ensure_ascii=False, indent=4)
        st.download_button(
            label="📥 Turnuvayı Dosya Olarak İndir (.json)",
            data=json_str,
            file_name="tenis_turnuva_yedek.json",
            mime="application/json"
        )
        st.caption("Bu butona basarak turnuvanın o anki tüm bilgilerini yedek bir dosya olarak bilgisayarınıza indirebilirsiniz.")

    with c_load:
        st.write("📤 **Kaydedilmiş Turnuvayı Geri Yükle**")
        uploaded_file = st.file_uploader("Yedek Dosyasını Seçin (.json)", type=["json"])
        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                st.session_state.skor_tablosu = pd.DataFrame(data["skor_tablosu"])
                st.session_state.mac_programi = pd.DataFrame(data["mac_programi"])
                st.session_state.takim_kadrolari = data["takim_kadrolari"]
                st.success("✅ Turnuva verileri başarıyla yüklendi! Tüm sekmeler güncellendi.")
                st.rerun()
            except Exception as e:
                st.error(f"Dosya yüklenirken bir hata oluştu: {e}")
                
    st.markdown("---")
    st.markdown("### 🚨 Tehlikeli Bölge")
    if not st.session_state.skor_tablosu.empty:
        gruplar = st.session_state.skor_tablosu['Grup'].unique()
        silinecek_grup = st.selectbox("Silinecek Grup:", gruplar)
        if st.button("❌ Bu Grubu ve Kadrolarını Tamamen Sil"):
            st.session_state.skor_tablosu = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] != silinecek_grup]
            if silinecek_grup in st.session_state.takim_kadrolari:
                del st.session_state.takim_kadrolari[silinecek_grup]
            st.session_state.skor_tablosu.index = range(1, len(st.session_state.skor_tablosu) + 1)
            st.rerun()
            
    if st.button("🚨 TÜM SİSTEMİ SIFIRLA (HER ŞEY SİLİNİR)"):
        st.session_state.skor_tablosu = pd.DataFrame(columns=[
            "Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu",
            "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"
        ])
        st.session_state.mac_programi = pd.DataFrame(columns=[
            "Maç Saati", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor"
        ])
        st.session_state.takim_kadrolari = {}
        st.rerun()
