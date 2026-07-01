import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Tenis Turnuva Otomasyonu", layout="wide")
st.title("🎾 Profesyonel Tenis Turnuva Yönetim Sistemi")

# --- TENİS KURALLARI VE DOĞRULAMA MOTORU ---
def set_gecerli_mi(t1, t2, is_set3=False):
    # Eğer her iki skor da 0 ise henüz maç oynanmamıştır, geçerli kabul edilir.
    if t1 == 0 and t2 == 0:
        return True, ""
    if t1 < 0 or t2 < 0:
        return False, "Skorlar negatif olamaz."
        
    max_s = max(t1, t2)
    min_s = min(t1, t2)
    diff = max_s - min_s
    
    # 3. Set için Süper Tie-break (Onda biten maç) kontrolü
    if is_set3 and (t1 >= 10 or t2 >= 10):
        if max_s == 10 and min_s <= 8:
            return True, ""
        elif max_s > 10 and diff == 2:
            return True, ""
        else:
            return False, "3. Set Süper Tie-Break skoru geçersiz! (En az 10'a ulaşılmalı ve fark tam olarak 2 olmalıdır, örn: 10-8, 11-9, 10-5)"
            
    # Standart Set Kuralları (1. Set, 2. Set ve normal oynanan 3. Set için)
    if max_s < 6:
        return False, "Set henüz bitmemiş (En az 6 oyun olmalı)."
    if max_s == 6 and diff >= 2:
        return True, ""
    if max_s == 7 and (diff == 2 or diff == 1): # 7-5 veya 7-6 durumları
        return True, ""
    if max_s > 7:
        return False, f"Normal set skoru {max_s} olamaz (En fazla 7-5 veya 7-6 olabilir)."
        
    return False, "Geçersiz set skoru (Örn: 6-5 olamaz, setin uzaması gerekir)."


# --- 1. OTOMASYON MOTORU ---
def eslesmeleri_olustur(grup_adi, takimlar, grup_tipi):
    if grup_tipi == "4'lü Grup":
        base_matches = [
            {"Gün": "1. Gün", "Eşleşme": "1 ve 4", "Takım 1": takimlar[0], "Takım 2": takimlar[3]},
            {"Gün": "1. Gün", "Eşleşme": "2 ve 3", "Takım 1": takimlar[1], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "1 ve 3", "Takım 1": takimlar[0], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "2 ve 4", "Takım 1": takimlar[1], "Takım 2": takimlar[3]},
            {"Gün": "3. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]},
            {"Gün": "3. Gün", "Eşleşme": "3 ve 4", "Takım 1": takimlar[2], "Takım 3": takimlar[3]}, # Eski yapınız korunmuştur
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
            # Olası anahtar uyumu düzeltmesi
            if "Takım 3" in satir:
                satir["Takım 2"] = satir.pop("Takım 3")
            satir["Branş"] = brans
            satir["Grup"] = grup_adi
            satir.update({"1.Set T1": 0, "1.Set T2": 0, "2.Set T1": 0, "2.Set T2": 0, "3.Set T1": 0, "3.Set T2": 0})
            program.append(satir)
    return program

# --- 2. HAFIZA ---
if 'skor_tablosu' not in st.session_state:
    st.session_state.skor_tablosu = pd.DataFrame(columns=["Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"])

if 'mac_programi' not in st.session_state:
    st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Takım 1", "Takım 2", "Kort", "Maç Skoru"])

# --- 3. SEKMELER ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 1. Grup Ayarları", "✍️ 2. Skor Girişi", "🏆 3. Puan Durumu", "📅 4. Maç Programı", "⚙️ 5. Yönetim"])

with tab1:
    st.subheader("Grup Takımlarını Seç ve Eşleşmeleri Oluştur")
    grup_tipi = st.radio("Kurulacak Grup Tipini Seçin:", ["4'lü Grup", "5'li Grup"], horizontal=True)
    grup_adi = st.text_input("Grup Adı")
    
    beklenen_sayi = 4 if grup_tipi == "4'lü Grup" else 5
    takim_listesi = st.text_area(f"Takımları Alt Alta Yaz (Tam olarak {beklenen_sayi} Takım Olmalı)")
    
    if st.button("🚀 Eşleşmeleri Oluştur"):
        takimlar = [t.strip() for t in takim_listesi.split('\n') if t.strip()]
        
        # 1. GÜVENLİK DUVARI: Aynı isimde mükerrer grup kontrolü
        if not st.session_state.skor_tablosu.empty and grup_adi in st.session_state.skor_tablosu['Grup'].unique():
            st.error(f"❌ Hata: '{grup_adi}' isminde bir grup zaten mevcut! Çift kayıt olmaması için lütfen farklı bir grup adı girin veya yönetim panelinden eski grubu silin.")
        elif len(takimlar) == beklenen_sayi:
            yeni_maclar = eslesmeleri_olustur(grup_adi, takimlar, grup_tipi)
            yeni_df = pd.DataFrame(yeni_maclar)
            st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
            st.session_state.skor_tablosu.index = range(1, len(st.session_state.skor_tablosu) + 1)
            st.success(f"Eşleşmeler {grup_tipi} modeline göre başarıyla oluşturuldu!")
            st.rerun()
        else:
            st.error(f"Hata: Seçtiğiniz grup tipi için {beklenen_sayi} takım girmelisiniz. (Şu an girilen: {len(takimlar)})")

with tab2:
    st.subheader("Maç Skorlarını Girin")
    if not st.session_state.skor_tablosu.empty:
        gruplar = st.session_state.skor_tablosu['Grup'].unique()
        secilen_grup = st.selectbox("Düzenlemek İçin Grup Seç:", gruplar)
        
        df_grup = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == secilen_grup].copy()
        edited_dfs = {}
        
        def gun_sirala(gun_adi):
            try: return int(gun_adi.split('.')[0])
            except: return 99
            
        aktif_gunler = sorted(df_grup['Gün'].unique(), key=gun_sirala)
        for gun in aktif_gunler:
            st.markdown(f"### {gun}")
            df_gun = df_grup[df_grup['Gün'] == gun]
            if not df_gun.empty:
                edited_dfs[gun] = st.data_editor(df_gun, use_container_width=True, key=f"editor_{secilen_grup}_{gun}")
        
        if st.button("✅ Tüm Skorları Kaydet"):
            all_edited = pd.concat(edited_dfs.values())
            
            hata_mesajlari = []
            uzerine_yazilanlar = []
            
            # Veri işleme ve Tenis Kuralları Kontrolü
            for idx, row in all_edited.iterrows():
                eski_row = st.session_state.skor_tablosu.loc[idx]
                mac_tanimi = f"{row['Gün']} - {row['Branş']} ({row['Takım 1']} vs {row['Takım 2']})"
                
                # Tenis kurallarına uygunluk doğrulaması
                ok1, msg1 = set_gecerli_mi(int(row['1.Set T1']), int(row['1.Set T2']), is_set3=False)
                ok2, msg2 = set_gecerli_mi(int(row['2.Set T1']), int(row['2.Set T2']), is_set3=False)
                ok3, msg3 = set_gecerli_mi(int(row['3.Set T1']), int(row['3.Set T2']), is_set3=True) # 3. Set için Süper Tie-break devrede
                
                if not ok1: hata_mesajlari.append(f"❌ {mac_tanimi} -> 1. Set: {msg1}")
                if not ok2: hata_mesajlari.append(f"❌ {mac_tanimi} -> 2. Set: {msg2}")
                if not ok3: hata_mesajlari.append(f"❌ {mac_tanimi} -> 3. Set: {msg3}")
                
                # 2. GÜVENLİK DUVARI: Üzerine iki kez yanlışlıkla skor yazma uyarısı
                eski_dolu = (eski_row['1.Set T1'] != 0 or eski_row['1.Set T2'] != 0 or eski_row['2.Set T1'] != 0 or eski_row['2.Set T2'] != 0 or eski_row['3.Set T1'] != 0 or eski_row['3.Set T2'] != 0)
                yeni_farkli = (eski_row['1.Set T1'] != row['1.Set T1'] or eski_row['1.Set T2'] != row['1.Set T2'] or eski_row['2.Set T1'] != row['2.Set T1'] or eski_row['2.Set T2'] != row['2.Set T2'] or eski_row['3.Set T1'] != row['3.Set T1'] or eski_row['3.Set T2'] != row['3.Set T2'])
                
                if eski_dolu and yeni_farkli:
                    uzerine_yazilanlar.append(mac_tanimi)
            
            # Hata varsa kaydetmeyi bloke et
            if hata_mesajlari:
                for h in hata_mesajlari:
                    st.error(h)
                st.error("Lütfen hatalı skorları düzelterek tekrar deneyin. Kayıt yapılmadı.")
            else:
                # Eğer üzerine yazılan eski veri varsa sarı uyarı göster ama kaydet
                if uzerine_yazilanlar:
                    st.warning("⚠️ Bilgi: Aşağıdaki maçların önceden girilmiş skorları güncellendi:\n" + "\n".join([f"- {m}" for m in uzerine_yazilanlar]))
                
                st.session_state.skor_tablosu.update(all_edited)
                st.success("Tüm skorlar tenis kurallarına göre başarıyla kontrol edildi ve kaydedildi!")
                st.rerun()
    else:
        st.info("Henüz grup oluşturmadınız.")

with tab3:
    st.subheader("Otomatik Puan Durumu")
    if not st.session_state.skor_tablosu.empty:
        df = st.session_state.skor_tablosu.copy()
        
        # --- 3. SET SÜPER TIE-BREAK UYUMLU DİNAMİK HESAPLAMA MOTORU ---
        def satir_istatistiklerini_hesapla(row):
            s1_t1, s1_t2 = int(row['1.Set T1']), int(row['1.Set T2'])
            s2_t1, s2_t2 = int(row['2.Set T1']), int(row['2.Set T2'])
            s3_t1, s3_t2 = int(row['3.Set T1']), int(row['3.Set T2'])
            
            # Maç hiç oynanmamışsa sıfır dön
            if s1_t1 == 0 and s1_t2 == 0 and s2_t1 == 0 and s2_t2 == 0 and s3_t1 == 0 and s3_t2 == 0:
                return pd.Series([0, 0, 0, 0])
                
            # İlk 2 setin verileri normal eklenir
            t1_set = int(s1_t1 > s1_t2) + int(s2_t1 > s2_t2)
            t2_set = int(s1_t2 > s1_t1) + int(s2_t2 > s2_t1)
            t1_oyun = s1_t1 + s2_t1
            t2_oyun = s1_t2 + s2_t2
            
            # 3. Set Değerlendirmesi
            if s3_t1 > 0 or s3_t2 > 0:
                if s3_t1 >= 10 or s3_t2 >= 10:
                    # KRİTİK İSTEK: Maç Tie-break (10'lu sistem) algılandı!
                    # Kazanan takıma tam olarak +1 set ve +1 oyun averajı (+1 e 0 yazarak) verilir.
                    if s3_t1 > s3_t2:
                        t1_set += 1
                        t1_oyun += 1
                        t2_oyun += 0
                    else:
                        t2_set += 1
                        t2_oyun += 1
                        t1_oyun += 0
                else:
                    # Normal 3. Set (6 veya 7 de biten normal set) algılandı! Tüm oyunlar normal eklenir.
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

with tab4:
    st.subheader("📅 Maç Programı Oluşturucu")
    if not st.session_state.skor_tablosu.empty:
        st.markdown("**1. Listeden Maç Seç ve Programa Ekle**")
        c1, c2, c3 = st.columns(3)
        
        gruplar_prog = st.session_state.skor_tablosu['Grup'].unique()
        sec_grup_prog = c1.selectbox("Grup Seç:", gruplar_prog, key="prog_grup")
        df_g_prog = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == sec_grup_prog]
        
        def gun_sirala_prog(gun_adi):
            try: return int(gun_adi.split('.')[0])
            except: return 99
            
        gunler_prog = sorted(df_g_prog['Gün'].unique(), key=gun_sirala_prog)
        sec_gun_prog = c2.selectbox("Gün Seç:", gunler_prog, key="prog_gun")
        df_m_prog = df_g_prog[df_g_prog['Gün'] == sec_gun_prog]
        
        mac_listesi = [f"{row['Takım 1']} vs {row['Takım 2']} ({row['Branş']})" for idx, row in df_m_prog.iterrows()]
        sec_mac_adi = c3.selectbox("Maç Seç:", mac_listesi, key="prog_mac")
        
        if st.button("➕ Programa Ekle"):
            secilen_row = df_m_prog.iloc[mac_listesi.index(sec_mac_adi)]
            yeni_kayit = pd.DataFrame([{
                "Maç Saati": "",
                "Takım 1": f"{secilen_row['Takım 1']} ({secilen_row['Branş']})",
                "Takım 2": secilen_row['Takım 2'],
                "Kort": "",
                "Maç Skoru": ""
            }])
            st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, yeni_kayit], ignore_index=True)
            st.success("Maç programa eklendi!")
            st.rerun()
            
        st.divider()
        st.markdown("**2. Oluşturulan Maç Programı**")
        if not st.session_state.mac_programi.empty:
            st.info("💡 Tablo üzerinde Saat, Kort ve Skor kısımlarına **çift tıklayarak** elle giriş yapabilirsiniz.")
            guncel_program = st.data_editor(
                st.session_state.mac_programi,
                column_config={"Takım 1": st.column_config.TextColumn(disabled=True), "Takım 2": st.column_config.TextColumn(disabled=True)},
                use_container_width=True, num_rows="dynamic", key="program_editor"
            )
            col_k, col_t = st.columns(2)
            if col_k.button("💾 Değişiklikleri Kaydet"):
                st.session_state.mac_programi = guncel_program
                st.success("Program güncellendi!")
                st.rerun()
            if col_t.button("🗑️ Tüm Programı Temizle"):
                st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Takım 1", "Takım 2", "Kort", "Maç Skoru"])
                st.rerun()
        else:
            st.warning("Henüz programa maç eklemediniz.")
    else:
        st.info("Önce 1. Sekmeden grup ve eşleşmeleri oluşturmalısınız.")

with tab5:
    st.subheader("⚙️ Yönetim Paneli")
    st.markdown("### 📁 Veri Dosyası İşlemleri")
    col1, col2 = st.columns(2)
    with col1:
        csv = st.session_state.skor_tablosu.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Verileri İndir (Yedekle)", data=csv, file_name='turnuva_verisi.csv', mime='text/csv')
    with col2:
        yuklenen_dosya = st.file_uploader("📂 Veri Dosyası Yükle (Geri Yükle)", type=['csv'])
        if yuklenen_dosya is not None:
            if st.button("🔄 Dosyayı Yükle ve Uygula"):
                st.session_state.skor_tablosu = pd.read_csv(yuklenen_dosya)
                st.success("Veri başarıyla geri yüklendi!")
                st.rerun()

    st.divider()
    if not st.session_state.skor_tablosu.empty:
        gruplar = st.session_state.skor_tablosu['Grup'].unique()
        grup_sec = st.selectbox("Düzenlenecek Grubu Seç:", gruplar)
        df_grup = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == group_sec if 'group_sec' in locals() else st.session_state.skor_tablosu['Grup'] == grup_sec]
        tum_takimlar = sorted(list(set(df_grup['Takım 1'].unique().tolist() + df_grup['Takım 2'].unique().tolist())))
        eski_isim = st.selectbox("Değiştirilecek Takım:", tum_takimlar)
        yeni_isim = st.text_input("Yeni İsim:")
        if st.button("Takımı Güncelle"):
            st.session_state.skor_tablosu.loc[st.session_state.skor_tablosu['Takım 1'] == eski_isim, 'Takım 1'] = yeni_isim
            st.session_state.skor_tablosu.loc[st.session_state.skor_tablosu['Takım 2'] == eski_isim, 'Takım 2'] = yeni_isim
            st.rerun()
            
        st.divider()
        silinecek_grup = st.selectbox("Silinecek Grup:", gruplar)
        if st.button("❌ Bu Grubu Tamamen Sil"):
            st.session_state.skor_tablosu = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] != silinecek_grup]
            st.session_state.skor_tablosu.index = range(1, len(st.session_state.skor_tablosu) + 1)
            st.rerun()
    else:
        st.info("Henüz grup yok.")

    st.divider()
    if st.button("🚨 TÜM VERİLERİ SIFIRLA"):
        st.session_state.skor_tablosu = pd.DataFrame(columns=["Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2"])
        st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Takım 1", "Takım 2", "Kort", "Maç Skoru"])
        st.rerun()
