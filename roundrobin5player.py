# ==============================================================================
# 1. KÜTÜPHANELER VE BAŞLANGIÇ AYARLARI
# ==============================================================================
import streamlit as st
import streamlit.components.v1 as components
import sys
import subprocess
import pandas as pd
import datetime
import base64
import os
import re
import html
import time
import uuid

# --- KENDİ YAZDIĞIMIZ MODÜLLER ---
from pdf_yonetimi import generate_pdf, generate_combined_standings_pdf, generate_klasman_pdf, generate_toplu_klasman_pdf, draw_matrix_pdf, generate_mac_sonuc_belgesi
from gorsel_stiller import arkaplan_ekle, genel_css_yukle
from hesaplama_motoru import dogal_sirala, sort_maclar, set_gecerli_mi, hesapla_mac_kazanani, get_formatted_match_score, render_html_matrix, hesapla_tum_puan_durumu, sirala_grup_df
from veritabani_islemleri import ortak_veriyi_kaydet, ortak_veriyi_yukle, show_pdf, BELGELER_KLASORU
import ui_hakem_paneli
import ui_admin_paneli

st.set_page_config(page_title="Tenis Turnuva Otomasyonu", page_icon="🎾", layout="wide", initial_sidebar_state="collapsed")

arkaplan_ekle("arkaplan.jpg")
# Sayfanın en üst noktası için görünmez bir hedef
st.markdown('<div id="tepe-noktasi"></div>', unsafe_allow_html=True)

# --- HER SAYFADA GÖRÜNEN BAŞA DÖN BUTONU ---
basa_don_html = """
<style>
.basa-don-btn {
    position: fixed;
    bottom: 70px;
    right: 20px;
    background-color: #0B3B24;
    color: white !important;
    padding: 10px 15px;
    border-radius: 50px;
    text-align: center;
    text-decoration: none;
    font-size: 14px;
    font-weight: bold;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    z-index: 99999;
}
.basa-don-btn:hover {
    background-color: #E86C43;
}
</style>
<a href="#tepe-noktasi" target="_self" class="basa-don-btn">
    ⬆️ Başa Dön
</a>
"""
st.markdown(basa_don_html, unsafe_allow_html=True)
# ------------------------------------------
# ==============================================================================
# 2. SESSION STATE (HAFIZA) BAŞLATMA
# ==============================================================================
if "sistem_kilitli" not in st.session_state: st.session_state.sistem_kilitli = False
if "cevrimdisi_mod" not in st.session_state: st.session_state.cevrimdisi_mod = False
if "takim_kadrolari" not in st.session_state: st.session_state.takim_kadrolari = {}
if "admin_mi" not in st.session_state: st.session_state.admin_mi = False
if "kaptan_mi" not in st.session_state: st.session_state.kaptan_mi = False
if "hakem_mi" not in st.session_state: st.session_state.hakem_mi = False
if "kaptan_takim" not in st.session_state: st.session_state.kaptan_takim = ""
if "aktif_hakem" not in st.session_state: st.session_state.aktif_hakem = ""
if "selected_date_filter" not in st.session_state: st.session_state.selected_date_filter = datetime.date.today()
if "grup_formatlari" not in st.session_state: st.session_state.grup_formatlari = {}
if "grup_kategorileri" not in st.session_state: st.session_state.grup_kategorileri = {}
if "grup_asamalari" not in st.session_state: st.session_state.grup_asamalari = {}
if "duyuru_metni" not in st.session_state: st.session_state.duyuru_metni = ""
if "gunluk_notlar" not in st.session_state: st.session_state.gunluk_notlar = {}
if "takim_havuzu" not in st.session_state: st.session_state.takim_havuzu = {}
if "havuz_kategorileri" not in st.session_state: st.session_state.havuz_kategorileri = {}
if "havuz_yas_gruplari" not in st.session_state: st.session_state.havuz_yas_gruplari = {}
if "grup_siralamalari" not in st.session_state: st.session_state.grup_siralamalari = {}
if "grup_tamamlandi" not in st.session_state: st.session_state.grup_tamamlandi = {}
if "grup_yas_gruplari" not in st.session_state: st.session_state.grup_yas_gruplari = {}
if "grup_statuleri" not in st.session_state: st.session_state.grup_statuleri = {}
if "takim_pinleri" not in st.session_state: st.session_state.takim_pinleri = {}
if "esame_kasasi" not in st.session_state: st.session_state.esame_kasasi = {}
if "esame_onayli" not in st.session_state: st.session_state.esame_onayli = {}
if "hakem_listesi" not in st.session_state: st.session_state.hakem_listesi = []
if "hakem_pinleri" not in st.session_state: st.session_state.hakem_pinleri = {}
if "grup_gun_takvimi" not in st.session_state: st.session_state.grup_gun_takvimi = {}
if "yayinlanan_gunler" not in st.session_state: st.session_state.yayinlanan_gunler = {}
if "current_page" not in st.session_state: st.session_state.current_page = "Home"
if "aktif_asama" not in st.session_state: st.session_state.aktif_asama = "1. Aşama"

# ==============================================================================
# 3. VERİTABANI YÜKLEME VE GÜVENLİK
# ==============================================================================
genel_css_yukle(st.session_state.admin_mi, st.session_state.kaptan_mi, st.session_state.hakem_mi)

if 'skor_tablosu' not in st.session_state:
    ortak_veriyi_yukle()
    if 'skor_tablosu' not in st.session_state or st.session_state.skor_tablosu.empty:
        st.session_state.skor_tablosu = pd.DataFrame(columns=["id", "Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu", "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2", "Durum", "STB"])
    if 'mac_programi' not in st.session_state or st.session_state.mac_programi.empty:
        st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Skor", "Kazanan", "Hakem"])

if 'skor_tablosu' in st.session_state and 'Durum' not in st.session_state.skor_tablosu.columns:
    st.session_state.skor_tablosu['Durum'] = "Tamamlandı"
if 'skor_tablosu' in st.session_state and 'STB' not in st.session_state.skor_tablosu.columns:
    st.session_state.skor_tablosu['STB'] = False
if 'skor_tablosu' in st.session_state and 'id' not in st.session_state.skor_tablosu.columns:
    st.session_state.skor_tablosu['id'] = [str(uuid.uuid4()) for _ in range(len(st.session_state.skor_tablosu))]

if 'mac_programi' in st.session_state:
    if st.session_state.mac_programi.empty and len(st.session_state.mac_programi.columns) < 5:
         st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Skor", "Kazanan", "Hakem"])
    else:
        if "T1 Oyuncu" not in st.session_state.mac_programi.columns: st.session_state.mac_programi["T1 Oyuncu"] = ""
        if "T2 Oyuncu" not in st.session_state.mac_programi.columns: st.session_state.mac_programi["T2 Oyuncu"] = ""
        if "Kazanan" not in st.session_state.mac_programi.columns: st.session_state.mac_programi["Kazanan"] = ""
        if "Hakem" not in st.session_state.mac_programi.columns: st.session_state.mac_programi["Hakem"] = ""

def render_big_button(icon, title, target_page):
    if st.button(f"{icon}\n{title}", use_container_width=True, key=f"btn_main_{target_page}"):
        st.session_state.current_page = target_page
        st.rerun()

# ==============================================================================
# 4. YAN MENÜ (SIDEBAR) VE ÜST AŞAMA SEÇİCİ
# ==============================================================================
with st.sidebar:
    st.markdown("<h3 style='text-align: center;'>🎾 Menü</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("**Turnuva Aşaması:**")
    c_as1, c_as2 = st.columns(2)
    with c_as1:
        if st.button("1. Aşama", type="primary" if st.session_state.aktif_asama == "1. Aşama" else "secondary", use_container_width=True, key="side_1"):
            st.session_state.aktif_asama = "1. Aşama"
            st.rerun()
    with c_as2:
        if st.button("2. Aşama", type="primary" if st.session_state.aktif_asama == "2. Aşama" else "secondary", use_container_width=True, key="side_2"):
            st.session_state.aktif_asama = "2. Aşama"
            st.rerun()
            
    st.markdown("---")
    st.markdown("**Sayfalar:**")
    
    if st.session_state.admin_mi:
        menu_items_side = ["🏠 Ana Sayfa", "👥 Grup Ayarları", "📝 Esame Kontrol Merkezi", "✍️ Skor Girişi", "🏆 Puan Durumu", "📅 Maç Programı", "🛡️ Takım Kadroları", "📢 Duyurular", "👮‍♂️ Hakem Yönetimi", "⚙️ Yönetim & Dosya", "📈 İstatistikler"]
    elif st.session_state.hakem_mi:
        menu_items_side = ["🏠 Ana Sayfa", "✍️ Gözlemci Hakem Paneli", "📅 Maç Programı", "🛡️ Takım Kadroları"]
    else:
        menu_items_side = ["🏠 Ana Sayfa", "👨‍✈️ Kaptan Girişi", "👮‍♂️ Gözlemci Hakem Girişi", "🛡️ Takım Kadroları", "🏆 Puan Durumu", "📅 Maç Programı", "📢 Duyurular"]

    for menu in menu_items_side:
        if menu == "🏠 Ana Sayfa": target = "Home"
        elif menu == "👨‍✈️ Kaptan Girişi": target = "👨‍✈️ Kaptan Esame Girişi" 
        elif menu == "👮‍♂️ Gözlemci Hakem Girişi": target = "👮‍♂️ Gözlemci Hakem Girişi"
        elif menu == "⚙️ Yönetim": target = "⚙️ Yönetim & Dosya"
        else: target = menu
        
        is_active = (st.session_state.current_page == target)
        if st.button(menu, type="primary" if is_active else "secondary", use_container_width=True, key=f"side_nav_{menu}"):
            st.session_state.current_page = target
            st.rerun()
            
    if st.session_state.admin_mi or st.session_state.kaptan_mi or st.session_state.hakem_mi:
        st.markdown("---")
        if st.button("🔓 Çıkış Yap", type="primary", use_container_width=True):
            st.session_state.admin_mi = False
            st.session_state.kaptan_mi = False
            st.session_state.kaptan_takim = ""
            st.session_state.hakem_mi = False
            st.session_state.aktif_hakem = ""
            st.session_state.current_page = "Home"
            st.rerun()

    if st.session_state.admin_mi:
        st.markdown("---")
        st.markdown("**⚙️ Bağlantı Modu**")
        
        aktif_durum = st.session_state.get("cevrimdisi_mod", False)
        ucak_modu = st.toggle("✈️ Çevrimdışı Çalış (Diğerlerini Kilitle)", value=aktif_durum)
        
        if ucak_modu != aktif_durum:
            st.session_state.cevrimdisi_mod = ucak_modu
            st.session_state.sistem_kilitli = ucak_modu
            ortak_veriyi_kaydet()
            if not ucak_modu:
                msg_kutu = st.empty()
                msg_kutu.success("🌐 İNTERNET BAĞLANTISI SAĞLANDI! Veritabanı ile tüm veriler başarıyla eşitlendi.")
                time.sleep(5)
                msg_kutu.empty()
            st.rerun()

    st.divider()
    if st.button("🔄 Verileri Güncelle", use_container_width=True):
        with st.spinner("Kortlardaki son durum çekiliyor..."):
            ortak_veriyi_yukle()
        st.rerun()

# ==============================================================================
# 5. ÜST LOGOLAR VE BAKIM MODU UYARISI
# ==============================================================================
c_st1, c_st2, c_space, c_logos = st.columns([1.5, 1.5, 6, 3])
with c_st1:
    if st.button("1. Aşama", type="primary" if st.session_state.aktif_asama == "1. Aşama" else "secondary", use_container_width=True, key="top_1"):
        st.session_state.aktif_asama = "1. Aşama"; st.rerun()
with c_st2:
    if st.button("2. Aşama", type="primary" if st.session_state.aktif_asama == "2. Aşama" else "secondary", use_container_width=True, key="top_2"):
        st.session_state.aktif_asama = "2. Aşama"; st.rerun()
with c_logos:
    ttf_logo_html = ""
    if os.path.exists("TTFLOGO.png"):
        with open("TTFLOGO.png", "rb") as f: b64 = base64.b64encode(f.read()).decode()
        ttf_logo_html = f'<img src="data:image/png;base64,{b64}" style="height: 28px; border-radius: 6px; filter: drop-shadow(0px 1px 2px rgba(0,0,0,0.2));" alt="TTF Logo">'
    else:
        ttf_logo_html = '<div style="background-color: #0B3B24; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size:12px;">🇹🇷 TTF</div>'

    st.markdown(f"""
        <div style="display: flex; gap: 8px; justify-content: flex-end; align-items: center; margin-top: 2px;">
            <a href="https://i-kort.ttf.org.tr/" target="_blank" style="text-decoration: none;">
                <div style="background-color: #0056b3; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size:12px;">🎾 i-Kort</div>
            </a>
            <a href="https://www.ttf.org.tr/" target="_blank">{ttf_logo_html}</a>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

if st.session_state.get("sistem_kilitli", False) and not st.session_state.admin_mi:
    st.error("🚨 **SİSTEM ÇEVRİMDIŞI BAKIM MODUNDA:** Başhakem şu an masaüstü programda veri girişi yapmaktadır. Kaptanların ve Hakemlerin giriş yetkileri geçici olarak durdurulmuştur.")

# ==============================================================================
# 6. ANA SAYFA KOKPİTİ (HOME)
# ==============================================================================
if st.session_state.current_page == "Home":
    st.markdown("<div class='dev-buton'>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>🎾 Turnuva Ana Ekranı</h1><br>", unsafe_allow_html=True)
    
    if st.session_state.admin_mi:
        if st.session_state.get("cevrimdisi_mod", False):
            st.warning("⚠️ ŞU AN UÇAK MODUNDASINIZ! İnternet kullanmıyorsunuz. Yaptığınız değişiklikler yerel bilgisayarınıza kaydediliyor, yayına yansımıyor.")
            
        st.markdown(f"<h4 style='text-align:center;'>👨‍⚖️ Başhakem Kontrol Paneli ({st.session_state.aktif_asama})</h4><br>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_big_button("👥", "Grup Ayarları", "👥 Grup Ayarları")
        with c2: render_big_button("🕵️‍♂️", "Esame Kontrol", "📝 Esame Kontrol Merkezi")
        with c3: render_big_button("✍️", "Skor Girişi", "✍️ Skor Girişi")
        with c4: render_big_button("🏆", "Puan Durumu", "🏆 Puan Durumu")
        st.write("")
        c5, c6, c7, c8 = st.columns(4)
        with c5: render_big_button("📅", "Maç Programı", "📅 Maç Programı")
        with c6: render_big_button("🛡️", "Takım Kadroları", "🛡️ Takım Kadroları")
        with c7: render_big_button("👮‍♂️", "Hakem Yönetimi", "👮‍♂️ Hakem Yönetimi")
        with c8: render_big_button("⚙️", "Yönetim & Dosya", "⚙️ Yönetim & Dosya")
    
    elif st.session_state.kaptan_mi:
        st.markdown(f"<h4 style='text-align:center;'>👨‍✈️ Kaptan Paneli ({st.session_state.kaptan_takim})</h4><br>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_big_button("📝", "Esame Bildirimi", "👨‍✈️ Kaptan Esame Girişi")
        with c2: render_big_button("🛡️", "Takım Kadroları", "🛡️ Takım Kadroları")
        with c3: render_big_button("📅", "Maç Programı", "📅 Maç Programı")
        with c4: render_big_button("🏆", "Puan Durumu", "🏆 Puan Durumu")
        
    elif st.session_state.hakem_mi:
        st.markdown(f"<h4 style='text-align:center;'>👮‍♂️ Gözlemci Hakem Paneli ({st.session_state.aktif_hakem})</h4><br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: render_big_button("✍️", "Görevli Olduğum Maçlar", "✍️ Gözlemci Hakem Paneli")
        with c2: render_big_button("📅", "Tüm Maç Programı", "📅 Maç Programı")
        with c3: render_big_button("🛡️", "Takım Kadroları", "🛡️ Takım Kadroları")

    else:
        st.markdown(f"<h4 style='text-align:center;'>İzleyici Paneli ({st.session_state.aktif_asama})</h4><br>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1: render_big_button("👨‍✈️", "Kaptan Girişi", "👨‍✈️ Kaptan Esame Girişi") 
        with c2: render_big_button("👮‍♂️", "Gözlemci Hakem Girişi", "👮‍♂️ Gözlemci Hakem Girişi") 
        with c3: render_big_button("🛡️", "Takım Kadroları", "🛡️ Takım Kadroları")
        with c4: render_big_button("🏆", "Puan Durumu", "🏆 Puan Durumu")
        with c5: render_big_button("📅", "Maç Programı", "📅 Maç Programı")
        with c6: render_big_button("📢", "Duyurular", "📢 Duyurular")
        
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("<br><br><br><br>", unsafe_allow_html=True)
    if not st.session_state.admin_mi:
        with st.expander("⚙️ Sistem Yöneticisi (Başhakem) Girişi"):
            girilen_sifre = st.text_input("Şifre:", type="password", key="login_pass")
            if st.button("🔒 Yönetici Olarak Giriş Yap"):
                # Şifre artık doğrudan kodun içinde değil, Streamlit Secrets kasasından kontrol ediliyor
                if girilen_sifre == st.secrets.get("ADMIN_PASS", "zonguldak2026"):
                    st.session_state.admin_mi = True
                    st.session_state.kaptan_mi = False
                    st.session_state.hakem_mi = False
                    st.success("Giriş Başarılı!")
                    st.rerun()
                else: st.error("❌ Hatalı Şifre!")
    
    if st.session_state.admin_mi or st.session_state.kaptan_mi or st.session_state.hakem_mi:
        if st.button("🔓 Çıkış Yap (İzleyici Moduna Dön)", type="secondary"):
            st.session_state.admin_mi = False
            st.session_state.kaptan_mi = False
            st.session_state.kaptan_takim = ""
            st.session_state.hakem_mi = False
            st.session_state.aktif_hakem = ""
            st.session_state.current_page = "Home"
            st.rerun()

# ==============================================================================
# 7. İSTATİSTİKLER SAYFASI
# ==============================================================================
elif st.session_state.current_page == "📈 İstatistikler":
    aktif_asama = st.session_state.get("aktif_asama", "1. Aşama")
    
    st.header("📊 Turnuva İstatistikleri")
    kapsam = st.radio("Hesaplanacak Veriler:", [f"Sadece {aktif_asama}", "Tüm Turnuva (Genel Toplam)"], horizontal=True)
    st.markdown("---")

    tum_fikstur = st.session_state.get('skor_tablosu', pd.DataFrame())
    tum_program = st.session_state.get('mac_programi', pd.DataFrame())
    
    if kapsam == "Tüm Turnuva (Genel Toplam)":
        df_fikstur = tum_fikstur
        df_program = tum_program
    else:
        gecerli_gruplar = [g for g, asama in st.session_state.get('grup_asamalari', {}).items() if asama == aktif_asama]
        df_fikstur = tum_fikstur[tum_fikstur['Grup'].isin(gecerli_gruplar)] if not tum_fikstur.empty else pd.DataFrame()
        df_program = tum_program[tum_program['Grup'].isin(gecerli_gruplar)] if not tum_program.empty else pd.DataFrame()

    if df_fikstur.empty:
        st.warning(f"Seçilen kapsama ait henüz oluşturulmuş bir fikstür veya veri yok.")
    else:
        st.subheader("👥 Katılım Özeti")
        k1, k2, k3 = st.columns(3)
        toplam_grup = len(df_fikstur['Grup'].unique()) if 'Grup' in df_fikstur.columns else 0
        
        tum_takimlar = set()
        if 'Takım 1' in df_fikstur.columns: tum_takimlar.update(df_fikstur['Takım 1'].unique())
        if 'Takım 2' in df_fikstur.columns: tum_takimlar.update(df_fikstur['Takım 2'].unique())
        toplam_takim = len(tum_takimlar)
        
        toplam_oyuncu = 0
        if 'takim_havuzu' in st.session_state:
            for takim, oyuncular in st.session_state.takim_havuzu.items():
                if takim in tum_takimlar:
                    gercek_oyuncular = [o for o in oyuncular if o != "Belirtilmedi" and str(o).strip() != ""]
                    toplam_oyuncu += len(gercek_oyuncular)
        
        k1.metric("🏆 Toplam Kategori/Grup", toplam_grup)
        k2.metric("🛡️ Toplam Takım", toplam_takim)
        k3.metric("👥 Toplam Oyuncu (Kayıtlı)", toplam_oyuncu)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📅 Maç ve Fikstür İlerlemesi")
        
        toplam_mac = len(df_fikstur)
        planlanan_mac = len(df_program) 
            
        oynanan_mac = 0
        for idx, row in df_fikstur.iterrows():
            try:
                s1t1 = float(row.get('1.Set T1', 0))
                s1t2 = float(row.get('1.Set T2', 0))
            except:
                s1t1, s1t2 = 0, 0
                
            durum = str(row.get('Durum', 'Tamamlandı'))
            if (s1t1 > 0 or s1t2 > 0) or ("W/O" in durum) or ("Ret." in durum) or (durum == "Çift Taraflı W/O"):
                oynanan_mac += 1

        planlama_orani = (planlanan_mac / toplam_mac * 100) if toplam_mac > 0 else 0
        oynanma_orani = (oynanan_mac / toplam_mac * 100) if toplam_mac > 0 else 0

        f1, f2, f3, f4 = st.columns(4)
        f1.metric("📋 Toplam Bireysel Maç", toplam_mac)
        f2.metric("🗓️ Planlanan Maç", planlanan_mac)
        f3.metric("✅ Oynanan Maç", oynanan_mac)
        
        with f4:
            st.markdown(f"**Planlanma:** %{planlama_orani:.1f}")
            st.progress(min(int(planlama_orani) / 100.0, 1.0))
            st.markdown(f"**Tamamlanma:** %{oynanma_orani:.1f}")
            st.progress(min(int(oynanma_orani) / 100.0, 1.0))

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🎾 Kort İçi Skor İstatistikleri")
        
        toplam_set = 0
        toplam_oyun = 0
        for idx, row in df_fikstur.iterrows():
            try:
                setler = [
                    float(row.get('1.Set T1', 0)), float(row.get('1.Set T2', 0)),
                    float(row.get('2.Set T1', 0)), float(row.get('2.Set T2', 0)),
                    float(row.get('3.Set T1', 0)), float(row.get('3.Set T2', 0))
                ]
                if setler[0] > 0 or setler[1] > 0: toplam_set += 1
                if setler[2] > 0 or setler[3] > 0: toplam_set += 1
                if setler[4] > 0 or setler[5] > 0: toplam_set += 1
                toplam_oyun += sum(setler)
            except:
                pass

        oynanan_takim_maci = 0
        if 'Eşleşme' in df_fikstur.columns:
            df_oynanan = df_fikstur[(df_fikstur['1.Set T1'] > 0) | (df_fikstur['1.Set T2'] > 0) | (df_fikstur['Durum'].str.contains('W/O|Ret.'))]
            oynanan_takim_maci = len(df_oynanan[['Grup', 'Eşleşme', 'Gün']].drop_duplicates())

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("🎾 Oynanan Takım Eşleşmesi", oynanan_takim_maci)
        s2.metric("🏸 Oynanan Bireysel Maç", oynanan_mac)
        s3.metric("🔢 Toplam Oynanan Set", int(toplam_set))
        s4.metric("🎯 Toplam Oynanan Oyun", int(toplam_oyun))

# ==============================================================================
# 8. YÖNLENDİRME (ROUTER) VE MODÜL ÇAĞRILARI
# ==============================================================================
else:
    aktif_asama = st.session_state.aktif_asama
    menu_secim = st.session_state.current_page
    
    if st.session_state.admin_mi:
        menu_items_top = ["🏠 Ana Sayfa", "👥 Grup Ayarları", "📝 Esame Kontrol Merkezi", "✍️ Skor Girişi", "🏆 Puan Durumu", "📅 Maç Programı", "🛡️ Takım Kadroları", "📢 Duyurular", "👮‍♂️ Hakem Yönetimi", "⚙️ Yönetim"]
    elif st.session_state.kaptan_mi:
        menu_items_top = ["🏠 Ana Sayfa", "👨‍✈️ Kaptan Esame Girişi", "🛡️ Takım Kadroları", "🏆 Puan Durumu", "📅 Maç Programı", "📢 Duyurular"]
    elif st.session_state.hakem_mi:
        menu_items_top = ["🏠 Ana Sayfa", "✍️ Gözlemci Hakem Paneli", "📅 Maç Programı", "🛡️ Takım Kadroları"]
    else:
        menu_items_top = ["🏠 Ana Sayfa", "👨‍✈️ Kaptan Girişi", "👮‍♂️ Gözlemci Hakem Girişi", "🛡️ Takım Kadroları", "🏆 Puan Durumu", "📅 Maç Programı", "📢 Duyurular"]

    nav_cols = st.columns(len(menu_items_top))
    for i, menu in enumerate(menu_items_top):
        with nav_cols[i]:
            if menu == "👨‍✈️ Kaptan Girişi": target_menu = "👨‍✈️ Kaptan Esame Girişi"
            elif menu == "👮‍♂️ Gözlemci Hakem Girişi": target_menu = "👮‍♂️ Gözlemci Hakem Girişi"
            elif menu == "⚙️ Yönetim": target_menu = "⚙️ Yönetim & Dosya"
            elif menu == "🏠 Ana Sayfa": target_menu = "Home"
            else: target_menu = menu
            
            is_active = (st.session_state.current_page == target_menu)
            btn_type = "primary" if is_active else "secondary"
            if st.button(menu, type=btn_type, use_container_width=True, key=f"nav_top_{menu}"):
                st.session_state.current_page = target_menu
                st.rerun()

    st.markdown("---")
    st.markdown(f"<h3 style='margin-top: -10px;'>{menu_secim} ({aktif_asama})</h3>", unsafe_allow_html=True)

    # --- EKRANLARI YÖNETEN MODÜL ÇAĞRILARI ---
    if menu_secim == "✍️ Gözlemci Hakem Paneli":
        ui_hakem_paneli.hakem_panelini_ciz()

    elif menu_secim == "📝 Esame Kontrol Merkezi":
        ui_admin_paneli.esame_kontrol_merkezi_ciz()
        
    elif menu_secim == "👥 Grup Ayarları":
        ui_admin_paneli.grup_ayarlari_ciz(aktif_asama)

    elif menu_secim == "👮‍♂️ Hakem Yönetimi":
        ui_admin_paneli.hakem_yonetimi_ciz()

    elif menu_secim == "⚙️ Yönetim & Dosya":
        ui_admin_paneli.yonetim_ve_dosya_ciz(aktif_asama)

    # ==============================================================================
    # 9. KAPTAN VE HAKEM GİRİŞ EKRANLARI
    # ==============================================================================
    elif menu_secim == "👨‍✈️ Kaptan Esame Girişi":
        if st.session_state.get("sistem_kilitli", False) and not st.session_state.admin_mi:
            st.error("🚨 SİSTEM BAKIMDA: Başhakem şu an çevrimdışı (Uçak) modunda maç programını düzenliyor. Lütfen esamelerinizi kağıt üzerinde Başhakem masasına iletiniz.")
        elif not st.session_state.kaptan_mi:
            st.info("Kendi takımınızın maç kadrosunu (esame) bildirmek için PIN kodunuzla giriş yapınız.")
            col_k1, col_k2 = st.columns([2, 1])
            with col_k1:
                detayli_takimlar = []
                for t_isim in dogal_sirala(list(st.session_state.takim_havuzu.keys())):
                    kategori = st.session_state.havuz_kategorileri.get(t_isim, "")
                    yas = st.session_state.havuz_yas_gruplari.get(t_isim, "")
                    ek_bilgi = kategori if yas == "Yaş Belirtme" else f"{yas} {kategori}".strip()
                    
                    if ek_bilgi:
                        detayli_takimlar.append(f"{t_isim} ({ek_bilgi})")
                    else:
                        detayli_takimlar.append(t_isim)
                        
                secilen_detayli_takim = st.selectbox("Takımınızı Seçin:", ["Seçiniz"] + detayli_takimlar)
                secilen_takim_login = secilen_detayli_takim.split(" (")[0].strip() if secilen_detayli_takim != "Seçiniz" else "Seçiniz"
                girilen_pin = st.text_input("4 Haneli PIN Kodu:", type="password", key="login_pin_page")
                
                if st.button("🚀 Kaptan Olarak Giriş Yap", type="primary"):
                    if secilen_takim_login == "Seçiniz":
                        st.warning("Lütfen takımınızı seçin.")
                    elif secilen_takim_login not in st.session_state.takim_pinleri:
                        st.error("Bu takım için henüz PIN üretilmemiş. Başhakeme başvurunuz.")
                    elif girilen_pin == str(st.session_state.takim_pinleri[secilen_takim_login]):
                        st.session_state.kaptan_mi = True
                        st.session_state.admin_mi = False
                        st.session_state.hakem_mi = False
                        st.session_state.kaptan_takim = secilen_takim_login
                        st.success(f"Hoş Geldiniz, {secilen_takim_login} Kaptanı!")
                        st.rerun()
                    else:
                        st.error("❌ Hatalı PIN kodu!")
        else:
            takim_adi = st.session_state.kaptan_takim
            st.info(f"Hoş geldin, **{takim_adi}** Kaptanı. Aşağıda bugün oynayacağınız maçlar listelenmiştir. Lütfen kadronuzu seçip kasaya gönderin.")
            
            bugun = datetime.date.today().strftime("%d.%m.%Y")
            df_bugun = st.session_state.mac_programi[(st.session_state.mac_programi['Tarih'] == bugun) & ((st.session_state.mac_programi['Takım 1'] == takim_adi) | (st.session_state.mac_programi['Takım 2'] == takim_adi))]
            
            if df_bugun.empty:
                st.success("Bugün takımınıza ait planlanmış bir maç bulunmamaktadır.")
            else:
                for (grup, gun, eslesme), match_df in df_bugun.groupby(['Grup', 'Gün', 'Eşleşme']):
                    t1 = match_df.iloc[0]['Takım 1']
                    t2 = match_df.iloc[0]['Takım 2']
                    kort = match_df.iloc[0]['Kort']
                    saat = match_df.iloc[0]['Maç Saati']
                    
                    match_key = f"{grup}_{gun}_{eslesme}"
                    is_approved = st.session_state.esame_onayli.get(match_key, False)
                    
                    st.markdown(f"#### 🎾 {saat} - {kort} | {grup} | {t1} vs {t2}")
                    
                    if is_approved:
                        st.success("✅ Bu maçın esamesi başhakem tarafından onaylanmış ve fikstüre yansıtılmıştır. Artık değişiklik yapamazsınız.")
                    else:
                        st.warning("🔒 Kapalı Zarf Modu: Girdiğiniz isimler sadece Başhakem tarafından görülebilir.")
                        
                        grup_kadrolari = st.session_state.takim_kadrolari.get(grup, {})
                        oyuncu_havuzu = grup_kadrolari.get(takim_adi, [])
                        
                        if not oyuncu_havuzu or oyuncu_havuzu == ["Belirtilmedi"]:
                            st.error("Takımınızın oyuncu havuzu boş. Lütfen Başhakem ile iletişime geçin.")
                        else:
                            kasadaki_veri = st.session_state.esame_kasasi.get(match_key, {}).get(takim_adi, {})
                            format_secimi = st.session_state.grup_formatlari.get(grup, "3 Maçlık (2 Tek, 1 Çift)")
                            
                            if "5 Maçlık" in format_secimi:
                                branslar_kaptan_form = ["3. Tekler", "2. Tekler", "1. Tekler", "2. Çiftler", "1. Çiftler"]
                                label_map = {
                                    "3. Tekler": "🥉 3. Tekler Oyuncusu (Günün 1. Maçına Çıkar)",
                                    "2. Tekler": "🥈 2. Tekler Oyuncusu (Günün 2. Maçına Çıkar)",
                                    "1. Tekler": "🥇 1. Tekler Oyuncusu (Takımın en iyisi - Günün 3. Maçına Çıkar)",
                                    "2. Çiftler": "👥 2. Çiftler Oyuncuları (Günün 4. Maçına Çıkar)",
                                    "1. Çiftler": "👥 1. Çiftler Oyuncuları (En iyi çift - Günün 5. Maçına Çıkar)"
                                }
                            else:
                                branslar_kaptan_form = ["2. Tekler", "1. Tekler", "Çiftler"]
                                label_map = {
                                    "2. Tekler": "🥈 2. Tekler Oyuncusu (Günün 1. Maçına Çıkar)",
                                    "1. Tekler": "🥇 1. Tekler Oyuncusu (Takımın en iyisi - Günün 2. Maçına Çıkar)",
                                    "Çiftler": "👥 Çiftler Oyuncuları (Günün 3. ve Son Maçına Çıkar)"
                                }
                                
                            form_secimleri = {}
                            
                            with st.form(key=f"esame_form_{match_key}"):
                                for b in branslar_kaptan_form:
                                    gorsel_label = label_map.get(b, f"{b} Oyuncusu")
                                    
                                    if "Çiftler" in b:
                                        eski_cift_str = kasadaki_veri.get(b, "")
                                        eski_cift_liste = [o.strip() for o in eski_cift_str.split(",") if o.strip() in oyuncu_havuzu]
                                        secim = st.multiselect(gorsel_label, options=oyuncu_havuzu, default=eski_cift_liste, max_selections=2)
                                        form_secimleri[b] = ", ".join(secim)
                                    else:
                                        eski_tek = kasadaki_veri.get(b, "Seçiniz")
                                        idx = (["Seçiniz"] + oyuncu_havuzu).index(eski_tek) if eski_tek in oyuncu_havuzu else 0
                                        secim = st.selectbox(gorsel_label, options=["Seçiniz"] + oyuncu_havuzu, index=idx)
                                        form_secimleri[b] = secim if secim != "Seçiniz" else ""
                                        
                                if st.form_submit_button("💾 Kasaya Gönder (Başhakeme İlet)"):
                                    hatalar = []
                                    for b in branslar_kaptan_form:
                                        if "Çiftler" in b:
                                            c_str = form_secimleri.get(b, "")
                                            c_list = [o.strip() for o in c_str.split(",") if o.strip()]
                                            if len(c_list) == 1:
                                                hatalar.append(f"{b} maçına tek oyuncu yazılamaz. Lütfen {b} için 2 kişi seçin veya maçı tamamen boş bırakın.")
                                    
                                    o1 = form_secimleri.get("1. Tekler", "")
                                    o2 = form_secimleri.get("2. Tekler", "")
                                    o3 = form_secimleri.get("3. Tekler", "")
                                    
                                    r1 = oyuncu_havuzu.index(o1) if o1 in oyuncu_havuzu else -1
                                    r2 = oyuncu_havuzu.index(o2) if o2 in oyuncu_havuzu else -1
                                    r3 = oyuncu_havuzu.index(o3) if o3 in oyuncu_havuzu else -1
                                    
                                    if r1 != -1 and r2 != -1 and r1 >= r2: hatalar.append(f"1. Tekler oyuncusu ({o1}), 2. Tekler oyuncusundan ({o2}) takım listesinde daha üst sırada (daha iyi) olmalıdır.")
                                    if r2 != -1 and r3 != -1 and r2 >= r3: hatalar.append(f"2. Tekler oyuncusu ({o2}), 3. Tekler oyuncusundan ({o3}) takım listesinde daha üst sırada (daha iyi) olmalıdır.")
                                    if r1 != -1 and r3 != -1 and r2 == -1 and r1 >= r3: hatalar.append(f"1. Tekler oyuncusu ({o1}), 3. Tekler oyuncusundan ({o3}) takım listesinde daha üst sırada (daha iyi) olmalıdır.")
                                    
                                    if o1 != "" and o1 == o2: hatalar.append(f"Aynı oyuncuyu ({o1}) hem 1. Tek hem 2. Tek maçına yazamazsınız.")
                                    if o2 != "" and o2 == o3: hatalar.append(f"Aynı oyuncuyu ({o2}) birden fazla tekler maçına yazamazsınız.")
                                    if o1 != "" and o1 == o3: hatalar.append(f"Aynı oyuncuyu ({o1}) birden fazla tekler maçına yazamazsınız.")
                                    
                                    if "5 Maçlık" in format_secimi:
                                        c1_oyuncular = form_secimleri.get("1. Çiftler", "")
                                        c2_oyuncular = form_secimleri.get("2. Çiftler", "")
                                        
                                        c1_list = [o.strip() for o in c1_oyuncular.split(",") if o.strip()]
                                        c2_list = [o.strip() for o in c2_oyuncular.split(",") if o.strip()]
                                        ortak_oyuncular = set(c1_list).intersection(set(c2_list))
                                        if ortak_oyuncular:
                                            hatalar.append(f"Aynı oyuncuyu ({', '.join(ortak_oyuncular)}) hem 1. Çiftler hem de 2. Çiftler maçına yazamazsınız.")
                                                
                                        if len(c1_list) == 2 and len(c2_list) == 2 and not ortak_oyuncular:
                                            dortlu_havuz = []
                                            for p in c1_list + c2_list:
                                                if p in oyuncu_havuzu:
                                                    dortlu_havuz.append((p, oyuncu_havuzu.index(p)))
                                            
                                            dortlu_sirali = sorted(dortlu_havuz, key=lambda x: x[1])
                                            yeni_ranking = {oyuncu: (i + 1) for i, (oyuncu, idx) in enumerate(dortlu_sirali)}
                                            
                                            toplam_c1 = yeni_ranking[c1_list[0]] + yeni_ranking[c1_list[1]]
                                            toplam_c2 = yeni_ranking[c2_list[0]] + yeni_ranking[c2_list[1]]
                                            
                                            if toplam_c1 > toplam_c2:
                                                hatalar.append(f"Çiftler Sıralama Hatası: Seçilen 4 oyuncu arasındaki güç dengesine göre, 1. Çiftler daha güçlü veya eşit (Toplam: {toplam_c1}) olmalıdır. Mevcut durumda 2. Çiftler (Toplam: {toplam_c2}) daha güçlü görünüyor.")
                                    
                                    if hatalar:
                                        st.error("❌ **KADRO HATASI (Gönderilemedi):** Lütfen aşağıdaki hataları düzeltin!\n\n" + "\n".join([f"- {h}" for h in hatalar]))
                                    else:
                                        if match_key not in st.session_state.esame_kasasi:
                                            st.session_state.esame_kasasi[match_key] = {}
                                        
                                        st.session_state.esame_kasasi[match_key][takim_adi] = form_secimleri
                                        if ortak_veriyi_kaydet():
                                            st.success("Kadro başarıyla kasaya kilitlendi! Başhakem onayına kadar gizli kalacaktır.")
                                            st.rerun()
                                        else:
                                            st.error("⚠️ Sistem şu an başka bir takımın kaydını işliyor (Meşgul). Çakışma önlendi, lütfen 3 saniye bekleyip butona tekrar basınız.")
                    st.divider()

    elif menu_secim == "👮‍♂️ Gözlemci Hakem Girişi":
        if st.session_state.get("sistem_kilitli", False) and not st.session_state.admin_mi:
            st.error("🚨 SİSTEM BAKIMDA: Başhakem şu an çevrimdışı (Uçak) modunda maç programını düzenliyor.")
        elif not st.session_state.hakem_mi:
            st.info("Görevli olduğunuz maçların skorlarını girebilmek için PIN kodunuzla giriş yapınız.")
            col_h1, col_h2 = st.columns([2, 1])
            with col_h1:
                hakem_listesi = st.session_state.get("hakem_listesi", [])
                secilen_hakem = st.selectbox("Hakem Seçin:", ["Seçiniz"] + hakem_listesi)
                girilen_pin = st.text_input("4 Haneli PIN Kodu:", type="password", key="login_pin_hakem")
                
                if st.button("🚀 Hakem Olarak Giriş Yap", type="primary"):
                    if secilen_hakem == "Seçiniz":
                        st.warning("Lütfen isminizi seçin.")
                    elif secilen_hakem not in st.session_state.get("hakem_pinleri", {}):
                        st.error("Bu hakem için PIN üretilmemiş. Başhakeme başvurunuz.")
                    elif girilen_pin == str(st.session_state.hakem_pinleri[secilen_hakem]):
                        st.session_state.hakem_mi = True
                        st.session_state.admin_mi = False
                        st.session_state.kaptan_mi = False
                        st.session_state.aktif_hakem = secilen_hakem
                        st.session_state.current_page = "✍️ Gözlemci Hakem Paneli"
                        st.success(f"Hoş Geldiniz, {secilen_hakem}!")
                        st.rerun()
                    else:
                        st.error("❌ Hatalı PIN kodu!")
        else:
            st.success(f"Zaten {st.session_state.aktif_hakem} olarak giriş yaptınız. Lütfen menüden Hakem Paneli'ne geçiş yapın.")

    # ==============================================================================
    # 10. SKOR GİRİŞİ (TARİH FİLTRELİ VE KOKPİT EKRANI)
    # ==============================================================================
    elif menu_secim == "✍️ Skor Girişi":
        if st.session_state.admin_mi:
            st.info("💡 **Not:** Bu sayfa 'Maç Programı'na aktarılan tarihlere göre çalışır. Kaptan esameleri onaylandığında buraya düşer.")
            if not st.session_state.skor_tablosu.empty:
                gecerli_gruplar_t2 = [g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama]
                
                if not gecerli_gruplar_t2:
                    st.info(f"{aktif_asama} için kayıtlı grup bulunmamaktadır.")
                else:
                    df_skor = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'].isin(gecerli_gruplar_t2)].copy()
                    df_prog = st.session_state.mac_programi.copy()
                    
                    tarih_map = {}
                    saat_map = {}
                    kort_map = {}
                    for _, r in df_prog.iterrows():
                        k = f"{r['Grup']}_{r['Gün']}_{r['Eşleşme']}"
                        tarih_map[k] = str(r.get('Tarih', ''))
                        saat_map[k] = str(r.get('Maç Saati', ''))
                        kort_map[k] = str(r.get('Kort', ''))
                        
                    def get_tarih(row):
                        k = f"{row['Grup']}_{row['Gün']}_{row['Eşleşme']}"
                        val = tarih_map.get(k, "")
                        return val if val else "Atanmadı"
                        
                    df_skor['Tarih_Filtre'] = df_skor.apply(get_tarih, axis=1)
                    tarihler = [t for t in df_skor['Tarih_Filtre'].unique() if t != "Atanmadı"]
                    tarihler_sirali = sorted(tarihler, key=lambda x: datetime.datetime.strptime(x, "%d.%m.%Y").date() if x else datetime.date.min)
                    
                    secenekler = tarihler_sirali
                    
                    bugun_str = datetime.date.today().strftime("%d.%m.%Y")
                    def_idx = secenekler.index(bugun_str) if bugun_str in secenekler else 0
                    
                    if not secenekler:
                        st.warning("⚠️ Henüz maç programında tarihi belirlenmiş hiçbir maç bulunmuyor. Lütfen önce 'Grup Ayarları' veya 'Maç Programı' sayfasından maçları günlere atayın.")
                    else:
                        secilen_tarih = st.selectbox("📅 Tarih Seçin:", secenekler, index=def_idx)
                        hedef_tarih = secilen_tarih
                        df_tarih = df_skor[df_skor['Tarih_Filtre'] == hedef_tarih]
                        
                        if df_tarih.empty:
                            st.success("Seçilen tarihte oynanacak maç bulunmuyor.")
                        else:
                            gruplar = dogal_sirala(df_tarih['Grup'].unique().tolist())
                            grup_secenekleri = ["Tümü (Tüm Grupları Göster)"] + gruplar
                            secilen_grup = st.selectbox("🛡️ Grup Seçin:", grup_secenekleri, key="skor_grup_sec")
                            
                            # --- KOKPİT (DASHBOARD) HESAPLAMALARI ---
                            if secilen_grup == "Tümü (Tüm Grupları Göster)":
                                df_aktif = df_tarih.copy()
                            else:
                                df_aktif = df_tarih[df_tarih['Grup'] == secilen_grup].copy()
                                
                            baslamamis = 0
                            devam_eden = 0
                            bitmis = 0
                            toplam_eslesme = 0
                            
                            eslesme_durumlari = {} 
                            
                            for (g_ad, es_ad), d_es in df_aktif.groupby(['Grup', 'Eşleşme']):
                                toplam_eslesme += 1
                                t_mac_sayisi = len(d_es)
                                biten_mac = 0
                                skor_var_mi = False
                                
                                k_key = f"{g_ad}_{d_es.iloc[0]['Gün']}_{es_ad}"
                                m_kort = kort_map.get(k_key, "")
                                kort_var_mi = m_kort != "" and m_kort != "Kort 1" and m_kort != "Kort Belirsiz" 
                                
                                for _, r in d_es.iterrows():
                                    d = str(r.get('Durum', 'Tamamlandı'))
                                    s1_1, s1_2 = int(r.get('1.Set T1', 0)), int(r.get('1.Set T2', 0))
                                    if "W/O" in d or "Ret." in d or s1_1 > 0 or s1_2 > 0 or d == "Çift Taraflı W/O":
                                        skor_var_mi = True
                                        biten_mac += 1
                                        
                                if biten_mac == t_mac_sayisi:
                                    bitmis += 1
                                    eslesme_durumlari[k_key] = "🟢 Tamamlandı"
                                elif skor_var_mi or kort_var_mi:
                                    devam_eden += 1
                                    eslesme_durumlari[k_key] = f"🟡 Devam Ediyor ({biten_mac}/{t_mac_sayisi})"
                                else:
                                    baslamamis += 1
                                    eslesme_durumlari[k_key] = "🔴 Başlamadı"
                                    
                            # --- KOMPAKT DASHBOARD ---
                            tamamlanma_orani = int((bitmis / toplam_eslesme) * 100) if toplam_eslesme > 0 else 0
                            
                            st.markdown(f"""
                            <div style='display: flex; justify-content: space-between; align-items: center; background-color: #f8f9fa; padding: 12px 20px; border-radius: 6px; border-left: 4px solid #0B3B24; border: 1px solid #e0e0e0; margin-bottom: 20px; font-family: sans-serif;'>
                                <div style='font-size: 14px; color: #333;'><b>📋 Toplam:</b> {toplam_eslesme}</div>
                                <div style='font-size: 14px; color: #d9534f;'><b>🔴 Başlamadı:</b> {baslamamis}</div>
                                <div style='font-size: 14px; color: #f0ad4e;'><b>🟡 Devam Ediyor:</b> {devam_eden}</div>
                                <div style='font-size: 14px; color: #28a745;'><b>🟢 Bitti:</b> {bitmis}</div>
                                <div style='font-size: 15px; font-weight: bold; color: #0B3B24;'>🎯 Tamamlanma: %{tamamlanma_orani}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # --- EXPANDER LİSTELEME ---
                            gosterilecek_gruplar = gruplar if secilen_grup == "Tümü (Tüm Grupları Göster)" else [secilen_grup]
                            
                            for cur_grup in gosterilecek_gruplar:
                                df_gun = df_aktif[df_aktif['Grup'] == cur_grup]
                                eslesmeler_listesi = dogal_sirala(df_gun['Eşleşme'].unique().tolist())
                                
                                for eslesme_adi in eslesmeler_listesi:
                                    df_eslesme = df_gun[df_gun['Eşleşme'] == eslesme_adi]
                                    t1 = df_eslesme.iloc[0]['Takım 1']
                                    t2 = df_eslesme.iloc[0]['Takım 2']
                                    gun_val = df_eslesme.iloc[0]['Gün']
                                    
                                    k_key = f"{cur_grup}_{gun_val}_{eslesme_adi}"
                                    m_saat = saat_map.get(k_key, "??:??")
                                    m_kort = kort_map.get(k_key, "Kort Belirsiz")
                                    
                                    durum_str = eslesme_durumlari.get(k_key, "Bilinmiyor")
                                    baslik = f"▶ {m_saat} | {m_kort} | {cur_grup} | {t1} vs {t2} [{durum_str}]"
                                    
                                    with st.expander(baslik, expanded=False):
                                        form_verileri = {}
                                        format_secimi = st.session_state.grup_formatlari.get(cur_grup, "3 Maçlık (2 Tek, 1 Çift)")
                                        
                                        for idx_mp, row_mp in sort_maclar(df_eslesme).iterrows():
                                            idx = idx_mp
                                            row = row_mp
        
                                            s1t1_k = int(row['1.Set T1'])
                                            s1t2_k = int(row['1.Set T2'])
                                            durum_k = str(row.get('Durum', 'Tamamlandı'))
                                            skor_girilmis = s1t1_k > 0 or s1t2_k > 0 or durum_k != "Tamamlandı"
                                            
                                            if skor_girilmis:
                                                st.markdown(f"<div style='padding: 6px 10px; border-radius: 6px; background-color: rgba(232, 108, 67, 0.15); border-left: 4px solid #E86C43; margin-bottom: 5px;'><b style='color: #E86C43;'>✅ {row['Branş']} - Skor Kayıtlı</b></div>", unsafe_allow_html=True)
                                            else:
                                                st.markdown(f"<div style='padding: 6px 10px; margin-bottom: 5px; opacity: 0.8;'><b>🔹 {row['Branş']}</b></div>", unsafe_allow_html=True)
                                            
                                            h_cols = st.columns([2.8, 2.8, 2.6, 1.4, 0.2, 1.4, 0.2, 1.4])
                                            
                                            t1_isim, t2_isim = row['Takım 1'], row['Takım 2']
                                            h_cols[0].markdown(f"<div style='font-size:14px; font-weight:bold; padding-bottom:5px;'>🛡️ {t1_isim}</div>", unsafe_allow_html=True)
                                            h_cols[1].markdown(f"<div style='font-size:14px; font-weight:bold; padding-bottom:5px;'>🛡️ {t2_isim}</div>", unsafe_allow_html=True)
                                            h_cols[3].markdown("<div style='text-align:center; font-size:11px; font-weight:bold; border-bottom: 2px solid rgba(128,128,128,0.5); padding-bottom: 2px;'>1. SET</div>", unsafe_allow_html=True)
                                            h_cols[5].markdown("<div style='text-align:center; font-size:11px; font-weight:bold; border-bottom: 2px solid rgba(128,128,128,0.5); padding-bottom: 2px;'>2. SET</div>", unsafe_allow_html=True)
                                            h_cols[7].markdown("<div style='text-align:center; font-size:11px; font-weight:bold; border-bottom: 2px solid rgba(128,128,128,0.5); padding-bottom: 2px;'>3. SET</div>", unsafe_allow_html=True)
        
                                            r_cols = st.columns([2.8, 2.8, 2.1, 0.5, 0.7, 0.7, 0.2, 0.7, 0.7, 0.2, 0.7, 0.7])
                                            
                                            grup_kadro_dict = st.session_state.takim_kadrolari.get(cur_grup, {})
                                            t1_havuz = grup_kadro_dict.get(t1_isim, ["Belirtilmedi"])
                                            t2_havuz = grup_kadro_dict.get(t2_isim, ["Belirtilmedi"])
                                            
                                            with r_cols[0]:
                                                if "Çiftler" in str(row['Branş']):
                                                    eski_kayit1 = str(row['T1_Oyuncu'])
                                                    for char in ["[", "]", "'", '"']: eski_kayit1 = eski_kayit1.replace(char, "")
                                                    eski_oyuncular1 = [o.strip() for o in eski_kayit1.split(",") if o.strip() and o.strip() in t1_havuz and o.strip() != "Seçiniz"]
                                                    t1_oyuncu = st.multiselect("T1 Oyuncular", options=t1_havuz, default=eski_oyuncular1, max_selections=2, key=f"t1_o_{idx}", label_visibility="collapsed")
                                                    t1_oyuncu_str = ", ".join(t1_oyuncu)
                                                else:
                                                    opts1 = ["Seçiniz"] + [o for o in t1_havuz if o != "Belirtilmedi"]
                                                    eski_veri1 = str(row['T1_Oyuncu']).strip()
                                                    for char in ["[", "]", "'", '"']: eski_veri1 = eski_veri1.replace(char, "")
                                                    eski_o1 = eski_veri1 if eski_veri1 and eski_veri1 not in ["nan", "None", ""] else "Seçiniz"
                                                    idx1 = opts1.index(eski_o1) if eski_o1 in opts1 else 0
                                                    t1_secim_raw = st.selectbox("T1 Oyuncu", options=opts1, index=idx1, key=f"t1_o_{idx}", label_visibility="collapsed")
                                                    t1_oyuncu_str = t1_secim_raw if t1_secim_raw != "Seçiniz" else ""
        
                                            with r_cols[1]:
                                                if "Çiftler" in str(row['Branş']):
                                                    eski_kayit2 = str(row['T2_Oyuncu'])
                                                    for char in ["[", "]", "'", '"']: eski_kayit2 = eski_kayit2.replace(char, "")
                                                    eski_oyuncular2 = [o.strip() for o in eski_kayit2.split(",") if o.strip() and o.strip() in t2_havuz and o.strip() != "Seçiniz"]
                                                    t2_oyuncu = st.multiselect("T2 Oyuncular", options=t2_havuz, default=eski_oyuncular2, max_selections=2, key=f"t2_o_{idx}", label_visibility="collapsed")
                                                    t2_oyuncu_str = ", ".join(t2_oyuncu)
                                                else:
                                                    opts2 = ["Seçiniz"] + [o for o in t2_havuz if o != "Belirtilmedi"]
                                                    eski_veri2 = str(row['T2_Oyuncu']).strip()
                                                    for char in ["[", "]", "'", '"']: eski_veri2 = eski_veri2.replace(char, "")
                                                    eski_o2 = eski_veri2 if eski_veri2 and eski_veri2 not in ["nan", "None", ""] else "Seçiniz"
                                                    idx2 = opts2.index(eski_o2) if eski_o2 in opts2 else 0
                                                    t2_secim_raw = st.selectbox("T2 Oyuncu", options=opts2, index=idx2, key=f"t2_o_{idx}", label_visibility="collapsed")
                                                    t2_oyuncu_str = t2_secim_raw if t2_secim_raw != "Seçiniz" else ""
                                            
                                            with r_cols[2]:
                                                durum_opts = ["Tamamlandı", "Takım 1 Kazandı (W/O)", "Takım 2 Kazandı (W/O)", "Takım 1 Kazandı (Ret.)", "Takım 2 Kazandı (Ret.)", "Çift Taraflı W/O"]
                                                mevcut_durum = str(row.get('Durum', 'Tamamlandı'))
                                                if mevcut_durum == "Takım 1 (W/O)": mevcut_durum = "Takım 2 Kazandı (W/O)"
                                                elif mevcut_durum == "Takım 2 (W/O)": mevcut_durum = "Takım 1 Kazandı (W/O)"
                                                elif mevcut_durum == "Takım 1 (Ret.)": mevcut_durum = "Takım 2 Kazandı (Ret.)"
                                                elif mevcut_durum == "Takım 2 (Ret.)": mevcut_durum = "Takım 1 Kazandı (Ret.)"
                                                d_idx = durum_opts.index(mevcut_durum) if mevcut_durum in durum_opts else 0
                                                secilen_durum = st.selectbox("Durum", options=durum_opts, index=d_idx, key=f"durum_{idx}", label_visibility="collapsed")
        
                                            with r_cols[3]:
                                                mevcut_stb = bool(row.get('STB', False))
                                                secilen_stb = st.checkbox("STB", value=mevcut_stb, key=f"stb_{idx}")
        
                                            is_wo = "W/O" in secilen_durum
                                            
                                            s1t1 = r_cols[4].number_input("S1T1", min_value=0, value=0 if is_wo else int(row['1.Set T1']), step=1, key=f"s1t1_{idx}", label_visibility="collapsed", disabled=is_wo)
                                            s1t2 = r_cols[5].number_input("S1T2", min_value=0, value=0 if is_wo else int(row['1.Set T2']), step=1, key=f"s1t2_{idx}", label_visibility="collapsed", disabled=is_wo)
                                            
                                            r_cols[6].markdown("<div style='text-align:center; opacity:0.5; margin-top:5px; font-weight:bold;'>|</div>", unsafe_allow_html=True)
                                            
                                            s2t1 = r_cols[7].number_input("S2T1", min_value=0, value=0 if is_wo else int(row['2.Set T1']), step=1, key=f"s2t1_{idx}", label_visibility="collapsed", disabled=is_wo)
                                            s2t2 = r_cols[8].number_input("S2T2", min_value=0, value=0 if is_wo else int(row['2.Set T2']), step=1, key=f"s2t2_{idx}", label_visibility="collapsed", disabled=is_wo)
                                            
                                            r_cols[9].markdown("<div style='text-align:center; opacity:0.5; margin-top:5px; font-weight:bold;'>|</div>", unsafe_allow_html=True)
                                            
                                            s3t1 = r_cols[10].number_input("S3T1", min_value=0, value=0 if is_wo else int(row['3.Set T1']), step=1, key=f"s3t1_{idx}", label_visibility="collapsed", disabled=is_wo)
                                            s3t2 = r_cols[11].number_input("S3T2", min_value=0, value=0 if is_wo else int(row['3.Set T2']), step=1, key=f"s3t2_{idx}", label_visibility="collapsed", disabled=is_wo)
                                            
                                            form_verileri[idx] = {
                                                "T1_Oyuncu": t1_oyuncu_str, "T2_Oyuncu": t2_oyuncu_str,
                                                "1.Set T1": s1t1, "1.Set T2": s1t2, "2.Set T1": s2t1, "2.Set T2": s2t2, "3.Set T1": s3t1, "3.Set T2": s3t2,
                                                "Durum": secilen_durum, "STB": secilen_stb, "Eşleşme": str(row['Eşleşme'])
                                            }
                                            st.divider()
                                            
                                        eslesme_dict = {}
                                        for idx, g_row in form_verileri.items():
                                            row_data = df_gun.loc[idx]
                                            brans = row_data["Branş"]
                                            if eslesme_adi not in eslesme_dict:
                                                eslesme_dict[eslesme_adi] = {"T1": {"isim": row_data["Takım 1"], "secimler": {}}, "T2": {"isim": row_data["Takım 2"], "secimler": {}}}
                                            eslesme_dict[eslesme_adi]["T1"]["secimler"][brans] = g_row["T1_Oyuncu"]
                                            eslesme_dict[eslesme_adi]["T2"]["secimler"][brans] = g_row["T2_Oyuncu"]
                                    
                                        for team_key in ["T1", "T2"]:
                                            takim_ismi = eslesme_dict[eslesme_adi][team_key]["isim"]
                                            havuz = grup_kadro_dict.get(takim_ismi, [])
                                            secimler = eslesme_dict[eslesme_adi][team_key]["secimler"]
                                            o1 = secimler.get("1. Tekler")
                                            o2 = secimler.get("2. Tekler")
                                            o3 = secimler.get("3. Tekler")
                                            r1 = havuz.index(o1) if o1 in havuz else -1
                                            r2 = havuz.index(o2) if o2 in havuz else -1
                                            r3 = havuz.index(o3) if o3 in havuz else -1
                                            
                                            uyarilar = []
                                            for b in ["1. Çiftler", "2. Çiftler", "Çiftler"]:
                                                c_str = secimler.get(b, "")
                                                if c_str:
                                                    c_list = [o.strip() for o in c_str.split(",") if o.strip()]
                                                    if len(c_list) == 1:
                                                        uyarilar.append(f"**{b}** maçına tek bir oyuncu seçilmiş. Çiftler maçı için 2 kişi seçilmeli veya boş bırakılmalıdır.")
                                                        
                                            if r1 != -1 and r2 != -1 and r1 >= r2: uyarilar.append(f"**1. Tekler** oyuncusu ({o1}), **2. Tekler** oyuncusundan ({o2}) takım listesinde daha üst sırada olmalıdır.")
                                            if r2 != -1 and r3 != -1 and r2 >= r3: uyarilar.append(f"**2. Tekler** oyuncusu ({o2}), **3. Tekler** oyuncusundan ({o3}) takım listesinde daha üst sırada olmalıdır.")
                                            if r1 != -1 and r3 != -1 and r2 == -1 and r1 >= r3: uyarilar.append(f"**1. Tekler** oyuncusu ({o1}), **3. Tekler** oyuncusundan ({o3}) takım listesinde daha üst sırada olmalıdır.")
                                            
                                            if o1 and o1 == o2: uyarilar.append(f"Aynı oyuncuyu ({o1}) birden fazla tekler maçına yazamazsınız.")
                                            if o2 and o2 == o3: uyarilar.append(f"Aynı oyuncuyu ({o2}) birden fazla tekler maçına yazamazsınız.")
                                            if o1 and o1 == o3: uyarilar.append(f"Aynı oyuncuyu ({o1}) birden fazla tekler maçına yazamazsınız.")
                                            
                                            if "5 Maçlık" in format_secimi:
                                                c1_oyuncular = secimler.get("1. Çiftler", "")
                                                c2_oyuncular = secimler.get("2. Çiftler", "")
                                                c1_list = [o.strip() for o in c1_oyuncular.split(",") if o.strip()]
                                                c2_list = [o.strip() for o in c2_oyuncular.split(",") if o.strip()]
                                                
                                                ortak_oyuncular = set(c1_list).intersection(set(c2_list))
                                                if ortak_oyuncular:
                                                    uyarilar.append(f"Aynı oyuncuyu ({', '.join(ortak_oyuncular)}) hem 1. Çiftler hem 2. Çiftler maçına yazamazsınız.")
                                                
                                                if len(c1_list) == 2 and len(c2_list) == 2 and not ortak_oyuncular:
                                                    dortlu_havuz = []
                                                    for p in c1_list + c2_list:
                                                        if p in havuz:
                                                            dortlu_havuz.append((p, havuz.index(p)))
                                                    
                                                    dortlu_sirali = sorted(dortlu_havuz, key=lambda x: x[1])
                                                    yeni_ranking = {oyuncu: (i + 1) for i, (oyuncu, idx) in enumerate(dortlu_sirali)}
                                                    
                                                    toplam_c1 = yeni_ranking.get(c1_list[0],99) + yeni_ranking.get(c1_list[1],99)
                                                    toplam_c2 = yeni_ranking.get(c2_list[0],99) + yeni_ranking.get(c2_list[1],99)
                                                    
                                                    if toplam_c1 > toplam_c2:
                                                        uyarilar.append(f"Çiftler Sıralama Hatası: Seçilen 4 oyuncu arasındaki güç dengesine göre, 1. Çiftler daha güçlü veya eşit (Toplam: {toplam_c1}) olmalıdır. Mevcut durumda 2. Çiftler (Toplam: {toplam_c2}) daha güçlü görünüyor.")
                                            
                                            if uyarilar: st.warning(f"⚠️ **Sıralama Uyarısı ({takim_ismi}):**\n\n" + "\n".join([f"- {u}" for u in uyarilar]) + "\n\n*(Başhakem olarak bu uyarıya rağmen kaydetme yetkiniz bulunmaktadır.)*")
                                        
                                        if st.button(f"💾 {t1} - {t2} Skorlarını Kaydet", key=f"btn_save_{cur_grup}_{gun_val}_{eslesme_adi}", type="primary", use_container_width=True):
                                            hata_mesajlari = []
                                            for idx_save, guncel_row in form_verileri.items():
                                                mac_tanimi = f"{st.session_state.skor_tablosu.loc[idx_save]['Branş']}"
                                                
                                                s1t1_s, s1t2_s = guncel_row["1.Set T1"], guncel_row["1.Set T2"]
                                                s2t1_s, s2t2_s = guncel_row["2.Set T1"], guncel_row["2.Set T2"]
                                                s3t1_s, s3t2_s = guncel_row["3.Set T1"], guncel_row["3.Set T2"]
                                                durum_s = guncel_row["Durum"]
                                                
                                                ok1, msg1 = set_gecerli_mi(s1t1_s, s1t2_s, durum=durum_s)
                                                ok2, msg2 = set_gecerli_mi(s2t1_s, s2t2_s, durum=durum_s)
                                                ok3, msg3 = set_gecerli_mi(s3t1_s, s3t2_s, is_set3=True, durum=durum_s)
                                                
                                                if not ok1: hata_mesajlari.append(f"{mac_tanimi} Set 1: {msg1}")
                                                if not ok2: hata_mesajlari.append(f"{mac_tanimi} Set 2: {msg2}")
                                                if not ok3: hata_mesajlari.append(f"{mac_tanimi} Set 3: {msg3}")
                                                
                                                if durum_s == "Tamamlandı":
                                                    if s1t1_s == 0 and s1t2_s == 0 and s2t1_s == 0 and s2t2_s == 0 and s3t1_s == 0 and s3t2_s == 0:
                                                        hata_mesajlari.append(f"❌ {mac_tanimi}: Durum 'Tamamlandı' seçilmiş ama tüm skorlar 0-0! Maç oynanmadıysa durumunu 'Çift Taraflı W/O' veya benzeri bir seçenekle değiştirin.")
                                                    else:
                                                        t1_s1_kazandi = s1t1_s > s1t2_s
                                                        t2_s1_kazandi = s1t2_s > s1t1_s
                                                        t1_s2_kazandi = s2t1_s > s2t2_s
                                                        t2_s2_kazandi = s2t2_s > s2t1_s
                                                        
                                                        if (t1_s1_kazandi and t1_s2_kazandi) or (t2_s1_kazandi and t2_s2_kazandi): 
                                                            if s3t1_s != 0 or s3t2_s != 0:
                                                                hata_mesajlari.append(f"❌ {mac_tanimi}: Maç 2-0 bittiği için 3. sete skor girilemez.")
                                                        
                                                        elif (t1_s1_kazandi and t2_s2_kazandi) or (t2_s1_kazandi and t1_s2_kazandi):
                                                            if s3t1_s == 0 and s3t2_s == 0:
                                                                hata_mesajlari.append(f"❌ {mac_tanimi}: Setlerde 1-1 eşitlik var, 3. set skoru girilmelidir.")
                                            
                                            if hata_mesajlari:
                                                for h in hata_mesajlari: st.error(h)
                                            else:
                                                for idx_save, guncel_row in form_verileri.items():
                                                    match_key = f"{cur_grup}_{gun_val}_{guncel_row['Eşleşme']}"
                                                    
                                                    st.session_state.skor_tablosu.at[idx_save, "T1_Oyuncu"] = guncel_row["T1_Oyuncu"]
                                                    st.session_state.skor_tablosu.at[idx_save, "T2_Oyuncu"] = guncel_row["T2_Oyuncu"]
                                                    st.session_state.skor_tablosu.at[idx_save, "1.Set T1"] = guncel_row["1.Set T1"]
                                                    st.session_state.skor_tablosu.at[idx_save, "1.Set T2"] = guncel_row["1.Set T2"]
                                                    st.session_state.skor_tablosu.at[idx_save, "2.Set T1"] = guncel_row["2.Set T1"]
                                                    st.session_state.skor_tablosu.at[idx_save, "2.Set T2"] = guncel_row["2.Set T2"]
                                                    st.session_state.skor_tablosu.at[idx_save, "3.Set T1"] = guncel_row["3.Set T1"]
                                                    st.session_state.skor_tablosu.at[idx_save, "3.Set T2"] = guncel_row["3.Set T2"]
                                                    st.session_state.skor_tablosu.at[idx_save, "Durum"] = guncel_row["Durum"]
                                                    st.session_state.skor_tablosu.at[idx_save, "STB"] = guncel_row["STB"]
                                                    
                                                    if guncel_row["T1_Oyuncu"] or guncel_row["T2_Oyuncu"]:
                                                        st.session_state.esame_onayli[match_key] = True
        
                                                if ortak_veriyi_kaydet():
                                                    st.success("Tebrikler! Bu maçın skorları kaydedildi ve Maç Programı'na aktarıldı.")
                                                    time.sleep(1)
                                                    st.rerun()
                                                else:
                                                    st.error("Sistem meşgul, lütfen tekrar deneyin.")
                                
                            if secilen_grup != "Tümü (Tüm Grupları Göster)":
                                st.markdown("---")
                                with st.expander(f"📊 {secilen_grup} Anlık Puan Durumu (Görüntülemek için tıklayın)"):
                                    df_guncel = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == secilen_grup].copy()
                                    if not df_guncel.empty:
                                        grup_stats = hesapla_tum_puan_durumu(df_guncel)
                                        if not grup_stats.empty:
                                            grup_df_display = grup_stats.drop(columns=['Grup'])
                                            grup_df_display = sirala_grup_df(grup_df_display, secilen_grup)
                                            st.dataframe(grup_df_display, use_container_width=True)
                                        else:
                                            st.info("Bu grup için henüz puan durumu oluşmadı.")
                    
                    st.markdown("---")
                    st.markdown("### ⚙️ Görünüm ve Çıktı Ayarları")
                    
                    with st.expander("🖨️ Islak İmzalı Hakem Maç Kağıtları"):
                        st.info("Kortlara dağıtılacak boş skor/imza kağıtlarını buradan üretebilirsiniz. Tüm günün maçlarını tek PDF'te basabilir veya sadece seçtiğiniz bir eşleşmenin kağıdını çıkarabilirsiniz.")
                        
                        gunluk_eslesmeler_listesi = []
                        eslesme_secenekleri = ["Seçiniz"]
                        
                        for (grup_adi, eslesme_adi), g_df in df_tarih.groupby(['Grup', 'Eşleşme']):
                            tarih_str = g_df.iloc[0]['Tarih_Filtre']
                            
                            k_key = f"{grup_adi}_{g_df.iloc[0]['Gün']}_{eslesme_adi}"
                            saat = saat_map.get(k_key, "??:??")
                            kort = kort_map.get(k_key, "Kortsuz")
                            
                            t1 = g_df.iloc[0]['Takım 1']
                            t2 = g_df.iloc[0]['Takım 2']
                            hakem = "" 
                            if not df_prog.empty:
                                h_mask = df_prog[(df_prog['Grup'] == grup_adi) & (df_prog['Eşleşme'] == eslesme_adi)]
                                if not h_mask.empty: hakem = h_mask.iloc[0].get('Hakem', '')
                            
                            alt_maclar = [{"Branş": r['Branş']} for _, r in sort_maclar(g_df).iterrows()]
                            
                            # --- TAKIM KADROLARINI DOĞRUDAN ÇEKME VE AKTARMA ---
                            grup_kadro_sozlugu = st.session_state.takim_kadrolari.get(grup_adi, {})
                            t1_kadro = grup_kadro_sozlugu.get(t1, [])
                            t2_kadro = grup_kadro_sozlugu.get(t2, [])

                            mac_dict = {
                                "Grup": grup_adi, "Tarih": tarih_str, "Maç Saati": saat, 
                                "Kort": kort, "Takım 1": t1, "Takım 2": t2, "Hakem": hakem, 
                                "Alt Maclar": alt_maclar, "Eşleşme": eslesme_adi,
                                "T1_Kadro": t1_kadro,
                                "T2_Kadro": t2_kadro
                            }
                            gunluk_eslesmeler_listesi.append(mac_dict)
                            eslesme_secenekleri.append(f"{saat} | {kort} | {grup_adi} | {t1} vs {t2}")

                        if gunluk_eslesmeler_listesi:
                            pdf_bytes_toplu = generate_mac_sonuc_belgesi(gunluk_eslesmeler_listesi)
                            st.download_button(
                                label=f"📥 Seçili Tarihin Tüm Maç Kağıtlarını Tek PDF'te İndir ({len(gunluk_eslesmeler_listesi)} Sayfa)",
                                data=pdf_bytes_toplu,
                                file_name=f"Tum_Hakem_Kagitlari_{hedef_tarih}.pdf",
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True
                            )
                            
                            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                            st.markdown("**Veya Tek Bir Eşleşmeyi Yeniden Yazdır:**")
                            secilen_tekil = st.selectbox("Kağıdı çıkarılacak maçı seçin:", eslesme_secenekleri, key="tekil_kagit_secici_skor")
                            if secilen_tekil != "Seçiniz":
                                secilen_idx = eslesme_secenekleri.index(secilen_tekil) - 1
                                tekil_veri = [gunluk_eslesmeler_listesi[secilen_idx]]
                                pdf_bytes_tekil = generate_mac_sonuc_belgesi(tekil_veri)
                                st.download_button(
                                    label="📥 Sadece Bu Maçın Kağıdını İndir",
                                    data=pdf_bytes_tekil,
                                    file_name=f"Hakem_Kagidi_{tekil_veri[0]['Takım 1']}_vs_{tekil_veri[0]['Takım 2']}.pdf",
                                    mime="application/pdf"
                                )
                        else:
                            st.warning("Bu tarih için programlanmış maç bulunmuyor.")

                    with st.expander("📄 PDF Çıktı Ayarları"):
                        gosterim_sekli = st.radio("PDF Gösterim Şekli:", ["Bireysel Maçlar (Detaylı Hiyerarşik Çıktı)", "Takım Maçları (Sadece Genel Skor)"], horizontal=True)
                        is_bireysel_pdf = "Bireysel" in gosterim_sekli
                        tum_kolonlar = ["Kort", "Maç Saati", "Tarih", "Gün Adı", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Skor", "Kazanan", "Hakem"]
                        
                        if not is_bireysel_pdf:
                            tum_kolonlar = [c for c in tum_kolonlar if c not in ["T1 Oyuncu", "T2 Oyuncu"]]
                            
                        secilen_pdf_cols = st.multiselect("PDF'e eklenecek sütunları seçin:", options=tum_kolonlar, default=["Maç Saati", "Kort", "Grup", "Takım 1", "Takım 2"])
    
                        if is_bireysel_pdf:
                            pdf_rows = []
                            for (grup_adi, eslesme_adi), g_df in df_tarih.groupby(['Grup', 'Eşleşme'], dropna=False):
                                t1 = g_df.iloc[0]['Takım 1']
                                t2 = g_df.iloc[0]['Takım 2']
                                k_key = f"{grup_adi}_{g_df.iloc[0]['Gün']}_{eslesme_adi}"
                                saat = saat_map.get(k_key, "")
                                kort = kort_map.get(k_key, "")
                                tarih_str = g_df.iloc[0]['Tarih_Filtre']
                                gun_val = g_df.iloc[0]['Gün']
                                
                                gun_isim = ""
                                if not df_prog.empty:
                                    prog_s = df_prog[(df_prog['Grup'] == grup_adi) & (df_prog['Eşleşme'] == eslesme_adi)]
                                    if not prog_s.empty: gun_isim = prog_s.iloc[0].get('Gün Adı', '')
                                
                                team_score = "Oynanmadı"
                                team_winner = ""
                                
                                header_row = {
                                    "Kort": kort, "Maç Saati": saat, "Tarih": tarih_str, "Gün Adı": gun_isim, 
                                    "Grup": grup_adi, "Gün": gun_val, "Eşleşme": eslesme_adi,
                                    "Branş": "**TAKIM EŞLEŞMESİ**",
                                    "Takım 1": f"**{t1}**" if team_winner == "T1" else t1, 
                                    "Takım 2": f"**{t2}**" if team_winner == "T2" else t2,
                                    "T1 Oyuncu": "", "T2 Oyuncu": "",
                                    "Skor": f"**{team_score}**", "Kazanan": "", "Hakem": "",
                                    "_IS_HEADER_": True
                                }
                                pdf_rows.append(header_row)
                                
                                for _, row in sort_maclar(g_df).iterrows():
                                    match_row = row.copy()
                                    match_row['Branş'] = f" -> {match_row['Branş']}" 
                                    match_row['Maç Saati'] = saat
                                    match_row['Kort'] = kort
                                    match_row['Tarih'] = tarih_str
                                    
                                    win = match_row.get('Kazanan', '')
                                    if win == 'T1':
                                        match_row['Takım 1'] = f"**{match_row['Takım 1']}**"
                                        if match_row['T1 Oyuncu']: match_row['T1 Oyuncu'] = f"**{match_row['T1 Oyuncu']}**"
                                    elif win == 'T2':
                                        match_row['Takım 2'] = f"**{match_row['Takım 2']}**"
                                        if match_row['T2 Oyuncu']: match_row['T2 Oyuncu'] = f"**{match_row['T2 Oyuncu']}**"
                                        
                                    match_row['_IS_HEADER_'] = False
                                    pdf_rows.append(match_row.to_dict())
                                    
                            df_pdf_export = pd.DataFrame(pdf_rows)
                        else:
                            st.info("Takım özet görünümü Maç Programı sekmesinden alınabilir.")
                            df_pdf_export = pd.DataFrame()
                                    
                        if not df_pdf_export.empty and secilen_pdf_cols:
                            final_pdf_df = df_pdf_export[secilen_pdf_cols].copy()
                            final_pdf_df["_IS_HEADER_"] = df_pdf_export["_IS_HEADER_"]
                            
                            pdf_notu = st.session_state.gunluk_notlar.get(hedef_tarih, "")
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            pdf_turu = st.radio("📄 Belge Başlığı (PDF'te ne yazsın?):", ["Maç Programı (Sabah)", "Günün Sonuçları (Akşam)"], horizontal=True)
                            
                            if "Sonuçları" in pdf_turu:
                                baslik_metni = f"{hedef_tarih} - Günün Sonuçları"
                                dosya_adi = f"mac_sonuclari_{hedef_tarih}.pdf"
                                buton_adi = "📥 Günün Sonuçlarını PDF Olarak İndir"
                            else:
                                baslik_metni = f"{hedef_tarih} - Maç Programı"
                                dosya_adi = f"mac_programi_{hedef_tarih}.pdf"
                                buton_adi = "📥 Maç Programını PDF Olarak İndir"
                                
                            pdf_bytes_admin = generate_pdf(final_pdf_df, baslik_metni, not_metni=pdf_notu, kategori_map=st.session_state.grup_kategorileri)
                            st.download_button(buton_adi, data=pdf_bytes_admin, file_name=dosya_adi, mime="application/pdf", key="pdf_admin_skor")
        else:
            st.warning("🔒 Skor ve esame giriş paneli dışarıya kapalıdır. Lütfen giriş yapınız.")

# ==============================================================================
# 11. PUAN DURUMU (ŞAMPİYONLUK VE KLASMAN VİTRİNİ)
# ==============================================================================
    elif menu_secim == "🏆 Puan Durumu":
        if not st.session_state.skor_tablosu.empty:
            tab_puan, tab_klasman = st.tabs(["📊 Grup Puan Durumları", "Nihai Klasman"])
            
            with tab_puan:
                gecerli_gruplar_t3 = [g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama]
                df_asama_t3 = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'].isin(gecerli_gruplar_t3)]
                
                if not df_asama_t3.empty:
                    tum_stats = hesapla_tum_puan_durumu(df_asama_t3)
                    mevcut_gruplar = dogal_sirala(list(tum_stats['Grup'].unique()))
                    
                    # --- YENİ KATEGORİ VE GRUP FİLTRESİ ---
                    kategori_dict = {}
                    for gp in mevcut_gruplar:
                        g_kat = st.session_state.grup_kategorileri.get(gp, "Erkekler")
                        g_yas = st.session_state.grup_yas_gruplari.get(gp, "Yaş Belirtme")
                        kat_isim = f"{g_yas} {g_kat}" if g_yas != "Yaş Belirtme" else g_kat
                        if kat_isim not in kategori_dict:
                            kategori_dict[kat_isim] = []
                        kategori_dict[kat_isim].append(gp)
                    
                    kat_isimleri = dogal_sirala(list(kategori_dict.keys()))
                    
                    c_kat, c_grup = st.columns(2)
                    secilen_kategoriler = c_kat.multiselect("📂 Görüntülenecek Kategoriyi Seçin:", options=["Tüm Kategorileri Göster"] + kat_isimleri, default=["Tüm Kategorileri Göster"])
                    
                    filtreli_gruplar = []
                    if "Tüm Kategorileri Göster" in secilen_kategoriler or len(secilen_kategoriler) == 0:
                        filtreli_gruplar = mevcut_gruplar
                    else:
                        for k in secilen_kategoriler:
                            if k in kategori_dict:
                                filtreli_gruplar.extend(kategori_dict[k])
                    
                    secim_grup_opsiyonlari = ["Tüm Grupları Göster"] + dogal_sirala(filtreli_gruplar)
                    secilen_gruplar = c_grup.multiselect("🔍 Görüntülenecek Grupları Seçin:", options=secim_grup_opsiyonlari, default=["Tüm Grupları Göster"])
                    
                    gosterilecek_gruplar = filtreli_gruplar if "Tüm Grupları Göster" in secilen_gruplar or len(secilen_gruplar) == 0 else [g for g in secilen_gruplar if g != "Tüm Grupları Göster"]
                    
                    st.markdown("---")
                    
                    pdf_gruplar_data = {}
                    manuel_siralanan_gruplar = [] 

                    for gp in dogal_sirala(gosterilecek_gruplar):
                        if gp in mevcut_gruplar:
                            g_kat = st.session_state.grup_kategorileri.get(gp, "Erkekler")
                            g_yas = st.session_state.grup_yas_gruplari.get(gp, "Yaş Belirtme")
                            baslik_ek = f" ({g_yas} {g_kat})" if g_yas != "Yaş Belirtme" else f" ({g_kat})"
                            
                            st.markdown(f"### 🏆 {gp} Puan Durumu{baslik_ek}")
                            
                            grup_df = tum_stats[tum_stats['Grup'] == gp].drop(columns=['Grup'])
                            grup_df = sirala_grup_df(grup_df, gp)
                            
                            pdf_df = grup_df.reset_index().rename(columns={"index": "Sıra"})
                            pdf_gruplar_data[gp] = pdf_df
                            
                            t_ic1, t_ic2 = st.tabs(["🏆 Puan Durumu Tablosu", "📊 Maç Matrisi"])
                            
                            with t_ic1:
                                st.dataframe(grup_df, use_container_width=True)
                                
                                if st.session_state.grup_tamamlandi.get(gp, False):
                                    st.success("✅ Bu grubun maçları tamamlanmış ve sıralaması kilitlenmiştir.")
                                    
                                if gp in st.session_state.grup_siralamalari and st.session_state.grup_siralamalari[gp]:
                                    st.warning("⚠️ Bu grupta averaj eşitliği veya başka bir sebeple Başhakem kararıyla Manuel Sıralama uygulanmıştır.")
                                    manuel_siralanan_gruplar.append(gp)

                                # YENİ EKLENEN AVERAJ VE KURA BİLDİRİMLERİ (Ekrana Basma - Otomatik)
                                if gp in st.session_state.get("kura_uyarilari", {}):
                                    st.error(st.session_state.kura_uyarilari[gp])
                                    
                                if gp in st.session_state.get("averaj_bilgileri", {}):
                                    st.markdown(f"<div style='padding: 12px; background-color: rgba(23, 162, 184, 0.1); border-left: 4px solid #17a2b8; color: #0c5460; border-radius: 4px; margin-top: 10px; margin-bottom: 10px; font-size: 14px; line-height: 1.5;'>{st.session_state.averaj_bilgileri[gp]}</div>", unsafe_allow_html=True)
                                
                                if gp in st.session_state.get("grup_averaj_tablolari", {}):
                                    for t_adi, t_df in st.session_state.grup_averaj_tablolari[gp].items():
                                        with st.expander(f"📊 {t_adi}", expanded=False):
                                            st.dataframe(t_df, use_container_width=True)
                                
                            with t_ic2:
                                df_gp_matches = df_asama_t3[df_asama_t3['Grup'] == gp]
                                matris_takimlar = dogal_sirala(list(set(df_gp_matches['Takım 1']).union(set(df_gp_matches['Takım 2']))))
                                
                                html_matrix = render_html_matrix(matris_takimlar, df_gp_matches)
                                st.markdown(html_matrix, unsafe_allow_html=True)
                                
                                st.write("")
                                
                                pdf_matrix_df = pd.DataFrame(index=matris_takimlar, columns=matris_takimlar)
                                on_hesap = {}
                                for (t_a, t_b), group_df in df_gp_matches.groupby(['Takım 1', 'Takım 2']):
                                    match_key = tuple(sorted([t_a, t_b]))
                                    if match_key not in on_hesap:
                                        ar_maclar = df_gp_matches[((df_gp_matches['Takım 1'] == match_key[0]) & (df_gp_matches['Takım 2'] == match_key[1])) | 
                                                                  ((df_gp_matches['Takım 1'] == match_key[1]) & (df_gp_matches['Takım 2'] == match_key[0]))]
                                        on_hesap[match_key] = hesapla_tum_puan_durumu(ar_maclar)
                                        
                                for t1 in matris_takimlar:
                                    for t2 in matris_takimlar:
                                        if t1 == t2:
                                            pdf_matrix_df.at[t1, t2] = "X"
                                        else:
                                            match_key = tuple(sorted([t1, t2]))
                                            matches = df_gp_matches[((df_gp_matches['Takım 1'] == t1) & (df_gp_matches['Takım 2'] == t2)) | ((df_gp_matches['Takım 1'] == t2) & (df_gp_matches['Takım 2'] == t1))]
                                            if matches.empty:
                                                pdf_matrix_df.at[t1, t2] = ""
                                            else:
                                                temp_stats = on_hesap.get(match_key, pd.DataFrame())
                                                t1_w = 0; t2_w = 0
                                                detay = []
                                                for _, row_m in sort_maclar(matches).iterrows():
                                                    w1, w2 = hesapla_mac_kazanani(row_m)
                                                    if row_m['Takım 1'] == t1:
                                                        t1_w += w1; t2_w += w2
                                                    else:
                                                        t1_w += w2; t2_w += w1
                                                    
                                                    fmt = get_formatted_match_score(row_m, t1)
                                                    if fmt: 
                                                        clean_fmt = fmt.replace("<b>", "").replace("</b>", "").replace("<span style='opacity: 0.8;'>", "").replace("</span>", "")
                                                        detay.append(clean_fmt)
                                                
                                                if t1_w == 0 and t2_w == 0 and not detay:
                                                    pdf_matrix_df.at[t1, t2] = ""
                                                else:
                                                    t1_galib = 0; t2_galib = 0
                                                    if not temp_stats.empty:
                                                        r1 = temp_stats[temp_stats['Takım'] == t1]
                                                        r2 = temp_stats[temp_stats['Takım'] == t2]
                                                        if not r1.empty: t1_galib = r1.iloc[0]['Galibiyet']
                                                        if not r2.empty: t2_galib = r2.iloc[0]['Galibiyet']
                                                        
                                                    c1 = "* " if t1_galib > t2_galib else ""
                                                    c2 = " *" if t2_galib > t1_galib else ""
                                                    
                                                    hucre_metni = f"{c1}{t1_w} - {t2_w}{c2}"
                                                    if detay:
                                                        hucre_metni += "\n" + "\n".join(detay)
                                                    pdf_matrix_df.at[t1, t2] = hucre_metni
                                                    
                                matris_pdf_bytes = draw_matrix_pdf(gp, matris_takimlar, pdf_matrix_df)
                                st.download_button(label="📥 Maç Matrisini İndir (PDF)", data=matris_pdf_bytes, file_name=f"matris_{gp}.pdf", mime="application/pdf", key=f"mat_pdf_{gp}")
                            
                            if st.session_state.admin_mi:
                                with st.expander(f"🛠️ {gp} - Başhakem Sıralama ve Onay Paneli", expanded=False):
                                    mevcut_takimlar = grup_df['Takım'].tolist()
                                    mevcut_takimlar_harf_sirali = sorted(mevcut_takimlar)
                                    
                                    def toggle_tamam(hedef_grup):
                                        st.session_state.grup_tamamlandi[hedef_grup] = st.session_state[f"tamam_{hedef_grup}"]
                                        ortak_veriyi_kaydet()

                                    if aktif_asama == "1. Aşama":
                                        st.markdown("**1. Aşama Sonucu (2. Aşama İçin Grubu Kilitle):**")
                                        st.info("Bu kutuyu işaretlediğiniz an grup kilitlenir ve takımlar 2. Aşama havuzuna düşer. Başka bir butona basmanıza gerek yoktur!")
                                        cb_metin = f"✅ {gp} Maçları Tamamlandı (2. Aşamaya Aktar)"
                                    else:
                                        st.markdown("**Fikstür Sonu (Sıralamayı Kesinleştir):**")
                                        st.info("Bu kutuyu işaretlediğiniz an gruptaki fikstür biter ve sıralama turnuva sonucu olarak kilitlenir. (Tüm gruplar kilitlendiğinde Nihai Klasman vitrinine yansır).")
                                        cb_metin = f"✅ {gp} Fikstürünü Bitir ve Sıralamaya Aktar"
                                        
                                    is_tamam = st.checkbox(cb_metin, value=st.session_state.grup_tamamlandi.get(gp, False), key=f"tamam_{gp}", on_change=toggle_tamam, args=(gp,))
                                    
                                    st.markdown("---")
                                    st.markdown("**2. Manuel Sıralama (Üçlü Averaj vs. için):**")
                                    st.write("SADECE sistemin otomatik sıralamasına müdahale etmeniz gerekiyorsa aşağıdaki listeyi değiştirip kaydedin.")
                                    
                                    default_sel = st.session_state.grup_siralamalari.get(gp, mevcut_takimlar)
                                    secilenler = []
                                    cols = st.columns(len(mevcut_takimlar))
                                    for idx_c in range(len(mevcut_takimlar)):
                                        with cols[idx_c]:
                                            def_team = default_sel[idx_c] if idx_c < len(default_sel) else mevcut_takimlar_harf_sirali[0]
                                            def_idx = mevcut_takimlar_harf_sirali.index(def_team) if def_team in mevcut_takimlar_harf_sirali else 0
                                            sec = st.selectbox(f"{idx_c+1}. Takım", options=mevcut_takimlar_harf_sirali, index=def_idx, key=f"sira_{gp}_{idx_c}")
                                            secilenler.append(sec)
                                    
                                    st.write("")
                                    c1, c2 = st.columns(2)
                                    if c1.button(f"💾 {gp} Manuel Sıralamayı Uygula", key=f"btn_save_{gp}", type="primary"):
                                        if len(set(secilenler)) != len(mevcut_takimlar):
                                            st.error("Hata: Aynı takımı birden fazla sıraya yerleştiremezsiniz! Lütfen farklı takımlar seçin.")
                                        else:
                                            if secilenler == mevcut_takimlar:
                                                if gp in st.session_state.grup_siralamalari:
                                                    del st.session_state.grup_siralamalari[gp]
                                                st.success("Sıralama otomatik hesaplamayla aynı olduğu için 'Manuel Müdahale' uyarısı kaldırıldı.")
                                                ortak_veriyi_kaydet()
                                                time.sleep(1.5)
                                                st.rerun()
                                            else:
                                                st.session_state.grup_siralamalari[gp] = secilenler
                                                if ortak_veriyi_kaydet():
                                                    st.success(f"{gp} için Başhakem Özel Sıralaması uygulandı!")
                                                    time.sleep(1.5)
                                                    st.rerun()
                                                else:
                                                    st.error("Sistem meşgul, lütfen tekrar deneyin.")
                                            
                                    if c2.button(f"🔄 Otomatik Sıralamaya Dön", key=f"btn_reset_{gp}"):
                                        if gp in st.session_state.grup_siralamalari:
                                            del st.session_state.grup_siralamalari[gp]
                                            if ortak_veriyi_kaydet():
                                                st.success("Manuel sıralama iptal edildi, sistem otomatik hesaplamaya döndü.")
                                                time.sleep(1.5)
                                                st.rerun()
                                            else:
                                                st.error("Sistem meşgul, lütfen tekrar deneyin.")
                                        else:
                                            st.info("Grup zaten otomatik sıralamada.")

                            st.markdown("<br><hr>", unsafe_allow_html=True)

                    if pdf_gruplar_data:
                        grup_averajlari = st.session_state.get("grup_averaj_tablolari", {})
                        grup_aciklamalari = st.session_state.get("averaj_bilgileri", {})
                        combined_pdf_bytes = generate_combined_standings_pdf(
                            pdf_gruplar_data, 
                            manuel_gruplar=manuel_siralanan_gruplar,
                            averaj_tablolari=grup_averajlari,
                            averaj_bilgileri=grup_aciklamalari,
                            kategori_map=st.session_state.grup_kategorileri
                        )
                        st.download_button(label="📥 Seçili Grupların Puan Durumunu Tek PDF Olarak İndir", data=combined_pdf_bytes, file_name="puan_durumu_toplu.pdf", mime="application/pdf", key="pdf_puan_toplu")
                    
                    st.markdown("---")
                    with st.expander("⚖️ Gelişmiş Averaj ve Çoklu Averaj Hesaplayıcı"):
                        st.info("ℹ️ Üçlü veya dörtlü averaj kilitlenmelerinde bir grup ve sadece averaja dahil edilecek takımları seçin. Sistem, dışarıdaki takımlarla oynanan maçları yoksayarak yepyeni bir Çoklu Averaj Hesaplaması oluşturur. Bu bilgiye bakarak üstteki 'Başhakem Sıralama Paneli'nden tabloyu dizebilirsiniz.")
                        
                        avg_gruplar = dogal_sirala(list(df_asama_t3['Grup'].unique()))
                        sec_avg_grup = st.selectbox("Averaj Hesaplanacak Grubu Seçin:", ["Seçiniz"] + avg_gruplar, key="avg_grup_sec")
                        
                        if sec_avg_grup != "Seçiniz":
                            grup_maclari_avg = df_asama_t3[df_asama_t3['Grup'] == sec_avg_grup]
                            takimlar_avg = dogal_sirala(list(set(grup_maclari_avg['Takım 1']).union(set(grup_maclari_avg['Takım 2']))))
                            
                            secilen_takimlar_avg = st.multiselect("Averaja Kalmış (Kendi aralarında hesaplanacak) Takımları Seçin:", options=takimlar_avg)
                            
                            if len(secilen_takimlar_avg) >= 2:
                                if st.button("🧮 Seçili Takımların Kendi Arasındaki Averajını Hesapla"):
                                    mask_t1 = grup_maclari_avg['Takım 1'].isin(secilen_takimlar_avg)
                                    mask_t2 = grup_maclari_avg['Takım 2'].isin(secilen_takimlar_avg)
                                    mini_lig_df = grup_maclari_avg[mask_t1 & mask_t2]
                                    
                                    if mini_lig_df.empty:
                                        st.warning("Bu takımlar arasında oynanmış ve skoru girilmiş bir maç bulunamadı.")
                                    else:
                                        mini_stats = hesapla_tum_puan_durumu(mini_lig_df)
                                        if not mini_stats.empty:
                                            mini_grup_df = mini_stats.drop(columns=['Grup']).sort_values(by=['Galibiyet', 'Maç Av.', 'Oyun Av.'], ascending=False)
                                            mini_grup_df.index = range(1, len(mini_grup_df) + 1)
                                            
                                            st.success(f"✅ {sec_avg_grup} - Çoklu Averaj Puan Durumu (Sadece seçili takımlar)")
                                            st.dataframe(mini_grup_df, use_container_width=True)
                            elif len(secilen_takimlar_avg) == 1:
                                st.warning("Averaj hesaplamak için en az 2 takım seçmelisiniz.")
                                
            with tab_klasman:
                st.markdown("### Nihai Klasman Vitrini")
                if aktif_asama != "2. Aşama":
                    st.info("Nihai klasman sıralamaları sadece '2. Aşama' tamamlandıktan sonra oluşturulur.")
                else:
                    st.info("Bu vitrin, maçları ve Başhakem onayları tamamen bitmiş olan kategorilerin şampiyonlarını ve play-out durumlarını listeler.")
                    
                    tum_gruplar_listesi = st.session_state.skor_tablosu['Grup'].unique()
                    tum_stats_genel = hesapla_tum_puan_durumu(st.session_state.skor_tablosu)
                    
                    kategori_asama_map = {}
                    for gp in tum_gruplar_listesi:
                        g_kat = st.session_state.grup_kategorileri.get(gp, "Erkekler")
                        g_yas = st.session_state.grup_yas_gruplari.get(gp, "Yaş Belirtme")
                        etiket = f"{g_yas} {g_kat}" if g_yas != "Yaş Belirtme" else f"{g_kat}"
                        asama_bilgisi = st.session_state.grup_asamalari.get(gp, "1. Aşama")
                        
                        if etiket not in kategori_asama_map:
                            kategori_asama_map[etiket] = {"1. Aşama": [], "2. Aşama": []}
                        kategori_asama_map[etiket][asama_bilgisi].append(gp)
                        
                    kat_gruplari_map = {}
                    for kat_ad, asamalar in kategori_asama_map.items():
                        if len(asamalar["2. Aşama"]) > 0:
                            kat_gruplari_map[kat_ad] = asamalar["2. Aşama"] 
                        else:
                            kat_gruplari_map[kat_ad] = asamalar["1. Aşama"] 
                            
                    tamamlanan_kategoriler = []
                    for kat_ad, gruplar_listesi in kat_gruplari_map.items():
                        herkes_tamam_mi = all(st.session_state.grup_tamamlandi.get(g, False) for g in gruplar_listesi)
                        if herkes_tamam_mi and len(gruplar_listesi) > 0:
                            tamamlanan_kategoriler.append(kat_ad)
                            
                    if not tamamlanan_kategoriler:
                        st.warning("Henüz tüm grupları 'Tamamlandı' olarak kilitlenmiş bir kategori bulunmuyor.")
                    else:
                        sec_klasmanlar = st.multiselect("Sonuçlarını Görmek ve Yazdırmak İstediğiniz Kategorileri Seçin:", options=sorted(tamamlanan_kategoriler), default=sorted(tamamlanan_kategoriler))
                        
                        if st.session_state.admin_mi:
                            dusme_hatti = st.number_input("Play-out Gruplarında İlk Kaç Takım Ligde Kalacak? (Kırmızı Çizgi)", min_value=1, value=st.session_state.get("kayitli_dusme_hatti", 2), step=1)
                            if dusme_hatti != st.session_state.get("kayitli_dusme_hatti", 2):
                                st.session_state["kayitli_dusme_hatti"] = dusme_hatti
                                ortak_veriyi_kaydet() 
                        else:
                            dusme_hatti = st.session_state.get("kayitli_dusme_hatti", 2)
                        
                        pdf_icin_hazir_veriler = {}
                        
                        for secilen_kategori in sec_klasmanlar:
                            with st.expander(f"{secilen_kategori} Nihai Sıralaması", expanded=True):
                                birinciler = []
                                ikinciler = []
                                playoutlar = []
                                
                                gruplar = kat_gruplari_map[secilen_kategori]
                                for gp in gruplar:
                                    statu = st.session_state.grup_statuleri.get(gp, "")
                                    
                                    if len(gruplar) == 1:
                                        birinciler.append(gp) 
                                    elif "Birinciler" in statu or "Birinciler" in gp:
                                        birinciler.append(gp)
                                    elif "İkinciler" in statu or "İkinciler" in gp:
                                        ikinciler.append(gp)
                                    else:
                                        playoutlar.append(gp) 
                                        
                                current_rank = 1
                                kat_verisi = {"birinciler": [], "ikinciler": [], "ligde_kalanlar": [], "dusenler": []}
                                
                                if birinciler:
                                    st.markdown("##### ŞAMPİYONLUK KÜRSÜSÜ")
                                    for bg in dogal_sirala(birinciler):
                                        grup_df = tum_stats_genel[tum_stats_genel['Grup'] == bg].drop(columns=['Grup'])
                                        grup_df = sirala_grup_df(grup_df, bg)
                                        
                                        for idx, row in grup_df.iterrows():
                                            takim = row['Takım']
                                            kat_verisi["birinciler"].append(takim)
                                            
                                            unvan = ""
                                            if current_rank == 1: unvan = "🥇 (Şampiyon)"
                                            elif current_rank == 2: unvan = "🥈 (İkinci)"
                                            elif current_rank == 3: unvan = "🥉 (Üçüncü)"
                                            elif current_rank == 4: unvan = "🏅 (Dördüncü)"
                                            
                                            st.markdown(f"**{current_rank}. Sıra:** {takim} {unvan}")
                                            current_rank += 1
                                            
                                if ikinciler:
                                    st.markdown("---")
                                    st.markdown("##### İKİNCİLER GRUBU (Klasman)")
                                    for ig in dogal_sirala(ikinciler):
                                        grup_df = tum_stats_genel[tum_stats_genel['Grup'] == ig].drop(columns=['Grup'])
                                        grup_df = sirala_grup_df(grup_df, ig)
                                        
                                        for idx, row in grup_df.iterrows():
                                            takim = row['Takım']
                                            kat_verisi["ikinciler"].append(takim)
                                            st.markdown(f"**{current_rank}. Sıra:** {takim}")
                                            current_rank += 1
                                
                                if playoutlar:
                                    for p_grup in playoutlar:
                                        grup_df = tum_stats_genel[tum_stats_genel['Grup'] == p_grup].drop(columns=['Grup'])
                                        grup_df = sirala_grup_df(grup_df, p_grup)
                                        
                                        sira = 1
                                        for _, row in grup_df.iterrows():
                                            if sira <= dusme_hatti:
                                                kat_verisi["ligde_kalanlar"].append(f"{row['Takım']} *(Grubu: {p_grup})*")
                                            else:
                                                kat_verisi["dusenler"].append(f"{row['Takım']} *(Grubu: {p_grup})*")
                                            sira += 1
                                                
                                    st.markdown("---")
                                    st.markdown("##### LİGDE KALANLAR (Play-Out Üst Sıralar)")
                                    if kat_verisi["ligde_kalanlar"]:
                                        for takim in dogal_sirala(kat_verisi["ligde_kalanlar"]):
                                            st.markdown(f"- {takim}")
                                    else:
                                        st.caption("Ligde kalan takım bulunamadı.")
                                        
                                    st.markdown("---")
                                    st.markdown("##### LİGDEN DÜŞENLER (Play-Out Alt Sıralar)")
                                    if kat_verisi["dusenler"]:
                                        for takim in dogal_sirala(kat_verisi["dusenler"]):
                                            st.markdown(f"- {takim}")
                                    else:
                                        st.caption("Düşme hattında takım bulunamadı.")
                                        
                                pdf_icin_hazir_veriler[secilen_kategori] = kat_verisi
                                
                                st.markdown("<br>", unsafe_allow_html=True)
                                tek_pdf_bytes = generate_klasman_pdf(
                                    secilen_kategori, 
                                    kat_verisi["birinciler"], 
                                    kat_verisi["ikinciler"], 
                                    kat_verisi["ligde_kalanlar"], 
                                    kat_verisi["dusenler"]
                                )
                                st.download_button(
                                    label=f"📥 SADECE {secilen_kategori} Klasmanını İndir", 
                                    data=tek_pdf_bytes, 
                                    file_name=f"Nihai_Klasman_{secilen_kategori.replace(' ', '_')}.pdf", 
                                    mime="application/pdf", 
                                    key=f"pdf_tek_{secilen_kategori}",
                                )
                                
                        if pdf_icin_hazir_veriler:
                            st.markdown("<br>", unsafe_allow_html=True)
                            toplu_pdf_bytes = generate_toplu_klasman_pdf(pdf_icin_hazir_veriler)
                            st.download_button(
                                label="📥 Seçili Kategorilerin Resmi Sonuç Bildirgesini İndir (PDF)", 
                                data=toplu_pdf_bytes, 
                                file_name=f"TTF_Takim_Sampiyonasi_Resmi_Sonuc.pdf", 
                                mime="application/pdf", 
                                key="pdf_toplu_klasman_btn",
                                type="primary",
                                use_container_width=True
                            )
        else:
            st.info(f"Bu aşamada henüz maç bulunmuyor.")

    # ==============================================================================
    # 12. MAÇ PROGRAMI (GÜNLÜK AKIŞ)
    # ==============================================================================
    elif menu_secim == "📅 Maç Programı":
        tab_gunluk, tab_genel = st.tabs(["🗓️ Günlük Akış (Tarihe Göre)", "📋 Tüm Maçların Genel Durumu"])
        
        with tab_genel:
            st.markdown(f"### 📋 {aktif_asama} - Tüm Maçların Genel Durumu")
            
            gecerli_gruplar_genel = [g for g in st.session_state.grup_asamalari.keys() if st.session_state.grup_asamalari[g] == aktif_asama]
            df_hepsi = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'].isin(gecerli_gruplar_genel)]
            
            # YAYINLAMA FİLTRESİ
            if not st.session_state.admin_mi:
                yayinli_tarihler = [t for t, stat in st.session_state.yayinlanan_gunler.items() if stat == True]
                izinli_gruplar_gunler = st.session_state.mac_programi[st.session_state.mac_programi['Tarih'].isin(yayinli_tarihler)][['Grup', 'Gün']].drop_duplicates()
                df_hepsi = df_hepsi.merge(izinli_gruplar_gunler, on=['Grup', 'Gün'], how='inner')
            
            if df_hepsi.empty:
                st.info(f"{aktif_asama} için henüz oluşturulmuş/yayınlanmış bir fikstür/maç bulunmuyor.")
            else:
                mevcut_gunler = dogal_sirala(list(df_hepsi['Gün'].unique()))
                
                if mevcut_gunler:
                    gun_sekmeleri = st.tabs(mevcut_gunler)
                    
                    for i, gun_adi in enumerate(mevcut_gunler):
                        with gun_sekmeleri[i]:
                            df_gunluk_hepsi = df_hepsi[df_hepsi['Gün'] == gun_adi]
                            tablo_verisi = []
                            
                            for (grup, eslesme), maclar_df in df_gunluk_hepsi.groupby(['Grup', 'Eşleşme']):
                                takim1 = maclar_df.iloc[0]['Takım 1']
                                takim2 = maclar_df.iloc[0]['Takım 2']
                                
                                prog_mask = st.session_state.mac_programi[
                                    (st.session_state.mac_programi['Grup'] == grup) &
                                    (st.session_state.mac_programi['Gün'] == gun_adi) &
                                    (st.session_state.mac_programi['Eşleşme'] == eslesme)
                                ]
                                
                                if not prog_mask.empty:
                                    tarih = prog_mask.iloc[0].get('Tarih', '')
                                    saat = prog_mask.iloc[0].get('Maç Saati', '')
                                    kort = prog_mask.iloc[0].get('Kort', '')
                                    program_metni = f"{tarih} | {saat} | {kort}"
                                else:
                                    program_metni = "📌 Henüz Programlanmadı"
                                    
                                biten_mac_sayisi = 0
                                toplam_mac_sayisi = len(maclar_df)
                                
                                for _, m_row in maclar_df.iterrows():
                                    durum = str(m_row.get('Durum', 'Tamamlandı'))
                                    s1t1, s1t2 = int(m_row.get('1.Set T1', 0)), int(m_row.get('1.Set T2', 0))
                                    if "W/O" in durum or "Ret." in durum or s1t1 > 0 or s1t2 > 0 or durum == "Çift Taraflı W/O":
                                        biten_mac_sayisi += 1
                                        
                                if biten_mac_sayisi == toplam_mac_sayisi and toplam_mac_sayisi > 0:
                                    durum_metni = "✅ Tamamlandı"
                                elif biten_mac_sayisi > 0:
                                    durum_metni = f"⏳ Devam Ediyor ({biten_mac_sayisi}/{toplam_mac_sayisi})"
                                else:
                                    durum_metni = "⏳ Bekliyor"
                                    
                                tablo_verisi.append({
                                    "Grup": grup,
                                    "Eşleşme": eslesme,
                                    "Takımlar": f"{takim1} vs {takim2}",
                                    "Takvim & Kort Durumu": program_metni,
                                    "Skor / Maç Durumu": durum_metni
                                })
                                
                            if tablo_verisi:
                                gosterim_df = pd.DataFrame(tablo_verisi)
                                gosterim_df['Sıra_Yardimci'] = gosterim_df['Grup'].apply(lambda x: tuple([int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(x))]))
                                gosterim_df = gosterim_df.sort_values(by=['Sıra_Yardimci', 'Eşleşme']).drop(columns=['Sıra_Yardimci'])
                                st.dataframe(gosterim_df, use_container_width=True, hide_index=True)
                            else:
                                st.info("Bu güne ait eşleşme bulunmuyor.")

        with tab_gunluk:
            st.markdown("### 📅 Maç Olan Günler")
            gecerli_gruplar_t4 = [g for g in st.session_state.grup_asamalari.keys() if st.session_state.grup_asamalari[g] == aktif_asama]
            mac_programi_asama = st.session_state.mac_programi[st.session_state.mac_programi['Grup'].isin(gecerli_gruplar_t4)].copy()
            
            # YAYINLAMA FİLTRESİ
            if not st.session_state.admin_mi:
                yayinli_tarihler = [t for t, stat in st.session_state.yayinlanan_gunler.items() if stat == True]
                mac_programi_asama = mac_programi_asama[mac_programi_asama['Tarih'].isin(yayinli_tarihler)]
    
            if not mac_programi_asama.empty:
                unique_dates = sorted(mac_programi_asama['Tarih'].unique())
                cols = st.columns(min(len(unique_dates), 5) if len(unique_dates) > 0 else 1)
                for i, d_str in enumerate(unique_dates):
                    match_count = len(mac_programi_asama[mac_programi_asama['Tarih'] == d_str])
                    d_obj = datetime.datetime.strptime(d_str, "%d.%m.%Y").date()
                    with cols[i % len(cols)]:
                        if st.button(f"🗓️ {d_str} ({match_count})", key=f"btn_date_{d_str}"):
                            st.session_state.selected_date_filter = d_obj
                            st.rerun()
            else:
                st.info("Bu aşama için henüz programlanmış/yayınlanmış maç bulunmuyor.")
            st.markdown("---")
    
            if not st.session_state.skor_tablosu.empty:
                turkce_gunler = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
                
                if st.session_state.admin_mi:
                    secilen_tarih = st.date_input("🗓️ Program Yapılacak / Görüntülenecek Tarih:", value=st.session_state.selected_date_filter)
                    st.session_state.selected_date_filter = secilen_tarih
                    formatted_tarih = secilen_tarih.strftime("%d.%m.%Y")
                    gun_adi = turkce_gunler[secilen_tarih.weekday()]
                    
                    gunluk_not = st.session_state.gunluk_notlar.get(formatted_tarih, "")
                    yeni_not = st.text_area(f"✍️ {formatted_tarih} Tarihi İçin Başhakem Notu:", value=gunluk_not, height=70, placeholder="Buraya yazacağınız not, bu tarihteki maç programının en tepesinde görünecektir.")
                    if st.button("💾 Notu Kaydet"):
                        st.session_state.gunluk_notlar[formatted_tarih] = yeni_not
                        ortak_veriyi_kaydet()
                        st.success("Not kaydedildi ve yayına alındı!")
                    
                    st.markdown("---")
                else:
                    formatted_tarih = st.session_state.selected_date_filter.strftime("%d.%m.%Y")
                    gun_adi = turkce_gunler[st.session_state.selected_date_filter.weekday()]
    
                gunluk_not_gosterim = st.session_state.gunluk_notlar.get(formatted_tarih, "")
                if gunluk_not_gosterim:
                    st.warning(f"📢 **Başhakem Notu:** {gunluk_not_gosterim}")
    
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
                        durum = str(m.get('Durum', 'Tamamlandı'))
                        
                        if durum == "Takım 1 (W/O)": durum = "Takım 2 Kazandı (W/O)"
                        elif durum == "Takım 2 (W/O)": durum = "Takım 1 Kazandı (W/O)"
                        elif durum == "Takım 1 (Ret.)": durum = "Takım 2 Kazandı (Ret.)"
                        elif durum == "Takım 2 (Ret.)": durum = "Takım 1 Kazandı (Ret.)"
                        
                        t1_o = str(m['T1_Oyuncu']).strip() if pd.notna(m['T1_Oyuncu']) and str(m['T1_Oyuncu']).strip() not in ["", "nan", "Seçiniz", "None"] else ""
                        t2_o = str(m['T2_Oyuncu']).strip() if pd.notna(m['T2_Oyuncu']) and str(m['T2_Oyuncu']).strip() not in ["", "nan", "Seçiniz", "None"] else ""
                        st.session_state.mac_programi.at[idx, "T1 Oyuncu"] = t1_o
                        st.session_state.mac_programi.at[idx, "T2 Oyuncu"] = t2_o
                        
                        if durum == "Çift Taraflı W/O":
                            st.session_state.mac_programi.at[idx, "Skor"] = "Çift Taraflı W/O"
                            st.session_state.mac_programi.at[idx, "Kazanan"] = ""
                        elif durum == "Takım 1 Kazandı (W/O)":
                            st.session_state.mac_programi.at[idx, "Skor"] = "W/O"
                            st.session_state.mac_programi.at[idx, "Kazanan"] = "T1"
                        elif durum == "Takım 2 Kazandı (W/O)":
                            st.session_state.mac_programi.at[idx, "Skor"] = "W/O"
                            st.session_state.mac_programi.at[idx, "Kazanan"] = "T2"
                        else:
                            s1t1, s1t2 = int(m['1.Set T1']), int(m['1.Set T2'])
                            s2t1, s2t2 = int(m['2.Set T1']), int(m['2.Set T2'])
                            s3t1, s3t2 = int(m['3.Set T1']), int(m['3.Set T2'])
                            
                            if s1t1 != 0 or s1t2 != 0 or "Ret." in durum:
                                skor_str = f"{s1t1}-{s1t2}"
                                if s2t1 != 0 or s2t2 != 0 or s1t1 != 0 or s1t2 != 0: skor_str += f" | {s2t1}-{s2t2}"
                                if s3t1 != 0 or s3t2 != 0: skor_str += f" | {s3t1}-{s3t2}" 
                                
                                if durum == "Takım 1 Kazandı (Ret.)": skor_str += " Ret."
                                if durum == "Takım 2 Kazandı (Ret.)": skor_str += " Ret."
                                
                                st.session_state.mac_programi.at[idx, "Skor"] = skor_str
                                
                                if durum == "Takım 1 Kazandı (Ret.)":
                                    st.session_state.mac_programi.at[idx, "Kazanan"] = "T1"
                                elif durum == "Takım 2 Kazandı (Ret.)":
                                    st.session_state.mac_programi.at[idx, "Kazanan"] = "T2"
                                else:
                                    t1_set_sayisi = (s1t1 > s1t2) + (s2t1 > s2t2) + (s3t1 > s3t2)
                                    t2_set_sayisi = (s1t2 > s1t1) + (s2t2 > s2t1) + (s3t2 > s3t1)
                                    st.session_state.mac_programi.at[idx, "Kazanan"] = "T1" if t1_set_sayisi >= 2 else ("T2" if t2_set_sayisi >= 2 else "")
                            else:
                                st.session_state.mac_programi.at[idx, "Skor"] = "Oynanmadı"
                                st.session_state.mac_programi.at[idx, "Kazanan"] = ""
    
                df_gunluk_safe = st.session_state.mac_programi[(st.session_state.mac_programi['Tarih'] == formatted_tarih) & (st.session_state.mac_programi['Grup'].isin(gecerli_gruplar_t4))].copy()
                df_gunluk_safe = df_gunluk_safe.fillna("")
                
                df_gunluk_safe['Hakem'] = df_gunluk_safe['Hakem'].replace("", "Atanmadı")
    
                df_team_summary_list = []
                for (saat, tarih, gun, kort, grup, match_gun, eslesme, takim1, takim2), g_df in df_gunluk_safe.groupby(
                    ['Maç Saati', 'Tarih', 'Gün Adı', 'Kort', 'Grup', 'Gün', 'Eşleşme', 'Takım 1', 'Takım 2'], dropna=False
                ):
                    played = (g_df['Skor'] != 'Oynanmadı').sum()
                    team_score = "Oynanmadı"
                    team_winner = ""
                    
                    if played > 0:
                        eslesen_skorlar = st.session_state.skor_tablosu[
                            (st.session_state.skor_tablosu['Grup'] == grup) & 
                            (st.session_state.skor_tablosu['Gün'] == match_gun) & 
                            (st.session_state.skor_tablosu['Eşleşme'] == eslesme)
                        ]
                        
                        if not eslesen_skorlar.empty:
                            temp_stats = hesapla_tum_puan_durumu(eslesen_skorlar)
                            if not temp_stats.empty:
                                t1_row = temp_stats[temp_stats['Takım'] == takim1]
                                t2_row = temp_stats[temp_stats['Takım'] == takim2]
                                
                                if not t1_row.empty and not t2_row.empty:
                                    if t1_row.iloc[0]['Galibiyet'] > t2_row.iloc[0]['Galibiyet']: team_winner = "T1"
                                    elif t2_row.iloc[0]['Galibiyet'] > t1_row.iloc[0]['Galibiyet']: team_winner = "T2"
                                    
                                    t1_aldigi = float(t1_row.iloc[0]['Aldığı Maç'])
                                    t2_aldigi = float(t2_row.iloc[0]['Aldığı Maç'])
                                    
                                    t1_skor_gosterim = int(t1_aldigi) if t1_aldigi.is_integer() else t1_aldigi
                                    t2_skor_gosterim = int(t2_aldigi) if t2_aldigi.is_integer() else t2_aldigi
                                    
                                    team_score = f"{t1_skor_gosterim}-{t2_skor_gosterim}"
                                else:
                                    t1_match_wins = (g_df['Kazanan'] == 'T1').sum()
                                    t2_match_wins = (g_df['Kazanan'] == 'T2').sum()
                                    team_score = f"{t1_match_wins}-{t2_match_wins}"
                            else:
                                t1_match_wins = (g_df['Kazanan'] == 'T1').sum()
                                t2_match_wins = (g_df['Kazanan'] == 'T2').sum()
                                team_score = f"{t1_match_wins}-{t2_match_wins}"
                        else:
                            t1_match_wins = (g_df['Kazanan'] == 'T1').sum()
                            t2_match_wins = (g_df['Kazanan'] == 'T2').sum()
                            team_score = f"{t1_match_wins}-{t2_match_wins}"
    
                    hakem_ilk = g_df.iloc[0]['Hakem'] if 'Hakem' in g_df.columns else "Atanmadı"
                    if pd.isna(hakem_ilk) or hakem_ilk == "": hakem_ilk = "Atanmadı"
    
                    df_team_summary_list.append({
                        "Maç Saati": saat, "Tarih": tarih, "Gün Adı": gun, "Kort": kort,
                        "Grup": grup, "Gün": match_gun, "Branş": "Genel Skor", "Eşleşme": eslesme,
                        "Takım 1": takim1, "Takım 2": takim2, "T1 Oyuncu": "-", "T2 Oyuncu": "-",
                        "Skor": team_score, "Kazanan": team_winner, "Hakem": hakem_ilk
                    })
                df_team_summary = pd.DataFrame(df_team_summary_list)
    
                if st.session_state.admin_mi:
                    
                    st.markdown(f"### ➕ {formatted_tarih} Tarihine Takım Eşleşmesi Ekle ({aktif_asama})")
                    c1, c2, c3 = st.columns(3)
                    
                    gruplar_prog = dogal_sirala([g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
                    if not gruplar_prog:
                        st.info("Bu aşamada ekleyebileceğiniz grup bulunmuyor.")
                    else:
                        sec_grup_prog = c1.selectbox("Grup Seç:", gruplar_prog, key="prog_grup")
                        df_g_prog = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == sec_grup_prog]
                        gunler_prog = sorted(df_g_prog['Gün'].unique(), key=lambda x: int(x.split('.')[0]) if '.' in x else 99)
                        sec_gun_prog = c2.selectbox("Gün Seç:", gunler_prog, key="prog_gun")
                        df_m_prog = df_g_prog[df_g_prog['Gün'] == sec_gun_prog]
                        
                        mevcut_mask = df_m_prog.apply(lambda r: not st.session_state.mac_programi[
                            (st.session_state.mac_programi['Grup'] == r['Grup']) &
                            (st.session_state.mac_programi['Gün'] == r['Gün']) & 
                            (st.session_state.mac_programi['Branş'] == r['Branş']) &
                            (st.session_state.mac_programi['Eşleşme'] == r['Eşleşme'])
                        ].empty, axis=1)
                        df_m_prog_eklenebilir = df_m_prog[~mevcut_mask]
                        
                        if df_m_prog_eklenebilir.empty: 
                            c3.info("✅ Bu gruba/güne ait tüm maçlar programa yerleştirilmiş.")
                        else:
                            eslesmeler = df_m_prog_eklenebilir[['Eşleşme', 'Takım 1', 'Takım 2']].drop_duplicates()
                            mac_listesi = [f"{row['Takım 1']} vs {row['Takım 2']} ({row['Eşleşme']})" for idx, row in eslesmeler.iterrows()]
                            
                            sec_mac_adi = c3.selectbox("Eşleşme Seç (Tüm Maçlar Eklenecek):", mac_listesi, key="prog_mac")
                            if st.button("➕ Tüm Eşleşmeyi Akışa Ekle"):
                                secilen_eslesme_idx = mac_listesi.index(sec_mac_adi)
                                secilen_eslesme_bilgisi = eslesmeler.iloc[secilen_eslesme_idx]
                                secilen_eslesme_no = secilen_eslesme_bilgisi['Eşleşme']
                                
                                eklenecek_maclar = df_m_prog_eklenebilir[df_m_prog_eklenebilir['Eşleşme'] == secilen_eslesme_no]
                                
                                yeni_kayitlar = []
                                for _, r in eklenecek_maclar.iterrows():
                                    yeni_kayitlar.append({
                                        "Maç Saati": "10:00", "Tarih": formatted_tarih, "Gün Adı": gun_adi, "Kort": "Kort 1",
                                        "Grup": r['Grup'], "Gün": r['Gün'], "Branş": r['Branş'], "Eşleşme": r['Eşleşme'],
                                        "Takım 1": r['Takım 1'], "Takım 2": r['Takım 2'], "T1 Oyuncu": "", "T2 Oyuncu": "", "Skor": "Oynanmadı", "Kazanan": "", "Hakem": "Atanmadı"
                                    })
                                
                                st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, pd.DataFrame(yeni_kayitlar)], ignore_index=True)
                                if ortak_veriyi_kaydet():
                                    st.success(f"Eşleşmeye ait {len(yeni_kayitlar)} maç başarıyla eklendi!")
                                    st.rerun()
                                else:
                                    st.error("Sistem meşgul, lütfen tekrar deneyin.")
    
                    if not df_gunluk_safe.empty:
                        st.markdown("### 📋 Günlük Akış (Kort, Saat ve Hakem Atama Editörü)")
                        st.info("Aşağıdan her eşleşme (takım maçı) için **Kort, Saat ve Hakem** belirleyebilirsiniz. Belirlediğiniz bu 3 değer, eşleşmenin içindeki tüm bireysel maçlara otomatik uygulanır.")
                        
                        eslesme_sil_liste = ["Seçiniz"]
                        eslesme_idx_map = {}
                        for (grup_adi, eslesme_adi), g_df in df_gunluk_safe.groupby(['Grup', 'Eşleşme']):
                            t1 = g_df.iloc[0]['Takım 1']
                            t2 = g_df.iloc[0]['Takım 2']
                            kort = g_df.iloc[0]['Kort']
                            saat = g_df.iloc[0]['Maç Saati']
                            secenek_metni = f"{saat} - {kort} | {grup_adi} | {t1} vs {t2} ({eslesme_adi})"
                            eslesme_sil_liste.append(secenek_metni)
                            eslesme_idx_map[secenek_metni] = g_df.index.tolist()
    
                        secilen_sil_eslesme = st.selectbox("⛔ Programdan Kaldırılacak Eşleşmeyi Seçin:", eslesme_sil_liste, key="program_eslesme_sil_selectbox")
                        if secilen_sil_eslesme != "Seçiniz":
                            if st.button("❌ Seçilen Eşleşmeyi Tüm Maçlarıyla Programdan Kaldır"):
                                silinecek_indexler = eslesme_idx_map[secilen_sil_eslesme]
                                st.session_state.mac_programi.drop(index=silinecek_indexler, inplace=True)
                                st.session_state.mac_programi.reset_index(drop=True, inplace=True)
                                if ortak_veriyi_kaydet():
                                    st.success("Seçilen eşleşmeye ait tüm maçlar programdan silindi!")
                                    st.rerun()
                                else:
                                    st.error("Sistem meşgul, lütfen tekrar deneyin.")
                        st.divider()
                        
                        edited_dfs = []
                        for (grup_adi, eslesme_adi), grup_df in df_gunluk_safe.groupby(['Grup', 'Eşleşme']):
                            takim_skoru_etiketi = ""
                            team_winner = ""
                            if not df_team_summary.empty:
                                ozet_satiri = df_team_summary[(df_team_summary['Grup'] == grup_adi) & (df_team_summary['Eşleşme'] == eslesme_adi)]
                                if not ozet_satiri.empty:
                                    val = ozet_satiri.iloc[0]['Skor']
                                    team_winner = ozet_satiri.iloc[0]['Kazanan']
                                    if val != "Oynanmadı": takim_skoru_etiketi = f"  🟢 SKOR: {val}"
                            
                            kort = grup_df.iloc[0]['Kort']
                            tarih = grup_df.iloc[0]['Tarih']
                            saat = grup_df.iloc[0]['Maç Saati']
                            takim1 = grup_df.iloc[0]['Takım 1']
                            takim2 = grup_df.iloc[0]['Takım 2']
                            mevcut_hakem = grup_df.iloc[0]['Hakem']
                            if pd.isna(mevcut_hakem) or mevcut_hakem == "": mevcut_hakem = "Atanmadı"
                            
                            t1_baslik = f"**{takim1}**" if team_winner == "T1" else takim1
                            t2_baslik = f"**{takim2}**" if team_winner == "T2" else takim2
                            
                            expander_title = f"{saat} | {kort} | {grup_adi} | {t1_baslik} - {t2_baslik}{takim_skoru_etiketi} (👮‍♂️ {mevcut_hakem})"
                            
                            with st.expander(expander_title, expanded=False):
                                c_k, c_s, c_h = st.columns(3)
                                secilen_kort = c_k.text_input("📍 Kort (Tüm maçlara uygulanır):", value=kort, key=f"kort_{grup_adi}_{eslesme_adi}_{formatted_tarih}")
                                secilen_saat = c_s.text_input("⏰ Maç Saati (Tüm maçlara uygulanır):", value=saat, key=f"saat_{grup_adi}_{eslesme_adi}_{formatted_tarih}")
                                opts = ["Atanmadı"] + st.session_state.hakem_listesi
                                idx_h = opts.index(mevcut_hakem) if mevcut_hakem in opts else 0
                                secilen_hakem = c_h.selectbox("👮‍♂️ Hakem (Tüm maçlara uygulanır):", options=opts, index=idx_h, key=f"hakem_{grup_adi}_{eslesme_adi}_{formatted_tarih}")
                                
                                grup_df_ordered = sort_maclar(grup_df)[["Branş", "T1 Oyuncu", "T2 Oyuncu", "Skor", "Grup", "Gün", "Eşleşme", "Takım 1", "Takım 2", "Tarih", "Gün Adı", "Kazanan", "Kort", "Maç Saati", "Hakem"]]
                                
                                for idx_m, row_m in grup_df_ordered.iterrows():
                                    win = row_m.get('Kazanan', '')
                                    if win == 'T1' and row_m['T1 Oyuncu']:
                                        grup_df_ordered.at[idx_m, 'T1 Oyuncu'] = f"**{row_m['T1 Oyuncu']}**"
                                    elif win == 'T2' and row_m['T2 Oyuncu']:
                                        grup_df_ordered.at[idx_m, 'T2 Oyuncu'] = f"**{row_m['T2 Oyuncu']}**"
                                
                                disabled_cols = grup_df_ordered.columns.tolist()
                                
                                e_df = st.data_editor(
                                    grup_df_ordered, 
                                    use_container_width=True, 
                                    disabled=disabled_cols,
                                    column_config={
                                        "Grup": None, "Gün": None, "Eşleşme": None, "Takım 1": None, "Takım 2": None, "Tarih": None, "Gün Adı": None, "Kazanan": None,
                                        "Kort": None, "Maç Saati": None, "Hakem": None
                                    },
                                    key=f"editor_{grup_adi}_{eslesme_adi}_{formatted_tarih}"
                                )
                                
                                e_df['T1 Oyuncu'] = grup_df['T1 Oyuncu']
                                e_df['T2 Oyuncu'] = grup_df['T2 Oyuncu']
                                
                                e_df['Kort'] = secilen_kort
                                e_df['Maç Saati'] = secilen_saat
                                e_df['Hakem'] = secilen_hakem
                                edited_dfs.append(e_df)
    
                        if st.button("💾 Değişiklikleri ve Atamaları Kaydet"):
                            if edited_dfs:
                                guncel_program = pd.concat(edited_dfs)
                                st.session_state.mac_programi.drop(index=df_gunluk_safe.index, inplace=True)
                                guncel_program['Tarih'] = guncel_program['Tarih'].fillna(formatted_tarih)
                                st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, guncel_program]).reset_index(drop=True)
                                if ortak_veriyi_kaydet():
                                    st.success("Tüm atamalar ve program başarıyla güncellendi!")
                                    st.rerun()
                                else:
                                    st.error("Sistem meşgul, lütfen tekrar deneyin.")

                        # YAYINLAMA / GİZLEME KONTROLÜ
                        st.markdown("<br>", unsafe_allow_html=True)
                        is_published = st.session_state.yayinlanan_gunler.get(formatted_tarih, False)
                        
                        if not is_published:
                            st.error("🔴 BU GÜNÜN PROGRAMI ŞU AN YAYINDA DEĞİL (Gizli)")
                            st.info("Değişikliklerinizi kaydedip programın hatasız olduğundan emin olduktan sonra İzleyicilere, Kaptanlara ve Hakemlere görünür hale getirebilirsiniz.")
                            if st.button("📢 Günün Programını Yayınla", type="primary", use_container_width=True):
                                st.session_state.yayinlanan_gunler[formatted_tarih] = True
                                ortak_veriyi_kaydet()
                                st.rerun()
                        else:
                            st.success("🟢 BU GÜNÜN PROGRAMI ŞU AN YAYINDA (Herkes Görebilir)")
                            if st.button("🛑 Programı Yayından Kaldır (Sadece Başhakem Görebilir)", use_container_width=True):
                                st.session_state.yayinlanan_gunler[formatted_tarih] = False
                                ortak_veriyi_kaydet()
                                st.rerun()
    
                    st.markdown("---")
                    st.markdown("### ⚙️ Görünüm ve Çıktı Ayarları")
                    
                    with st.expander("🖨️ Islak İmzalı Hakem Maç Kağıtları"):
                        st.info("Kortlara dağıtılacak boş skor/imza kağıtlarını buradan üretebilirsiniz. Tüm günün maçlarını tek PDF'te basabilir veya sadece seçtiğiniz bir eşleşmenin kağıdını çıkarabilirsiniz.")
                        
                        gunluk_eslesmeler_listesi = []
                        eslesme_secenekleri = ["Seçiniz"]
                        
                        for (grup_adi, eslesme_adi), g_df in df_gunluk_safe.groupby(['Grup', 'Eşleşme']):
                            tarih_str = g_df.iloc[0]['Tarih']
                            saat = g_df.iloc[0]['Maç Saati']
                            kort = g_df.iloc[0]['Kort']
                            t1 = g_df.iloc[0]['Takım 1']
                            t2 = g_df.iloc[0]['Takım 2']
                            hakem = g_df.iloc[0]['Hakem']
                            
                            alt_maclar = [{"Branş": r['Branş']} for _, r in sort_maclar(g_df).iterrows()]
                            
                            # --- TAKIM KADROLARINI DOĞRUDAN ÇEKME VE AKTARMA (MAÇ PROGRAMI) ---
                            grup_kadro_sozlugu = st.session_state.takim_kadrolari.get(grup_adi, {})
                            t1_kadro = grup_kadro_sozlugu.get(t1, ["Kayıt yok"])
                            t2_kadro = grup_kadro_sozlugu.get(t2, ["Kayıt yok"])

                            mac_dict = {
                                "Grup": grup_adi, "Tarih": tarih_str, "Maç Saati": saat, 
                                "Kort": kort, "Takım 1": t1, "Takım 2": t2, "Hakem": hakem, 
                                "Alt Maclar": alt_maclar, "Eşleşme": eslesme_adi,
                                "T1_Kadro": t1_kadro,
                                "T2_Kadro": t2_kadro
                            }
                            gunluk_eslesmeler_listesi.append(mac_dict)
                            eslesme_secenekleri.append(f"{saat} | {kort} | {grup_adi} | {t1} vs {t2}")

                        if gunluk_eslesmeler_listesi:
                            pdf_bytes_toplu = generate_mac_sonuc_belgesi(gunluk_eslesmeler_listesi)
                            st.download_button(
                                label=f"📥 Günün Tüm Maç Kağıtlarını Tek PDF'te İndir ({len(gunluk_eslesmeler_listesi)} Sayfa)",
                                data=pdf_bytes_toplu,
                                file_name=f"Tum_Hakem_Kagitlari_{formatted_tarih}.pdf",
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True
                            )
                            
                            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                            st.markdown("**Veya Tek Bir Eşleşmeyi Yeniden Yazdır:**")
                            secilen_tekil = st.selectbox("Kağıdı çıkarılacak maçı seçin:", eslesme_secenekleri, key="tekil_kagit_secici")
                            if secilen_tekil != "Seçiniz":
                                secilen_idx = eslesme_secenekleri.index(secilen_tekil) - 1
                                tekil_veri = [gunluk_eslesmeler_listesi[secilen_idx]]
                                pdf_bytes_tekil = generate_mac_sonuc_belgesi(tekil_veri)
                                st.download_button(
                                    label="📥 Sadece Bu Maçın Kağıdını İndir",
                                    data=pdf_bytes_tekil,
                                    file_name=f"Hakem_Kagidi_{tekil_veri[0]['Takım 1']}_vs_{tekil_veri[0]['Takım 2']}.pdf",
                                    mime="application/pdf"
                                )
                        else:
                            st.warning("Bu tarih için programlanmış maç bulunmuyor.")

                    with st.expander("📄 PDF Çıktı Ayarları"):
                        gosterim_sekli = st.radio("PDF Gösterim Şekli:", ["Bireysel Maçlar (Detaylı Hiyerarşik Çıktı)", "Takım Maçları (Sadece Genel Skor)"], horizontal=True)
                        is_bireysel_pdf = "Bireysel" in gosterim_sekli
                        tum_kolonlar = ["Kort", "Maç Saati", "Tarih", "Gün Adı", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Skor", "Kazanan", "Hakem"]
                        
                        if not is_bireysel_pdf:
                            tum_kolonlar = [c for c in tum_kolonlar if c not in ["T1 Oyuncu", "T2 Oyuncu"]]
                            
                        secilen_pdf_cols = st.multiselect("PDF'e eklenecek sütunları seçin:", options=tum_kolonlar, default=["Maç Saati", "Kort", "Grup", "Takım 1", "Takım 2"])
    
                        if is_bireysel_pdf:
                            pdf_rows = []
                            for (grup_adi, eslesme_adi), g_df in df_gunluk_safe.groupby(['Grup', 'Eşleşme'], dropna=False):
                                t1 = g_df.iloc[0]['Takım 1']
                                t2 = g_df.iloc[0]['Takım 2']
                                saat = g_df.iloc[0]['Maç Saati']
                                kort = g_df.iloc[0]['Kort']
                                tarih_str = g_df.iloc[0]['Tarih']
                                gun_isim = g_df.iloc[0]['Gün Adı']
                                gun_val = g_df.iloc[0]['Gün']
                                
                                team_score = "Oynanmadı"
                                team_winner = ""
                                ozet_df = df_team_summary[(df_team_summary['Grup'] == grup_adi) & (df_team_summary['Eşleşme'] == eslesme_adi)]
                                if not ozet_df.empty:
                                    team_score = ozet_df.iloc[0]['Skor']
                                    team_winner = ozet_df.iloc[0]['Kazanan']
                                
                                header_row = {
                                    "Kort": kort, "Maç Saati": saat, "Tarih": tarih_str, "Gün Adı": gun_isim, 
                                    "Grup": grup_adi, "Gün": gun_val, "Eşleşme": eslesme_adi,
                                    "Branş": "**TAKIM EŞLEŞMESİ**",
                                    "Takım 1": f"**{t1}**" if team_winner == "T1" else t1, 
                                    "Takım 2": f"**{t2}**" if team_winner == "T2" else t2,
                                    "T1 Oyuncu": "", "T2 Oyuncu": "",
                                    "Skor": f"**{team_score}**", "Kazanan": "", "Hakem": "",
                                    "_IS_HEADER_": True
                                }
                                pdf_rows.append(header_row)
                                
                                for _, row in sort_maclar(g_df).iterrows():
                                    match_row = row.copy()
                                    match_row['Branş'] = f" -> {match_row['Branş']}" 
                                    
                                    win = match_row.get('Kazanan', '')
                                    if win == 'T1':
                                        match_row['Takım 1'] = f"**{match_row['Takım 1']}**"
                                        if match_row['T1 Oyuncu']: match_row['T1 Oyuncu'] = f"**{match_row['T1 Oyuncu']}**"
                                    elif win == 'T2':
                                        match_row['Takım 2'] = f"**{match_row['Takım 2']}**"
                                        if match_row['T2 Oyuncu']: match_row['T2 Oyuncu'] = f"**{match_row['T2 Oyuncu']}**"
                                        
                                    match_row['_IS_HEADER_'] = False
                                    pdf_rows.append(match_row.to_dict())
                                    
                            df_pdf_export = pd.DataFrame(pdf_rows)
                        else:
                            df_pdf_export = df_team_summary.copy()
                            if not df_pdf_export.empty:
                                df_pdf_export['_IS_HEADER_'] = False
                                for i in df_pdf_export.index:
                                    win = df_pdf_export.at[i, 'Kazanan']
                                    if win == 'T1': df_pdf_export.at[i, 'Takım 1'] = f"**{df_pdf_export.at[i, 'Takım 1']}**"
                                    elif win == 'T2': df_pdf_export.at[i, 'Takım 2'] = f"**{df_pdf_export.at[i, 'Takım 2']}**"
                                    df_pdf_export.at[i, 'Skor'] = f"**{df_pdf_export.at[i, 'Skor']}**"
                                    
                        if not df_pdf_export.empty and secilen_pdf_cols:
                            final_pdf_df = df_pdf_export[secilen_pdf_cols].copy()
                            final_pdf_df["_IS_HEADER_"] = df_pdf_export["_IS_HEADER_"]
                            
                            pdf_notu = st.session_state.gunluk_notlar.get(formatted_tarih, "")
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            pdf_turu = st.radio("📄 Belge Başlığı (PDF'te ne yazsın?):", ["Maç Programı (Sabah)", "Günün Sonuçları (Akşam)"], horizontal=True)
                            
                            if "Sonuçları" in pdf_turu:
                                baslik_metni = f"{formatted_tarih} {gun_adi} - Günün Sonuçları"
                                dosya_adi = f"mac_sonuclari_{formatted_tarih}.pdf"
                                buton_adi = "📥 Günün Sonuçlarını PDF Olarak İndir"
                            else:
                                baslik_metni = f"{formatted_tarih} {gun_adi} - Maç Programı"
                                dosya_adi = f"mac_programi_{formatted_tarih}.pdf"
                                buton_adi = "📥 Maç Programını PDF Olarak İndir"
                                
                            pdf_bytes_admin = generate_pdf(final_pdf_df, baslik_metni, not_metni=pdf_notu, kategori_map=st.session_state.grup_kategorileri)
                            st.download_button(buton_adi, data=pdf_bytes_admin, file_name=dosya_adi, mime="application/pdf", key="pdf_admin")
    
                else:
                    st.markdown(f"### 📋 {formatted_tarih} Tarihli Maç Akışı ({aktif_asama})")
                    if df_gunluk_safe.empty:
                        st.info("Bu tarihte planlanmış maç bulunmamaktadır.")
                    else:
                        st.divider()
                        for (grup_adi, eslesme_adi), grup_df in df_gunluk_safe.groupby(['Grup', 'Eşleşme']):
                            takim_skoru_etiketi = ""
                            team_winner = ""
                            if not df_team_summary.empty:
                                ozet_satiri = df_team_summary[(df_team_summary['Grup'] == grup_adi) & (df_team_summary['Eşleşme'] == eslesme_adi)]
                                if not ozet_satiri.empty:
                                    val = ozet_satiri.iloc[0]['Skor']
                                    team_winner = ozet_satiri.iloc[0]['Kazanan']
                                    if val != "Oynanmadı": takim_skoru_etiketi = f"  🟢 SKOR: {val}"
    
                            kort = grup_df.iloc[0]['Kort']
                            saat = grup_df.iloc[0]['Maç Saati']
                            takim1 = grup_df.iloc[0]['Takım 1']
                            takim2 = grup_df.iloc[0]['Takım 2']
                            gun_kodu = grup_df.iloc[0]['Gün']
                            mevcut_hakem = grup_df.iloc[0]['Hakem']
                            if pd.isna(mevcut_hakem) or mevcut_hakem == "Atanmadı": mevcut_hakem = ""
                            
                            match_key = f"{grup_adi}_{gun_kodu}_{eslesme_adi}"
                            is_approved = st.session_state.esame_onayli.get(match_key, False)
                            
                            hakem_baslik_etiketi = f" (👮‍♂️ {mevcut_hakem})" if mevcut_hakem else ""
                            
                            t1_baslik = f"**{takim1}**" if team_winner == "T1" else takim1
                            t2_baslik = f"**{takim2}**" if team_winner == "T2" else takim2
                            
                            expander_title = f"🎾 {saat} | {kort} | {grup_adi} | {t1_baslik} - {t2_baslik}{takim_skoru_etiketi}{hakem_baslik_etiketi}"
                            
                            with st.expander(expander_title, expanded=False):
                                html_rows = ""
                                for _, row in sort_maclar(grup_df).iterrows():
                                    skor = str(row.get('Skor', 'Oynanmadı'))
                                    skor_html = f"<span style='color:#28a745; font-weight:bold;'>{skor}</span>" if skor not in ["Oynanmadı", ""] else "<i>Bekleniyor</i>"
                                    
                                    if is_approved:
                                        t1_o = html.escape(str(row.get('T1 Oyuncu', '')).strip())
                                        t2_o = html.escape(str(row.get('T2 Oyuncu', '')).strip())
                                    else:
                                        t1_o = "🔒 Esame Bekleniyor"
                                        t2_o = "🔒 Esame Bekleniyor"
                                    
                                    if row.get('Kazanan') == 'T1' and is_approved: t1_o = f"<b>{t1_o}</b>"
                                    elif row.get('Kazanan') == 'T2' and is_approved: t2_o = f"<b>{t2_o}</b>"
                                    
                                    html_rows += f"<tr><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{row['Branş']}</td><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{t1_o} / {t2_o}</td><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{skor_html}</td></tr>"
                                
                                st.markdown(f"""
                                <table style="width:100%; border-collapse: collapse; font-family: sans-serif;">
                                    <tr><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Branş</th><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Oyuncular</th><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Skor</th></tr>
                                    {html_rows}
                                </table>
                                """, unsafe_allow_html=True)

    # ==============================================================================
    # 13. TAKIM KADROLARI (İZLEYİCİ VE GENEL GÖRÜNÜM)
    # ==============================================================================
    elif menu_secim == "🛡️ Takım Kadroları":
        st.subheader(f"🛡️ Takım Kadroları ({aktif_asama})")
        
        gosterilecek_gruplar = dogal_sirala([g for g in st.session_state.takim_kadrolari.keys() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
        
        if not gosterilecek_gruplar:
            st.info(f"{aktif_asama} için kayıtlı takım veya kadro bulunmuyor.")
        else:
            kategori_dict = {}
            for g_isim in gosterilecek_gruplar:
                f_kat = st.session_state.grup_kategorileri.get(g_isim, "Erkekler")
                f_yas = st.session_state.grup_yas_gruplari.get(g_isim, "Yaş Belirtme")
                
                if f_yas != "Yaş Belirtme":
                    kategori_anahtari = f_yas + " " + f_kat
                else:
                    kategori_anahtari = f_kat
                
                if kategori_anahtari not in kategori_dict:
                    kategori_dict[kategori_anahtari] = []
                kategori_dict[kategori_anahtari].append(g_isim)
                
            kategori_isimleri = dogal_sirala(list(kategori_dict.keys()))
            
            secilen_kat = st.selectbox("📂 Görüntülenecek Kategoriyi Seçin:", kategori_isimleri, key="kadro_kat_sec")
            st.markdown("<br>", unsafe_allow_html=True)
            
            for g_isim in dogal_sirala(kategori_dict[secilen_kat]):
                f_turu = st.session_state.grup_formatlari.get(g_isim, "")
                g_kadro = st.session_state.takim_kadrolari[g_isim]
                takim_sayisi = len(g_kadro.keys())
                
                with st.expander(f"📁 {g_isim} ({takim_sayisi} Takım | {f_turu})", expanded=False):
                    for t_isim in dogal_sirala(list(g_kadro.keys())):
                        with st.expander(f"🛡️ {t_isim}", expanded=False):
                            oyuncular = g_kadro[t_isim]
                            if not oyuncular or oyuncular == ["Belirtilmedi"]:
                                st.warning("Bu takım için henüz oyuncu kadrosu girilmemiş.")
                            else:
                                html_liste = "<ul style='list-style-type: none; padding-left: 0; margin-top: 5px;'>"
                                for idx_o, oyuncu in enumerate(oyuncular):
                                    sira_no = idx_o + 1
                                    html_liste += f"<li style='padding: 6px 0; border-bottom: 1px solid #eee; font-size: 15px;'><b>{sira_no}.</b> {oyuncu}</li>"
                                html_liste += "</ul>"
                                st.markdown(html_liste, unsafe_allow_html=True)

    # ==============================================================================
    # 14. DUYURULAR
    # ==============================================================================
    elif menu_secim == "📢 Duyurular":
        st.subheader("📢 Turnuva Duyuruları ve Belgeler")
        if st.session_state.admin_mi:
            st.markdown("### ✍️ Duyuru Düzenleme (Sadece Başhakem)")
            yeni_duyuru = st.text_area("Duyuru Metni:", value=st.session_state.duyuru_metni, height=150)
            if st.button("💾 Duyuruyu Kaydet"):
                st.session_state.duyuru_metni = yeni_duyuru
                if ortak_veriyi_kaydet():
                    st.success("Duyuru metni başarıyla güncellendi!")
                else:
                    st.error("Sistem meşgul, lütfen tekrar deneyin.")
            
            st.markdown("---")
            st.markdown("### 📄 Turnuva Belgeleri Ekle (Çoklu Yükleme)")
            st.info("Kural kitapçığı veya yönetmelik gibi PDF dosyalarını sisteme buradan yükleyebilirsiniz. (Not: Ücretsiz bulut sunucular uyku moduna geçtiğinde yüklenen PDF dosyaları silinebilir. Turnuva anında profesyonel sunucuya geçildiğinde bu durum kalıcı olarak çözülecektir.)")
            uploaded_pdfs = st.file_uploader("PDF Dosyalarını Seçin:", type=["pdf"], accept_multiple_files=True)
            if uploaded_pdfs:
                if st.button("📤 Seçilen PDF'leri Sisteme Yükle"):
                    for pdf_file in uploaded_pdfs:
                        file_path = os.path.join(BELGELER_KLASORU, pdf_file.name)
                        with open(file_path, "wb") as f:
                            f.write(pdf_file.getbuffer())
                    st.success("Belgeler başarıyla yüklendi!")
                    st.rerun()
            
            pdf_dosyalari = [f for f in os.listdir(BELGELER_KLASORU) if f.endswith('.pdf')]
            if pdf_dosyalari:
                st.markdown("### 🗑️ Yüklü Belgeleri Yönet")
                for pdf in pdf_dosyalari:
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"📄 **{pdf}**", unsafe_allow_html=True)
                    if col2.button("Sil", key=f"del_{pdf}"):
                        os.remove(os.path.join(BELGELER_KLASORU, pdf))
                        st.success(f"{pdf} başarıyla silindi!")
                        st.rerun()
        else:
            st.markdown("### 📝 Güncel Duyurular")
            if st.session_state.duyuru_metni: st.info(st.session_state.duyuru_metni)
            else: st.write("Şu an için aktif bir turnuva duyurusu bulunmamaktadır.")
                
            st.markdown("---")
            st.markdown("### 📄 Turnuva Belgeleri")
            pdf_dosyalari = [f for f in os.listdir(BELGELER_KLASORU) if f.endswith('.pdf')]
            if pdf_dosyalari:
                st.write("Aşağıdaki belgelere tıklayarak sayfadan ayrılmadan doğrudan okuyabilirsiniz:")
                for pdf in pdf_dosyalari:
                    dosya_yolu = os.path.join(BELGELER_KLASORU, pdf)
                    with st.expander(f"📖 {pdf} - Görüntülemek İçin Tıklayın"):
                        show_pdf(dosya_yolu)
                        with open(dosya_yolu, "rb") as f:
                            st.download_button(label=f"📥 {pdf} Dosyasını İndir", data=f.read(), file_name=pdf, mime="application/pdf", key=f"dl_btn_{pdf}")
            else:
                st.write("Sisteme henüz herhangi bir belge yüklenmemiş.")
