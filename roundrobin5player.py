import streamlit as st
import pandas as pd
import json
import os
import itertools

# --- AYARLAR VE VERİ YÖNETİMİ ---
st.set_page_config(layout="wide", page_title="Tenis Turnuva Yönetim Sistemi", page_icon="🎾")

DATA_FILE = "turnuva_veri.json"

def verileri_yukle():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                veri = json.load(f)
                # Eski sürümdeki verilerde format anahtarı yoksa ekleyelim (geriye dönük uyumluluk)
                if "grup_formatlari" not in veri:
                    veri["grup_formatlari"] = {}
                return veri
            except json.JSONDecodeError:
                return {"gruplar": {}, "program": [], "skorlar": {}, "esameler": {}, "grup_formatlari": {}}
    return {"gruplar": {}, "program": [], "skorlar": {}, "esameler": {}, "grup_formatlari": {}}

def verileri_kaydet(veri):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

if "data" not in st.session_state:
    st.session_state.data = verileri_yukle()

# Fikstür oluşturma algoritması (Round Robin)
def round_robin_eslesme(takimlar):
    if len(takimlar) < 2:
        return []
    aktif_takimlar = takimlar.copy()
    if len(aktif_takimlar) % 2 != 0:
        aktif_takimlar.append('BAY')
    
    n = len(aktif_takimlar)
    eslesmeler = []
    
    for _ in range(n - 1):
        gun_eslesmeleri = []
        for j in range(n // 2):
            t1 = aktif_takimlar[j]
            t2 = aktif_takimlar[n - 1 - j]
            if t1 != 'BAY' and t2 != 'BAY':
                gun_eslesmeleri.append((t1, t2))
        eslesmeler.append(gun_eslesmeleri)
        aktif_takimlar.insert(1, aktif_takimlar.pop())
        
    return eslesmeler

# Süper Tie-Break kurallı set kontrolü
def set_gecerli_mi(skor_str):
    if not skor_str or skor_str.strip() == "":
        return False
    try:
        t1, t2 = map(int, skor_str.split('-'))
        if (t1 == 6 and t2 <= 4) or (t2 == 6 and t1 <= 4): return True
        if (t1 == 7 and t2 in [5, 6]) or (t2 == 7 and t1 in [5, 6]): return True
        # Süper tie-break (10'a ulaşan veya farkı 2 olan)
        if (t1 >= 10 or t2 >= 10) and abs(t1 - t2) >= 2: return True
        return False
    except ValueError:
        return False

# --- ARAYÜZ (SEKMELER) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎾 Grup Ayarları", "📝 Esame ve Skor", "🏆 Puan Durumu", "📺 Misafir Ekranı", "⚙️ Yönetim Paneli"])

# SEKME 1: GRUP AYARLARI
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Yeni Grup / Takım Oluştur")
        
        with st.form("grup_olustur_form"):
            grup_adi_input = st.text_input("Grup Adı (Örn: A Grubu)")
            
            # YENİ ÖZELLİK: Maç Formatı Seçimi
            format_secimi = st.radio("Grubun Maç Formatı", 
                                     ["2 Tek, 1 Çift (3 Maçlık)", "3 Tek, 2 Çift (5 Maçlık)"],
                                     help="Bu seçim kaydedildikten sonra fikstürü buna göre üretecektir.")
            
            takimlar_input = st.text_area("Takım İsimleri (Her satıra bir takım)")
            submit_grup = st.form_submit_button("Grubu ve Formatı Kaydet")
            
            if submit_grup:
                grup_adi = grup_adi_input.strip()
                if not grup_adi:
                    st.error("Grup adı boş olamaz!")
                elif grup_adi in st.session_state.data["gruplar"]:
                    # YENİ ÖZELLİK: Mükerrer grup uyarısı
                    st.error(f"⚠️ '{grup_adi}' adında bir grup zaten mevcut! Lütfen farklı bir isim seçin veya Yönetim Panelinden düzenleyin.")
                else:
                    takim_listesi = [t.strip() for t in takimlar_input.split('\n') if t.strip()]
                    if len(takim_listesi) > 1:
                        st.session_state.data["gruplar"][grup_adi] = {takim: [] for takim in takim_listesi}
                        st.session_state.data["grup_formatlari"][grup_adi] = format_secimi
                        
                        # Fikstür Üretimi (Seçilen formata göre)
                        eslesme_gunleri = round_robin_eslesme(takim_listesi)
                        program = st.session_state.data["program"]
                        
                        if "5 Maçlık" in format_secimi:
                            branslar = ["1. Tekler", "2. Tekler", "3. Tekler", "1. Çiftler", "2. Çiftler"]
                        else:
                            branslar = ["1. Tekler", "2. Tekler", "Çiftler"]
                            
                        mac_kodu = len(program) + 1
                        for gun, eslesmeler in enumerate(eslesme_gunleri, 1):
                            for t1, t2 in eslesmeler:
                                for brans in branslar:
                                    program.append({
                                        "ID": f"M{mac_kodu}",
                                        "Grup": grup_adi,
                                        "Tarih": f"Gün {gun}",
                                        "Takım 1": t1,
                                        "Takım 2": t2,
                                        "Branş": brans
                                    })
                                    mac_kodu += 1
                                    
                        verileri_kaydet(st.session_state.data)
                        st.success(f"{grup_adi} ({format_secimi}) başarıyla oluşturuldu ve fikstür çekildi!")
                        st.rerun()
                    else:
                        st.error("En az 2 takım girmelisiniz.")

        st.divider()
        st.subheader("Oyuncu Ekle")
        grup_sec = st.selectbox("Grup Seç", ["Seçiniz..."] + list(st.session_state.data["gruplar"].keys()), key="oyuncu_grup_sec")
        if grup_sec != "Seçiniz...":
            takim_sec = st.selectbox("Takım Seç", list(st.session_state.data["gruplar"][grup_sec].keys()))
            oyuncular_input = st.text_area("Oyuncu İsimleri (Her satıra bir oyuncu)")
            if st.button("Oyuncuları Kaydet"):
                yeni_oyuncular = [o.strip() for o in oyuncular_input.split('\n') if o.strip()]
                st.session_state.data["gruplar"][grup_sec][takim_sec].extend(yeni_oyuncular)
                st.session_state.data["gruplar"][grup_sec][takim_sec] = list(set(st.session_state.data["gruplar"][grup_sec][takim_sec])) # Mükerrer engelleme
                verileri_kaydet(st.session_state.data)
                st.success(f"Oyuncular {takim_sec} takımına eklendi!")
                st.rerun()

    with col2:
        # YENİ ÖZELLİK: Alfabetik Akordeon Liste (Kayıtlı Gruplar ve Detayları)
        st.header("Kayıtlı Gruplar ve Kadrolar")
        if not st.session_state.data["gruplar"]:
            st.info("Sistemde henüz kayıtlı grup bulunmamaktadır.")
        else:
            sirali_gruplar = sorted(st.session_state.data["gruplar"].keys())
            for grup_adi in sirali_gruplar:
                formati = st.session_state.data["grup_formatlari"].get(grup_adi, "2 Tek, 1 Çift (3 Maçlık)")
                with st.expander(f"📁 {grup_adi}  |  📌 Format: {formati}"):
                    takimlar_sozlugu = st.session_state.data["gruplar"][grup_adi]
                    if not takimlar_sozlugu:
                        st.warning("Bu grupta takım yok.")
                    else:
                        for takim_adi in sorted(takimlar_sozlugu.keys()):
                            oyuncu_listesi = takimlar_sozlugu[takim_adi]
                            st.markdown(f"**🛡️ {takim_adi}**")
                            if oyuncu_listesi:
                                st.write(" • " + ", ".join(sorted(oyuncu_listesi)))
                            else:
                                st.caption("Henüz oyuncu eklenmemiş.")
                            st.divider()

# SEKME 2: ESAME VE SKOR GİRİŞİ
with tab2:
    st.header("Maç Kartı: Esame ve Skor Girişi")
    if not st.session_state.data["program"]:
        st.info("Henüz oluşturulmuş bir fikstür yok.")
    else:
        df_program = pd.DataFrame(st.session_state.data["program"])
        
        # Sadece eşleşmeleri (Serileri) gruplayıp benzersiz hale getirelim
        eslesmeler = df_program[['Grup', 'Tarih', 'Takım 1', 'Takım 2']].drop_duplicates().reset_index(drop=True)
        eslesme_secenekleri = [
            f"[{row['Grup']}] {row['Tarih']} | {row['Takım 1']} vs {row['Takım 2']}"
            for _, row in eslesmeler.iterrows()
        ]
        
        secilen_eslesme_str = st.selectbox("Eşleşme Seçiniz", ["Seçiniz..."] + eslesme_secenekleri)
        
        if secilen_eslesme_str != "Seçiniz...":
            secim_idx = eslesme_secenekleri.index(secilen_eslesme_str) - 1
            secilen_seri = eslesmeler.iloc[secim_idx]
            
            # Seçilen eşleşmenin alt maçlarını (Branşlarını) getirme (Format neyse o kadar gelecek)
            maclar = df_program[
                (df_program['Grup'] == secilen_seri['Grup']) & 
                (df_program['Tarih'] == secilen_seri['Tarih']) & 
                (df_program['Takım 1'] == secilen_seri['Takım 1']) & 
                (df_program['Takım 2'] == secilen_seri['Takım 2'])
            ]
            
            st.markdown(f"### {secilen_seri['Takım 1']} ⚔️ {secilen_seri['Takım 2']}")
            
            takim1_oyuncular = st.session_state.data["gruplar"].get(secilen_seri['Grup'], {}).get(secilen_seri['Takım 1'], [])
            takim2_oyuncular = st.session_state.data["gruplar"].get(secilen_seri['Grup'], {}).get(secilen_seri['Takım 2'], [])
            
            takim1_oyuncular = ["Bilinmiyor"] + takim1_oyuncular
            takim2_oyuncular = ["Bilinmiyor"] + takim2_oyuncular

            with st.form(f"skor_form_{secilen_seri['Tarih']}"):
                yeni_skorlar = {}
                yeni_esameler = {}
                
                for _, mac in maclar.iterrows():
                    mac_id = mac['ID']
                    st.subheader(f"🎾 {mac['Branş']}")
                    
                    mevcut_esame = st.session_state.data["esameler"].get(mac_id, {"T1": "Bilinmiyor", "T2": "Bilinmiyor"})
                    mevcut_skor = st.session_state.data["skorlar"].get(mac_id, {"S1": "", "S2": "", "S3": "", "Kazanan": ""})
                    
                    c1, c2, c3 = st.columns([2, 3, 2])
                    
                    with c1:
                        idx1 = takim1_oyuncular.index(mevcut_esame["T1"]) if mevcut_esame["T1"] in takim1_oyuncular else 0
                        t1_oyuncu = st.selectbox(f"{secilen_seri['Takım 1']} Oyuncusu", takim1_oyuncular, index=idx1, key=f"t1_{mac_id}")
                        
                    with c2:
                        sc1, sc2, sc3 = st.columns(3)
                        s1 = sc1.text_input("1. Set", value=mevcut_skor.get("S1", ""), key=f"s1_{mac_id}", placeholder="6-4")
                        s2 = sc2.text_input("2. Set", value=mevcut_skor.get("S2", ""), key=f"s2_{mac_id}", placeholder="4-6")
                        s3 = sc3.text_input("3. Set (Tie-Break)", value=mevcut_skor.get("S3", ""), key=f"s3_{mac_id}", placeholder="10-8")
                        
                    with c3:
                        idx2 = takim2_oyuncular.index(mevcut_esame["T2"]) if mevcut_esame["T2"] in takim2_oyuncular else 0
                        t2_oyuncu = st.selectbox(f"{secilen_seri['Takım 2']} Oyuncusu", takim2_oyuncular, index=idx2, key=f"t2_{mac_id}")

                    yeni_esameler[mac_id] = {"T1": t1_oyuncu, "T2": t2_oyuncu}
                    
                    # Kazanan hesaplama algoritması
                    kazanan = ""
                    t1_set = 0
                    t2_set = 0
                    
                    for set_skoru in [s1, s2, s3]:
                        if set_gecerli_mi(set_skoru):
                            p1, p2 = map(int, set_skoru.split('-'))
                            if p1 > p2: t1_set += 1
                            elif p2 > p1: t2_set += 1
                            
                    if t1_set >= 2: kazanan = secilen_seri['Takım 1']
                    elif t2_set >= 2: kazanan = secilen_seri['Takım 2']
                    
                    yeni_skorlar[mac_id] = {"S1": s1, "S2": s2, "S3": s3, "Kazanan": kazanan}
                    
                    if kazanan:
                        st.success(f"Maç Kazananı: **{kazanan}**")
                    st.divider()

                kaydet_btn = st.form_submit_button("Skorları ve Esameleri Kaydet")
                if kaydet_btn:
                    st.session_state.data["skorlar"].update(yeni_skorlar)
                    st.session_state.data["esameler"].update(yeni_esameler)
                    verileri_kaydet(st.session_state.data)
                    st.success("Veriler başarıyla kaydedildi!")
                    st.rerun()

# SEKME 3: PUAN DURUMU
with tab3:
    st.header("🏆 Puan Durumu")
    
    if st.session_state.data["program"]:
        df_p = pd.DataFrame(st.session_state.data["program"])
        
        # Skor bilgilerini data frame'e entegre et
        def kazanan_bul(mac_id):
            return st.session_state.data["skorlar"].get(mac_id, {}).get("Kazanan", "")
            
        df_p['Kazanan'] = df_p['ID'].apply(kazanan_bul)
        
        df_p['T1_Match_Win'] = (df_p['Kazanan'] == df_p['Takım 1']).astype(int)
        df_p['T2_Match_Win'] = (df_p['Kazanan'] == df_p['Takım 2']).astype(int)
        
        # Serileri (Eşleşmeleri) gruplayıp, takımların kazandığı maç sayılarını topluyoruz
        seriler = df_p.groupby(['Grup', 'Tarih', 'Takım 1', 'Takım 2']).agg({
            'T1_Match_Win': 'sum',
            'T2_Match_Win': 'sum'
        }).reset_index()
        
        # YENİ ÖZELLİK MANTIĞI: Seri (Etab) Kazanma Kriteri Evrenselleşti
        # Format 3 maçlıksa da, 5 maçlıksa da kim daha çok maç kazanmışsa seriyi o alır. 
        # Sabit "2 maç" sınırı yerine ">" büyüktür operatörü sistemi kurtarır.
        seriler['T1_Win'] = (seriler['T1_Match_Win'] > seriler['T2_Match_Win']).astype(int)
        seriler['T2_Win'] = (seriler['T2_Match_Win'] > seriler['T1_Match_Win']).astype(int)
        
        gruplar_puan_tablolari = {}
        
        for g in st.session_state.data["gruplar"].keys():
            takimlar = list(st.session_state.data["gruplar"][g].keys())
            puan_tablosu = []
            
            for t in takimlar:
                # Takım 1 olarak oynadığı seriler
                t1_oynadigi = seriler[(seriler['Grup'] == g) & (seriler['Takım 1'] == t)]
                galibiyet_t1 = t1_oynadigi['T1_Win'].sum()
                mac_kazanma_t1 = t1_oynadigi['T1_Match_Win'].sum()
                mac_kaybetme_t1 = t1_oynadigi['T2_Match_Win'].sum()
                
                # Takım 2 olarak oynadığı seriler
                t2_oynadigi = seriler[(seriler['Grup'] == g) & (seriler['Takım 2'] == t)]
                galibiyet_t2 = t2_oynadigi['T2_Win'].sum()
                mac_kazanma_t2 = t2_oynadigi['T2_Match_Win'].sum()
                mac_kaybetme_t2 = t2_oynadigi['T1_Match_Win'].sum()
                
                toplam_seri = len(t1_oynadigi) + len(t2_oynadigi)
                toplam_galibiyet = galibiyet_t1 + galibiyet_t2
                toplam_maglubiyet = toplam_seri - toplam_galibiyet
                
                alinan_mac = mac_kazanma_t1 + mac_kazanma_t2
                verilen_mac = mac_kaybetme_t1 + mac_kaybetme_t2
                averaj = alinan_mac - verilen_mac
                puan = toplam_galibiyet * 2
                
                puan_tablosu.append({
                    "Takım": t,
                    "O": toplam_seri,
                    "G": toplam_galibiyet,
                    "M": toplam_maglubiyet,
                    "AM": alinan_mac,
                    "VM": verilen_mac,
                    "Averaj": averaj,
                    "Puan": puan
                })
                
            df_tablo = pd.DataFrame(puan_tablosu).sort_values(by=["Puan", "Averaj"], ascending=[False, False]).reset_index(drop=True)
            df_tablo.index += 1
            gruplar_puan_tablolari[g] = df_tablo
            
        for g, tablo in gruplar_puan_tablolari.items():
            st.subheader(f"[{g}] Puan Durumu")
            st.dataframe(tablo, use_container_width=True)
    else:
        st.info("Puan durumu hesaplanması için fikstür oluşturulmalıdır.")

# SEKME 4: MİSAFİR EKRANI
with tab4:
    st.header("📢 Turnuva Misafir Ekranı")
    st.write("Bu ekran sadece skorları ve fikstürü okumak için tasarlanmıştır. Veriler değiştirilemez.")
    
    if st.session_state.data["program"]:
        df_misafir = pd.DataFrame(st.session_state.data["program"])
        
        def skor_metni_olustur(mac_id):
            s = st.session_state.data["skorlar"].get(mac_id, {})
            setler = [s.get("S1",""), s.get("S2",""), s.get("S3","")]
            temiz_setler = [st for st in setler if st]
            return " | ".join(temiz_setler) if temiz_setler else "-"
            
        df_misafir['Skor'] = df_misafir['ID'].apply(skor_metni_olustur)
        df_misafir['Kazanan'] = df_misafir['ID'].apply(lambda x: st.session_state.data["skorlar"].get(x, {}).get("Kazanan", "-"))
        
        # HTML Tablo Çıktısı (Şık görünüm)
        st.markdown(df_misafir[['Grup', 'Tarih', 'Takım 1', 'Takım 2', 'Branş', 'Skor', 'Kazanan']].to_html(index=False, classes='table table-striped'), unsafe_allow_html=True)
    else:
        st.info("Gösterilecek veri bulunamadı.")

# SEKME 5: YÖNETİM PANELİ (TEHLİKELİ BÖLGE)
with tab5:
    st.header("⚙️ Yönetim Paneli ve Veri Editörü")
    st.warning("Bu sekmedeki değişiklikler JSON veritabanına doğrudan yazılır. Dikkatli kullanınız.")
    
    secim = st.selectbox("Düzenlenecek Veriyi Seçin", ["Gruplar", "Fikstür Programı", "Skorlar", "Esameler", "Grup Formatları"])
    
    anahtar_map = {
        "Gruplar": "gruplar", 
        "Fikstür Programı": "program", 
        "Skorlar": "skorlar", 
        "Esameler": "esameler",
        "Grup Formatları": "grup_formatlari"
    }
    veri_anahtari = anahtar_map[secim]
    
    if isinstance(st.session_state.data[veri_anahtari], (dict, list)):
        if isinstance(st.session_state.data[veri_anahtari], list):
            df_edit = pd.DataFrame(st.session_state.data[veri_anahtari])
        else:
            df_edit = pd.DataFrame([{ "Anahtar": k, "Değer": v } for k,v in st.session_state.data[veri_anahtari].items()])
            
        st.write(f"**{secim} Düzenle:**")
        duzenlenen_df = st.data_editor(df_edit, use_container_width=True, num_rows="dynamic")
        
        if st.button(f"{secim} Değişikliklerini JSON'a Uygula"):
            if isinstance(st.session_state.data[veri_anahtari], list):
                st.session_state.data[veri_anahtari] = duzenlenen_df.to_dict('records')
            else:
                yeni_dict = {}
                for _, row in duzenlenen_df.iterrows():
                    yeni_dict[row['Anahtar']] = row['Değer']
                st.session_state.data[veri_anahtari] = yeni_dict
                
            verileri_kaydet(st.session_state.data)
            st.success(f"**{secim}** başarıyla güncellendi!")
            st.rerun()

    st.divider()
    st.subheader("🚨 Tehlikeli Bölge")
    col_del1, col_del2 = st.columns(2)
    with col_del1:
        if st.button("Skorları ve Esameleri Sıfırla (Fikstür Kalır)", type="primary"):
            st.session_state.data["skorlar"] = {}
            st.session_state.data["esameler"] = {}
            verileri_kaydet(st.session_state.data)
            st.success("Skorlar ve Esameler temizlendi!")
            st.rerun()
    with col_del2:
        if st.button("TÜM TURNUVAYI SIFIRLA (Her Şey Silinir)", type="primary"):
            st.session_state.data = {"gruplar": {}, "program": [], "skorlar": {}, "esameler": {}, "grup_formatlari": {}}
            verileri_kaydet(st.session_state.data)
            st.success("Tüm sistem sıfırlandı!")
            st.rerun()
