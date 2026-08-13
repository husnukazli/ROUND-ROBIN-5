import streamlit as st
import pandas as pd
import datetime
import random
import re
import time
import json
import os
import shutil
from hesaplama_motoru import dogal_sirala, sort_maclar, eslesmeleri_olustur, hesapla_tum_puan_durumu, sirala_grup_df
from veritabani_islemleri import ortak_veriyi_kaydet, supabase, BELGELER_KLASORU

def esame_kontrol_merkezi_ciz():
    if st.session_state.admin_mi:
        st.info("ℹ️ Kaptanların veya Hakemlerin girdikleri kadrolar burada toplanır. Geçmiş veya gelecek tüm esameleri tarih seçerek inceleyebilirsin.")
        
        tum_tarihler = st.session_state.mac_programi['Tarih'].dropna().unique().tolist()
        
        if not tum_tarihler:
            st.warning("Henüz maç programında tarihli bir maç bulunmuyor.")
        else:
            bugun = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime("%d.%m.%Y")
            try:
                varsayilan_index = tum_tarihler.index(bugun)
            except ValueError:
                varsayilan_index = len(tum_tarihler) - 1 
            
            secilen_tarih = st.selectbox("📅 Görüntülenecek Tarihi Seçin (Arşiv):", tum_tarihler, index=varsayilan_index)
            st.divider()
            
            df_secilen_gun = st.session_state.mac_programi[st.session_state.mac_programi['Tarih'] == secilen_tarih]
            
            if df_secilen_gun.empty:
                st.success(f"{secilen_tarih} tarihi için planlanmış maç bulunmuyor.")
            else:
                for (grup, gun, eslesme), match_df in df_secilen_gun.groupby(['Grup', 'Gün', 'Eşleşme']):
                    t1 = match_df.iloc[0]['Takım 1']
                    t2 = match_df.iloc[0]['Takım 2']
                    kort = match_df.iloc[0]['Kort']
                    saat = match_df.iloc[0]['Maç Saati']
                    
                    match_key = f"{grup}_{gun}_{eslesme}"
                    is_approved = st.session_state.esame_onayli.get(match_key, False)
                    kasadaki_veri = st.session_state.esame_kasasi.get(match_key, {})
                    
                    t1_girdi = t1 in kasadaki_veri
                    t2_girdi = t2 in kasadaki_veri
                    
                    kaynak_t1 = kasadaki_veri.get(t1, {}).get("_kaynak", "Kaptan") if t1_girdi else ""
                    kaynak_t2 = kasadaki_veri.get(t2, {}).get("_kaynak", "Kaptan") if t2_girdi else ""
                    
                    durum_ikon_t1 = f"✅ Teslim Etti ({kaynak_t1})" if t1_girdi else "❌ Bekleniyor"
                    durum_ikon_t2 = f"✅ Teslim Etti ({kaynak_t2})" if t2_girdi else "❌ Bekleniyor"
                    
                    with st.expander(f"{saat} | {kort} | {grup} | {t1} ({durum_ikon_t1})  VS  {t2} ({durum_ikon_t2})", expanded=False):
                        if is_approved:
                            st.success(f"Bu esameler onaylanmış ve {secilen_tarih} tarihli Maç Programına yansıtılmıştır.")
                            if kaynak_t1 == "Hakem" or kaynak_t2 == "Hakem":
                                st.warning("⚠️ Bu kadrolardan biri veya ikisi Gözlemci Hakem tarafından girilmiştir.")
                            elif kaynak_t1 == "Başhakem" or kaynak_t2 == "Başhakem":
                                st.info("👑 Bu kadrolar Başhakem tarafından doğrudan sisteme işlenmiştir.")
                            
                            if st.button("🔓 Kilidi Aç ve Kadroları Yeniden Düzenle", key=f"kilit_ac_{match_key}"):
                                st.session_state.esame_onayli[match_key] = False
                                st.rerun()
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown(f"**🛡️ {t1} Kadrosu**")
                            if t1_girdi:
                                if kaynak_t1 == "Hakem": st.caption("*(Hakem Tarafından Girildi)*")
                                elif kaynak_t1 == "Başhakem": st.caption("*(Başhakem Tarafından Girildi)*")
                                for k, v in kasadaki_veri[t1].items(): 
                                    if k != "_kaynak": st.write(f"- {k}: **{v}**")
                            else: st.warning("Henüz giriş yapılmadı.")
                        with c2:
                            st.markdown(f"**🛡️ {t2} Kadrosu**")
                            if t2_girdi:
                                if kaynak_t2 == "Hakem": st.caption("*(Hakem Tarafından Girildi)*")
                                elif kaynak_t2 == "Başhakem": st.caption("*(Başhakem Tarafından Girildi)*")
                                for k, v in kasadaki_veri[t2].items(): 
                                    if k != "_kaynak": st.write(f"- {k}: **{v}**")
                            else: st.warning("Henüz giriş yapılmadı.")
                            
                        if not is_approved:
                            if kaynak_t1 == "Hakem" or kaynak_t2 == "Hakem":
                                st.error("⚠️ Bu esame bilgileri hakem tarafından girilmiştir.")
                            elif kaynak_t1 == "Başhakem" or kaynak_t2 == "Başhakem":
                                st.info("👑 Bu esame bilgileri Başhakem olarak sizin tarafınızdan girilmiştir.")
                                
                            st.markdown("---")
                            st.markdown("#### 👑 Başhakem Kadro Girişi / Düzenleme")
                            st.caption("Kaptanlardan veya hakemden beklemek yerine, kadroları doğrudan siz belirleyebilirsiniz. (Çiftleri boş bırakabilirsiniz)")
                            
                            grup_kadrolari = st.session_state.takim_kadrolari.get(grup, {})
                            t1_havuz = grup_kadrolari.get(t1, ["Belirtilmedi"])
                            t2_havuz = grup_kadrolari.get(t2, ["Belirtilmedi"])
                            
                            with st.form(key=f"form_admin_{match_key}"):
                                c_f1, c_f2 = st.columns(2)
                                form_t1 = {}
                                form_t2 = {}
                                
                                with c_f1:
                                    st.markdown(f"**{t1}**")
                                    for idx_mp_e, row_mp_e in sort_maclar(match_df).iterrows():
                                        brans = row_mp_e['Branş']
                                        eski_val = kasadaki_veri.get(t1, {}).get(brans, "")
                                        if "Çiftler" in brans:
                                            eski_liste = [o.strip() for o in eski_val.split(",") if o.strip() in t1_havuz]
                                            sec_t1 = st.multiselect(f"{brans}", options=t1_havuz, default=eski_liste, max_selections=2, key=f"adm_ms_t1_{match_key}_{brans}")
                                            form_t1[brans] = ", ".join(sec_t1)
                                        else:
                                            idx_def = (["Seçiniz"] + t1_havuz).index(eski_val) if eski_val in t1_havuz else 0
                                            sec_t1 = st.selectbox(f"{brans}", options=["Seçiniz"] + t1_havuz, index=idx_def, key=f"adm_sb_t1_{match_key}_{brans}")
                                            form_t1[brans] = sec_t1 if sec_t1 != "Seçiniz" else ""
                                
                                with c_f2:
                                    st.markdown(f"**{t2}**")
                                    for idx_mp_e, row_mp_e in sort_maclar(match_df).iterrows():
                                        brans = row_mp_e['Branş']
                                        eski_val = kasadaki_veri.get(t2, {}).get(brans, "")
                                        if "Çiftler" in brans:
                                            eski_liste = [o.strip() for o in eski_val.split(",") if o.strip() in t2_havuz]
                                            sec_t2 = st.multiselect(f"{brans}", options=t2_havuz, default=eski_liste, max_selections=2, key=f"adm_ms_t2_{match_key}_{brans}")
                                            form_t2[brans] = ", ".join(sec_t2)
                                        else:
                                            idx_def = (["Seçiniz"] + t2_havuz).index(eski_val) if eski_val in t2_havuz else 0
                                            sec_t2 = st.selectbox(f"{brans}", options=["Seçiniz"] + t2_havuz, index=idx_def, key=f"adm_sb_t2_{match_key}_{brans}")
                                            form_t2[brans] = sec_t2 if sec_t2 != "Seçiniz" else ""
                                
                                if st.form_submit_button("💾 Kadroları Başhakem Olarak Kaydet (Zarfa Koy)", use_container_width=True):
                                    hatalar = []
                                    format_sec = st.session_state.grup_formatlari.get(grup, "3 Maçlık (2 Tek, 1 Çift)")
                                    
                                    for t_adi, f_data, havuz in [(t1, form_t1, t1_havuz), (t2, form_t2, t2_havuz)]:
                                        o1 = f_data.get("1. Tekler")
                                        o2 = f_data.get("2. Tekler")
                                        o3 = f_data.get("3. Tekler")
                                        r1 = havuz.index(o1) if o1 in havuz else -1
                                        r2 = havuz.index(o2) if o2 in havuz else -1
                                        r3 = havuz.index(o3) if o3 in havuz else -1

                                        for b in ["1. Çiftler", "2. Çiftler", "Çiftler"]:
                                            c_str = f_data.get(b, "")
                                            if c_str:
                                                c_list = [o.strip() for o in c_str.split(",") if o.strip()]
                                                if len(c_list) == 1: hatalar.append(f"❌ {t_adi}: {b} maçına tek oyuncu yazılamaz. Boş bırakabilirsiniz.")

                                        if r1 != -1 and r2 != -1 and r1 >= r2: hatalar.append(f"❌ {t_adi}: 1. Tekler oyuncusu, 2. Teklerden üst sırada olmalıdır.")
                                        if r2 != -1 and r3 != -1 and r2 >= r3: hatalar.append(f"❌ {t_adi}: 2. Tekler oyuncusu, 3. Teklerden üst sırada olmalıdır.")
                                        if r1 != -1 and r3 != -1 and r2 == -1 and r1 >= r3: hatalar.append(f"❌ {t_adi}: 1. Tekler oyuncusu, 3. Teklerden üst sırada olmalıdır.")

                                        if o1 and o1 != "Seçiniz" and o1 == o2: hatalar.append(f"❌ {t_adi}: Aynı oyuncu birden fazla tekler maçına yazılamaz.")
                                        if o2 and o2 != "Seçiniz" and o2 == o3: hatalar.append(f"❌ {t_adi}: Aynı oyuncu birden fazla tekler maçına yazılamaz.")
                                        if o1 and o1 != "Seçiniz" and o1 == o3: hatalar.append(f"❌ {t_adi}: Aynı oyuncu birden fazla tekler maçına yazılamaz.")

                                        if "5 Maçlık" in format_sec:
                                            c1_list = [o.strip() for o in f_data.get("1. Çiftler", "").split(",") if o.strip()]
                                            c2_list = [o.strip() for o in f_data.get("2. Çiftler", "").split(",") if o.strip()]
                                            ortak = set(c1_list).intersection(set(c2_list))
                                            if ortak: hatalar.append(f"❌ {t_adi}: Aynı oyuncu iki çiftler maçına da yazılamaz.")

                                            if len(c1_list) == 2 and len(c2_list) == 2 and not ortak:
                                                dortlu = sorted([(p, havuz.index(p)) for p in c1_list + c2_list if p in havuz], key=lambda x: x[1])
                                                yeni_rank = {p: i+1 for i, (p, _) in enumerate(dortlu)}
                                                t_c1 = yeni_rank.get(c1_list[0], 99) + yeni_rank.get(c1_list[1], 99)
                                                t_c2 = yeni_rank.get(c2_list[0], 99) + yeni_rank.get(c2_list[1], 99)
                                                if t_c1 > t_c2: hatalar.append(f"❌ {t_adi}: 1. Çiftler, 2. Çiftlerden daha güçlü (veya eşit) olmalıdır.")

                                    if hatalar:
                                        for h in hatalar: st.error(h)
                                    else:
                                        if match_key not in st.session_state.esame_kasasi:
                                            st.session_state.esame_kasasi[match_key] = {}
                                        
                                        form_t1["_kaynak"] = "Başhakem"
                                        form_t2["_kaynak"] = "Başhakem"
                                        
                                        st.session_state.esame_kasasi[match_key][t1] = form_t1
                                        st.session_state.esame_kasasi[match_key][t2] = form_t2
                                        
                                        if ortak_veriyi_kaydet():
                                            st.success("Kadrolar başarıyla kaydedildi! Şimdi aşağıdan Onaylayarak maç programına yansıtabilirsiniz.")
                                            st.rerun()
                                        else:
                                            st.error("Sistem meşgul, lütfen tekrar deneyin.")

                            st.markdown("---")
                            if st.button("📢 Esameleri Onayla ve Maç Programına Yansıt (Zarfları Aç)", key=f"onay_{match_key}", type="primary"):
                                st.session_state.esame_onayli[match_key] = True
                                
                                skor_mask = (st.session_state.skor_tablosu['Grup'] == grup) & (st.session_state.skor_tablosu['Gün'] == gun) & (st.session_state.skor_tablosu['Eşleşme'] == eslesme)
                                for idx, row in st.session_state.skor_tablosu[skor_mask].iterrows():
                                    brans = row['Branş']
                                    if t1_girdi: st.session_state.skor_tablosu.at[idx, 'T1_Oyuncu'] = kasadaki_veri[t1].get(brans, "")
                                    if t2_girdi: st.session_state.skor_tablosu.at[idx, 'T2_Oyuncu'] = kasadaki_veri[t2].get(brans, "")
                                
                                if ortak_veriyi_kaydet():
                                    st.success("Esameler başarıyla açıldı ve Skor Girişi ile Maç Programı sayfalarına gönderildi!")
                                    st.rerun()
                                else:
                                    st.error("⚠️ Sistem şu an meşgul. Çakışma önlendi, lütfen tekrar deneyin.")

def grup_ayarlari_ciz(aktif_asama):
    yas_secenekleri = ["Yaş Belirtme"] + [f"{i}+" for i in range(30, 85, 5)]
    
    if st.session_state.admin_mi:
        if aktif_asama == "1. Aşama":
            with st.expander("📥 Akıllı Havuz: Excel / CSV'den Takım Yükle", expanded=False):
                st.info("ℹ️ Excel dosyanızın düzenini seçin ve yükleyin. Seçtiğiniz yaş ve kategori etiketleriyle sisteme işlenecektir.")
                
                c_up1, c_up2 = st.columns(2)
                with c_up1: up_yas = st.selectbox("Yüklenecek Dosyanın Yaş Grubu:", yas_secenekleri, key="up_yas")
                with c_up2: up_kat = st.radio("Yüklenecek Dosyanın Kategorisi:", ["Erkekler", "Kadınlar"], horizontal=True, key="up_kat")
                
                dosya_duzeni = st.radio("Excel/CSV İçindeki Dosya Düzeni (Çok Önemli):", [
                    "⬇️ Sütunlarda (1. Satır Takım Adı, Altındaki Satırlar Oyuncular)", 
                    "➡️ Satırlarda (1. Sütun Takım Adı, Yanındaki Sütunlar Oyuncular)"
                ])
                
                uploaded_file = st.file_uploader("Takım listesini yükleyin (.xlsx veya .csv)", type=["csv", "xlsx"])
                if uploaded_file:
                    try:
                        if uploaded_file.name.endswith('.csv'):
                            df_havuz = pd.read_csv(uploaded_file, sep=None, engine='python', header=None, dtype=str)
                        else: 
                            df_havuz = pd.read_excel(uploaded_file, header=None, dtype=str)
                        
                        if "Satırlarda" in dosya_duzeni:
                            df_havuz = df_havuz.set_index(0).T
                        else:
                            df_havuz.columns = df_havuz.iloc[0]
                            df_havuz = df_havuz[1:]
                        
                        yeni_havuz = {}
                        for col in df_havuz.columns:
                            t_adi = str(col).strip()
                            if t_adi and t_adi.lower() != 'nan' and "unnamed" not in t_adi.lower() and "takım adı" not in t_adi.lower() and "takim adi" not in t_adi.lower():
                                oyuncular = df_havuz[col].dropna().astype(str).tolist()
                                temiz_oyuncular = [o.strip() for o in oyuncular if o.strip() and o.strip().lower() != 'nan']
                                
                                if temiz_oyuncular:
                                    yeni_havuz[t_adi] = temiz_oyuncular
                        
                        st.markdown("#### 👀 Sisteme Kaydedilecek Dosya Önizlemesi")
                        preview_df = pd.DataFrame([{"Takım Adı": k, "Sistemin Okuduğu Kadro": ", ".join(v)} for k, v in yeni_havuz.items()])
                        st.dataframe(preview_df, use_container_width=True)
                        
                        st.warning("⚠️ **Lütfen Dikkat:** Yukarıdaki listeyi kontrol edin. Her şey doğruysa aşağıdaki 'Havuza Kaydet' butonuna basın. Dosyayı yüklemiş olmanız henüz kaydedildiği anlamına gelmez!")
                        
                        if st.button("✅ Önizlemeyi Onayla ve Havuza Kaydet", type="primary"):
                            for t_adi, temiz_oyuncular in yeni_havuz.items():
                                if up_yas != "Yaş Belirtme":
                                    benzersiz_t_adi = f"{t_adi.strip()} ({up_yas} {up_kat})"
                                else:
                                    benzersiz_t_adi = f"{t_adi.strip()} ({up_kat})"
                                    
                                st.session_state.havuz_kategorileri[benzersiz_t_adi] = up_kat
                                st.session_state.havuz_yas_gruplari[benzersiz_t_adi] = up_yas
                                st.session_state.takim_havuzu[benzersiz_t_adi] = temiz_oyuncular
                            
                            if ortak_veriyi_kaydet():
                                st.success(f"✅ Başarılı! Takımlar '{up_yas} {up_kat}' etiketiyle sisteme güvenle kaydedildi.")
                            else:
                                st.error("Sistem meşgul, lütfen tekrar deneyin.")
                            
                    except Exception as e:
                        st.error(f"Dosya okuma hatası: {e}. Lütfen formatın doğru olduğundan emin olun.")
                
                if st.session_state.takim_havuzu:
                    st.write(f"📊 Sistemde şu an **{len(st.session_state.takim_havuzu)}** hazır takım bulunuyor.")
                    
                    with st.expander("👀 Havuzdaki Takımları Gör ve Yönet", expanded=False):
                        for t_isim, oyuncular in list(st.session_state.takim_havuzu.items()):
                            kategori = st.session_state.havuz_kategorileri.get(t_isim, "Bilinmiyor")
                            yas = st.session_state.havuz_yas_gruplari.get(t_isim, "Bilinmiyor")
                            
                            c1, c2 = st.columns([4, 1])
                            with c1:
                                st.markdown(f"**🛡️ {t_isim}** *(Kategori: {kategori} | Yaş: {yas})*")
                                st.caption(", ".join(oyuncular))
                            with c2:
                                if st.button("❌ Sil", key=f"del_havuz_{t_isim}"):
                                    del st.session_state.takim_havuzu[t_isim]
                                    if t_isim in st.session_state.havuz_kategorileri: del st.session_state.havuz_kategorileri[t_isim]
                                    if t_isim in st.session_state.havuz_yas_gruplari: del st.session_state.havuz_yas_gruplari[t_isim]
                                    ortak_veriyi_kaydet()
                                    st.rerun()
                        st.markdown("<hr style='margin: 5px 0px;'>", unsafe_allow_html=True)
                        
                    if st.button("🗑️ Tüm Takım Havuzunu Komple Temizle"):
                        st.session_state.takim_havuzu = {}
                        st.session_state.havuz_kategorileri = {}
                        st.session_state.havuz_yas_gruplari = {}
                        ortak_veriyi_kaydet()
                        st.rerun()
            st.markdown("---")
        
        col_y, col_t1, col_t2, col_t3 = st.columns(4)
        
        with col_y:
            yas_secimi = st.selectbox("Yaş Grubu:", yas_secenekleri)
        with col_t1:
            kategori_secimi = st.radio("Kategori:", ["Erkekler", "Kadınlar"], horizontal=True)
        with col_t2:
            if aktif_asama == "1. Aşama":
                grup_tipi_liste = ["3'lü Grup", "4'lü Grup", "5'li Grup", "6'lı Grup"]
            else:
                grup_tipi_liste = ["2'li Grup", "3'lü Grup", "4'lü Grup"]
            grup_tipi = st.radio("Grup Tipi:", grup_tipi_liste, horizontal=True)
        with col_t3:
            format_secimi = st.radio("Müsabaka Maç Formatı:", ["3 Maçlık (2 Tek, 1 Çift)", "5 Maçlık (3 Tek, 2 Çift)"], horizontal=True)
        
        grup_adi_raw = st.text_input("Grup Özel Adı (Örn: A Grubu, 1. Grup, Şampiyonluk Grubu):", placeholder="Sadece grubun harfini veya numarasını yazın")
        grup_statusu = "Play-out Grubu (Düşme Hattı)"
        if aktif_asama == "2. Aşama":
            grup_statusu = st.radio("🏅 Grup Statüsü:", ["Birinciler Grubu (Kürsü)", "İkinciler Grubu (Orta Klasman)", "Play-out Grubu (Düşme Hattı)"], horizontal=True, index=2, key="yeni_grup_statu")
        if yas_secimi != "Yaş Belirtme":
            tam_grup_adi = f"{yas_secimi} {kategori_secimi} {grup_adi_raw.strip()}".strip()
        else:
            tam_grup_adi = f"{kategori_secimi} {grup_adi_raw.strip()}".strip()
        
        if grup_adi_raw.strip() != "":
            st.markdown(f"<div style='margin-top:-10px; margin-bottom:15px; font-size:14px; color:#555;'>📌 <b>Oluşacak Tam Grup Adı:</b> <span style='color:#000;'>{tam_grup_adi}</span></div>", unsafe_allow_html=True)
            
        grup_adi_temiz = tam_grup_adi
        
        havuz_isimleri = ["✏️ Yeni / Listede Olmayan Takım (Elle Gir)"]
        baska_gruplardaki_takimlar = {}

        if aktif_asama == "1. Aşama":
            for g_n, g_k in st.session_state.takim_kadrolari.items():
                g_kat = st.session_state.grup_kategorileri.get(g_n, "Erkekler")
                g_asam = st.session_state.grup_asamalari.get(g_n, "1. Aşama")
                g_yas = st.session_state.grup_yas_gruplari.get(g_n, "Yaş Belirtme")
                
                if g_n != grup_adi_temiz and g_kat == kategori_secimi and g_yas == yas_secimi and g_asam == "1. Aşama":
                    for t_n in g_k.keys(): baska_gruplardaki_takimlar[t_n] = g_n
                    
            musait_havuz = dogal_sirala([
                t for t in st.session_state.takim_havuzu.keys() 
                if t not in baska_gruplardaki_takimlar
                and st.session_state.havuz_kategorileri.get(t, "Erkekler") == kategori_secimi
                and st.session_state.havuz_yas_gruplari.get(t, "Yaş Belirtme") == yas_secimi
            ])
            havuz_isimleri += musait_havuz
        else:
            for g_n, g_k in st.session_state.takim_kadrolari.items():
                g_kat = st.session_state.grup_kategorileri.get(g_n, "Erkekler")
                g_asam = st.session_state.grup_asamalari.get(g_n, "1. Aşama")
                g_yas = st.session_state.grup_yas_gruplari.get(g_n, "Yaş Belirtme")
                
                if g_n != grup_adi_temiz and g_kat == kategori_secimi and g_yas == yas_secimi and g_asam == "2. Aşama":
                    for t_n in g_k.keys(): baska_gruplardaki_takimlar[t_n] = g_n
            
            stage1_gruplar = []
            for g in st.session_state.takim_kadrolari.keys():
                k = st.session_state.grup_kategorileri.get(g, "Erkekler")
                a = st.session_state.grup_asamalari.get(g, "1. Aşama")
                y = st.session_state.grup_yas_gruplari.get(g, "Yaş Belirtme")
                
                if k == kategori_secimi and y == yas_secimi and a == "1. Aşama":
                    stage1_gruplar.append(g)
                    
            df_s1 = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'].isin(stage1_gruplar)]
            stats_s1 = hesapla_tum_puan_durumu(df_s1)
            
            stage2_havuz = []
            if not stats_s1.empty:
                for gp in dogal_sirala(list(stats_s1['Grup'].unique())):
                    if st.session_state.grup_tamamlandi.get(gp, False):
                        grup_df = stats_s1[stats_s1['Grup'] == gp].copy()
                        grup_df = sirala_grup_df(grup_df, gp) 
                        for sira, row in grup_df.iterrows():
                            takim = row['Takım']
                            if takim not in baska_gruplardaki_takimlar:
                                stage2_havuz.append(f"{takim} [{gp} {sira}.si]")
            havuz_isimleri += stage2_havuz
            
            if not stage2_havuz:
                st.info(f"ℹ️ 2. Aşama havuzu şu an boş. Bunun sebebi 1. Aşama'da '{yas_secimi} {kategori_secimi}' için 'Maçları Tamamlandı' olarak kilitlenmiş hiçbir grup olmamasıdır.")
        
        if grup_tipi == "2'li Grup": beklenen_sayi = 2
        elif grup_tipi == "3'lü Grup": beklenen_sayi = 3
        elif grup_tipi == "4'lü Grup": beklenen_sayi = 4
        elif grup_tipi == "5'li Grup": beklenen_sayi = 5
        else: beklenen_sayi = 6
        
        st.markdown(f"### 🛡️ Takım ve Kadro Seçimi ({beklenen_sayi} Takım)")
        takimlar = []; grup_kadrolari = {}; kadro_hata = False
        
        cols = st.columns(beklenen_sayi if beklenen_sayi < 5 else 4)
        for i in range(beklenen_sayi):
            with cols[i % len(cols)]:
                st.markdown(f"**{i+1}. Takım**")
                secim = st.selectbox(f"{i+1}. Takım Seçimi", options=havuz_isimleri, key=f"sec_takim_{i}", label_visibility="collapsed")
                
                if secim == "✏️ Yeni / Listede Olmayan Takım (Elle Gir)":
                    raw_isim = st.text_input("Takım Adı:", key=f"isim_t_{i}", placeholder="Örn: Atik 1")
                    if raw_isim.strip():
                        if yas_secimi != "Yaş Belirtme":
                            t_isim = f"{raw_isim.strip()} ({yas_secimi} {kategori_secimi})"
                        else:
                            t_isim = f"{raw_isim.strip()} ({kategori_secimi})"
                    else:
                        t_isim = ""
                    def_kadro = ""
                elif aktif_asama == "2. Aşama":
                    match = re.search(r'(.*?) \[(.*?)\]$', secim)
                    if match:
                        t_isim = match.group(1).strip()
                        def_kadro = ""
                        for g_n, g_k in st.session_state.takim_kadrolari.items():
                            if st.session_state.grup_asamalari.get(g_n, "1. Aşama") == "1. Aşama" and t_isim in g_k:
                                def_kadro = "\n".join(g_k[t_isim])
                                break
                    else:
                        t_isim = secim; def_kadro = ""
                else:
                    t_isim = secim
                    def_kadro = "\n".join(st.session_state.takim_havuzu.get(secim, []))
                
                oyuncular_raw = st.text_area(f"✍️ Kadro (Her satıra bir kişi)", value=def_kadro, key=f"input_kadro_{i}_{secim}", height=150)
                oyuncu_listesi = [o.strip() for o in oyuncular_raw.split('\n') if o.strip()]
                if len(oyuncu_listesi) > 10:
                    st.error("Maksimum 10 oyuncu sınırı aşıldı!")
                    kadro_hata = True
                if t_isim:
                    takimlar.append(t_isim)
                    grup_kadrolari[t_isim] = oyuncu_listesi if oyuncu_listesi else ["Belirtilmedi"]

        if st.button("🚀 Grubu Oluştur ve Kadroları Kaydet"):
            cakisan_takimlar = [t for t in takimlar if t in baska_gruplardaki_takimlar]
            if cakisan_takimlar:
                hata_detay = ", ".join([f"'{t}' ({baska_gruplardaki_takimlar[t]})" for t in cakisan_takimlar])
                st.error(f"⚠️ Hata: Girdiğiniz takım(lar) {yas_secimi} {kategori_secimi} kategorisinde ({aktif_asama}) zaten kayıtlı!\nÇakışanlar: {hata_detay}")
            elif not grup_adi_raw or len(takimlar) != beklenen_sayi or kadro_hata or len(set(takimlar)) != beklenen_sayi:
                st.error("Lütfen grup özel adını girin, tüm takımları eksiksiz/farklı doldurun ve kurallara uyun.")
            else:
                for t_n, o_list in grup_kadrolari.items():
                    if t_n not in st.session_state.takim_havuzu:
                        st.session_state.takim_havuzu[t_n] = o_list
                        st.session_state.havuz_kategorileri[t_n] = kategori_secimi
                        st.session_state.havuz_yas_gruplari[t_n] = yas_secimi
                
                st.session_state.takim_kadrolari[grup_adi_temiz] = grup_kadrolari
                st.session_state.grup_formatlari[grup_adi_temiz] = format_secimi
                st.session_state.grup_kategorileri[grup_adi_temiz] = kategori_secimi
                st.session_state.grup_asamalari[grup_adi_temiz] = aktif_asama
                st.session_state.grup_yas_gruplari[grup_adi_temiz] = yas_secimi
                st.session_state.grup_statuleri[grup_adi_temiz] = grup_statusu
                
                if not st.session_state.skor_tablosu.empty and grup_adi_temiz in st.session_state.skor_tablosu['Grup'].unique():
                    if ortak_veriyi_kaydet():
                        st.success("Mevcut grup bulundu! Kadrolar başarıyla güncellendi, eski fikstür korundu.")
                    else:
                        st.error("Sistem meşgul, lütfen tekrar deneyin.")
                else:
                    yeni_df = pd.DataFrame(eslesmeleri_olustur(grup_adi_temiz, takimlar, grup_tipi, format_secimi))
                    if st.session_state.skor_tablosu.empty: st.session_state.skor_tablosu = yeni_df
                    else: st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
                    if ortak_veriyi_kaydet():
                        st.success(f"{aktif_asama} grubu başarıyla oluşturuldu! Şimdi aşağıdan tarih atamasını yapabilirsiniz.")
                    else:
                        st.error("Sistem meşgul, lütfen tekrar deneyin.")
                
        st.markdown("---")
        st.markdown("### 🗓️ Grup Gün-Tarih Eşleştirmesi (Fikstür Takvimi)")
        st.info("Grupların fikstüründeki '1. Gün', '2. Gün' gibi aşamaları gerçek takvim günleriyle eşleştirip, maçları gizli olarak Maç Programı sayfasına fırlatabilirsiniz.")
        
        if not st.session_state.skor_tablosu.empty:
            t_gruplar_takvim = dogal_sirala([g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
            if t_gruplar_takvim:
                kategori_grup_map = {}
                for g in t_gruplar_takvim:
                    yas = st.session_state.grup_yas_gruplari.get(g, "Yaş Belirtme")
                    kat = st.session_state.grup_kategorileri.get(g, "Erkekler")
                    k_adi = f"{yas} {kat}" if yas != "Yaş Belirtme" else kat
                    if k_adi not in kategori_grup_map:
                        kategori_grup_map[k_adi] = []
                    kategori_grup_map[k_adi].append(g)
                
                kategoriler = dogal_sirala(list(kategori_grup_map.keys()))
                
                c_sel1, c_sel2 = st.columns(2)
                with c_sel1:
                    sec_kat = st.selectbox("1) Kategori Seçin:", ["Seçiniz"] + kategoriler, key="takvim_kat_sec")
                
                if sec_kat != "Seçiniz":
                    gruplar = dogal_sirala(kategori_grup_map[sec_kat])
                    with c_sel2:
                        sec_grup = st.selectbox("2) Grup Seçimi:", ["Tüm Gruplar (Toplu Atama)"] + gruplar, key="takvim_grup_sec")
                    
                    hedef_gruplar = gruplar if sec_grup == "Tüm Gruplar (Toplu Atama)" else [sec_grup]
                    
                    df_hedef = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'].isin(hedef_gruplar)]
                    gunler = dogal_sirala(df_hedef['Gün'].unique().tolist())
                    
                    mevcut_takvim = st.session_state.grup_gun_takvimi.get(hedef_gruplar[0], {})
                    yeni_takvim = {}
                    
                    st.write(f"**{sec_kat} - {sec_grup} Takvimi:**")
                    
                    if mevcut_takvim:
                        st.warning("⚠️ DİKKAT: Seçilen grupların bazılarında önceden tarih atanmış! Aşağıdan yeni tarih kaydederseniz eski program güncellenir ve maçlar yeni tarihlere taşınır.")
                        
                    c1, c2 = st.columns(2)
                    for i, gun in enumerate(gunler):
                        eski_tarih_str = mevcut_takvim.get(gun, "")
                        if eski_tarih_str:
                            try: default_date = datetime.datetime.strptime(eski_tarih_str, "%d.%m.%Y").date()
                            except: default_date = datetime.date.today()
                        else:
                            default_date = datetime.date.today()
                            
                        with c1 if i % 2 == 0 else c2:
                            sec_tarih = st.date_input(f"📅 {gun} Tarihi:", value=default_date, key=f"dt_{sec_kat}_{i}")
                            yeni_takvim[gun] = sec_tarih.strftime("%d.%m.%Y")
                            
                    st.write("")
                    c_btn1, c_btn2 = st.columns(2)
                    if c_btn1.button("💾 Tarihleri Kaydet ve Programı Güncelle", type="primary", use_container_width=True):
                        turkce_gunler = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
                        yeni_kayitlar = []
                        
                        for h_grup in hedef_gruplar:
                            st.session_state.grup_gun_takvimi[h_grup] = yeni_takvim.copy()
                            df_grup_takvim = df_hedef[df_hedef['Grup'] == h_grup]
                            
                            for gun_val in gunler:
                                if gun_val not in df_grup_takvim['Gün'].values:
                                    continue
                                    
                                tarih_str = yeni_takvim[gun_val]
                                tarih_obj = datetime.datetime.strptime(tarih_str, "%d.%m.%Y").date()
                                gun_adi = turkce_gunler[tarih_obj.weekday()]
                                
                                mask_grup_gun = (st.session_state.mac_programi['Grup'] == h_grup) & (st.session_state.mac_programi['Gün'] == gun_val)
                                
                                if mask_grup_gun.any():
                                    st.session_state.mac_programi.loc[mask_grup_gun, 'Tarih'] = tarih_str
                                    st.session_state.mac_programi.loc[mask_grup_gun, 'Gün Adı'] = gun_adi
                                
                                df_gunluk_skor = df_grup_takvim[df_grup_takvim['Gün'] == gun_val]
                                for _, row in df_gunluk_skor.iterrows():
                                    mask_bireysel_mac = mask_grup_gun & (st.session_state.mac_programi['Branş'] == row['Branş']) & (st.session_state.mac_programi['Eşleşme'] == row['Eşleşme'])
                                    if not mask_bireysel_mac.any():
                                        yeni_kayitlar.append({
                                            "Maç Saati": "10:00", "Tarih": tarih_str, "Gün Adı": gun_adi, "Kort": "Kort 1",
                                            "Grup": row['Grup'], "Gün": row['Gün'], "Branş": row['Branş'], "Eşleşme": row['Eşleşme'],
                                            "Takım 1": row['Takım 1'], "Takım 2": row['Takım 2'], "T1 Oyuncu": "", "T2 Oyuncu": "", "Skor": "Oynanmadı", "Kazanan": "", "Hakem": "Atanmadı"
                                        })
                        
                        if yeni_kayitlar:
                            st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, pd.DataFrame(yeni_kayitlar)], ignore_index=True)
                            
                        if ortak_veriyi_kaydet():
                            st.success(f"✅ Tarihler başarıyla atandı ve seçili grupların programı güncellendi!")
                            time.sleep(1.5)
                            st.rerun()
                            
                    if c_btn2.button("🗑️ Seçili Grupların Takvimini Sil", use_container_width=True):
                        for h_grup in hedef_gruplar:
                            if h_grup in st.session_state.grup_gun_takvimi:
                                del st.session_state.grup_gun_takvimi[h_grup]
                        st.session_state.mac_programi = st.session_state.mac_programi[~st.session_state.mac_programi['Grup'].isin(hedef_gruplar)].reset_index(drop=True)
                        if ortak_veriyi_kaydet():
                            st.success("✅ Seçilen grupların fikstürü takvimden silindi!")
                            time.sleep(1.5)
                            st.rerun()
                
        if st.session_state.takim_kadrolari:
            st.markdown("---")
            st.markdown(f"### 📁 Mevcut Kayıtlı Gruplar ve Kadrolar ({aktif_asama})")
            gosterilecek_gruplar_klasor = dogal_sirala([g for g in st.session_state.takim_kadrolari.keys() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
            
            kategori_dict = {}
            for g_isim in gosterilecek_gruplar_klasor:
                f_kat = st.session_state.grup_kategorileri.get(g_isim, "Erkekler")
                f_yas = st.session_state.grup_yas_gruplari.get(g_isim, "Yaş Belirtme")
                kategori_anahtari = f"{f_yas} {f_kat}" if f_yas != "Yaş Belirtme" else f_kat
                
                if kategori_anahtari not in kategori_dict:
                    kategori_dict[kategori_anahtari] = []
                kategori_dict[kategori_anahtari].append(g_isim)
                
            for kat_adi in dogal_sirala(list(kategori_dict.keys())):
                kategori_tarihleri = set()
                for g_isim in kategori_dict[kat_adi]:
                    grup_takvimi = st.session_state.grup_gun_takvimi.get(g_isim, {})
                    for tarih_str in grup_takvimi.values():
                        if tarih_str:
                            kategori_tarihleri.add(tarih_str)
                            
                if kategori_tarihleri:
                    sirali_tarihler = sorted(list(kategori_tarihleri), key=lambda x: datetime.datetime.strptime(x, "%d.%m.%Y"))
                    tarih_metni = f"📅 {', '.join(sirali_tarihler)}"
                else:
                    tarih_metni = "⚠️ Tarih Belirlenmedi!"
                
                expander_baslik = f"📂 {kat_adi} Kategorisi ({len(kategori_dict[kat_adi])} Grup) | {tarih_metni}"
                
                with st.expander(expander_baslik):
                    for g_isim in dogal_sirala(kategori_dict[kat_adi]):
                        f_turu = st.session_state.grup_formatlari.get(g_isim, "3 Maçlık (2 Tek, 1 Çift)")
                        
                        grup_takvimi = st.session_state.grup_gun_takvimi.get(g_isim, {})
                        g_tarihler = [t for t in grup_takvimi.values() if t]
                        grup_tarih_metni = f"📅 {', '.join(sorted(g_tarihler, key=lambda x: datetime.datetime.strptime(x, '%d.%m.%Y')))}" if g_tarihler else "⚠️ Tarih Bekliyor"
                        
                        with st.expander(f"📁 {g_isim} ({f_turu}) | {grup_tarih_metni}"):
                            g_kadro = st.session_state.takim_kadrolari[g_isim]
                            for t_isim in dogal_sirala(list(g_kadro.keys())):
                                st.markdown(f"**🛡️ {t_isim}**")
                                if g_kadro[t_isim] and g_kadro[t_isim] != ["Belirtilmedi"]:
                                    liste_metni = "<br>".join([f"**{i+1}.** {oyuncu}" for i, oyuncu in enumerate(g_kadro[t_isim])])
                                    st.markdown(liste_metni, unsafe_allow_html=True)
                                else:
                                    st.write("Oyuncu yok")
                                st.markdown("---")
    else:
        st.warning("🔒 Bu panel dışarıya kapalıdır. Lütfen giriş yapınız.")

def hakem_yonetimi_ciz():
    if st.session_state.admin_mi:
        st.subheader("👮‍♂️ Hakem Tanımlama ve Yönetim Paneli")
        st.info("Aşağıdan turnuvada görev yapacak hakemlerin isimlerini ekleyebilir ve onlara sisteme girmeleri için otomatik PIN kodları üretebilirsiniz.")
        
        c_h1, c_h2 = st.columns([3, 1])
        with c_h1:
            yeni_hakem = st.text_input("Yeni Hakem Adı Soyadı:", placeholder="Örn: Ahmet Yılmaz")
        with c_h2:
            st.write("")
            st.write("")
            if st.button("➕ Hakemi Ekle", use_container_width=True):
                if yeni_hakem and yeni_hakem not in st.session_state.hakem_listesi:
                    st.session_state.hakem_listesi.append(yeni_hakem.strip())
                    if ortak_veriyi_kaydet():
                        st.success(f"✅ {yeni_hakem} sisteme başarıyla eklendi.")
                        st.rerun()
                elif yeni_hakem in st.session_state.hakem_listesi:
                    st.warning("Bu hakem zaten listede mevcut.")
                    
        st.markdown("---")
        st.markdown("### 🔑 Hakem PIN (Şifre) Üretimi")
        
        if st.button("🚀 Tüm Hakemlere 4 Haneli PIN Üret (Mevcutları Koru)", type="primary"):
            if not st.session_state.hakem_listesi:
                st.warning("Henüz sisteme eklenmiş bir hakem bulunmuyor.")
            else:
                for h in st.session_state.hakem_listesi:
                    if h not in st.session_state.hakem_pinleri:
                        st.session_state.hakem_pinleri[h] = random.randint(1000, 9999)
                if ortak_veriyi_kaydet():
                    st.success("Tüm hakemler için şifreler başarıyla üretildi!")
                    st.rerun()
        
        if st.session_state.hakem_listesi:
            h_df_data = []
            for h in st.session_state.hakem_listesi:
                h_df_data.append({"Hakem Adı": h, "Giriş PIN Kodu": st.session_state.hakem_pinleri.get(h, "Üretilmedi")})
            st.dataframe(pd.DataFrame(h_df_data), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🗑️ Hakem Sil")
        if st.session_state.hakem_listesi:
            sil_hakem = st.selectbox("Sistemden Kaldırılacak Hakemi Seçin:", ["Seçiniz"] + st.session_state.hakem_listesi)
            if sil_hakem != "Seçiniz":
                if st.button(f"❌ '{sil_hakem}' İsimli Hakemi Sil"):
                    st.session_state.hakem_listesi.remove(sil_hakem)
                    if sil_hakem in st.session_state.hakem_pinleri:
                        del st.session_state.hakem_pinleri[sil_hakem]
                    if ortak_veriyi_kaydet():
                        st.success(f"{sil_hakem} sistemden kaldırıldı.")
                        st.rerun()

def yonetim_ve_dosya_ciz(aktif_asama):
    st.subheader(f"⚙️ Gelişmiş Yönetim Paneli ({aktif_asama})")

    if st.session_state.admin_mi:
        
        with st.expander("🔑 Kaptan Şifreleri (PIN) Yönetimi", expanded=False):
            st.info("ℹ️ Turnuvaya katılan her takıma otomatik 4 haneli PIN üretilir. Sistem, kayıtlı gruplardaki takımları baz alır.")
            
            tum_takimlar_seti = set()
            
            for g_k in st.session_state.get('takim_kadrolari', {}).values():
                for t in g_k.keys():
                    tum_takimlar_seti.add(t)
                    
            gecersizler = ["", "None", "nan", "--- BOŞ (BYE) ---", "W/O"]
            tum_takim_listesi = dogal_sirala([t for t in tum_takimlar_seti if str(t).strip() not in gecersizler])
            
            st.write(f"📊 Gruplara yerleştirilmiş toplam benzersiz takım sayısı: **{len(tum_takim_listesi)}**")
            
            c_pin1, c_pin2 = st.columns(2)
            
            with c_pin1:
                if st.button("🚀 Kaptan Listesini Yenile ve Şifre Üret", type="primary", use_container_width=True):
                    yeni_pinler = {}
                    for t in tum_takim_listesi:
                        eski_pin = st.session_state.takim_pinleri.get(t)
                        yeni_pinler[t] = eski_pin if eski_pin else random.randint(1000, 9999)
                    
                    st.session_state.takim_pinleri = yeni_pinler
                    if ortak_veriyi_kaydet():
                        st.success(f"Liste güncellendi ve {len(tum_takim_listesi)} takım için şifreler hazırlandı!")
                        st.rerun()
                    else:
                        st.error("Sistem meşgul, lütfen tekrar deneyin.")
            
            with c_pin2:
                if st.button("🗑️ Şifreleri Tamamen Sıfırla (İptal Et)", use_container_width=True):
                    st.session_state.takim_pinleri = {}
                    if ortak_veriyi_kaydet():
                        st.success("Tüm şifreler sistemden silindi! Yeniden şifre üretmeniz gerekmektedir.")
                        st.rerun()
                    else:
                        st.error("Sistem meşgul, lütfen tekrar deneyin.")
            
            if st.session_state.takim_pinleri:
                pin_df = pd.DataFrame(list(st.session_state.takim_pinleri.items()), columns=["Takım Adı", "Kaptan PIN Kodu"])
                st.dataframe(pin_df, use_container_width=True)
        
        with st.expander("✍️ Grup Tipi, Format, İsim ve Kadroları Revize Et", expanded=True):
            if not st.session_state.skor_tablosu.empty:
                t_gruplar = dogal_sirala([g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
                
                if not t_gruplar:
                    st.info(f"{aktif_asama} için kayıtlı grup bulunmamaktadır.")
                else:
                    sec_g = st.selectbox("Düzenlenecek Grup Seç:", ["Seçiniz"] + t_gruplar, key="admin_edit_grup")
                    
                    if sec_g != "Seçiniz":
                        yeni_grup_adi = st.text_input("Grup Adını Güncelle:", value=sec_g, key="yeni_g_adi")
                        st.markdown("---")
                        
                        m_kadrolar = st.session_state.takim_kadrolari.get(sec_g, {})
                        mevcut_takim_sayisi = len(m_kadrolar)
                        tip_liste = ["3'lü Grup", "4'lü Grup", "5'li Grup", "6'lı Grup"] if aktif_asama == "1. Aşama" else ["2'li Grup", "3'lü Grup", "4'lü Grup"]
                        
                        tip_idx = 0
                        for i_opt, opt in enumerate(tip_liste):
                            if str(mevcut_takim_sayisi) in opt:
                                tip_idx = i_opt
                                break
                        
                        mevcut_format = st.session_state.grup_formatlari.get(sec_g, "3 Maçlık (2 Tek, 1 Çift)")
                        format_liste = ["3 Maçlık (2 Tek, 1 Çift)", "5 Maçlık (3 Tek, 2 Çift)"]
                        format_idx = format_liste.index(mevcut_format) if mevcut_format in format_liste else 0

                        mevcut_kategori = st.session_state.grup_kategorileri.get(sec_g, "Erkekler")
                        kategori_liste = ["Erkekler", "Kadınlar"]
                        kategori_idx = kategori_liste.index(mevcut_kategori) if mevcut_kategori in kategori_liste else 0
                        
                        mevcut_yas = st.session_state.grup_yas_gruplari.get(sec_g, "Yaş Belirtme")
                        yas_liste = ["Yaş Belirtme"] + [f"{i}+" for i in range(30, 85, 5)]
                        yas_idx = yas_liste.index(mevcut_yas) if mevcut_yas in yas_liste else 0

                        c_y, c_f1, c_f2, c_f3 = st.columns(4)
                        with c_y: yeni_yas = st.selectbox("🔄 Yaş Grubu:", yas_liste, index=yas_idx, key="edit_yas")
                        with c_f1: yeni_kategori = st.radio("🔄 Kategori:", kategori_liste, index=kategori_idx, horizontal=True, key="edit_kategori")
                        with c_f2: yeni_grup_tipi = st.radio("🔄 Grup Tipi:", tip_liste, index=tip_idx, horizontal=True, key="edit_grup_tipi")
                        with c_f3: yeni_format = st.radio("🔄 Müsabaka Formatı:", format_liste, index=format_idx, horizontal=True, key="edit_format")
                        
                        st.caption("💡 Not: Yaş grubunu veya kategoriyi değiştirirseniz, sistem karışıklığını önlemek için yukarıdaki 'Grup Adı' içindeki metni de elle düzeltmeyi unutmayın.")
                        
                        grup_statusu = "Play-out Grubu (Düşme Hattı)"
                        if aktif_asama == "2. Aşama":
                            mevcut_statu = st.session_state.grup_statuleri.get(sec_g, "Play-out Grubu (Düşme Hattı)")
                            statu_opts = ["Birinciler Grubu (Kürsü)", "İkinciler Grubu (Orta Klasman)", "Play-out Grubu (Düşme Hattı)"]
                            s_idx = statu_opts.index(mevcut_statu) if mevcut_statu in statu_opts else 2
                            grup_statusu = st.radio("🏅 Grup Statüsü (Bu grubun amacı nedir?):", statu_opts, horizontal=True, index=s_idx, key=f"edit_statu_{sec_g}")

                        fikstur_sifirlanacak_mi = (yeni_grup_tipi != tip_liste[tip_idx]) or (yeni_format != mevcut_format)
                        if fikstur_sifirlanacak_mi:
                            st.warning("⚠️ DİKKAT: Grup tipini veya maç formatını değiştirdiniz! Kaydettiğinizde bu grubun eski fikstürü ve skorları TAMAMEN SİLİNİP, yeni ayarlarla baştan oluşturulacaktır.")

                        st.markdown("---")
                        mevcut_takim_isimleri = list(m_kadrolar.keys())
                        beklenen_yeni_sayi = int(yeni_grup_tipi[0])
                        yeni_k_yapisi = {}; isim_degisiklikleri = {}
                        
                        for i in range(beklenen_yeni_sayi):
                            esk_ad = mevcut_takim_isimleri[i] if i < len(mevcut_takim_isimleri) else f"Yeni Takım {i+1}"
                            
                            tum_takimlar = dogal_sirala(list(st.session_state.takim_havuzu.keys()))
                            bye_opt = "--- BOŞ (BYE) ---"
                            if bye_opt not in tum_takimlar: tum_takimlar.insert(0, bye_opt)
                            if esk_ad not in tum_takimlar: tum_takimlar.insert(1, esk_ad)
                            
                            c_a, c_b = st.columns([1, 2])
                            with c_a:
                                y_ad = st.selectbox(f"{i+1}. Takım Seçimi", options=tum_takimlar, index=tum_takimlar.index(esk_ad), key=f"ad_{sec_g}_{i}")
                                
                                if i < len(mevcut_takim_isimleri) and y_ad != esk_ad: 
                                    isim_degisiklikleri[esk_ad] = y_ad
                                    if y_ad == bye_opt:
                                        aktif_oyuncular = ["(Boş)"]
                                    else:
                                        aktif_oyuncular = st.session_state.takim_havuzu.get(y_ad, ["Oyuncu Bulunamadı"])
                                else:
                                    aktif_oyuncular = m_kadrolar.get(esk_ad, ["Belirtilmedi"])
                                    
                            with c_b:
                                y_o_text = st.text_area(f"Oyuncular ({y_ad})", value="\n".join(aktif_oyuncular), key=f"oyuncu_{sec_g}_{i}", height=100)
                                yeni_k_yapisi[y_ad if y_ad else esk_ad] = [o.strip() for o in y_o_text.split('\n') if o.strip()]
                        
                        if st.button("💾 Yapılan Değişiklikleri Veritabanına Yaz"):
                            g_hedef = yeni_grup_adi if yeni_grup_adi.strip() != "" else sec_g
                            
                            if g_hedef != sec_g and g_hedef in st.session_state.takim_kadrolari:
                                st.error(f"⚠️ KRİTİK HATA: '{g_hedef}' adında bir grup zaten sistemde mevcut! İki grubu birleştiremezsiniz, lütfen farklı bir ad girin.")
                            else:
                                kullanilan_baska_takimlar_tab6 = {}
                                for g_n, g_k in st.session_state.takim_kadrolari.items():
                                    g_kat = st.session_state.grup_kategorileri.get(g_n, "Erkekler")
                                    g_asam = st.session_state.grup_asamalari.get(g_n, "1. Aşama")
                                    g_yas_kontrol = st.session_state.grup_yas_gruplari.get(g_n, "Yaş Belirtme")
                                    
                                    if g_n != sec_g and g_kat == yeni_kategori and g_yas_kontrol == yeni_yas and g_asam == aktif_asama:
                                        for t_n in g_k.keys(): kullanilan_baska_takimlar_tab6[t_n] = g_n
                                
                                cakisanlar_tab6 = [t for t in list(yeni_k_yapisi.keys()) if t in kullanilan_baska_takimlar_tab6 and t != bye_opt]
                                if cakisanlar_tab6:
                                    hata_msj = ", ".join([f"'{t}' ({kullanilan_baska_takimlar_tab6[t]})" for t in cakisanlar_tab6])
                                    st.error(f"⚠️ Hata: Eklemek veya değiştirmek istediğiniz takım(lar) {yeni_yas} {yeni_kategori} kategorisinde ({aktif_asama}) zaten başka gruplarda kayıtlı!\nÇakışanlar: {hata_msj}")
                                else:
                                    if fikstur_sifirlanacak_mi:
                                        silinecek_idler = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == sec_g]['id'].dropna().tolist()
                                        try:
                                            if "supabase" in globals() and supabase and silinecek_idler:
                                                for idx_chunk in range(0, len(silinecek_idler), 100):
                                                    supabase.table("maclar").delete().in_("id", silinecek_idler[idx_chunk:idx_chunk+100]).execute()
                                        except Exception:
                                            pass
                                        
                                        st.session_state.skor_tablosu = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] != sec_g]
                                        st.session_state.mac_programi = st.session_state.mac_programi[st.session_state.mac_programi['Grup'] != sec_g]
                                        
                                        st.session_state.takim_kadrolari[g_hedef] = yeni_k_yapisi
                                        st.session_state.grup_formatlari[g_hedef] = yeni_format
                                        st.session_state.grup_kategorileri[g_hedef] = yeni_kategori
                                        st.session_state.grup_asamalari[g_hedef] = aktif_asama
                                        st.session_state.grup_yas_gruplari[g_hedef] = yeni_yas
                                        st.session_state.grup_statuleri[g_hedef] = grup_statusu 
                                        
                                        if sec_g != g_hedef:
                                            st.session_state.skor_tablosu.loc[st.session_state.skor_tablosu['Grup'] == sec_g, 'Grup'] = g_hedef
                                            st.session_state.mac_programi.loc[st.session_state.mac_programi['Grup'] == sec_g, 'Grup'] = g_hedef
                                            st.session_state.takim_kadrolari[g_hedef] = st.session_state.takim_kadrolari.pop(sec_g)
                                            if sec_g in st.session_state.grup_formatlari: st.session_state.grup_formatlari[g_hedef] = st.session_state.grup_formatlari.pop(sec_g)
                                            if sec_g in st.session_state.grup_kategorileri: st.session_state.grup_kategorileri[g_hedef] = st.session_state.grup_kategorileri.pop(sec_g)
                                            if sec_g in st.session_state.grup_asamalari: st.session_state.grup_asamalari[g_hedef] = st.session_state.grup_asamalari.pop(sec_g)
                                            if sec_g in st.session_state.grup_siralamalari: st.session_state.grup_siralamalari[g_hedef] = st.session_state.grup_siralamalari.pop(sec_g)
                                            if sec_g in st.session_state.grup_tamamlandi: st.session_state.grup_tamamlandi[g_hedef] = st.session_state.grup_tamamlandi.pop(sec_g)
                                            if sec_g in st.session_state.grup_yas_gruplari: st.session_state.grup_yas_gruplari[g_hedef] = st.session_state.grup_yas_gruplari.pop(sec_g)
                                            if sec_g in st.session_state.grup_statuleri: st.session_state.grup_statuleri[g_hedef] = st.session_state.grup_statuleri.pop(sec_g)
                                        
                                        yeni_takim_listesi = list(yeni_k_yapisi.keys())
                                        yeni_df = pd.DataFrame(eslesmeleri_olustur(g_hedef, yeni_takim_listesi, yeni_grup_tipi, yeni_format))
                                        if st.session_state.skor_tablosu.empty: st.session_state.skor_tablosu = yeni_df
                                        else: st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
                                        
                                        if ortak_veriyi_kaydet():
                                            st.success("Grup ayarları güncellendi ve yeni fikstür başarıyla oluşturuldu!")
                                        else:
                                            st.error("Sistem meşgul, lütfen tekrar deneyin.")
                                        st.rerun()
                                        
                                    else:
                                        st.session_state.takim_kadrolari[sec_g] = yeni_k_yapisi
                                        st.session_state.grup_kategorileri[sec_g] = yeni_kategori
                                        st.session_state.grup_asamalari[sec_g] = aktif_asama
                                        st.session_state.grup_yas_gruplari[sec_g] = yeni_yas
                                        st.session_state.grup_statuleri[sec_g] = grup_statusu 
                                        
                                        if isim_degisiklikleri:
                                            mask_s = st.session_state.skor_tablosu['Grup'] == sec_g
                                            mask_m = st.session_state.mac_programi['Grup'] == sec_g
                                            for e_a, y_a in isim_degisiklikleri.items():
                                                st.session_state.skor_tablosu.loc[mask_s, 'Takım 1'] = st.session_state.skor_tablosu.loc[mask_s, 'Takım 1'].replace(e_a, y_a)
                                                st.session_state.skor_tablosu.loc[mask_s, 'Takım 2'] = st.session_state.skor_tablosu.loc[mask_s, 'Takım 2'].replace(e_a, y_a)
                                                st.session_state.mac_programi.loc[mask_m, 'Takım 1'] = st.session_state.mac_programi.loc[mask_m, 'Takım 1'].replace(e_a, y_a)
                                                st.session_state.mac_programi.loc[mask_m, 'Takım 2'] = st.session_state.mac_programi.loc[mask_m, 'Takım 2'].replace(e_a, y_a)
                                            
                                        if g_hedef != sec_g:
                                            st.session_state.skor_tablosu.loc[st.session_state.skor_tablosu['Grup'] == sec_g, 'Grup'] = g_hedef
                                            st.session_state.mac_programi.loc[st.session_state.mac_programi['Grup'] == sec_g, 'Grup'] = g_hedef
                                            st.session_state.takim_kadrolari[g_hedef] = st.session_state.takim_kadrolari.pop(sec_g)
                                            if sec_g in st.session_state.grup_formatlari: st.session_state.grup_formatlari[g_hedef] = st.session_state.grup_formatlari.pop(sec_g)
                                            if sec_g in st.session_state.grup_kategorileri: st.session_state.grup_kategorileri[g_hedef] = st.session_state.grup_kategorileri.pop(sec_g)
                                            if sec_g in st.session_state.grup_asamalari: st.session_state.grup_asamalari[g_hedef] = st.session_state.grup_asamalari.pop(sec_g)
                                            if sec_g in st.session_state.grup_siralamalari: st.session_state.grup_siralamalari[g_hedef] = st.session_state.grup_siralamalari.pop(sec_g)
                                            if sec_g in st.session_state.grup_tamamlandi: st.session_state.grup_tamamlandi[g_hedef] = st.session_state.grup_tamamlandi.pop(sec_g)
                                            if sec_g in st.session_state.grup_yas_gruplari: st.session_state.grup_yas_gruplari[g_hedef] = st.session_state.grup_yas_gruplari.pop(sec_g)
                                            if sec_g in st.session_state.grup_statuleri: st.session_state.grup_statuleri[g_hedef] = st.session_state.grup_statuleri.pop(sec_g)
                                        
                                        if ortak_veriyi_kaydet():
                                            st.success("Takım ve kadro bilgileri başarıyla güncellendi!")
                                        else:
                                            st.error("Sistem meşgul, lütfen tekrar deneyin.")
                                        st.rerun()

        st.markdown("### 🗑️ Grup Silme İşlemleri")
        if not st.session_state.skor_tablosu.empty:
            silinecek_gruplar = dogal_sirala([g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
            secilen_sil_grup = st.selectbox("Silinecek Grubu Seçin:", ["Seçiniz"] + silinecek_gruplar, key="grup_sil_secim")
            
            if secilen_sil_grup != "Seçiniz":
                st.warning(f"⚠️ DİKKAT: '{secilen_sil_grup}' grubunu ve bu gruba ait tüm fikstür/kadro kayıtlarını kalıcı olarak sileceksiniz!")
                
                if st.button(f"🚨 '{secilen_sil_grup}' Grubunu Tamamen Sil"):
                    silinecek_idler = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == secilen_sil_grup]['id'].dropna().tolist()
                    try:
                        if "supabase" in globals() and supabase and silinecek_idler:
                            for idx_chunk in range(0, len(silinecek_idler), 100):
                                supabase.table("maclar").delete().in_("id", silinecek_idler[idx_chunk:idx_chunk+100]).execute()
                    except Exception:
                        pass
                        
                    st.session_state.skor_tablosu = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] != secilen_sil_grup]
                    st.session_state.mac_programi = st.session_state.mac_programi[st.session_state.mac_programi['Grup'] != secilen_sil_grup]
                    
                    if secilen_sil_grup in st.session_state.takim_kadrolari: del st.session_state.takim_kadrolari[secilen_sil_grup]
                    if secilen_sil_grup in st.session_state.grup_formatlari: del st.session_state.grup_formatlari[secilen_sil_grup]
                    if secilen_sil_grup in st.session_state.grup_kategorileri: del st.session_state.grup_kategorileri[secilen_sil_grup]
                    if secilen_sil_grup in st.session_state.grup_asamalari: del st.session_state.grup_asamalari[secilen_sil_grup]
                    if secilen_sil_grup in st.session_state.grup_siralamalari: del st.session_state.grup_siralamalari[secilen_sil_grup]
                    if secilen_sil_grup in st.session_state.grup_tamamlandi: del st.session_state.grup_tamamlandi[secilen_sil_grup]
                    if secilen_sil_grup in st.session_state.grup_yas_gruplari: del st.session_state.grup_yas_gruplari[secilen_sil_grup]
                    if secilen_sil_grup in st.session_state.grup_statuleri: del st.session_state.grup_statuleri[secilen_sil_grup] 
                    if secilen_sil_grup in st.session_state.grup_gun_takvimi: del st.session_state.grup_gun_takvimi[secilen_sil_grup]
                    
                    keys_to_delete = [k for k in st.session_state.esame_kasasi.keys() if k.startswith(secilen_sil_grup + "_")]
                    for k in keys_to_delete:
                        del st.session_state.esame_kasasi[k]
                    keys_to_delete_onay = [k for k in st.session_state.esame_onayli.keys() if k.startswith(secilen_sil_grup + "_")]
                    for k in keys_to_delete_onay:
                        del st.session_state.esame_onayli[k]
                    
                    if ortak_veriyi_kaydet():
                        st.success(f"'{secilen_sil_grup}' grubu ve esame kalıntıları sistemden başarıyla silindi!")
                        st.rerun()
                    else:
                        st.error("Sistem meşgul, lütfen tekrar deneyin.")
        else:
            st.info(f"{aktif_asama} için silinecek herhangi bir grup bulunmuyor.")

        st.markdown("---")
        st.markdown("### 💾 Yedekleme Paneli")
        c_sv, c_ld = st.columns(2)
        with c_sv:
            export_data = {
                "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records") if not st.session_state.skor_tablosu.empty else [],
                "mac_programi": st.session_state.mac_programi.to_dict(orient="records") if not st.session_state.mac_programi.empty else [],
                "takim_kadrolari": st.session_state.get("takim_kadrolari", {}),
                "grup_formatlari": st.session_state.get("grup_formatlari", {}),
                "grup_kategorileri": st.session_state.get("grup_kategorileri", {}),
                "grup_asamalari": st.session_state.get("grup_asamalari", {}),
                "duyuru_metni": st.session_state.get("duyuru_metni", ""),
                "gunluk_notlar": st.session_state.get("gunluk_notlar", {}),
                "takim_havuzu": st.session_state.get("takim_havuzu", {}),
                "havuz_kategorileri": st.session_state.get("havuz_kategorileri", {}),
                "havuz_yas_gruplari": st.session_state.get("havuz_yas_gruplari", {}),
                "grup_siralamalari": st.session_state.get("grup_siralamalari", {}),
                "grup_tamamlandi": st.session_state.get("grup_tamamlandi", {}),
                "grup_yas_gruplari": st.session_state.get("grup_yas_gruplari", {}),
                "takim_pinleri": st.session_state.get("takim_pinleri", {}),
                "esame_kasasi": st.session_state.get("esame_kasasi", {}),
                "esame_onayli": st.session_state.get("esame_onayli", {}),
                "hakem_listesi": st.session_state.get("hakem_listesi", []),
                "hakem_pinleri": st.session_state.get("hakem_pinleri", {}),
                "grup_gun_takvimi": st.session_state.get("grup_gun_takvimi", {}),
                "yayinlanan_gunler": st.session_state.get("yayinlanan_gunler", {})
            }
            zaman_damgasi = datetime.datetime.now().strftime("%d_%m_%Y_%H%M")
            yedek_adi = f"turnuva_yedek_{zaman_damgasi}.json"
            st.download_button("📥 Turnuva Veritabanını İndir (.json)", data=json.dumps(export_data, ensure_ascii=False, indent=4), file_name=yedek_adi, mime="application/json")
        with c_ld:
            up_file = st.file_uploader("Geri Yüklemek İçin Yedek Dosyası Seçin:", type=["json"])
            if up_file is not None and st.button("📤 Seçilen Yedeği Sisteme Entegre Et"):
                try:
                    d = json.load(up_file)
                    st.session_state.skor_tablosu = pd.DataFrame(d.get("skor_tablosu", []))
                    st.session_state.mac_programi = pd.DataFrame(d.get("mac_programi", []))
                    st.session_state.takim_kadrolari = d.get("takim_kadrolari", {})
                    st.session_state.grup_formatlari = d.get("grup_formatlari", {})
                    st.session_state.grup_kategorileri = d.get("grup_kategorileri", {})
                    st.session_state.grup_asamalari = d.get("grup_asamalari", {})
                    st.session_state.duyuru_metni = d.get("duyuru_metni", "")
                    st.session_state.gunluk_notlar = d.get("gunluk_notlar", {})
                    st.session_state.takim_havuzu = d.get("takim_havuzu", {})
                    st.session_state.havuz_kategorileri = d.get("havuz_kategorileri", {})
                    st.session_state.havuz_yas_gruplari = d.get("havuz_yas_gruplari", {})
                    st.session_state.grup_siralamalari = d.get("grup_siralamalari", {})
                    st.session_state.grup_tamamlandi = d.get("grup_tamamlandi", {})
                    st.session_state.grup_yas_gruplari = d.get("grup_yas_gruplari", {})
                    st.session_state.takim_pinleri = d.get("takim_pinleri", {})
                    st.session_state.esame_kasasi = d.get("esame_kasasi", {})
                    st.session_state.esame_onayli = d.get("esame_onayli", {})
                    st.session_state.hakem_listesi = d.get("hakem_listesi", [])
                    st.session_state.hakem_pinleri = d.get("hakem_pinleri", {})
                    st.session_state.grup_gun_takvimi = d.get("grup_gun_takvimi", {})
                    st.session_state.yayinlanan_gunler = d.get("yayinlanan_gunler", {})
                    
                    if ortak_veriyi_kaydet():
                        st.success("Yedek başarıyla yüklendi!")
                        st.rerun()
                    else:
                        st.error("Sistem meşgul, lütfen tekrar deneyin.")
                except Exception as ex: st.error(f"Hata: {ex}")
        st.markdown("---")
        st.markdown("### ⚠️ Sistem Sıfırlama (Tehlikeli İşlem)")
        
        if "confirm_reset" not in st.session_state:
            st.session_state.confirm_reset = False

        if not st.session_state.confirm_reset:
            if st.button("🗑️ Tüm Turnuva Verilerini Kalıcı Olarak Sıfırla"):
                st.session_state.confirm_reset = True
                st.rerun()
        else:
            st.warning("⚠️ DİKKAT: Tüm turnuva verileri (maçlar, kadrolar, skorlar, yüklenen belgeler) kalıcı olarak silinecektir. Bu işlem geri alınamaz!")
            col_evet, col_hayir = st.columns(2)
            if col_evet.button("✅ Evet, Tüm Verileri Sil"):
                if supabase:
                    try:
                        res = supabase.table("maclar").select("id").execute()
                        if res.data:
                            ids = [item['id'] for item in res.data]
                            for i in range(0, len(ids), 100):
                                batch_ids = ids[i:i+100]
                                supabase.table("maclar").delete().in_("id", batch_ids).execute()
                        
                        bos_ayarlar = {
                            "takim_kadrolari": {}, "grup_formatlari": {}, "grup_kategorileri": {}, "grup_asamalari": {},
                            "duyuru_metni": "", "gunluk_notlar": {}, "takim_havuzu": {}, "havuz_kategorileri": {},
                            "havuz_yas_gruplari": {}, "grup_siralamalari": {}, "grup_tamamlandi": {}, "grup_yas_gruplari": {},
                            "takim_pinleri": {}, "esame_kasasi": {}, "esame_onayli": {}, "mac_programi": [], "hakem_listesi": [], "hakem_pinleri": {},
                            "grup_gun_takvimi": {}, "yayinlanan_gunler": {}
                        }
                        supabase.table("turnuva_ayarlari").update(bos_ayarlar).eq("id", 1).execute()
                    except Exception as e:
                        st.error(f"Veritabanı silinirken hata oluştu: {e}")

                if os.path.exists(BELGELER_KLASORU): shutil.rmtree(BELGELER_KLASORU)
                st.session_state.clear()
                st.session_state.confirm_reset = False
                st.success("Tüm veritabanı başarıyla temizlendi!")
                time.sleep(1.5)
                st.rerun()
            if col_hayir.button("❌ Vazgeç"):
                st.session_state.confirm_reset = False
                st.rerun()
