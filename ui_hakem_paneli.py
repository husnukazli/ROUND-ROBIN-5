import streamlit as st
import datetime
import time
import html
from hesaplama_motoru import sort_maclar, set_gecerli_mi, hesapla_mac_kazanani
from veritabani_islemleri import ortak_veriyi_kaydet
from gorsel_stiller import hakem_mobil_css_yukle

def hakem_panelini_ciz():
    hakem_mobil_css_yukle()
    if st.session_state.get("sistem_kilitli", False) and not st.session_state.admin_mi:
        st.error("🚨 SİSTEM BAKIMDA: Başhakem şu an çevrimdışı (Uçak) modunda maç programı düzenliyor. Lütfen skor değişikliklerini kağıt üzerinde Başhakem masasına iletiniz.")
    elif not st.session_state.hakem_mi:
        st.warning("Bu paneli görüntülemek için lütfen hakem olarak giriş yapın.")
    else:
        aktif_hakem = st.session_state.aktif_hakem
        st.info(f"Hoş geldin, **{aktif_hakem}**. Aşağıda turnuva boyunca üzerinize atanan maçlar listelenmiştir. Kaptanlardan gelen esameleri ve maç skorlarını buradan girebilirsiniz.")
        
        # --- ÇARPIYLA KAPATILAN KALICI BAŞARI MESAJI ---
        if "basari_mesaji" in st.session_state:
            st.success(f"🏆 **{st.session_state.basari_mesaji}**")
            if st.button("✖️ Mesajı Kapat", key="btn_kapat_basari", use_container_width=True):
                del st.session_state.basari_mesaji
                st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
        # --------------------------------------------------------
        
        df_hakem_maclari = st.session_state.mac_programi[st.session_state.mac_programi['Hakem'] == aktif_hakem]
        
        if df_hakem_maclari.empty:
            st.success("Şu ana kadar üzerinize atanmış herhangi bir görev bulunmamaktadır.")
        else:
            bugun = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date()
            
            tarihler = df_hakem_maclari['Tarih'].dropna().unique()
            tarihler_sirali = sorted(tarihler, key=lambda x: datetime.datetime.strptime(x, "%d.%m.%Y").date())
            
            st.markdown("### ☀️ Bugünün Maçları")
            container_bugun = st.container()
            st.markdown("<br>", unsafe_allow_html=True)
            container_diger = st.expander("🕰️ Geçmiş ve Gelecek Maçları Görüntüle (Arşiv & Planlananlar)", expanded=False)
            
            bugun_mac_var_mi = False
            
            for tarih_str in tarihler_sirali:
                mac_tarihi = datetime.datetime.strptime(tarih_str, "%d.%m.%Y").date()
                is_gecmis = mac_tarihi < bugun
                is_gelecek = mac_tarihi > bugun
                is_kilitli = is_gecmis or is_gelecek
                
                hedef_alan = container_diger if is_kilitli else container_bugun
                
                with hedef_alan:
                    if not is_kilitli:
                        bugun_mac_var_mi = True
                        
                    st.markdown(f"#### 🗓️ Tarih: {tarih_str}")
                    
                    if is_gecmis:
                        st.error("🔒 **GEÇMİŞ TARİH:** Bu maçlar geçmişte kalmıştır. Skorları sadece görüntüleyebilirsiniz. Hatalı bir işlem varsa lütfen Başhakem'e bildiriniz.")
                    elif is_gelecek:
                        st.warning("⏳ **GELECEK TARİH:** Bu maçların tarihi henüz gelmemiştir. Esame ve skor girişi maç günü açılacaktır.")
                    else:
                        st.success("✍️ **ESAME VE SKOR GİRİŞİ AÇIK:** Bugüne ait maçların kadrolarını ve maç skorlarını aşağıdan girebilirsiniz.")
                        
                    df_gun = df_hakem_maclari[df_hakem_maclari['Tarih'] == tarih_str]
                    
                    for (grup_adi, eslesme_adi), g_df in df_gun.groupby(['Grup', 'Eşleşme']):
                        t1 = g_df.iloc[0]['Takım 1']
                        t2 = g_df.iloc[0]['Takım 2']
                        kort = g_df.iloc[0]['Kort']
                        saat = g_df.iloc[0]['Maç Saati']
                        gun_val = g_df.iloc[0]['Gün']
                        match_key = f"{grup_adi}_{gun_val}_{eslesme_adi}"
                        
                        g_kat = st.session_state.grup_kategorileri.get(grup_adi, "")
                        g_yas = st.session_state.grup_yas_gruplari.get(grup_adi, "")
                        kat_bilgisi = f"({g_yas} {g_kat})" if g_yas != "Yaş Belirtme" else f"({g_kat})"
                        
                        is_approved = st.session_state.esame_onayli.get(match_key, False)
                        kasadaki_veri = st.session_state.esame_kasasi.get(match_key, {})
                        
                        t1_kaptan_girdi = t1 in kasadaki_veri and kasadaki_veri[t1].get("_kaynak", "Kaptan") == "Kaptan"
                        t2_kaptan_girdi = t2 in kasadaki_veri and kasadaki_veri[t2].get("_kaynak", "Kaptan") == "Kaptan"

                        if is_gecmis:
                            baslik_durumu = "🔒 [GEÇMİŞ]"
                        elif is_gelecek:
                            baslik_durumu = "🔒 [GELECEK]"
                        elif is_approved:
                            baslik_durumu = "✍️ [SKOR AÇIK]"
                        else:
                            baslik_durumu = "📋 [ESAME BEKLENİYOR]"
                            
                        expander_baslik = f"{saat} - :red[**📍 {kort}**] | {kat_bilgisi} {grup_adi} | {t1} vs {t2} | {baslik_durumu}"
                        
                        with st.expander(expander_baslik, expanded=False):
                            
                            if is_gelecek:
                                st.warning(f"⏳ **{tarih_str} Bekleniyor:** Bu eşleşmenin günü henüz gelmemiştir. Oyuncu kadroları ve skor girişleri maç günü aktif olacaktır.")
                            
                            elif is_gecmis:
                                st.error(f"🔒 **{tarih_str} Geçmiş Maç:** Bu eşleşme geçmişte kalmıştır. Herhangi bir esame veya skor değişikliği yapılamaz.")
                                html_rows = ""
                                for _, row in sort_maclar(g_df).iterrows():
                                    skor = str(row.get('Skor', 'Oynanmadı'))
                                    skor_html = f"<span style='color:#28a745; font-weight:bold;'>{skor}</span>" if skor not in ["Oynanmadı", ""] else "<i>Oynanmadı</i>"
                                    
                                    t1_o_val = str(row.get('T1 Oyuncu', ''))
                                    t2_o_val = str(row.get('T2 Oyuncu', ''))
                                    t1_o = html.escape(t1_o_val.strip()) if t1_o_val not in ["nan", "None", ""] else "-"
                                    t2_o = html.escape(t2_o_val.strip()) if t2_o_val not in ["nan", "None", ""] else "-"
                                    
                                    if row.get('Kazanan') == 'T1': t1_o = f"<b>{t1_o}</b>"
                                    elif row.get('Kazanan') == 'T2': t2_o = f"<b>{t2_o}</b>"
                                    
                                    html_rows += f"<tr><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{row['Branş']}</td><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{t1_o} / {t2_o}</td><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{skor_html}</td></tr>"
                                
                                st.markdown(f"""
                                <table style="width:100%; border-collapse: collapse; font-family: sans-serif; margin-top:10px;">
                                    <tr><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Branş</th><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Oyuncular</th><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Skor</th></tr>
                                    {html_rows}
                                </table>
                                """, unsafe_allow_html=True)
                            
                            else:
                                if is_approved:
                                    st.markdown("<div style='background-color: #f8fff9; border-left: 5px solid #28a745; padding: 10px; border-radius: 4px; color: #155724; font-weight: bold; margin-bottom: 15px;'>BU MAÇIN SKOR GİRİŞİ AÇIKTIR</div>", unsafe_allow_html=True)
                                else:
                                    st.markdown("<div style='background-color: #f4f8ff; border-left: 5px solid #17a2b8; padding: 10px; border-radius: 4px; color: #0c5460; font-weight: bold; margin-bottom: 15px;'>ESAMELERİN ONAYLANMASI BEKLENİYOR</div>", unsafe_allow_html=True)

                                if not is_approved:
                                    hk_sent = (t1 in kasadaki_veri and kasadaki_veri[t1].get("_kaynak") == "Hakem") or \
                                              (t2 in kasadaki_veri and kasadaki_veri[t2].get("_kaynak") == "Hakem")
                                    kaptan_sent = (t1 in kasadaki_veri and kasadaki_veri[t1].get("_kaynak") == "Kaptan") and \
                                                  (t2 in kasadaki_veri and kasadaki_veri[t2].get("_kaynak") == "Kaptan")
                                                  
                                    if hk_sent or kaptan_sent:
                                        st.info("✅ Takım Esame Listeleri Başhakem'e iletildi. Lütfen Başhakem'in onaylamasını bekleyiniz (Onaydan sonra Skor ekranı açılacaktır).")
                                    else:
                                        st.info("📌 Maçın esameleri henüz onaylanmamış. Hakem olarak Takım Esame Listesini korta siz girebilirsiniz. Çiftler maçlarını şimdilik boş bırakabilirsiniz.")
                                        
                                        hk_adim_key = f"hk_adim_{match_key}"
                                        if hk_adim_key not in st.session_state:
                                            st.session_state[hk_adim_key] = 1
                                            
                                        hk_step = st.session_state[hk_adim_key]
                                        
                                        grup_kadro_dict = st.session_state.takim_kadrolari.get(grup_adi, {})
                                        t1_havuz = grup_kadro_dict.get(t1, ["Belirtilmedi"])
                                        t2_havuz = grup_kadro_dict.get(t2, ["Belirtilmedi"])
                                        
                                        if hk_step == 1:
                                            st.markdown(f"<h4 style='color:#0B3B24;'>1. Adım: Takım Esame Listesi ({t1})</h4>", unsafe_allow_html=True)
                                            if t1_kaptan_girdi:
                                                st.success(f"✅ {t1} kadrosu Kaptan tarafından uygulamadan girilmiş.")
                                                st.session_state[f"temp_hk_t1_{match_key}"] = kasadaki_veri[t1]
                                                if st.button("Sonraki Takıma Geç ➡️", key=f"btn_nxt_t1_{match_key}", use_container_width=True):
                                                    st.session_state[hk_adim_key] = 2
                                                    st.rerun()
                                            else:
                                                form_secimleri_t1 = st.session_state.get(f"temp_hk_t1_{match_key}", {})
                                                with st.form(key=f"form_hk_t1_{match_key}"):
                                                    for idx_mp_e, row_mp_e in sort_maclar(g_df).iterrows():
                                                        brans = row_mp_e['Branş']
                                                        if "Çiftler" in brans:
                                                            eski_val = form_secimleri_t1.get(brans, "")
                                                            eski_liste = [o.strip() for o in eski_val.split(",") if o.strip() in t1_havuz]
                                                            secim = st.multiselect(f"{brans} Seçimi", options=t1_havuz, default=eski_liste, max_selections=2, key=f"ms_t1_{match_key}_{brans}")
                                                            form_secimleri_t1[brans] = ", ".join(secim)
                                                        else:
                                                            eski_val = form_secimleri_t1.get(brans, "Seçiniz")
                                                            idx_e = (["Seçiniz"] + t1_havuz).index(eski_val) if eski_val in t1_havuz else 0
                                                            sec = st.selectbox(f"{brans} Seçimi", options=["Seçiniz"] + t1_havuz, index=idx_e, key=f"sb_t1_{match_key}_{brans}")
                                                            form_secimleri_t1[brans] = sec if sec != "Seçiniz" else ""
                                                    
                                                    if st.form_submit_button("💾 Kaydet ve 2. Takıma Geç", use_container_width=True, type="primary"):
                                                        hatalar = []
                                                        format_secimi = st.session_state.grup_formatlari.get(grup_adi, "3 Maçlık (2 Tek, 1 Çift)")
                                                        o1 = form_secimleri_t1.get("1. Tekler")
                                                        o2 = form_secimleri_t1.get("2. Tekler")
                                                        o3 = form_secimleri_t1.get("3. Tekler")
                                                        r1 = t1_havuz.index(o1) if o1 in t1_havuz else -1
                                                        r2 = t1_havuz.index(o2) if o2 in t1_havuz else -1
                                                        r3 = t1_havuz.index(o3) if o3 in t1_havuz else -1
                                                        
                                                        for b in ["1. Çiftler", "2. Çiftler", "Çiftler"]:
                                                            c_str = form_secimleri_t1.get(b, "")
                                                            if c_str:
                                                                c_list = [o.strip() for o in c_str.split(",") if o.strip()]
                                                                if len(c_list) == 1: hatalar.append(f"❌ {b} maçına tek oyuncu yazılamaz. (Boş bırakabilirsiniz)")
                                                                
                                                        if r1 != -1 and r2 != -1 and r1 >= r2: hatalar.append("❌ 1. Tekler oyuncusu, 2. Teklerden üst sırada olmalıdır.")
                                                        if r2 != -1 and r3 != -1 and r2 >= r3: hatalar.append("❌ 2. Tekler oyuncusu, 3. Teklerden üst sırada olmalıdır.")
                                                        if r1 != -1 and r3 != -1 and r2 == -1 and r1 >= r3: hatalar.append("❌ 1. Tekler oyuncusu, 3. Teklerden üst sırada olmalıdır.")
                                                        
                                                        if o1 and o1 != "Seçiniz" and o1 == o2: hatalar.append("❌ Aynı oyuncu birden fazla tekler maçına yazılamaz.")
                                                        if o2 and o2 != "Seçiniz" and o2 == o3: hatalar.append("❌ Aynı oyuncu birden fazla tekler maçına yazılamaz.")
                                                        if o1 and o1 != "Seçiniz" and o1 == o3: hatalar.append("❌ Aynı oyuncu birden fazla tekler maçına yazılamaz.")
                                                        
                                                        if "5 Maçlık" in format_secimi:
                                                            c1_list = [o.strip() for o in form_secimleri_t1.get("1. Çiftler", "").split(",") if o.strip()]
                                                            c2_list = [o.strip() for o in form_secimleri_t1.get("2. Çiftler", "").split(",") if o.strip()]
                                                            ortak = set(c1_list).intersection(set(c2_list))
                                                            if ortak: hatalar.append("❌ Aynı oyuncu iki çiftler maçına da yazılamaz.")
                                                            
                                                            if len(c1_list) == 2 and len(c2_list) == 2 and not ortak:
                                                                dortlu = sorted([(p, t1_havuz.index(p)) for p in c1_list + c2_list if p in t1_havuz], key=lambda x: x[1])
                                                                yeni_rank = {p: i+1 for i, (p, _) in enumerate(dortlu)}
                                                                t_c1 = yeni_rank.get(c1_list[0], 99) + yeni_rank.get(c1_list[1], 99)
                                                                t_c2 = yeni_rank.get(c2_list[0], 99) + yeni_rank.get(c2_list[1], 99)
                                                                if t_c1 > t_c2: hatalar.append("❌ 1. Çiftler, 2. Çiftlerden daha güçlü (veya eşit) olmalıdır.")

                                                        if hatalar:
                                                            for h in hatalar: st.error(h)
                                                        else:
                                                            st.session_state[f"temp_hk_t1_{match_key}"] = form_secimleri_t1
                                                            st.session_state[hk_adim_key] = 2
                                                            st.rerun()

                                        elif hk_step == 2:
                                            st.markdown(f"<h4 style='color:#0B3B24;'>2. Adım: Takım Esame Listesi ({t2})</h4>", unsafe_allow_html=True)
                                            if t2_kaptan_girdi:
                                                st.success(f"✅ {t2} kadrosu Kaptan tarafından uygulamadan girilmiş.")
                                                st.session_state[f"temp_hk_t2_{match_key}"] = kasadaki_veri[t2]
                                                col_b1, col_b2 = st.columns(2)
                                                if col_b1.button("🔙 Geri Dön", key=f"btn_bk_t2_{match_key}", use_container_width=True):
                                                    st.session_state[hk_adim_key] = 1
                                                    st.rerun()
                                                if col_b2.button("Eşleşmeleri Göster ➡️", key=f"btn_sh_t2_{match_key}", use_container_width=True):
                                                    st.session_state[hk_adim_key] = 3
                                                    st.rerun()
                                            else:
                                                form_secimleri_t2 = st.session_state.get(f"temp_hk_t2_{match_key}", {})
                                                with st.form(key=f"form_hk_t2_{match_key}"):
                                                    for idx_mp_e2, row_mp_e2 in sort_maclar(g_df).iterrows():
                                                        brans = row_mp_e2['Branş']
                                                        if "Çiftler" in brans:
                                                            eski_val = form_secimleri_t2.get(brans, "")
                                                            eski_liste = [o.strip() for o in eski_val.split(",") if o.strip() in t2_havuz]
                                                            secim = st.multiselect(f"{brans} Seçimi", options=t2_havuz, default=eski_liste, max_selections=2, key=f"ms_t2_{match_key}_{brans}")
                                                            form_secimleri_t2[brans] = ", ".join(secim)
                                                        else:
                                                            eski_val = form_secimleri_t2.get(brans, "Seçiniz")
                                                            idx_e2 = (["Seçiniz"] + t2_havuz).index(eski_val) if eski_val in t2_havuz else 0
                                                            sec = st.selectbox(f"{brans} Seçimi", options=["Seçiniz"] + t2_havuz, index=idx_e2, key=f"sb_t2_{match_key}_{brans}")
                                                            form_secimleri_t2[brans] = sec if sec != "Seçiniz" else ""
                                                    
                                                    if st.form_submit_button("💾 Kaydet ve Eşleşmeleri Göster", use_container_width=True, type="primary"):
                                                        hatalar = []
                                                        format_secimi = st.session_state.grup_formatlari.get(grup_adi, "3 Maçlık (2 Tek, 1 Çift)")
                                                        o1 = form_secimleri_t2.get("1. Tekler")
                                                        o2 = form_secimleri_t2.get("2. Tekler")
                                                        o3 = form_secimleri_t2.get("3. Tekler")
                                                        r1 = t2_havuz.index(o1) if o1 in t2_havuz else -1
                                                        r2 = t2_havuz.index(o2) if o2 in t2_havuz else -1
                                                        r3 = t2_havuz.index(o3) if o3 in t2_havuz else -1
                                                        
                                                        for b in ["1. Çiftler", "2. Çiftler", "Çiftler"]:
                                                            c_str = form_secimleri_t2.get(b, "")
                                                            if c_str:
                                                                c_list = [o.strip() for o in c_str.split(",") if o.strip()]
                                                                if len(c_list) == 1: hatalar.append(f"❌ {b} maçına tek oyuncu yazılamaz. (Boş bırakabilirsiniz)")
                                                                
                                                        if r1 != -1 and r2 != -1 and r1 >= r2: hatalar.append("❌ 1. Tekler oyuncusu, 2. Teklerden üst sırada olmalıdır.")
                                                        if r2 != -1 and r3 != -1 and r2 >= r3: hatalar.append("❌ 2. Tekler oyuncusu, 3. Teklerden üst sırada olmalıdır.")
                                                        if r1 != -1 and r3 != -1 and r2 == -1 and r1 >= r3: hatalar.append("❌ 1. Tekler oyuncusu, 3. Teklerden üst sırada olmalıdır.")
                                                        
                                                        if o1 and o1 != "Seçiniz" and o1 == o2: hatalar.append("❌ Aynı oyuncu birden fazla tekler maçına yazılamaz.")
                                                        if o2 and o2 != "Seçiniz" and o2 == o3: hatalar.append("❌ Aynı oyuncu birden fazla tekler maçına yazılamaz.")
                                                        if o1 and o1 != "Seçiniz" and o1 == o3: hatalar.append("❌ Aynı oyuncu birden fazla tekler maçına yazılamaz.")
                                                        
                                                        if "5 Maçlık" in format_secimi:
                                                            c1_list = [o.strip() for o in form_secimleri_t2.get("1. Çiftler", "").split(",") if o.strip()]
                                                            c2_list = [o.strip() for o in form_secimleri_t2.get("2. Çiftler", "").split(",") if o.strip()]
                                                            ortak = set(c1_list).intersection(set(c2_list))
                                                            if ortak: hatalar.append("❌ Aynı oyuncu iki çiftler maçına da yazılamaz.")
                                                            
                                                            if len(c1_list) == 2 and len(c2_list) == 2 and not ortak:
                                                                dortlu = sorted([(p, t2_havuz.index(p)) for p in c1_list + c2_list if p in t2_havuz], key=lambda x: x[1])
                                                                yeni_rank = {p: i+1 for i, (p, _) in enumerate(dortlu)}
                                                                t_c1 = yeni_rank.get(c1_list[0], 99) + yeni_rank.get(c1_list[1], 99)
                                                                t_c2 = yeni_rank.get(c2_list[0], 99) + yeni_rank.get(c2_list[1], 99)
                                                                if t_c1 > t_c2: hatalar.append("❌ 1. Çiftler, 2. Çiftlerden daha güçlü (veya eşit) olmalıdır.")

                                                        if hatalar:
                                                            for h in hatalar: st.error(h)
                                                        else:
                                                            st.session_state[f"temp_hk_t2_{match_key}"] = form_secimleri_t2
                                                            st.session_state[hk_adim_key] = 3
                                                            st.rerun()
                                                if st.button("🔙 1. Takıma Geri Dön", key=f"btn_bk1_t2_{match_key}", use_container_width=True):
                                                    st.session_state[hk_adim_key] = 1
                                                    st.rerun()

                                        elif hk_step == 3:
                                            st.markdown(f"<h4 style='color:#0B3B24;'>3. Adım: Eşleşmeleri Onayla</h4>", unsafe_allow_html=True)
                                            temp_t1 = st.session_state.get(f"temp_hk_t1_{match_key}", {})
                                            temp_t2 = st.session_state.get(f"temp_hk_t2_{match_key}", {})
                                            
                                            st.info("Lütfen aşağıdaki eşleşmeleri kontrol edip Başhakem onayına gönderiniz.")
                                            
                                            for i_m, row_mp_3 in enumerate(sort_maclar(g_df).iterrows()):
                                                _, r_data = row_mp_3
                                                brans = r_data['Branş']
                                                o1 = temp_t1.get(brans, "Belirtilmedi")
                                                if not o1: o1 = "Belirtilmedi"
                                                o2 = temp_t2.get(brans, "Belirtilmedi")
                                                if not o2: o2 = "Belirtilmedi"
                                                st.markdown(f"**{i_m+1}. Maç ({brans}):** {o1} &nbsp;🆚&nbsp; {o2}")
                                                
                                            st.write("")
                                            col1, col2 = st.columns(2)
                                            if col1.button("🔙 Geri Dön (Düzenle)", key=f"btn_bk_edit_{match_key}", use_container_width=True):
                                                st.session_state[hk_adim_key] = 2
                                                st.rerun()
                                            if col2.button("📢 Başhakem Onayına Gönder", key=f"btn_snd_bh_{match_key}", type="primary", use_container_width=True):
                                                if match_key not in st.session_state.esame_kasasi:
                                                    st.session_state.esame_kasasi[match_key] = {}
                                                
                                                if not t1_kaptan_girdi:
                                                    st.session_state.esame_kasasi[match_key][t1] = temp_t1
                                                    st.session_state.esame_kasasi[match_key][t1]["_kaynak"] = "Hakem"
                                                if not t2_kaptan_girdi:
                                                    st.session_state.esame_kasasi[match_key][t2] = temp_t2
                                                    st.session_state.esame_kasasi[match_key][t2]["_kaynak"] = "Hakem"
                                                
                                                ortak_veriyi_kaydet()
                                                st.rerun()
                                                
                                else:
                                    form_verileri = {}
                                    for idx_mp, row_mp in sort_maclar(g_df).iterrows():
                                        mask = (st.session_state.skor_tablosu['Grup'] == row_mp['Grup']) & \
                                               (st.session_state.skor_tablosu['Gün'] == row_mp['Gün']) & \
                                               (st.session_state.skor_tablosu['Eşleşme'] == row_mp['Eşleşme']) & \
                                               (st.session_state.skor_tablosu['Branş'] == row_mp['Branş'])
                                        skor_row_df = st.session_state.skor_tablosu[mask]

                                        if not skor_row_df.empty:
                                            idx = skor_row_df.index[0]
                                            row = skor_row_df.iloc[0]
                                            brans_adi = row['Branş']
                                            is_ciftler = "Çiftler" in brans_adi
                                            
                                            if is_ciftler:
                                                c_isim, c_degistir = st.columns([3, 1])
                                                with c_isim:
                                                    st.markdown(f"**{brans_adi}** &nbsp;&nbsp;|&nbsp;&nbsp; {row.get('T1_Oyuncu', '-')} vs {row.get('T2_Oyuncu', '-')}")
                                                with c_degistir:
                                                    if st.button("🔄 Kadro Değiştir", key=f"btn_cift_edit_{idx}_{idx_mp}", use_container_width=True):
                                                        st.session_state[f"show_edit_{idx}"] = not st.session_state.get(f"show_edit_{idx}", False)
                                                        st.rerun()
                                                
                                                if st.session_state.get(f"show_edit_{idx}", False):
                                                    st.markdown("<div style='background-color:#fff3cd; padding:10px; border-radius:5px; border-left:3px solid #ffc107; margin-bottom:10px;'>", unsafe_allow_html=True)
                                                    st.write("👥 **Çiftler Oyuncularını Belirle / Güncelle**")
                                                    
                                                    grup_kadrolari = st.session_state.takim_kadrolari.get(grup_adi, {})
                                                    t1_havuzu = grup_kadrolari.get(t1, ["Belirtilmedi"])
                                                    t2_havuzu = grup_kadrolari.get(t2, ["Belirtilmedi"])
                                                    
                                                    eski_t1 = [x.strip() for x in str(row.get('T1_Oyuncu', '')).split(",") if x.strip() in t1_havuzu]
                                                    eski_t2 = [x.strip() for x in str(row.get('T2_Oyuncu', '')).split(",") if x.strip() in t2_havuzu]
                                                    
                                                    yeni_cift_t1 = st.multiselect(f"{t1} Kadrosu:", options=t1_havuzu, default=eski_t1, max_selections=2, key=f"ms_t1_cift_{idx}")
                                                    yeni_cift_t2 = st.multiselect(f"{t2} Kadrosu:", options=t2_havuzu, default=eski_t2, max_selections=2, key=f"ms_t2_cift_{idx}")
                                                    
                                                    if st.button("💾 Yeni Kadroyu Onayla ve Kapat", key=f"btn_cift_save_{idx}", type="primary"):
                                                        if len(yeni_cift_t1) == 1 or len(yeni_cift_t2) == 1:
                                                            st.error("❌ Çiftler maçına tek oyuncu yazılamaz. Lütfen 2 kişi seçin veya boş bırakın.")
                                                        else:
                                                            st.session_state.skor_tablosu.at[idx, 'T1_Oyuncu'] = ", ".join(yeni_cift_t1) if yeni_cift_t1 else "Belirtilmedi"
                                                            st.session_state.skor_tablosu.at[idx, 'T2_Oyuncu'] = ", ".join(yeni_cift_t2) if yeni_cift_t2 else "Belirtilmedi"
                                                            
                                                            if match_key in st.session_state.esame_kasasi:
                                                                if t1 in st.session_state.esame_kasasi[match_key]:
                                                                    st.session_state.esame_kasasi[match_key][t1][brans_adi] = ", ".join(yeni_cift_t1) if yeni_cift_t1 else ""
                                                                if t2 in st.session_state.esame_kasasi[match_key]:
                                                                    st.session_state.esame_kasasi[match_key][t2][brans_adi] = ", ".join(yeni_cift_t2) if yeni_cift_t2 else ""
                                                            
                                                            ortak_veriyi_kaydet()
                                                            st.session_state[f"show_edit_{idx}"] = False
                                                            st.rerun()
                                                    st.markdown("</div>", unsafe_allow_html=True)
                                            else:
                                                st.markdown(f"**{brans_adi}** &nbsp;&nbsp;|&nbsp;&nbsp; {row.get('T1_Oyuncu', '-')} vs {row.get('T2_Oyuncu', '-')}")

                                            st.markdown("<div style='background-color: rgba(128,128,128,0.05); padding: 15px; border-radius: 10px; border-left: 5px solid #0B3B24; margin-bottom: 10px;'>", unsafe_allow_html=True)
                                            durum_opts = ["Tamamlandı", "Takım 1 Kazandı (W/O)", "Takım 2 Kazandı (W/O)", "Takım 1 Kazandı (Ret.)", "Takım 2 Kazandı (Ret.)", "Çift Taraflı W/O"]
                                            mevcut_durum = str(row.get('Durum', 'Tamamlandı'))
                                            if mevcut_durum == "Takım 1 (W/O)": mevcut_durum = "Takım 2 Kazandı (W/O)"
                                            elif mevcut_durum == "Takım 2 (W/O)": mevcut_durum = "Takım 1 Kazandı (W/O)"
                                            elif mevcut_durum == "Takım 1 (Ret.)": mevcut_durum = "Takım 2 Kazandı (Ret.)"
                                            elif mevcut_durum == "Takım 2 (Ret.)": mevcut_durum = "Takım 1 Kazandı (Ret.)"
                                            d_idx = durum_opts.index(mevcut_durum) if mevcut_durum in durum_opts else 0
                                            
                                            c_stb, c_durum = st.columns([1, 2])
                                            with c_stb: secilen_stb = st.checkbox("Süper Tie-Break", value=bool(row.get('STB', False)), key=f"h_stb_{idx}_{idx_mp}")
                                            with c_durum: secilen_durum = st.selectbox("Maç Durumu", options=durum_opts, index=d_idx, key=f"h_durum_{idx}_{idx_mp}")
                                            
                                            is_wo = "W/O" in secilen_durum
                                            
                                            live_s1t1 = st.session_state.get(f"h_s1t1_{idx}_{idx_mp}", int(row['1.Set T1']))
                                            live_s1t2 = st.session_state.get(f"h_s1t2_{idx}_{idx_mp}", int(row['1.Set T2']))
                                            live_s2t1 = st.session_state.get(f"h_s2t1_{idx}_{idx_mp}", int(row['2.Set T1']))
                                            live_s2t2 = st.session_state.get(f"h_s2t2_{idx}_{idx_mp}", int(row['2.Set T2']))
                                            live_s3t1 = st.session_state.get(f"h_s3t1_{idx}_{idx_mp}", int(row['3.Set T1']))
                                            live_s3t2 = st.session_state.get(f"h_s3t2_{idx}_{idx_mp}", int(row['3.Set T2']))
                                            
                                            is_t1_winner = False
                                            is_t2_winner = False
                                            
                                            if secilen_durum in ["Takım 1 Kazandı (W/O)", "Takım 1 Kazandı (Ret.)"]:
                                                is_t1_winner = True
                                            elif secilen_durum in ["Takım 2 Kazandı (W/O)", "Takım 2 Kazandı (Ret.)"]:
                                                is_t2_winner = True
                                            elif secilen_durum == "Tamamlandı":
                                                t1_sets = (1 if live_s1t1 > live_s1t2 else 0) + (1 if live_s2t1 > live_s2t2 else 0) + (1 if live_s3t1 > live_s3t2 else 0)
                                                t2_sets = (1 if live_s1t2 > live_s1t1 else 0) + (1 if live_s2t2 > live_s2t1 else 0) + (1 if live_s3t2 > live_s3t1 else 0)
                                                if t1_sets > t2_sets: is_t1_winner = True
                                                elif t2_sets > t1_sets: is_t2_winner = True
                                            
                                            lbl_s1t1 = f"**:blue[{t1}]**" if is_t1_winner else f"{t1}"
                                            lbl_s1t2 = f"**:blue[{t2}]**" if is_t2_winner else f"{t2}"
                                            lbl_s2t1 = f"**:blue[{t1}]** " if is_t1_winner else f"{t1} "
                                            lbl_s2t2 = f"**:blue[{t2}]** " if is_t2_winner else f"{t2} "
                                            lbl_s3t1 = f"**:blue[{t1}]**  " if is_t1_winner else f"{t1}  "
                                            lbl_s3t2 = f"**:blue[{t2}]**  " if is_t2_winner else f"{t2}  "
                                            
                                            st.markdown("<br><p style='font-size:13px; font-weight:bold; color:#0B3B24; margin-bottom:5px; text-align:center;'>🎾 SET SKORLARI (Mobil Giriş)</p>", unsafe_allow_html=True)
                                            
                                            c_s1, c_s2, c_s3 = st.columns(3)
                                            with c_s1:
                                                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:12px; border-bottom:2px solid #ccc; margin-bottom:10px; padding-bottom:5px;'>1. SET</div>", unsafe_allow_html=True)
                                                s1t1 = st.number_input(lbl_s1t1, min_value=0, value=0 if is_wo else int(row['1.Set T1']), step=1, key=f"h_s1t1_{idx}_{idx_mp}", disabled=is_wo)
                                                s1t2 = st.number_input(lbl_s1t2, min_value=0, value=0 if is_wo else int(row['1.Set T2']), step=1, key=f"h_s1t2_{idx}_{idx_mp}", disabled=is_wo)
                                            with c_s2:
                                                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:12px; border-bottom:2px solid #ccc; margin-bottom:10px; padding-bottom:5px;'>2. SET</div>", unsafe_allow_html=True)
                                                s2t1 = st.number_input(lbl_s2t1, min_value=0, value=0 if is_wo else int(row['2.Set T1']), step=1, key=f"h_s2t1_{idx}_{idx_mp}", disabled=is_wo)
                                                s2t2 = st.number_input(lbl_s2t2, min_value=0, value=0 if is_wo else int(row['2.Set T2']), step=1, key=f"h_s2t2_{idx}_{idx_mp}", disabled=is_wo)
                                            with c_s3:
                                                st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:12px; border-bottom:2px solid #ccc; margin-bottom:10px; padding-bottom:5px;'>3. SET</div>", unsafe_allow_html=True)
                                                s3t1 = st.number_input(lbl_s3t1, min_value=0, value=0 if is_wo else int(row['3.Set T1']), step=1, key=f"h_s3t1_{idx}_{idx_mp}", disabled=is_wo)
                                                s3t2 = st.number_input(lbl_s3t2, min_value=0, value=0 if is_wo else int(row['3.Set T2']), step=1, key=f"h_s3t2_{idx}_{idx_mp}", disabled=is_wo)
                                            
                                            st.markdown("</div>", unsafe_allow_html=True)
                                            
                                            form_verileri[idx] = {
                                                "1.Set T1": s1t1, "1.Set T2": s1t2, "2.Set T1": s2t1, "2.Set T2": s2t2, "3.Set T1": s3t1, "3.Set T2": s3t2,
                                                "Durum": secilen_durum, "STB": secilen_stb, "Branş": row['Branş']
                                            }
                                            st.markdown("<hr style='margin: 8px 0px; opacity: 0.3;'>", unsafe_allow_html=True)

                                    if form_verileri:
                                        t1_wins, t2_wins, biten_mac = 0, 0, 0
                                        for i, f_row in form_verileri.items():
                                            w1, w2 = hesapla_mac_kazanani(f_row)
                                            t1_wins += w1; t2_wins += w2
                                            if w1 > 0 or w2 > 0 or f_row['Durum'] == "Çift Taraflı W/O": biten_mac += 1
                                            
                                        toplam_mac = len(form_verileri)
                                        st.markdown("---")
                                        if biten_mac == toplam_mac: st.success(f"🏆 **MAÇ SONUCU:** {t1} **{t1_wins} - {t2_wins}** {t2} *(Tüm branş skorları girildi)*")
                                        elif biten_mac > 0: st.info(f"📊 **ANLIK DURUM:** {t1} **{t1_wins} - {t2_wins}** {t2} *(Girilen maç: {biten_mac}/{toplam_mac})*")
                                        else: st.write("Henüz geçerli bir skor girilmedi.")

                                    # =========================================================================
                                    # YENİ "ETSİN AMA KAYDETSİN" ZEKASI AŞAĞIDADIR
                                    # =========================================================================
                                    if st.button(f"💾 {t1} - {t2} Skorlarını Kaydet", key=f"btn_h_skor_save_{grup_adi}_{eslesme_adi}_{tarih_str}", use_container_width=True, type="primary"):
                                        hata_mesajlari = []
                                        uyari_mesajlari = [] # KAYDEDİLMEYİ ENGELLEMEYEN UYARILAR
                                        
                                        for idx, guncel_row in form_verileri.items():
                                            mac_tanimi = f"{guncel_row['Branş']}"
                                            s1t1, s1t2 = guncel_row["1.Set T1"], guncel_row["1.Set T2"]
                                            s2t1, s2t2 = guncel_row["2.Set T1"], guncel_row["2.Set T2"]
                                            s3t1, s3t2 = guncel_row["3.Set T1"], guncel_row["3.Set T2"]
                                            durum = guncel_row["Durum"]
                                            ok1, msg1 = set_gecerli_mi(s1t1, s1t2, durum=durum)
                                            ok2, msg2 = set_gecerli_mi(s2t1, s2t2, durum=durum)
                                            ok3, msg3 = set_gecerli_mi(s3t1, s3t2, is_set3=True, durum=durum)
                                            
                                            if not ok1: hata_mesajlari.append(f"❌ {mac_tanimi} Set 1: {msg1}")
                                            if not ok2: hata_mesajlari.append(f"❌ {mac_tanimi} Set 2: {msg2}")
                                            if not ok3: hata_mesajlari.append(f"❌ {mac_tanimi} Set 3: {msg3}")
                                            
                                            if durum == "Tamamlandı":
                                                if s1t1 == 0 and s1t2 == 0 and s2t1 == 0 and s2t2 == 0 and s3t1 == 0 and s3t2 == 0:
                                                    # İŞTE BURASI: Hata vermek yerine sadece uyarı listesine ekliyoruz
                                                    uyari_mesajlari.append(f"⚠️ {mac_tanimi} (0-0 Bırakıldı)")
                                                else:
                                                    t1_s1_kazandi = s1t1 > s1t2
                                                    t2_s1_kazandi = s1t2 > s1t1
                                                    t1_s2_kazandi = s2t1 > s2t2
                                                    t2_s2_kazandi = s2t2 > s2t1
                                                    
                                                    if (t1_s1_kazandi and t1_s2_kazandi) or (t2_s1_kazandi and t2_s2_kazandi): 
                                                        if s3t1 != 0 or s3t2 != 0:
                                                            hata_mesajlari.append(f"❌ {mac_tanimi}: Maç 2-0 bittiği için 3. sete skor girilemez.")
                                                    
                                                    elif (t1_s1_kazandi and t2_s2_kazandi) or (t2_s1_kazandi and t1_s2_kazandi):
                                                        if s3t1 == 0 and s3t2 == 0:
                                                            hata_mesajlari.append(f"❌ {mac_tanimi}: Setlerde 1-1 eşitlik var, 3. set skoru girilmelidir.")
                                        
                                        # EĞER KIRMIZI HATA (GERÇEK BİR KURAL İHLALİ) VARSA KAYDETTİRME:
                                        if hata_mesajlari:
                                            for h in hata_mesajlari: st.error(h)
                                            
                                        # EĞER SADECE SARI UYARILAR VARSA, BAŞARIYLA KAYDET VE UYARIYI FISILDA:
                                        else:
                                            for idx, guncel_row in form_verileri.items():
                                                for k in ["1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2", "Durum", "STB"]:
                                                    st.session_state.skor_tablosu.at[idx, k] = guncel_row[k]
                                            if ortak_veriyi_kaydet():
                                                t1_isim = f":red[{t1}]" if t1_wins > t2_wins else t1
                                                t2_isim = f":red[{t2}]" if t2_wins > t1_wins else t2
                                                
                                                basari_metni = f"Skor Kaydedildi! Durum: {t1_isim}: {t1_wins} - {t2_isim}: {t2_wins}"
                                                
                                                # EĞER OYNANMAYAN MAÇ KALDIYSA METNİN YANINA UYARIYI EKLE:
                                                if uyari_mesajlari:
                                                    basari_metni += f" | Bekleyenler: {', '.join(uyari_mesajlari)}"
                                                    
                                                st.session_state.basari_mesaji = basari_metni
                                                st.rerun()
                                            else:
                                                st.error("Sistem meşgul, lütfen tekrar deneyin.")

            if not bugun_mac_var_mi:
                with container_bugun:
                    st.info("✅ Bugün için üzerinize atanmış bir maç bulunmamaktadır.")
