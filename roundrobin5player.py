import streamlit as st
import pandas as pd
import json
import os

# --- AYARLAR VE VERİ YÖNETİMİ ---
st.set_page_config(layout="wide", page_title="Tenis Turnuva Yönetimi", page_icon="🎾")

DATA_FILE = "turnuva_veri.json"
ADMIN_SIFRE = "1234"  # Buraya kendi yönetici şifreni yazabilirsin

# YENİ: Hata verdirtmeyen, kurşun geçirmez veri yükleme fonksiyonu (KeyError Çözümü)
def verileri_yukle():
    varsayilan_veri = {"gruplar": {}, "program": [], "skorlar": {}, "esameler": {}, "grup_formatlari": {}}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                veri = json.load(f)
                # Eksik anahtarlar varsa (eski dosya yüzünden) onları varsayılanla doldur
                for anahtar, varsayilan_deger in varsayilan_veri.items():
                    if anahtar not in veri:
                        veri[anahtar] = varsayilan_deger
                return veri
            except json.JSONDecodeError:
                return varsayilan_veri
    return varsayilan_veri

def verileri_kaydet(veri):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

if "data" not in st.session_state:
    st.session_state.data = verileri_yukle()

if "admin_mi" not in st.session_state:
    st.session_state.admin_mi = False

# YENİDEN EKLENEN: Yönetici Girişi (Sidebar'da)
with st.sidebar:
    st.header("🔐 Yönetici Girişi")
    if not st.session_state.admin_mi:
        sifre_giris = st.text_input("Şifrenizi Girin", type="password")
        if st.button("Giriş Yap"):
            if sifre_giris == ADMIN_SIFRE:
                st.session_state.admin_mi = True
                st.success("Giriş Başarılı!")
                st.rerun()
            else:
                st.error("Hatalı Şifre!")
    else:
        st.success("Yönetici yetkisi aktif.")
        if st.button("Çıkış Yap"):
            st.session_state.admin_mi = False
            st.rerun()

# Fikstür oluşturma algoritması
def round_robin_eslesme(takimlar):
    if len(takimlar) < 2: return []
    aktif_takimlar = takimlar.copy()
    if len(aktif_takimlar) % 2 != 0: aktif_takimlar.append('BAY')
    n = len(aktif_takimlar)
    eslesmeler = []
    for _ in range(n - 1):
        gun_eslesmeleri = []
        for j in range(n // 2):
            t1 = aktif_takimlar[j]
            t2 = aktif_takimlar[n - 1 - j]
            if t1 != 'BAY' and t2 != 'BAY': gun_eslesmeleri.append((t1, t2))
        eslesmeler.append(gun_eslesmeleri)
        aktif_takimlar.insert(1, aktif_takimlar.pop())
    return eslesmeler

# Set kontrolü
def set_gecerli_mi(skor_str):
    if not skor_str or skor_str.strip() == "": return False
    try:
        t1, t2 = map(int, skor_str.split('-'))
        if (t1 == 6 and t2 <= 4) or (t2 == 6 and t1 <= 4): return True
        if (t1 == 7 and t2 in [5, 6]) or (t2 == 7 and t1 in [5, 6]): return True
        if (t1 >= 10 or t2 >= 10) and abs(t1 - t2) >= 2: return True
        return False
    except ValueError:
        return False

# --- ARAYÜZ (SEKMELER) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎾 Grup Ayarları", "📝 Esame ve Skor", "🏆 Puan Durumu", "📺 Misafir Ekranı", "⚙️ Yönetim Paneli"])

# SEKME 1: GRUP AYARLARI (Sadece Yönetici)
with tab1:
    if not st.session_state.admin_mi:
        st.warning("Bu sekmeyi görüntülemek için sol menüden yönetici girişi yapmalısınız.")
    else:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.header("Yeni Grup Oluştur")
            with st.form("grup_olustur_form"):
                grup_adi_input = st.text_input("Grup Adı")
                
                # İSTEK 3: Maç Formatı Seçimi
                format_secimi = st.radio("Grubun Maç Formatı", ["2 Tek, 1 Çift (3 Maçlık)", "3 Tek, 2 Çift (5 Maçlık)"])
                
                takimlar_input = st.text_area("Takım İsimleri (Her satıra bir takım)")
                submit_grup = st.form_submit_button("Grubu Kaydet")
                
                if submit_grup:
                    grup_adi = grup_adi_input.strip()
                    if not grup_adi:
                        st.error("Grup adı boş olamaz!")
                    elif grup_adi in st.session_state.data["gruplar"]:
                        # İSTEK 2: Mükerrer grup uyarısı
                        st.error("⚠️ Bu isimde bir grup zaten var! Lütfen farklı bir isim seçin.")
                    else:
                        takim_listesi = [t.strip() for t in takimlar_input.split('\n') if t.strip()]
                        if len(takim_listesi) > 1:
                            st.session_state.data["gruplar"][grup_adi] = {takim: [] for takim in takim_listesi}
                            st.session_state.data["grup_formatlari"][grup_adi] = format_secimi
                            
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
                                            "ID": f"M{mac_kodu}", "Grup": grup_adi, "Tarih": f"Gün {gun}",
                                            "Takım 1": t1, "Takım 2": t2, "Branş": brans
                                        })
                                        mac_kodu += 1
                                        
                            verileri_kaydet(st.session_state.data)
                            st.success(f"{grup_adi} oluşturuldu!")
                            st.rerun()
                        else:
                            st.error("En az 2 takım girmelisiniz.")

            st.divider()
            st.subheader("Oyuncu Ekle")
            grup_sec = st.selectbox("Grup Seç", ["Seçiniz..."] + list(st.session_state.data["gruplar"].keys()))
            if grup_sec != "Seçiniz...":
                takim_sec = st.selectbox("Takım Seç", list(st.session_state.data["gruplar"][grup_sec].keys()))
                oyuncular_input = st.text_area("Oyuncu İsimleri (Her satıra bir oyuncu)")
                if st.button("Oyuncuları Kaydet"):
                    yeni_oyuncular = [o.strip() for o in oyuncular_input.split('\n') if o.strip()]
                    st.session_state.data["gruplar"][grup_sec][takim_sec].extend(yeni_oyuncular)
                    st.session_state.data["gruplar"][grup_sec][takim_sec] = list(set(st.session_state.data["gruplar"][grup_sec][takim_sec]))
                    verileri_kaydet(st.session_state.data)
                    st.success("Oyuncular eklendi!")
                    st.rerun()

        with col2:
            # İSTEK 1: Alfabetik Sıralı Akordeon (İç İçe) Görünüm
            st.header("Mevcut Gruplar")
            if not st.session_state.data["gruplar"]:
                st.info("Kayıtlı grup yok.")
            else:
                for grup_adi in sorted(st.session_state.data["gruplar"].keys()):
                    formati = st.session_state.data["grup_formatlari"].get(grup_adi, "2 Tek, 1 Çift (3 Maçlık)")
                    with st.expander(f"📁 {grup_adi} ({formati})"):
                        for takim_adi in sorted(st.session_state.data["gruplar"][grup_adi].keys()):
                            oyuncular = st.session_state.data["gruplar"][grup_adi][takim_adi]
                            st.markdown(f"**🛡️ {takim_adi}**")
                            st.caption(", ".join(sorted(oyuncular)) if oyuncular else "Oyuncu yok")

# SEKME 2: ESAME VE SKOR (Sadece Yönetici)
with tab2:
    if not st.session_state.admin_mi:
        st.warning("Bu sekmeyi görüntülemek için sol menüden yönetici girişi yapmalısınız.")
    else:
        st.header("Esame ve Skor Girişi")
        if not st.session_state.data["program"]:
            st.info("Fikstür yok.")
        else:
            df_program = pd.DataFrame(st.session_state.data["program"])
            eslesmeler = df_program[['Grup', 'Tarih', 'Takım 1', 'Takım 2']].drop_duplicates().reset_index(drop=True)
            secenekler = [f"[{r['Grup']}] {r['Tarih']} | {r['Takım 1']} vs {r['Takım 2']}" for _, r in eslesmeler.iterrows()]
            
            secim_str = st.selectbox("Eşleşme Seç", ["Seçiniz..."] + secenekler)
            
            if secim_str != "Seçiniz...":
                idx = secenekler.index(secim_str) - 1
                seri = eslesmeler.iloc[idx]
                
                maclar = df_program[(df_program['Grup'] == seri['Grup']) & (df_program['Tarih'] == seri['Tarih']) & 
                                    (df_program['Takım 1'] == seri['Takım 1']) & (df_program['Takım 2'] == seri['Takım 2'])]
                
                st.markdown(f"### {seri['Takım 1']} - {seri['Takım 2']}")
                
                t1_kadro = ["Bilinmiyor"] + st.session_state.data["gruplar"].get(seri['Grup'], {}).get(seri['Takım 1'], [])
                t2_kadro = ["Bilinmiyor"] + st.session_state.data["gruplar"].get(seri['Grup'], {}).get(seri['Takım 2'], [])

                with st.form(f"skor_form_{seri['Tarih']}"):
                    y_skorlar, y_esameler = {}, {}
                    
                    for _, mac in maclar.iterrows():
                        m_id = mac['ID']
                        st.write(f"**{mac['Branş']}**")
                        
                        m_esame = st.session_state.data["esameler"].get(m_id, {"T1": "Bilinmiyor", "T2": "Bilinmiyor"})
                        m_skor = st.session_state.data["skorlar"].get(m_id, {"S1": "", "S2": "", "S3": "", "Kazanan": ""})
                        
                        c1, c2, c3 = st.columns([2, 3, 2])
                        with c1:
                            i1 = t1_kadro.index(m_esame["T1"]) if m_esame["T1"] in t1_kadro else 0
                            o1 = st.selectbox(f"{seri['Takım 1']}", t1_kadro, index=i1, key=f"t1_{m_id}")
                        with c2:
                            s1 = st.text_input("1. Set", m_skor.get("S1", ""), key=f"s1_{m_id}")
                            s2 = st.text_input("2. Set", m_skor.get("S2", ""), key=f"s2_{m_id}")
                            s3 = st.text_input("3. Set", m_skor.get("S3", ""), key=f"s3_{m_id}")
                        with c3:
                            i2 = t2_kadro.index(m_esame["T2"]) if m_esame["T2"] in t2_kadro else 0
                            o2 = st.selectbox(f"{seri['Takım 2']}", t2_kadro, index=i2, key=f"t2_{m_id}")

                        y_esameler[m_id] = {"T1": o1, "T2": o2}
                        
                        kazanan, t1_s, t2_s = "", 0, 0
                        for s_skor in [s1, s2, s3]:
                            if set_gecerli_mi(s_skor):
                                p1, p2 = map(int, s_skor.split('-'))
                                if p1 > p2: t1_s += 1
                                elif p2 > p1: t2_s += 1
                                
                        if t1_s >= 2: kazanan = seri['Takım 1']
                        elif t2_s >= 2: kazanan = seri['Takım 2']
                        
                        y_skorlar[m_id] = {"S1": s1, "S2": s2, "S3": s3, "Kazanan": kazanan}
                        st.divider()

                    if st.form_submit_button("Kaydet"):
                        st.session_state.data["skorlar"].update(y_skorlar)
                        st.session_state.data["esameler"].update(y_esameler)
                        verileri_kaydet(st.session_state.data)
                        st.success("Kaydedildi!")
                        st.rerun()

# SEKME 3: PUAN DURUMU (Herkese Açık)
with tab3:
    st.header("🏆 Puan Durumu")
    if st.session_state.data["program"]:
        df_p = pd.DataFrame(st.session_state.data["program"])
        df_p['Kazanan'] = df_p['ID'].apply(lambda x: st.session_state.data["skorlar"].get(x, {}).get("Kazanan", ""))
        
        df_p['T1_Match_Win'] = (df_p['Kazanan'] == df_p['Takım 1']).astype(int)
        df_p['T2_Match_Win'] = (df_p['Kazanan'] == df_p['Takım 2']).astype(int)
        
        seriler = df_p.groupby(['Grup', 'Tarih', 'Takım 1', 'Takım 2']).agg({'T1_Match_Win': 'sum', 'T2_Match_Win': 'sum'}).reset_index()
        
        # 3 veya 5 maçlık formata uyum sağlayan yeni kazanan belirleme mantığı (Çoğunluk olan kazanır)
        seriler['T1_Win'] = (seriler['T1_Match_Win'] > seriler['T2_Match_Win']).astype(int)
        seriler['T2_Win'] = (seriler['T2_Match_Win'] > seriler['T1_Match_Win']).astype(int)
        
        for g in st.session_state.data["gruplar"].keys():
            takimlar = list(st.session_state.data["gruplar"][g].keys())
            puan_tablosu = []
            
            for t in takimlar:
                t1_o = seriler[(seriler['Grup'] == g) & (seriler['Takım 1'] == t)]
                t2_o = seriler[(seriler['Grup'] == g) & (seriler['Takım 2'] == t)]
                
                g_sayisi = t1_o['T1_Win'].sum() + t2_o['T2_Win'].sum()
                oynanan = len(t1_o) + len(t2_o)
                a_mac = t1_o['T1_Match_Win'].sum() + t2_o['T2_Match_Win'].sum()
                v_mac = t1_o['T2_Match_Win'].sum() + t2_o['T1_Match_Win'].sum()
                
                puan_tablosu.append({
                    "Takım": t, "O": oynanan, "G": g_sayisi, "M": oynanan - g_sayisi,
                    "AM": a_mac, "VM": v_mac, "Averaj": a_mac - v_mac, "Puan": g_sayisi * 2
                })
                
            df_tablo = pd.DataFrame(puan_tablosu).sort_values(by=["Puan", "Averaj"], ascending=[False, False]).reset_index(drop=True)
            df_tablo.index += 1
            st.subheader(f"{g}")
            st.dataframe(df_tablo, use_container_width=True)

# SEKME 4: MİSAFİR EKRANI (Herkese Açık)
with tab4:
    st.header("📢 Fikstür ve Canlı Skorlar")
    if st.session_state.data["program"]:
        df_m = pd.DataFrame(st.session_state.data["program"])
        df_m['Skor'] = df_m['ID'].apply(lambda x: " | ".join([s for s in [st.session_state.data["skorlar"].get(x, {}).get(k, "") for k in ["S1","S2","S3"]] if s]) or "-")
        df_m['Kazanan'] = df_m['ID'].apply(lambda x: st.session_state.data["skorlar"].get(x, {}).get("Kazanan", "-"))
        st.dataframe(df_m[['Grup', 'Tarih', 'Takım 1', 'Takım 2', 'Branş', 'Skor', 'Kazanan']], use_container_width=True)

# SEKME 5: YÖNETİM PANELİ (Sadece Yönetici)
with tab5:
    if not st.session_state.admin_mi:
        st.warning("Bu sekmeyi görüntülemek için sol menüden yönetici girişi yapmalısınız.")
    else:
        st.header("⚙️ Veritabanı Düzenleyici")
        secim = st.selectbox("Düzenle", ["Gruplar", "Fikstür Programı", "Skorlar", "Esameler", "Grup Formatları"])
        map_db = {"Gruplar": "gruplar", "Fikstür Programı": "program", "Skorlar": "skorlar", "Esameler": "esameler", "Grup Formatları": "grup_formatlari"}
        v_key = map_db[secim]
        
        if isinstance(st.session_state.data[v_key], list):
            df_e = pd.DataFrame(st.session_state.data[v_key])
        else:
            df_e = pd.DataFrame([{"Anahtar": k, "Değer": v} for k, v in st.session_state.data[v_key].items()])
            
        duzenlenen = st.data_editor(df_e, use_container_width=True, num_rows="dynamic")
        
        if st.button("Değişiklikleri Uygula"):
            if isinstance(st.session_state.data[v_key], list):
                st.session_state.data[v_key] = duzenlenen.to_dict('records')
            else:
                st.session_state.data[v_key] = {row['Anahtar']: row['Değer'] for _, row in duzenlenen.iterrows()}
            verileri_kaydet(st.session_state.data)
            st.success("Güncellendi!")
            st.rerun()
