import streamlit as st
import streamlit.components.v1 as components
import sys
import subprocess
import pandas as pd
import json
import os
import datetime
import base64
import shutil
import re
import html
import random
import time
import uuid
from supabase import create_client, Client
from fpdf import FPDF

def arkaplan_ekle(resim_yolu):
    try:
        with open(resim_yolu, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpg;base64,{encoded_string}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        pass

# --- GENEL SAYFA AYARLARI ---
st.set_page_config(page_title="Tenis Turnuva Otomasyonu", page_icon="🎾", layout="wide", initial_sidebar_state="collapsed")
arkaplan_ekle("arkaplan.jpg")

# --- SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None # İnternet veya şifre yoksa hata verme, uçak moduna hazır ol

supabase = init_supabase()

# --- GENEL STİLLER ---
st.markdown("""
<style>
    footer {visibility: hidden !important;}
    
    .dev-buton .stButton > button {
        border-radius: 12px;
        min-height: 80px !important; 
        font-size: 18px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.2s ease-in-out;
    }
    .dev-buton .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# --- SADECE MİSAFİR MODU İÇİN GİZLİLİK KALKANI ---
if not st.session_state.get("admin_mi", False) and not st.session_state.get("kaptan_mi", False) and not st.session_state.get("hakem_mi", False):
    st.markdown("""
    <style>
        [data-testid="stToolbar"] {visibility: hidden !important;}
    </style>
    """, unsafe_allow_html=True)

# --- SABİT KLASÖR YOLU AYARI ---
SISTEM_KLASORU = os.path.dirname(os.path.abspath(__file__))
BELGELER_KLASORU = os.path.join(SISTEM_KLASORU, "turnuva_belgeleri")

if not os.path.exists(BELGELER_KLASORU):
    os.makedirs(BELGELER_KLASORU)

# ==============================================================================
# SİSTEM FONKSİYONLARI
# ==============================================================================

def dogal_sirala(liste):
    def _natural_keys(text):
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]
    return sorted(liste, key=_natural_keys)

def sort_maclar(df):
    if df.empty: return df
    sort_map = {"3. Tekler": 1, "2. Tekler": 2, "1. Tekler": 3, "2. Çiftler": 4, "1. Çiftler": 5, "Çiftler": 6}
    df_temp = df.copy()
    df_temp['sira'] = df_temp['Branş'].map(sort_map).fillna(99)
    if 'Maç Saati' in df_temp.columns and 'Kort' in df_temp.columns:
        return df_temp.sort_values(['Maç Saati', 'Kort', 'Grup', 'Eşleşme', 'sira']).drop(columns=['sira'])
    elif 'Eşleşme' in df_temp.columns:
        return df_temp.sort_values(['Grup', 'Eşleşme', 'sira']).drop(columns=['sira'])
    else:
        return df_temp.sort_values('sira').drop(columns=['sira'])

FONT_YUKLENDI = os.path.exists("arial.ttf")
FONT_BOLD_YUKLENDI = os.path.exists("arialbd.ttf")

def to_pdf_text(text):
    if FONT_YUKLENDI: return str(text)
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def setup_pdf_fonts(pdf):
    if FONT_YUKLENDI:
        try:
            pdf.add_font("ArialTR", "", "arial.ttf", uni=True)
            if FONT_BOLD_YUKLENDI:
                pdf.add_font("ArialTR", "B", "arialbd.ttf", uni=True)
        except:
            pass

def apply_font(pdf, bold=False, size=10):
    if FONT_YUKLENDI:
        if bold and FONT_BOLD_YUKLENDI:
            pdf.set_font("ArialTR", "B", size)
        else:
            pdf.set_font("ArialTR", "", size)
    else:
        pdf.set_font("Arial", 'B' if bold else '', size)

def pdf_cell_fit(pdf, w, h, txt, border=1, align='C', is_bold=False, fill=False, base_size=9):
    size = base_size
    apply_font(pdf, bold=is_bold, size=size)
    while pdf.get_string_width(to_pdf_text(txt)) > (w - 2) and size > 5:
        size -= 0.5
        apply_font(pdf, bold=is_bold, size=size)
    pdf.cell(w, h, to_pdf_text(txt), border=border, align=align, fill=fill)
    apply_font(pdf, bold=False, size=9) 

def get_proportional_widths(pdf, df, usable_width=190):
    col_widths = []
    for col in df.columns:
        max_w = pdf.get_string_width(to_pdf_text(col)) + 4
        for _, row in df.iterrows():
            text = str(row[col])
            if text.startswith("**") and text.endswith("**"): text = text[2:-2]
            w = pdf.get_string_width(to_pdf_text(text)) + 4
            if w > max_w: max_w = w
        col_widths.append(max_w)
    
    total_w = sum(col_widths)
    return [w * (usable_width / total_w) for w in col_widths]

def get_pdf_bytes(pdf):
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

def generate_pdf(df, baslik, not_metni=""):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    setup_pdf_fonts(pdf)
    
    apply_font(pdf, bold=True, size=14)
    pdf.cell(0, 10, to_pdf_text(baslik), ln=True, align='C')
    
    if not_metni:
        pdf.ln(2)
        apply_font(pdf, bold=False, size=10)
        pdf.multi_cell(0, 6, to_pdf_text(f"Bashakem Notu: {not_metni}"), align='C')
        pdf.ln(5)
    else:
        pdf.ln(5)
    
    df_print = df.copy()
    
    # GİZLİ KOLON KONTROLÜ
    has_header_col = "_IS_HEADER_" in df_print.columns
    if has_header_col:
        header_flags = df_print["_IS_HEADER_"].tolist()
        df_print = df_print.drop(columns=["_IS_HEADER_"])
    
    if len(df_print.columns) > 0:
        col_widths = get_proportional_widths(pdf, df_print)
        
        pdf.set_fill_color(200, 200, 200)
        for i, col in enumerate(df_print.columns): 
            pdf_cell_fit(pdf, col_widths[i], 10, col, is_bold=True, fill=True, base_size=10)
        pdf.ln()
        
        for row_idx, row in df_print.reset_index(drop=True).iterrows():
            is_takim_satiri = False
            
            if has_header_col:
                is_takim_satiri = bool(header_flags[row_idx])
            else:
                if "Skor" in df_print.columns and str(row["Skor"]).startswith("**"):
                    is_takim_satiri = True
                else:
                    for val in row.values:
                        if "**TAKIM EŞLEŞMESİ**" in str(val):
                            is_takim_satiri = True
                            break
                    if not is_takim_satiri and "Takım 1" in df_print.columns and "Takım 2" in df_print.columns:
                        if str(row["Takım 1"]).startswith("**") and str(row["Takım 2"]).startswith("**"):
                            is_takim_satiri = True
            
            if is_takim_satiri:
                pdf.set_fill_color(225, 225, 225)
            
            for i, item in enumerate(row): 
                text = str(item)
                is_bold = False
                
                if text.startswith("**") and text.endswith("**"):
                    text = text[2:-2]
                    is_bold = True
                
                hedef_punto = 10.5 if is_takim_satiri else 9
                    
                if is_bold and FONT_YUKLENDI and not FONT_BOLD_YUKLENDI:
                    text = f"{text} *" 
                    
                pdf_cell_fit(pdf, col_widths[i], 8, text, is_bold=is_bold, fill=is_takim_satiri, base_size=hedef_punto)
            pdf.ln()
    return get_pdf_bytes(pdf)

def generate_combined_standings_pdf(gruplar_dict):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    setup_pdf_fonts(pdf)
    
    for grup_adi, df in gruplar_dict.items():
        satir_sayisi = len(df)
        gerekli_yukseklik = 10 + 8 + (satir_sayisi * 8) + 10 
        if pdf.get_y() + gerekli_yukseklik > 280: 
            pdf.add_page()

        apply_font(pdf, bold=True, size=12)
        pdf.cell(0, 10, to_pdf_text(grup_adi + " Puan Durumu"), ln=True, align='L')
        
        if len(df.columns) > 0:
            col_widths = get_proportional_widths(pdf, df)
            for i, col in enumerate(df.columns): 
                pdf_cell_fit(pdf, col_widths[i], 8, col, is_bold=True)
            pdf.ln()
            for _, row in df.iterrows():
                for i, item in enumerate(row): 
                    pdf_cell_fit(pdf, col_widths[i], 8, str(item), is_bold=False)
                pdf.ln()
        pdf.ln(5)
    return get_pdf_bytes(pdf)

def generate_klasman_pdf(kategori_adi, birinciler_liste, ikinciler_liste, ligde_kalanlar, dusenler):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    setup_pdf_fonts(pdf)

    # Resmi Antet
    apply_font(pdf, bold=True, size=16)
    pdf.cell(0, 8, to_pdf_text("TURKIYE TENIS FEDERASYONU"), ln=True, align='C')
    apply_font(pdf, bold=False, size=12)
    pdf.cell(0, 6, to_pdf_text("Takim Sampiyonasi Resmi Sonuc Bildirgesi"), ln=True, align='C')
    pdf.line(10, pdf.get_y()+2, 200, pdf.get_y()+2)
    pdf.ln(10)

    # Ana Başlık
    apply_font(pdf, bold=True, size=14)
    pdf.cell(0, 10, to_pdf_text(f"KATEGORI: {kategori_adi.upper()} - NIHAI KLASMAN"), ln=True, align='C')
    pdf.ln(5)

    current_rank = 1

    if birinciler_liste:
        pdf.set_fill_color(220, 220, 220)
        apply_font(pdf, bold=True, size=11)
        pdf.cell(0, 8, to_pdf_text("SAMPİYONLUK KURSUSU"), border=1, ln=True, fill=True, align='L')
        apply_font(pdf, bold=False, size=11)
        pdf.ln(2)
        for takim in birinciler_liste:
            unvan = ""
            if current_rank == 1: unvan = " (Sampiyon)"
            elif current_rank == 2: unvan = " (Ikinci)"
            elif current_rank == 3: unvan = " (Ucuncu)"
            elif current_rank == 4: unvan = " (Dorduncu)"
            pdf.cell(0, 7, to_pdf_text(f"  {current_rank}. Sira: {takim}{unvan}"), ln=True)
            current_rank += 1
        pdf.ln(5)

    if ikinciler_liste:
        pdf.set_fill_color(235, 235, 235)
        apply_font(pdf, bold=True, size=11)
        pdf.cell(0, 8, to_pdf_text("IKINCILER GRUBU (Klasman)"), border=1, ln=True, fill=True, align='L')
        apply_font(pdf, bold=False, size=11)
        pdf.ln(2)
        for takim in ikinciler_liste:
            pdf.cell(0, 7, to_pdf_text(f"  {current_rank}. Sira: {takim}"), ln=True)
            current_rank += 1
        pdf.ln(5)

    if ligde_kalanlar:
        pdf.set_fill_color(245, 245, 245)
        apply_font(pdf, bold=True, size=11)
        pdf.cell(0, 8, to_pdf_text("LIGDE KALANLAR (Play-Out Ust Siralar)"), border=1, ln=True, fill=True, align='L')
        apply_font(pdf, bold=False, size=11)
        pdf.ln(2)
        for takim in dogal_sirala(ligde_kalanlar):
            pdf.cell(0, 7, to_pdf_text(f"  - {takim}"), ln=True)
        pdf.ln(5)

    if dusenler:
        pdf.set_fill_color(245, 245, 245)
        apply_font(pdf, bold=True, size=11)
        pdf.cell(0, 8, to_pdf_text("LIGDEN DUSENLER (Play-Out Alt Siralar)"), border=1, ln=True, fill=True, align='L')
        apply_font(pdf, bold=False, size=11)
        pdf.ln(2)
        for takim in dogal_sirala(dusenler):
            pdf.cell(0, 7, to_pdf_text(f"  - {takim}"), ln=True)

    return get_pdf_bytes(pdf)

def generate_toplu_klasman_pdf(kategoriler_verisi):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    setup_pdf_fonts(pdf)

    for kat_adi, veriler in kategoriler_verisi.items():
        pdf.add_page()
        
        # Resmi Antet
        apply_font(pdf, bold=True, size=16)
        pdf.cell(0, 8, to_pdf_text("TURKIYE TENIS FEDERASYONU"), ln=True, align='C')
        apply_font(pdf, bold=False, size=12)
        pdf.cell(0, 6, to_pdf_text("Takim Sampiyonasi Resmi Sonuc Bildirgesi"), ln=True, align='C')
        pdf.line(10, pdf.get_y()+2, 200, pdf.get_y()+2)
        pdf.ln(10)
        
        apply_font(pdf, bold=True, size=14)
        pdf.cell(0, 10, to_pdf_text(f"KATEGORI: {kat_adi.upper()} - NIHAI KLASMAN"), ln=True, align='C')
        pdf.ln(5)

        current_rank = 1
        birinciler = veriler.get("birinciler", [])
        ikinciler = veriler.get("ikinciler", [])
        ligde_kalanlar = veriler.get("ligde_kalanlar", [])
        dusenler = veriler.get("dusenler", [])

        if birinciler:
            pdf.set_fill_color(220, 220, 220)
            apply_font(pdf, bold=True, size=11)
            pdf.cell(0, 8, to_pdf_text("SAMPIYONLUK KURSUSU"), border=1, ln=True, fill=True, align='L')
            apply_font(pdf, bold=False, size=11)
            pdf.ln(2)
            for takim in birinciler:
                unvan = ""
                if current_rank == 1: unvan = " (Sampiyon)"
                elif current_rank == 2: unvan = " (Ikinci)"
                elif current_rank == 3: unvan = " (Ucuncu)"
                elif current_rank == 4: unvan = " (Dorduncu)"
                pdf.cell(0, 7, to_pdf_text(f"  {current_rank}. Sira: {takim}{unvan}"), ln=True)
                current_rank += 1
            pdf.ln(5)

        if ikinciler:
            pdf.set_fill_color(235, 235, 235)
            apply_font(pdf, bold=True, size=11)
            pdf.cell(0, 8, to_pdf_text("IKINCILER GRUBU (Klasman)"), border=1, ln=True, fill=True, align='L')
            apply_font(pdf, bold=False, size=11)
            pdf.ln(2)
            for takim in ikinciler:
                pdf.cell(0, 7, to_pdf_text(f"  {current_rank}. Sira: {takim}"), ln=True)
                current_rank += 1
            pdf.ln(5)

        if ligde_kalanlar:
            pdf.set_fill_color(245, 245, 245)
            apply_font(pdf, bold=True, size=11)
            pdf.cell(0, 8, to_pdf_text("LIGDE KALANLAR (Play-Out Ust Siralar)"), border=1, ln=True, fill=True, align='L')
            apply_font(pdf, bold=False, size=11)
            pdf.ln(2)
            for takim in dogal_sirala(ligde_kalanlar):
                pdf.cell(0, 7, to_pdf_text(f"  - {takim}"), ln=True)
            pdf.ln(5)

        if dusenler:
            pdf.set_fill_color(245, 245, 245)
            apply_font(pdf, bold=True, size=11)
            pdf.cell(0, 8, to_pdf_text("LIGDEN DUSENLER (Play-Out Alt Siralar)"), border=1, ln=True, fill=True, align='L')
            apply_font(pdf, bold=False, size=11)
            pdf.ln(2)
            for takim in dogal_sirala(dusenler):
                pdf.cell(0, 7, to_pdf_text(f"  - {takim}"), ln=True)

    return get_pdf_bytes(pdf)

def set_gecerli_mi(t1, t2, is_set3=False, durum="Tamamlandı"):
    if durum != "Tamamlandı": return True, ""
    if t1 == 0 and t2 == 0: return True, ""
    if t1 < 0 or t2 < 0: return False, "Skorlar negatif olamaz."
    max_s, min_s = max(t1, t2), min(t1, t2)
    diff = max_s - min_s
    if is_set3:
        if max_s >= 10:
            if max_s == 10 and min_s <= 8: return True, ""
            elif max_s > 10 and diff == 2: return True, ""
            else: return False, "Süper Tie-Break kurallarına uymuyor."
        else:
            if max_s < 6: return False, "Set en az 6 oyun olmalıdır."
            if max_s == 6 and diff >= 2: return True, ""
            if max_s == 7 and (diff == 2 or diff == 1): return True, ""
            return False, "Geçersiz normal set skoru."
    else:
        if max_s < 6: return False, "Set en az 6 oyun olmalıdır."
        if max_s == 6 and diff >= 2: return True, ""
        if max_s == 7 and (diff == 2 or diff == 1): return True, ""
        return False, "Geçersiz set skoru."

def eslesmeleri_olustur(grup_adi, takimlar, grup_tipi, format_secimi):
    if grup_tipi == "2'li Grup":
        base_matches = [{"Gün": "1. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]}]
    elif grup_tipi == "3'lü Grup":
        base_matches = [
            {"Gün": "1. Gün", "Eşleşme": "2 ve 3", "Takım 1": takimlar[1], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "1 ve 3", "Takım 1": takimlar[0], "Takım 2": takimlar[2]},
            {"Gün": "3. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]},
        ]
    elif grup_tipi == "4'lü Grup":
        base_matches = [
            {"Gün": "1. Gün", "Eşleşme": "1 ve 4", "Takım 1": takimlar[0], "Takım 2": takimlar[3]},
            {"Gün": "1. Gün", "Eşleşme": "2 ve 3", "Takım 1": takimlar[1], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "1 ve 3", "Takım 1": takimlar[0], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "2 ve 4", "Takım 1": takimlar[1], "Takım 2": takimlar[3]},
            {"Gün": "3. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]},
            {"Gün": "3. Gün", "Eşleşme": "3 ve 4", "Takım 1": takimlar[2], "Takım 2": takimlar[3]},
        ]
    elif grup_tipi == "5'li Grup":
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
    else: 
        base_matches = [
            {"Gün": "1. Gün", "Eşleşme": "1 ve 6", "Takım 1": takimlar[0], "Takım 2": takimlar[5]},
            {"Gün": "1. Gün", "Eşleşme": "2 ve 5", "Takım 1": takimlar[1], "Takım 2": takimlar[4]},
            {"Gün": "1. Gün", "Eşleşme": "3 ve 4", "Takım 1": takimlar[2], "Takım 2": takimlar[3]},
            {"Gün": "2. Gün", "Eşleşme": "1 ve 5", "Takım 1": takimlar[0], "Takım 2": takimlar[4]},
            {"Gün": "2. Gün", "Eşleşme": "2 ve 3", "Takım 1": takimlar[1], "Takım 2": takimlar[2]},
            {"Gün": "2. Gün", "Eşleşme": "4 ve 6", "Takım 1": takimlar[3], "Takım 2": takimlar[5]},
            {"Gün": "3. Gün", "Eşleşme": "1 ve 4", "Takım 1": takimlar[0], "Takım 2": takimlar[3]},
            {"Gün": "3. Gün", "Eşleşme": "5 ve 3", "Takım 1": takimlar[4], "Takım 2": takimlar[2]},
            {"Gün": "3. Gün", "Eşleşme": "2 ve 6", "Takım 1": takimlar[1], "Takım 2": takimlar[5]},
            {"Gün": "4. Gün", "Eşleşme": "1 ve 3", "Takım 1": takimlar[0], "Takım 2": takimlar[2]},
            {"Gün": "4. Gün", "Eşleşme": "4 ve 2", "Takım 1": takimlar[3], "Takım 2": takimlar[1]},
            {"Gün": "4. Gün", "Eşleşme": "5 ve 6", "Takım 1": takimlar[4], "Takım 2": takimlar[5]},
            {"Gün": "5. Gün", "Eşleşme": "1 ve 2", "Takım 1": takimlar[0], "Takım 2": takimlar[1]},
            {"Gün": "5. Gün", "Eşleşme": "4 ve 5", "Takım 1": takimlar[3], "Takım 2": takimlar[4]},
            {"Gün": "5. Gün", "Eşleşme": "3 ve 6", "Takım 1": takimlar[2], "Takım 2": takimlar[5]},
        ]
    
    if format_secimi == "5 Maçlık (3 Tek, 2 Çift)":
        branslar = ["3. Tekler", "2. Tekler", "1. Tekler", "2. Çiftler", "1. Çiftler"]
    else:
        branslar = ["2. Tekler", "1. Tekler", "Çiftler"]

    program = []
    for m in base_matches:
        for brans in branslar:
            satir = m.copy()
            satir["id"] = str(uuid.uuid4())
            satir["Branş"] = brans
            satir["Grup"] = grup_adi
            satir.update({
                "T1_Oyuncu": "", "T2_Oyuncu": "",
                "1.Set T1": 0, "1.Set T2": 0, "2.Set T1": 0, "2.Set T2": 0, "3.Set T1": 0, "3.Set T2": 0, "Durum": "Tamamlandı", "STB": False
            })
            program.append(satir)
    return program

    
def hesapla_mac_kazanani(row):
    durum = str(row.get('Durum', 'Tamamlandı'))
    if durum == "Takım 1 (W/O)": durum = "Takım 2 Kazandı (W/O)"
    elif durum == "Takım 2 (W/O)": durum = "Takım 1 Kazandı (W/O)"
    elif durum == "Takım 1 (Ret.)": durum = "Takım 2 Kazandı (Ret.)"
    elif durum == "Takım 2 (Ret.)": durum = "Takım 1 Kazandı (Ret.)"

    if durum == "Çift Taraflı W/O": return (0, 0)
    if durum == "Takım 1 Kazandı (W/O)" or durum == "Takım 1 Kazandı (Ret.)": return (1, 0)
    if durum == "Takım 2 Kazandı (W/O)" or durum == "Takım 2 Kazandı (Ret.)": return (0, 1)
    
    s1_t1, s1_t2 = int(row['1.Set T1']), int(row['1.Set T2'])
    s2_t1, s2_t2 = int(row['2.Set T1']), int(row['2.Set T2'])
    s3_t1, s3_t2 = int(row['3.Set T1']), int(row['3.Set T2'])
    if s1_t1 == 0 and s1_t2 == 0 and s2_t1 == 0 and s2_t2 == 0: return 0, 0
    
    # YENİ: Otomatik STB Algılama (Kutu seçili VEYA 3. set skoru 10'dan büyükse)
    is_stb = bool(row.get('STB', False)) or (s3_t1 >= 10 or s3_t2 >= 10)
    
    t1_s1_win = s1_t1 >= 6 and (s1_t1 - s1_t2) >= 2 or s1_t1 == 7
    t2_s1_win = s1_t2 >= 6 and (s1_t2 - s1_t1) >= 2 or s1_t2 == 7
    t1_s2_win = s2_t1 >= 6 and (s2_t1 - s2_t2) >= 2 or s2_t1 == 7
    t2_s2_win = s2_t2 >= 6 and (s2_t2 - s2_t1) >= 2 or s2_t2 == 7
    t1_s3_win = (s3_t1 >= 10 and (s3_t1 - s3_t2) >= 2) if is_stb else (s3_t1 >= 6 and (s3_t1 - s3_t2) >= 2 or s3_t1 == 7)
    t2_s3_win = (s3_t2 >= 10 and (s3_t2 - s3_t1) >= 2) if is_stb else (s3_t2 >= 6 and (s3_t2 - s3_t1) >= 2 or s3_t2 == 7)

    t1_set = int(t1_s1_win) + int(t1_s2_win) + int(t1_s3_win)
    t2_set = int(t2_s1_win) + int(t2_s2_win) + int(t2_s3_win)
    return (1, 0) if t1_set > t2_set else ((0, 1) if t2_set > t1_set else (0, 0))

def get_formatted_match_score(row, target_t1):
    is_t1 = row['Takım 1'] == target_t1
    durum = str(row.get('Durum', 'Tamamlandı'))
    if durum == "Takım 1 (W/O)": durum = "Takım 2 Kazandı (W/O)"
    elif durum == "Takım 2 (W/O)": durum = "Takım 1 Kazandı (W/O)"
    elif durum == "Takım 1 (Ret.)": durum = "Takım 2 Kazandı (Ret.)"
    elif durum == "Takım 2 (Ret.)": durum = "Takım 1 Kazandı (Ret.)"

    brans = str(row['Branş']).replace("1. Tekler", "1.Tek").replace("2. Tekler", "2.Tek").replace("3. Tekler", "3.Tek").replace("1. Çiftler", "1.Çift").replace("2. Çiftler", "2.Çift").replace("Çiftler", "Çift")

    if durum == "Çift Taraflı W/O": 
        return f"<b>{brans}</b>: <span style='opacity: 0.8;'>Çift Taraflı W/O</span>"
    if durum == "Takım 1 Kazandı (W/O)": 
        score_str = "W/O (Galip)" if is_t1 else "W/O (Mağlup)"
        return f"<b>{brans}</b>: {score_str}"
    if durum == "Takım 2 Kazandı (W/O)": 
        score_str = "W/O (Mağlup)" if is_t1 else "W/O (Galip)"
        return f"<b>{brans}</b>: {score_str}"

    s1_1, s1_2 = int(row['1.Set T1']), int(row['1.Set T2'])
    s2_1, s2_2 = int(row['2.Set T1']), int(row['2.Set T2'])
    s3_1, s3_2 = int(row['3.Set T1']), int(row['3.Set T2'])

    if not is_t1:
        s1_1, s1_2 = s1_2, s1_1
        s2_1, s2_2 = s2_2, s2_1
        s3_1, s3_2 = s3_2, s3_1

    if s1_1 == 0 and s1_2 == 0 and s2_1 == 0 and s2_2 == 0 and "Ret." not in durum:
        return ""

    score_str = f"{s1_1}-{s1_2}"
    if s2_1 != 0 or s2_2 != 0 or s1_1 != 0 or s1_2 != 0: score_str += f" | {s2_1}-{s2_2}"
    if s3_1 != 0 or s3_2 != 0: score_str += f" | {s3_1}-{s3_2}"

    if durum == "Takım 1 Kazandı (Ret.)": 
        score_str += " Ret. (Galip)" if is_t1 else " Ret. (Mağlup)"
    elif durum == "Takım 2 Kazandı (Ret.)": 
        score_str += " Ret. (Mağlup)" if is_t1 else " Ret. (Galip)"

    return f"<b>{brans}</b>: <span style='opacity: 0.8;'>{score_str}</span>"

def render_html_matrix(takimlar, df_grup):
    html = '<table style="width:100%; border-collapse: collapse; text-align:center; font-family: sans-serif; font-size: 14px;">'
    html += '<tr style="background-color: rgba(128,128,128,0.1);">'
    html += '<th style="border: 1px solid rgba(128,128,128,0.3); padding: 10px;">Takımlar</th>'
    for t in takimlar:
        html += f'<th style="border: 1px solid rgba(128,128,128,0.3); padding: 10px;">{t}</th>'
    html += '</tr>'

    for t1 in takimlar:
        html += f'<tr><td style="border: 1px solid rgba(128,128,128,0.3); padding: 10px; font-weight: bold; background-color: rgba(128,128,128,0.1);">{t1}</td>'
        for t2 in takimlar:
            if t1 == t2:
                html += '<td style="border: 1px solid rgba(128,128,128,0.3); padding: 10px; background-color: rgba(128,128,128,0.2);"><b>X</b></td>'
            else:
                matches = df_grup[((df_grup['Takım 1'] == t1) & (df_grup['Takım 2'] == t2)) | ((df_grup['Takım 1'] == t2) & (df_grup['Takım 2'] == t1))]
                if matches.empty:
                    html += '<td style="border: 1px solid rgba(128,128,128,0.3); padding: 10px;"></td>'
                else:
                    temp_stats = hesapla_tum_puan_durumu(matches)
                    t1_wins = 0; t2_wins = 0
                    t1_puan_info = 0.0; t2_puan_info = 0.0
                    details = []
                    
                    for _, row in sort_maclar(matches).iterrows():
                        w1, w2 = hesapla_mac_kazanani(row)
                        brans = str(row.get('Branş', '')).lower()
                        is_cift = "çift" in brans
                        format_secimi = st.session_state.grup_formatlari.get(row['Grup'], "3 Maçlık (2 Tek, 1 Çift)")
                        w_val = 1.5 if (format_secimi == "5 Maçlık (3 Tek, 2 Çift)" and is_cift) else (2.0 if is_cift else 1.0)

                        if row['Takım 1'] == t1:
                            t1_wins += w1; t2_wins += w2
                            t1_puan_info += w1 * w_val; t2_puan_info += w2 * w_val
                        else:
                            t1_wins += w2; t2_wins += w1
                            t1_puan_info += w2 * w_val; t2_puan_info += w1 * w_val
                        
                        fmt = get_formatted_match_score(row, t1)
                        if fmt: details.append(fmt)

                    if t1_wins == 0 and t2_wins == 0 and not details:
                        html += '<td style="border: 1px solid rgba(128,128,128,0.3); padding: 10px;"></td>'
                    else:
                        t1_galibiyet = 0
                        t2_galibiyet = 0
                        if not temp_stats.empty:
                            r1 = temp_stats[temp_stats['Takım'] == t1]
                            r2 = temp_stats[temp_stats['Takım'] == t2]
                            if not r1.empty: t1_galibiyet = r1.iloc[0]['Galibiyet']
                            if not r2.empty: t2_galibiyet = r2.iloc[0]['Galibiyet']

                        crown1 = "👑 " if t1_galibiyet > t2_galibiyet else ""
                        crown2 = " 👑" if t2_galibiyet > t1_galibiyet else ""
                        
                        puan_str = f"Puan: {t1_puan_info:g} - {t2_puan_info:g}" if (t1_puan_info > 0 or t2_puan_info > 0) else ""
                        if t1_puan_info == t2_puan_info and (t1_galibiyet > 0 or t2_galibiyet > 0):
                            puan_str += " (Av.)"
                        
                        main_score = f"<div style='font-size: 18px; font-weight: bold; margin-bottom: 2px;'>{crown1}{t1_wins} - {t2_wins}{crown2}</div>"
                        puan_div = f"<div style='font-size: 11px; opacity: 0.9; font-weight: bold; margin-bottom: 5px;'>{puan_str}</div>" if puan_str else ""
                        details_html = "<br>".join(details)
                        
                        html += f'<td style="border: 1px solid rgba(128,128,128,0.3); padding: 10px; vertical-align: top;">{main_score}{puan_div}<div style="font-size: 11px; opacity: 0.8; line-height: 1.4;">{details_html}</div></td>'
        html += '</tr>'
    html += '</table>'
    return html

def generate_matrix_pdf(grup_adi, takimlar, df_grup):
    # Alt maç skorlarını düz yazı formatına (PDF'e uygun) çeviren yardımcı fonksiyon
    def get_plain_score(row, target_t1):
        is_t1 = row['Takım 1'] == target_t1
        durum = str(row.get('Durum', 'Tamamlandı'))
        if durum == "Takım 1 (W/O)": durum = "Takım 2 Kazandı (W/O)"
        elif durum == "Takım 2 (W/O)": durum = "Takım 1 Kazandı (W/O)"
        elif durum == "Takım 1 (Ret.)": durum = "Takım 2 Kazandı (Ret.)"
        elif durum == "Takım 2 (Ret.)": durum = "Takım 1 Kazandı (Ret.)"

        brans = str(row['Branş']).replace("1. Tekler", "1T").replace("2. Tekler", "2T").replace("3. Tekler", "3T").replace("1. Çiftler", "1Ç").replace("2. Çiftler", "2Ç").replace("Çiftler", "Ç")

        if durum == "Çift Taraflı W/O": 
            return f"{brans}: Çift W/O"
        if durum == "Takım 1 Kazandı (W/O)": 
            return f"{brans}: W/O(G)" if is_t1 else f"{brans}: W/O(M)"
        if durum == "Takım 2 Kazandı (W/O)": 
            return f"{brans}: W/O(M)" if is_t1 else f"{brans}: W/O(G)"

        s1_1, s1_2 = int(row['1.Set T1']), int(row['1.Set T2'])
        s2_1, s2_2 = int(row['2.Set T1']), int(row['2.Set T2'])
        s3_1, s3_2 = int(row['3.Set T1']), int(row['3.Set T2'])

        if not is_t1:
            s1_1, s1_2 = s1_2, s1_1
            s2_1, s2_2 = s2_2, s2_1
            s3_1, s3_2 = s3_2, s3_1

        if s1_1 == 0 and s1_2 == 0 and s2_1 == 0 and s2_2 == 0 and "Ret." not in durum:
            return ""

        score_str = f"{s1_1}-{s1_2}"
        if s2_1 != 0 or s2_2 != 0 or s1_1 != 0 or s1_2 != 0: score_str += f" | {s2_1}-{s2_2}"
        if s3_1 != 0 or s3_2 != 0: score_str += f" | {s3_1}-{s3_2}"

        if durum == "Takım 1 Kazandı (Ret.)": 
            score_str += " Ret.(G)" if is_t1 else " Ret.(M)"
        elif durum == "Takım 2 Kazandı (Ret.)": 
            score_str += " Ret.(M)" if is_t1 else " Ret.(G)"

        return f"{brans}: {score_str}"

    matrix = pd.DataFrame(index=takimlar, columns=takimlar)
    matrix = matrix.fillna("")
    for t in takimlar: matrix.at[t, t] = "X"
    
    for (t1, t2), group in df_grup.groupby(['Takım 1', 'Takım 2']):
        t1_total, t2_total = 0, 0
        t1_details = []
        t2_details = []
        for _, row in sort_maclar(group).iterrows():
            w1, w2 = hesapla_mac_kazanani(row)
            t1_total += w1; t2_total += w2
            
            det1 = get_plain_score(row, t1)
            if det1: t1_details.append(det1)
            det2 = get_plain_score(row, t2)
            if det2: t2_details.append(det2)

        if t1_total > 0 or t2_total > 0:
            # --- GERÇEK KAZANANI BULMA (Tie-break / Averaj Kontrolü) ---
            temp_stats = hesapla_tum_puan_durumu(group)
            t1_galibiyet = 0
            t2_galibiyet = 0
            if not temp_stats.empty:
                r1 = temp_stats[temp_stats['Takım'] == t1]
                r2 = temp_stats[temp_stats['Takım'] == t2]
                if not r1.empty: t1_galibiyet = r1.iloc[0]['Galibiyet']
                if not r2.empty: t2_galibiyet = r2.iloc[0]['Galibiyet']

            yildiz_t1 = "*" if t1_galibiyet > t2_galibiyet else ""
            yildiz_t2 = "*" if t2_galibiyet > t1_galibiyet else ""
            
            matrix.at[t1, t2] = f"{t1_total}{yildiz_t1} - {t2_total}{yildiz_t2}\n" + "\n".join(t1_details)
            matrix.at[t2, t1] = f"{t2_total}{yildiz_t2} - {t1_total}{yildiz_t1}\n" + "\n".join(t2_details)
            
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    setup_pdf_fonts(pdf)
    
    apply_font(pdf, bold=True, size=14)
    pdf.cell(0, 8, to_pdf_text(f"{grup_adi} - Takım Maçları Matrisi"), ln=True, align='C')
    
    # --- BİLGİ NOTU EKLENDİ ---
    apply_font(pdf, bold=False, size=8)
    pdf.cell(0, 4, to_pdf_text("Not: Skorun yanındaki (*) yıldız işareti, kazanan takımı gösterir."), ln=True, align='C')
    pdf.ln(5)
    
    cols = ["Takımlar"] + takimlar
    col_width = 190 / len(cols) 
    
    for col in cols:
        pdf_cell_fit(pdf, col_width, 10, col, is_bold=True, base_size=11)
    pdf.ln()
    
    for t1 in takimlar:
        max_lines = 1
        for t2 in takimlar:
            val = str(matrix.at[t1, t2])
            if val:
                lines = len(val.split('\n'))
                if lines > max_lines: max_lines = lines
        
        row_height = max_lines * 4.5 + 5
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        if y_start + row_height > 280:
            pdf.add_page()
            x_start = pdf.get_x()
            y_start = pdf.get_y()
        
        pdf.rect(x_start, y_start, col_width, row_height)
        pdf.set_xy(x_start, y_start + (row_height/2) - 2)
        apply_font(pdf, bold=True, size=10)
        pdf_cell_fit(pdf, col_width, 4, to_pdf_text(t1), border=0, is_bold=True)
        
        for t2 in takimlar:
            x_start += col_width
            val = str(matrix.at[t1, t2])
            
            pdf.rect(x_start, y_start, col_width, row_height)
            pdf.set_xy(x_start, y_start + 2.5)
            
            if val == "X":
                pdf.set_xy(x_start, y_start + (row_height/2) - 2)
                apply_font(pdf, bold=True, size=11)
                pdf.cell(col_width, 4, "X", align='C')
            elif val != "":
                lines = val.split('\n')
                apply_font(pdf, bold=True, size=10.5)
                pdf.cell(col_width, 4.5, to_pdf_text(lines[0]), align='C', ln=2)
                apply_font(pdf, bold=False, size=7.5)
                for line in lines[1:]:
                    pdf.cell(col_width, 4, to_pdf_text(line), align='C', ln=2)
        
        pdf.set_xy(10, y_start + row_height)
        
    return get_pdf_bytes(pdf)

def hesapla_tum_puan_durumu(df_girdi):
    if df_girdi.empty: return pd.DataFrame()
    df = df_girdi.copy()
    
    def satir_hesapla(row):
        durum = str(row.get('Durum', 'Tamamlandı'))
        if durum == "Takım 1 (W/O)": durum = "Takım 2 Kazandı (W/O)"
        elif durum == "Takım 2 (W/O)": durum = "Takım 1 Kazandı (W/O)"
        elif durum == "Takım 1 (Ret.)": durum = "Takım 2 Kazandı (Ret.)"
        elif durum == "Takım 2 (Ret.)": durum = "Takım 1 Kazandı (Ret.)"

        s1_t1, s1_t2 = int(row['1.Set T1']), int(row['1.Set T2'])
        s2_t1, s2_t2 = int(row['2.Set T1']), int(row['2.Set T2'])
        s3_t1, s3_t2 = int(row['3.Set T1']), int(row['3.Set T2'])
        
        # YENİ: Otomatik STB Algılama (Averaj hesabı için)
        is_stb = bool(row.get('STB', False)) or (s3_t1 >= 10 or s3_t2 >= 10)

        if durum == "Çift Taraflı W/O": return pd.Series([0, 0, 0, 0])
        if durum == "Takım 1 Kazandı (W/O)": return pd.Series([12, 0, 2, 0])
        if durum == "Takım 2 Kazandı (W/O)": return pd.Series([0, 12, 0, 2])

        if s1_t1 == 0 and s1_t2 == 0 and s2_t1 == 0 and s2_t2 == 0 and s3_t1 == 0 and s3_t2 == 0 and durum == "Tamamlandı":
            return pd.Series([0, 0, 0, 0])

        t1_s1_win = s1_t1 >= 6 and (s1_t1 - s1_t2) >= 2 or s1_t1 == 7
        t2_s1_win = s1_t2 >= 6 and (s1_t2 - s1_t1) >= 2 or s1_t2 == 7
        
        t1_s2_win = s2_t1 >= 6 and (s2_t1 - s2_t2) >= 2 or s2_t1 == 7
        t2_s2_win = s2_t2 >= 6 and (s2_t2 - s2_t1) >= 2 or s2_t2 == 7
        
        t1_s3_win = (s3_t1 >= 10 and (s3_t1 - s3_t2) >= 2) if is_stb else (s3_t1 >= 6 and (s3_t1 - s3_t2) >= 2 or s3_t1 == 7)
        t2_s3_win = (s3_t2 >= 10 and (s3_t2 - s3_t1) >= 2) if is_stb else (s3_t2 >= 6 and (s3_t2 - s3_t1) >= 2 or s3_t2 == 7)

        t1_oyun = s1_t1 + s2_t1
        t2_oyun = s1_t2 + s2_t2
        
        if s3_t1 > 0 or s3_t2 > 0:
            if is_stb:
                if s3_t1 > s3_t2: t1_oyun += 1
                elif s3_t2 > s3_t1: t2_oyun += 1
            else:
                t1_oyun += s3_t1
                t2_oyun += s3_t2

        t1_set, t2_set = 0, 0

        if durum == "Takım 1 Kazandı (Ret.)":
            if t1_s1_win: t1_set = 1
            elif t2_s1_win: t2_set = 1
            else:
                t1_set += 1; t1_oyun += max(0, (6 if s1_t2 <= 4 else 7) - s1_t1)
                t1_set += 1; t1_oyun += 6
                return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])
                
            if t1_s2_win: t1_set += 1
            elif t2_s2_win: t2_set += 1
            else:
                t1_set += 1; t1_oyun += max(0, (6 if s2_t2 <= 4 else 7) - s2_t1)
                if t1_set == 1 and t2_set == 1:
                    t1_set += 1; t1_oyun += 1 if is_stb else 6
                return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])
                
            if t1_set == 1 and t2_set == 1:
                if is_stb:
                    if t1_s3_win: t1_set += 1
                    elif t2_s3_win: t2_set += 1
                    else:
                        t1_set += 1; t1_oyun += 1
                        if s3_t2 > s3_t1: t2_oyun = max(0, t2_oyun - 1)
                else:
                    if t1_s3_win: t1_set += 1
                    elif t2_s3_win: t2_set += 1
                    else:
                        t1_set += 1; t1_oyun += max(0, (6 if s3_t2 <= 4 else 7) - s3_t1)
            return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])
            
        elif durum == "Takım 2 Kazandı (Ret.)":
            if t1_s1_win: t1_set = 1
            elif t2_s1_win: t2_set = 1
            else:
                t2_set += 1; t2_oyun += max(0, (6 if s1_t1 <= 4 else 7) - s1_t2)
                t2_set += 1; t2_oyun += 6
                return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])
                
            if t1_s2_win: t1_set += 1
            elif t2_s2_win: t2_set += 1
            else:
                t2_set += 1; t2_oyun += max(0, (6 if s2_t1 <= 4 else 7) - s2_t2)
                if t1_set == 1 and t2_set == 1:
                    t2_set += 1; t2_oyun += 1 if is_stb else 6
                return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])
                
            if t1_set == 1 and t2_set == 1:
                    if is_stb:
                        if t1_s3_win: t1_set += 1
                        elif t2_s3_win: t2_set += 1
                        else:
                            t2_set += 1
                            # Eğer zaten öndeyse puanı aldı, tekrar verme!
                            if not (s3_t2 > s3_t1): t2_oyun += 1
                            # Rakip haksız yere puan aldıysa geri al!
                            if s3_t1 > s3_t2: t1_oyun = max(0, t1_oyun - 1)
                    else:
                        if t1_s3_win: t1_set += 1
                        elif t2_s3_win: t2_set += 1
                        else:
                            t2_set += 1; t2_oyun += max(0, (6 if s3_t1 <= 4 else 7) - s3_t2)
            return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])

        else: 
            t1_set = int(t1_s1_win) + int(t1_s2_win) + int(t1_s3_win)
            t2_set = int(t2_s1_win) + int(t2_s2_win) + int(t2_s3_win)
            return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])

    df[['T1_Oyun', 'T2_Oyun', 'T1_Set_Skor', 'T2_Set_Skor']] = df.apply(satir_hesapla, axis=1)
    df['T1_Match_Win'] = (df['T1_Set_Skor'] > df['T2_Set_Skor']).astype(int)
    df['T2_Match_Win'] = (df['T2_Set_Skor'] > df['T1_Set_Skor']).astype(int)
    
    def get_match_point(row, team_idx):
        grup = row.get('Grup', '')
        brans = str(row.get('Branş', '')).lower()
        is_cift = "çift" in brans
        format_secimi = st.session_state.grup_formatlari.get(grup, "3 Maçlık (2 Tek, 1 Çift)")
        
        if format_secimi == "5 Maçlık (3 Tek, 2 Çift)":
            weight = 1.5 if is_cift else 1.0
        else:
            weight = 2.0 if is_cift else 1.0
            
        if team_idx == 1: return weight if row['T1_Match_Win'] > row['T2_Match_Win'] else 0.0
        else: return weight if row['T2_Match_Win'] > row['T1_Match_Win'] else 0.0

    df['T1_Match_Point'] = df.apply(lambda r: get_match_point(r, 1), axis=1)
    df['T2_Match_Point'] = df.apply(lambda r: get_match_point(r, 2), axis=1)

    seriler = df.groupby(['Grup', 'Gün', 'Eşleşme', 'Takım 1', 'Takım 2']).agg({
        'T1_Match_Win': 'sum', 'T2_Match_Win': 'sum', 
        'T1_Set_Skor': 'sum', 'T2_Set_Skor': 'sum', 
        'T1_Oyun': 'sum', 'T2_Oyun': 'sum',
        'T1_Match_Point': 'sum', 'T2_Match_Point': 'sum'
    }).reset_index()
    
    def determine_team_win(r):
        if r['T1_Match_Win'] == 0 and r['T2_Match_Win'] == 0: return 0, 0
        if r['T1_Match_Point'] > r['T2_Match_Point']: return 1, 0
        elif r['T2_Match_Point'] > r['T1_Match_Point']: return 0, 1
        else:
            if r['T1_Match_Point'] == 0 and r['T2_Match_Point'] == 0: return 0, 0
            
            set_av_t1 = r['T1_Set_Skor'] - r['T2_Set_Skor']
            set_av_t2 = r['T2_Set_Skor'] - r['T1_Set_Skor']
            if set_av_t1 > set_av_t2: return 1, 0
            elif set_av_t2 > set_av_t1: return 0, 1
            else:
                oyun_av_t1 = r['T1_Oyun'] - r['T2_Oyun']
                oyun_av_t2 = r['T2_Oyun'] - r['T1_Oyun']
                if oyun_av_t1 > oyun_av_t2: return 1, 0
                elif oyun_av_t2 > oyun_av_t1: return 0, 1
                else: return 0, 0 
                
    win_res = seriler.apply(lambda r: determine_team_win(r), axis=1)
    seriler['T1_Win'] = [x[0] for x in win_res]
    seriler['T2_Win'] = [x[1] for x in win_res]
    
    seriler['Oynanan'] = seriler.apply(lambda r: 1 if r['T1_Win'] + r['T2_Win'] > 0 or r['T1_Oyun'] + r['T2_Oyun'] > 0 else 0, axis=1)
    
    t1 = seriler[['Grup', 'Takım 1', 'Oynanan', 'T1_Win', 'T1_Match_Win', 'T2_Match_Win', 'T1_Set_Skor', 'T2_Set_Skor', 'T1_Oyun', 'T2_Oyun']].rename(columns={'Takım 1': 'Takım'})
    t2 = seriler[['Grup', 'Takım 2', 'Oynanan', 'T2_Win', 'T2_Match_Win', 'T1_Match_Win', 'T2_Set_Skor', 'T1_Set_Skor', 'T2_Oyun', 'T1_Oyun']].rename(columns={'Takım 2': 'Takım'})
    
    t1.columns = ['Grup', 'Takım', 'Oynanan Maç', 'Galibiyet', 'Aldığı Maç', 'Verdiği Maç', 'Aldığı Set', 'Verdiği Set', 'Aldığı Oyun', 'Verdiği Oyun']
    t2.columns = ['Grup', 'Takım', 'Oynanan Maç', 'Galibiyet', 'Aldığı Maç', 'Verdiği Maç', 'Aldığı Set', 'Verdiği Set', 'Aldığı Oyun', 'Verdiği Oyun']
    
    tum_stats = pd.concat([t1, t2]).groupby(['Grup', 'Takım']).sum().reset_index()
    tum_stats['Maç Av.'] = tum_stats['Aldığı Maç'] - tum_stats['Verdiği Maç']
    tum_stats['Set Av.'] = tum_stats['Aldığı Set'] - tum_stats['Verdiği Set']
    tum_stats['Oyun Av.'] = tum_stats['Aldığı Oyun'] - tum_stats['Verdiği Oyun']
    return tum_stats

def sirala_grup_df(grup_df, gp):
    if gp in st.session_state.grup_siralamalari and st.session_state.grup_siralamalari[gp]:
        manuel_sira = st.session_state.grup_siralamalari[gp]
        grup_df['Sıra_Degeri'] = grup_df['Takım'].apply(lambda x: manuel_sira.index(x) if x in manuel_sira else 999)
        grup_df = grup_df.sort_values(by=['Sıra_Degeri', 'Galibiyet', 'Maç Av.', 'Set Av.', 'Oyun Av.'], ascending=[True, False, False, False, False]).drop(columns=['Sıra_Degeri'])
    else:
        grup_df = grup_df.sort_values(by=['Galibiyet', 'Maç Av.', 'Set Av.', 'Oyun Av.'], ascending=False)
    
    grup_df.index = range(1, len(grup_df) + 1)
    return grup_df

def safe_val(val, default=""):
    if pd.isna(val) or val is None: return default
    return val

def safe_int(val, default=0):
    if pd.isna(val) or val is None or val == "": return default
    try: return int(val)
    except: return default

def ortak_veriyi_kaydet():
    mac_kayitlari = []
    if not st.session_state.skor_tablosu.empty:
        if 'id' not in st.session_state.skor_tablosu.columns:
            st.session_state.skor_tablosu['id'] = [str(uuid.uuid4()) for _ in range(len(st.session_state.skor_tablosu))]
            
        for idx, row in st.session_state.skor_tablosu.iterrows():
            mac_id = row.get("id")
            if pd.isna(mac_id) or not mac_id:
                mac_id = str(uuid.uuid4())
                st.session_state.skor_tablosu.at[idx, 'id'] = mac_id
                
            mac_kayitlari.append({
                "id": str(mac_id),
                "grup_adi": str(safe_val(row.get("Grup"), "")),
                "musabaka_gunu": str(safe_val(row.get("Gün"), "")),
                "eslesme": str(safe_val(row.get("Eşleşme"), "")),
                "brans": str(safe_val(row.get("Branş"), "")),
                "takim_a": str(safe_val(row.get("Takım 1"), "")),
                "takim_b": str(safe_val(row.get("Takım 2"), "")),
                "oyuncu_a": str(safe_val(row.get("T1_Oyuncu"), "")),
                "oyuncu_b": str(safe_val(row.get("T2_Oyuncu"), "")),
                "set1_a": safe_int(row.get("1.Set T1"), 0),
                "set1_b": safe_int(row.get("1.Set T2"), 0),
                "set2_a": safe_int(row.get("2.Set T1"), 0),
                "set2_b": safe_int(row.get("2.Set T2"), 0),
                "set3_a": safe_int(row.get("3.Set T1"), 0),
                "set3_b": safe_int(row.get("3.Set T2"), 0),
                "durum": str(safe_val(row.get("Durum"), "Tamamlandı")),
                "stb": bool(safe_val(row.get("STB"), False))
            })

    mp_records = []
    if not st.session_state.get("mac_programi", pd.DataFrame()).empty:
        mp_df = st.session_state.mac_programi.copy()
        mp_df = mp_df.where(pd.notnull(mp_df), "")
        mp_records = mp_df.to_dict(orient="records")

    ayarlar = {
        "takim_kadrolari": st.session_state.get("takim_kadrolari", {}),
        "grup_formatlari": st.session_state.get("grup_formatlari", {}),
        "grup_kategorileri": st.session_state.get("grup_kategorileri", {}),
        "grup_asamalari": st.session_state.get("grup_asamalari", {}),
        "duyuru_metni": str(safe_val(st.session_state.get("duyuru_metni", ""), "")),
        "gunluk_notlar": st.session_state.get("gunluk_notlar", {}),
        "takim_havuzu": st.session_state.get("takim_havuzu", {}),
        "havuz_kategorileri": st.session_state.get("havuz_kategorileri", {}),
        "havuz_yas_gruplari": st.session_state.get("havuz_yas_gruplari", {}),
        "grup_siralamalari": st.session_state.get("grup_siralamalari", {}),
        "grup_tamamlandi": st.session_state.get("grup_tamamlandi", {}),
        "grup_yas_gruplari": st.session_state.get("grup_yas_gruplari", {}),
        "grup_statuleri": st.session_state.get("grup_statuleri", {}), # YENİ EKLENEN: GRUP STATÜSÜ
        "takim_pinleri": st.session_state.get("takim_pinleri", {}),
        "esame_kasasi": st.session_state.get("esame_kasasi", {}),
        "esame_onayli": st.session_state.get("esame_onayli", {}),
        "mac_programi": mp_records,
        "hakem_listesi": st.session_state.get("hakem_listesi", []),
        "hakem_pinleri": st.session_state.get("hakem_pinleri", {})
    }
    
    ayarlar["sistem_kilitli"] = st.session_state.get("sistem_kilitli", False)

    cevrimdisi = st.session_state.get("cevrimdisi_mod", False)
    
    if cevrimdisi:
        cevrimdisi_veri = {"maclar": mac_kayitlari, "ayarlar": ayarlar}
        try:
            yerel_dosya = os.path.join(SISTEM_KLASORU, "cevrimdisi_veritabani.json")
            with open(yerel_dosya, "w", encoding="utf-8") as f:
                json.dump(cevrimdisi_veri, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    else:
        if not supabase: return False
        try:
            if mac_kayitlari:
                supabase.table("maclar").upsert(mac_kayitlari).execute()
            supabase.table("turnuva_ayarlari").update(ayarlar).eq("id", 1).execute()
            return True
        except Exception as e:
            st.error(f"Supabase Kayıt Hatası: {e}")
            return False

def ortak_veriyi_yukle():
    data = None
    maclar_data = None
    cevrimdisi = st.session_state.get("cevrimdisi_mod", False)

    if cevrimdisi:
        yerel_dosya = os.path.join(SISTEM_KLASORU, "cevrimdisi_veritabani.json")
        if os.path.exists(yerel_dosya):
            try:
                with open(yerel_dosya, "r", encoding="utf-8") as f:
                    cevrimdisi_veri = json.load(f)
                data = cevrimdisi_veri.get("ayarlar", {})
                maclar_data = cevrimdisi_veri.get("maclar", [])
            except:
                pass
    else:
        if supabase:
            try:
                res = supabase.table("turnuva_ayarlari").select("*").eq("id", 1).execute()
                if res.data: data = res.data[0]
                maclar_res = supabase.table("maclar").select("*").execute()
                if maclar_res.data: maclar_data = maclar_res.data
            except:
                pass 

    if data:
        st.session_state.sistem_kilitli = data.get("sistem_kilitli", False)
        st.session_state.cevrimdisi_mod = st.session_state.sistem_kilitli 
        
        if data.get("mac_programi"):
            mp_df = pd.DataFrame(data["mac_programi"])
            if "T1 Oyuncu" not in mp_df.columns: mp_df["T1 Oyuncu"] = ""; mp_df["T2 Oyuncu"] = ""
            if "Kazanan" not in mp_df.columns: mp_df["Kazanan"] = ""
            if "Hakem" not in mp_df.columns: mp_df["Hakem"] = ""
            st.session_state.mac_programi = mp_df
        else:
            st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Skor", "Kazanan", "Hakem"])

        st.session_state.takim_kadrolari = data.get("takim_kadrolari", {})
        st.session_state.grup_formatlari = data.get("grup_formatlari", {})
        st.session_state.grup_kategorileri = data.get("grup_kategorileri", {})
        st.session_state.grup_asamalari = data.get("grup_asamalari", {})
        st.session_state.duyuru_metni = data.get("duyuru_metni", "")
        st.session_state.gunluk_notlar = data.get("gunluk_notlar", {})
        st.session_state.takim_havuzu = data.get("takim_havuzu", {})
        st.session_state.havuz_kategorileri = data.get("havuz_kategorileri", {})
        st.session_state.havuz_yas_gruplari = data.get("havuz_yas_gruplari", {})
        st.session_state.grup_siralamalari = data.get("grup_siralamalari", {})
        st.session_state.grup_tamamlandi = data.get("grup_tamamlandi", {})
        st.session_state.grup_yas_gruplari = data.get("grup_yas_gruplari", {})
        st.session_state.grup_statuleri = data.get("grup_statuleri", {}) # YENİ EKLENEN: GRUP STATÜSÜ
        st.session_state.takim_pinleri = data.get("takim_pinleri", {})
        st.session_state.esame_kasasi = data.get("esame_kasasi", {})
        st.session_state.esame_onayli = data.get("esame_onayli", {})
        st.session_state.hakem_listesi = data.get("hakem_listesi", [])
        st.session_state.hakem_pinleri = data.get("hakem_pinleri", {})
    
    if maclar_data is not None:
        mac_listesi = []
        for m in maclar_data:
            mac_listesi.append({
                "id": m.get("id"), "Grup": m.get("grup_adi"), "Gün": m.get("musabaka_gunu"),
                "Eşleşme": m.get("eslesme"), "Branş": m.get("brans"),
                "Takım 1": m.get("takim_a"), "Takım 2": m.get("takim_b"),
                "T1_Oyuncu": m.get("oyuncu_a"), "T2_Oyuncu": m.get("oyuncu_b"),
                "1.Set T1": m.get("set1_a"), "1.Set T2": m.get("set1_b"),
                "2.Set T1": m.get("set2_a"), "2.Set T2": m.get("set2_b"),
                "3.Set T1": m.get("set3_a"), "3.Set T2": m.get("set3_b"),
                "Durum": m.get("durum"), "STB": m.get("stb")
            })
        st.session_state.skor_tablosu = pd.DataFrame(mac_listesi)

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# ==============================================================================
# HAFIZA (SESSION STATE) BAŞLATMA
# ==============================================================================
if "sistem_kilitli" not in st.session_state: st.session_state.sistem_kilitli = False
if "cevrimdisi_mod" not in st.session_state: st.session_state.cevrimdisi_mod = False
if "takim_kadrolari" not in st.session_state: st.session_state.takim_kadrolari = {}
if "admin_mi" not in st.session_state: st.session_state.admin_mi = False
if "kaptan_mi" not in st.session_state: st.session_state.kaptan_mi = False
if "hakem_mi" not in st.session_state: st.session_state.hakem_mi = False
if "kaptan_takim" not in st.session_state: st.session_state.kaptan_takim = ""
if "aktif_hakem" not in st.session_state: st.session_state.aktif_hakem = ""
if "expand_all" not in st.session_state: st.session_state.expand_all = False
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
if "grup_statuleri" not in st.session_state: st.session_state.grup_statuleri = {} # YENİ EKLENEN: GRUP STATÜSÜ
if "takim_pinleri" not in st.session_state: st.session_state.takim_pinleri = {}
if "esame_kasasi" not in st.session_state: st.session_state.esame_kasasi = {}
if "esame_onayli" not in st.session_state: st.session_state.esame_onayli = {}
if "hakem_listesi" not in st.session_state: st.session_state.hakem_listesi = []
if "hakem_pinleri" not in st.session_state: st.session_state.hakem_pinleri = {}
if "current_page" not in st.session_state: st.session_state.current_page = "Home"
if "aktif_asama" not in st.session_state: st.session_state.aktif_asama = "1. Aşama"

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
# YAN MENÜ (SIDEBAR) - HER YERDEN ERİŞİLEBİLİR
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
        menu_items_side = ["🏠 Ana Sayfa", "👥 Grup Ayarları", "📝 Esame Kontrol Merkezi", "✍️ Skor Girişi", "🏆 Puan Durumu", "📅 Maç Programı", "📢 Duyurular", "👮‍♂️ Hakem Yönetimi", "⚙️ Yönetim & Dosya", "📈 İstatistikler"]
    elif st.session_state.hakem_mi:
        menu_items_side = ["🏠 Ana Sayfa", "✍️ Gözlemci Hakem Paneli", "📅 Maç Programı"]
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
            if ucak_modu: 
                if supabase: 
                    try:
                        supabase.table("turnuva_ayarlari").upsert({"id": 1, "sistem_kilitli": True}).execute()
                    except:
                        pass
                ortak_veriyi_kaydet()
                st.rerun()
            else: 
                if supabase:
                    try:
                        supabase.table("turnuva_ayarlari").upsert({"id": 1, "sistem_kilitli": False}).execute()
                    except:
                        pass
                ortak_veriyi_kaydet()
                
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
# EN ÜST BÖLÜM (LOGOLAR VE AŞAMA SEÇİMİ)
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
# ANA SAYFA GÖRÜNÜMÜ (DEV BUTONLAR, NAVBAR YOK)
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
        with c6: render_big_button("📢", "Duyurular", "📢 Duyurular")
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
        c1, c2 = st.columns(2)
        with c1: render_big_button("✍️", "Görevli Olduğum Maçlar", "✍️ Gözlemci Hakem Paneli")
        with c2: render_big_button("📅", "Tüm Maç Programı", "📅 Maç Programı")

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
                if girilen_sifre == "zonguldak2026":
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
            if 'Takım 1' in df_fikstur.columns:
                tum_takimlar.update(df_fikstur['Takım 1'].unique())
            if 'Takım 2' in df_fikstur.columns:
                tum_takimlar.update(df_fikstur['Takım 2'].unique())
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
# ALT SAYFALARIN İÇERİKLERİ (YATAY MENÜ SADECE BURADA ÇIKAR)
# ==============================================================================
else:
    aktif_asama = st.session_state.aktif_asama
    menu_secim = st.session_state.current_page
    
    # --- İÇ SAYFA YATAY NAVBAR ---
    if st.session_state.admin_mi:
        menu_items_top = ["🏠 Ana Sayfa", "👥 Grup Ayarları", "📝 Esame Kontrol Merkezi", "✍️ Skor Girişi", "🏆 Puan Durumu", "📅 Maç Programı", "📢 Duyurular", "👮‍♂️ Hakem Yönetimi", "⚙️ Yönetim"]
    elif st.session_state.kaptan_mi:
        menu_items_top = ["🏠 Ana Sayfa", "👨‍✈️ Kaptan Esame Girişi", "🛡️ Takım Kadroları", "🏆 Puan Durumu", "📅 Maç Programı", "📢 Duyurular"]
    elif st.session_state.hakem_mi:
        menu_items_top = ["🏠 Ana Sayfa", "✍️ Gözlemci Hakem Paneli", "📅 Maç Programı"]
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

    # --- KAPTAN SAYFASI: ESAME BİLDİRİMİ ---
    if menu_secim == "👨‍✈️ Kaptan Esame Girişi":
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

    # --- HAKEM GİRİŞ SAYFASI (Eksik Olan ve Geri Getirilen Kısım) ---
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

   # --- HAKEM SAYFASI: SKOR GİRİŞ PANELİ ---
    elif menu_secim == "✍️ Gözlemci Hakem Paneli":
        if st.session_state.get("sistem_kilitli", False) and not st.session_state.admin_mi:
            st.error("🚨 SİSTEM BAKIMDA: Başhakem şu an çevrimdışı (Uçak) modunda maç programı düzenliyor. Lütfen skor değişikliklerini kağıt üzerinde Başhakem masasına iletiniz.")
        elif not st.session_state.hakem_mi:
            st.warning("Bu paneli görüntülemek için lütfen hakem olarak giriş yapın.")
        else:
            aktif_hakem = st.session_state.aktif_hakem
            st.info(f"Hoş geldin, **{aktif_hakem}**. Aşağıda turnuva boyunca üzerinize atanan maçlar listelenmiştir.")
            
            df_hakem_maclari = st.session_state.mac_programi[st.session_state.mac_programi['Hakem'] == aktif_hakem]
            
            if df_hakem_maclari.empty:
                st.success("Şu ana kadar üzerinize atanmış herhangi bir görev bulunmamaktadır.")
            else:
                bugun = datetime.date.today()
                
                tarihler = df_hakem_maclari['Tarih'].dropna().unique()
                tarihler_sirali = sorted(tarihler, key=lambda x: datetime.datetime.strptime(x, "%d.%m.%Y").date())
                
                # --- YENİ EKLENEN VİTRİN DÜZENİ ---
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
                    
                    # Maçın kilitli (geçmiş/gelecek) olup olmamasına göre hangi kutuya atılacağını belirliyoruz
                    hedef_alan = container_diger if is_kilitli else container_bugun
                    
                    with hedef_alan:
                        if not is_kilitli:
                            bugun_mac_var_mi = True
                            
                        st.markdown(f"#### 🗓️ Tarih: {tarih_str}")
                        
                        if is_gecmis:
                            st.error("🔒 **GEÇMİŞ TARİH:** Bu maçlar geçmişte kalmıştır. Skorları sadece görüntüleyebilirsiniz. Hatalı bir skor varsa lütfen Başhakem'e kağıtla bildiriniz.")
                        elif is_gelecek:
                            st.warning("⏳ **GELECEK TARİH:** Bu maçların tarihi henüz gelmemiştir. Skor girişi maç günü açılacaktır.")
                        else:
                            st.success("✍️ **SKOR GİRİŞİ AÇIK:** Aşağıdaki maçların skorlarını girebilir ve güncelleyebilirsiniz.")
                            
                        df_gun = df_hakem_maclari[df_hakem_maclari['Tarih'] == tarih_str]
                        
                        for (grup_adi, eslesme_adi), g_df in df_gun.groupby(['Grup', 'Eşleşme']):
                            t1 = g_df.iloc[0]['Takım 1']
                            t2 = g_df.iloc[0]['Takım 2']
                            kort = g_df.iloc[0]['Kort']
                            saat = g_df.iloc[0]['Maç Saati']
                            
                            baslik_durumu = "🔒 (Kilitli)" if is_kilitli else "✍️ (Skor Girilebilir)"
                            expander_baslik = f"🎾 {saat} - {kort} | {grup_adi} | {t1} vs {t2} {baslik_durumu}"
                            
                            with st.expander(expander_baslik, expanded=not is_kilitli):
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

                                        st.markdown(f"**{row['Branş']}** &nbsp;&nbsp;|&nbsp;&nbsp; {row.get('T1_Oyuncu', '-')} vs {row.get('T2_Oyuncu', '-')}")

                                        r_cols = st.columns([2.5, 1, 1.5, 1.5, 0.2, 1.5, 1.5, 0.2, 1.5, 1.5])
                                        
                                        durum_opts = ["Tamamlandı", "Takım 1 Kazandı (W/O)", "Takım 2 Kazandı (W/O)", "Takım 1 Kazandı (Ret.)", "Takım 2 Kazandı (Ret.)", "Çift Taraflı W/O"]
                                        mevcut_durum = str(row.get('Durum', 'Tamamlandı'))
                                        if mevcut_durum == "Takım 1 (W/O)": mevcut_durum = "Takım 2 Kazandı (W/O)"
                                        elif mevcut_durum == "Takım 2 (W/O)": mevcut_durum = "Takım 1 Kazandı (W/O)"
                                        elif mevcut_durum == "Takım 1 (Ret.)": mevcut_durum = "Takım 2 Kazandı (Ret.)"
                                        elif mevcut_durum == "Takım 2 (Ret.)": mevcut_durum = "Takım 1 Kazandı (Ret.)"
                                        
                                        d_idx = durum_opts.index(mevcut_durum) if mevcut_durum in durum_opts else 0
                                        
                                        with r_cols[0]: secilen_durum = st.selectbox("Durum", options=durum_opts, index=d_idx, key=f"h_durum_{idx}_{idx_mp}", label_visibility="collapsed", disabled=is_kilitli)
                                        with r_cols[1]: secilen_stb = st.checkbox("STB", value=bool(row.get('STB', False)), key=f"h_stb_{idx}_{idx_mp}", disabled=is_kilitli)
                                        
                                        is_wo = "W/O" in secilen_durum
                                        kutu_kilitli = is_wo or is_kilitli 
                                        
                                        s1t1 = r_cols[2].number_input("S1T1", min_value=0, value=0 if is_wo else int(row['1.Set T1']), step=1, key=f"h_s1t1_{idx}_{idx_mp}", label_visibility="collapsed", disabled=kutu_kilitli)
                                        s1t2 = r_cols[3].number_input("S1T2", min_value=0, value=0 if is_wo else int(row['1.Set T2']), step=1, key=f"h_s1t2_{idx}_{idx_mp}", label_visibility="collapsed", disabled=kutu_kilitli)
                                        r_cols[4].markdown("<div style='text-align:center; opacity:0.5; margin-top:5px; font-weight:bold;'>|</div>", unsafe_allow_html=True)
                                        s2t1 = r_cols[5].number_input("S2T1", min_value=0, value=0 if is_wo else int(row['2.Set T1']), step=1, key=f"h_s2t1_{idx}_{idx_mp}", label_visibility="collapsed", disabled=kutu_kilitli)
                                        s2t2 = r_cols[6].number_input("S2T2", min_value=0, value=0 if is_wo else int(row['2.Set T2']), step=1, key=f"h_s2t2_{idx}_{idx_mp}", label_visibility="collapsed", disabled=kutu_kilitli)
                                        r_cols[7].markdown("<div style='text-align:center; opacity:0.5; margin-top:5px; font-weight:bold;'>|</div>", unsafe_allow_html=True)
                                        s3t1 = r_cols[8].number_input("S3T1", min_value=0, value=0 if is_wo else int(row['3.Set T1']), step=1, key=f"h_s3t1_{idx}_{idx_mp}", label_visibility="collapsed", disabled=kutu_kilitli)
                                        s3t2 = r_cols[9].number_input("S3T2", min_value=0, value=0 if is_wo else int(row['3.Set T2']), step=1, key=f"h_s3t2_{idx}_{idx_mp}", label_visibility="collapsed", disabled=kutu_kilitli)
                                        
                                        form_verileri[idx] = {
                                            "1.Set T1": s1t1, "1.Set T2": s1t2, "2.Set T1": s2t1, "2.Set T2": s2t2, "3.Set T1": s3t1, "3.Set T2": s3t2,
                                            "Durum": secilen_durum, "STB": secilen_stb, "Branş": row['Branş']
                                        }
                                        st.markdown("<hr style='margin: 8px 0px; opacity: 0.3;'>", unsafe_allow_html=True)

                                if form_verileri:
                                    t1_wins, t2_wins, biten_mac = 0, 0, 0
                                    
                                    for i, f_row in form_verileri.items():
                                        w1, w2 = hesapla_mac_kazanani(f_row)
                                        t1_wins += w1
                                        t2_wins += w2
                                        if w1 > 0 or w2 > 0 or f_row['Durum'] == "Çift Taraflı W/O":
                                            biten_mac += 1
                                            
                                    toplam_mac = len(form_verileri)
                                    st.markdown("---")
                                    
                                    if biten_mac == toplam_mac:
                                        st.success(f"🏆 **MAÇ SONUCU:** {t1} **{t1_wins} - {t2_wins}** {t2} *(Tüm branş skorları girildi)*")
                                    elif biten_mac > 0:
                                        st.info(f"📊 **ANLIK DURUM:** {t1} **{t1_wins} - {t2_wins}** {t2} *(Girilen maç: {biten_mac}/{toplam_mac})*")
                                    else:
                                        st.write("Henüz geçerli bir skor girilmedi.")

                                    if not is_kilitli:
                                        if st.button(f"💾 {t1} - {t2} Eşleşmesini Kaydet", key=f"btn_h_save_{grup_adi}_{eslesme_adi}_{tarih_str}", use_container_width=True, type="primary"):
                                            hata_mesajlari = []
                                            for idx, guncel_row in form_verileri.items():
                                                mac_tanimi = f"{guncel_row['Branş']}"
                                                s1t1, s1t2 = guncel_row["1.Set T1"], guncel_row["1.Set T2"]
                                                s2t1, s2t2 = guncel_row["2.Set T1"], guncel_row["2.Set T2"]
                                                s3t1, s3t2 = guncel_row["3.Set T1"], guncel_row["3.Set T2"]
                                                durum = guncel_row["Durum"]
                                                
                                                ok1, msg1 = set_gecerli_mi(s1t1, s1t2, durum=durum)
                                                ok2, msg2 = set_gecerli_mi(s2t1, s2t2, durum=durum)
                                                ok3, msg3 = set_gecerli_mi(s3t1, s3t2, is_set3=True, durum=durum)
                                                
                                                if not ok1: hata_mesajlari.append(f"{mac_tanimi} Set 1: {msg1}")
                                                if not ok2: hata_mesajlari.append(f"{mac_tanimi} Set 2: {msg2}")
                                                if not ok3: hata_mesajlari.append(f"{mac_tanimi} Set 3: {msg3}")
                                                
                                                if durum == "Tamamlandı":
                                                    if ((s1t1 > s1t2) and (s2t1 > s2t2)) or ((s1t2 > s1t1) and (s2t2 > s2t1)): 
                                                        if s3t1 != 0 or s3t2 != 0: hata_mesajlari.append(f"{mac_tanimi}: Maç 2-0 bittiği için 3. sete skor girilemez.")
                                                    elif ((s1t1 > s1t2) and (s2t2 > s2t1)) or ((s1t2 > s1t1) and (s2t1 > s2t2)):
                                                        if s3t1 == 0 and s3t2 == 0: hata_mesajlari.append(f"{mac_tanimi}: Setlerde 1-1 eşitlik var, 3. set skoru girilmelidir.")
                                            
                                            if hata_mesajlari:
                                                for h in hata_mesajlari: st.error(h)
                                            else:
                                                for idx, guncel_row in form_verileri.items():
                                                    for k in ["1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2", "Durum", "STB"]:
                                                        st.session_state.skor_tablosu.at[idx, k] = guncel_row[k]
                                                if ortak_veriyi_kaydet():
                                                    st.toast(f"✅ Kaydedildi! Sonuç: {t1} {t1_wins} - {t2_wins} {t2}", icon="🏆")
                                                    time.sleep(1)
                                                    st.rerun()
                                                else:
                                                    st.error("Sistem meşgul, lütfen tekrar deneyin.")

                # Eğer o gün atanmış hiç maç yoksa hakeme bilgi veriyoruz
                if not bugun_mac_var_mi:
                    with container_bugun:
                        st.info("✅ Bugün için üzerinize atanmış bir maç bulunmamaktadır.")

    # --- BAŞHAKEM SAYFASI: ESAME KONTROL MERKEZİ ---
    elif menu_secim == "📝 Esame Kontrol Merkezi":
        if st.session_state.admin_mi:
            st.info("ℹ️ Kaptanların girdikleri kadrolar (kapalı zarflar) burada toplanır. Geçmiş veya gelecek tüm esameleri tarih seçerek inceleyebilirsin.")
            
            tum_tarihler = st.session_state.mac_programi['Tarih'].dropna().unique().tolist()
            
            if not tum_tarihler:
                st.warning("Henüz maç programında tarihli bir maç bulunmuyor.")
            else:
                bugun = datetime.date.today().strftime("%d.%m.%Y")
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
                        
                        durum_ikon_t1 = "✅ Teslim Etti" if t1_girdi else "❌ Bekleniyor"
                        durum_ikon_t2 = "✅ Teslim Etti" if t2_girdi else "❌ Bekleniyor"
                        
                        with st.expander(f"{saat} | {kort} | {grup} | {t1} ({durum_ikon_t1})  VS  {t2} ({durum_ikon_t2})", expanded=not is_approved):
                            if is_approved:
                                st.success(f"Bu esameler onaylanmış ve {secilen_tarih} tarihli Maç Programına yansıtılmıştır.")
                            
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown(f"**🛡️ {t1} Kadrosu**")
                                if t1_girdi:
                                    for k, v in kasadaki_veri[t1].items(): st.write(f"- {k}: **{v}**")
                                else: st.warning("Kaptan henüz giriş yapmadı.")
                            with c2:
                                st.markdown(f"**🛡️ {t2} Kadrosu**")
                                if t2_girdi:
                                    for k, v in kasadaki_veri[t2].items(): st.write(f"- {k}: **{v}**")
                                else: st.warning("Kaptan henüz giriş yapmadı.")
                                
                            if not is_approved:
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

    # --- SAYFA 1: GRUP AYARLARI ---
    elif menu_secim == "👥 Grup Ayarları":
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
                                    st.session_state.havuz_kategorileri[t_adi] = up_kat
                                    st.session_state.havuz_yas_gruplari[t_adi] = up_yas
                                    
                                st.session_state.takim_havuzu.update(yeni_havuz)
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
            # --- YENİ EKLENEN: SADECE 2. AŞAMADA ÇIKAN STATÜ SEÇİMİ ---
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
                                    stage2_havuz.append(f"{gp} {sira}.si ({takim})")
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
                        t_isim = st.text_input("Takım Adı:", key=f"isim_t_{i}", placeholder="Takım Adı Yazın")
                        def_kadro = ""
                    elif aktif_asama == "2. Aşama":
                        match = re.search(r'\((.*?)\)$', secim)
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

            if st.button("🚀 Grubu ve Maç Programını Oluştur / Güncelle"):
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
                            st.success("Mevcut grup bulundu! Kadrolar başarıyla güncellendi, eski maç programı korundu.")
                        else:
                            st.error("Sistem meşgul, lütfen tekrar deneyin.")
                    else:
                        yeni_df = pd.DataFrame(eslesmeleri_olustur(grup_adi_temiz, takimlar, grup_tipi, format_secimi))
                        if st.session_state.skor_tablosu.empty: st.session_state.skor_tablosu = yeni_df
                        else: st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
                        if ortak_veriyi_kaydet():
                            st.success(f"{aktif_asama} grubu başarıyla oluşturuldu!")
                        else:
                            st.error("Sistem meşgul, lütfen tekrar deneyin.")
                    
            if st.session_state.takim_kadrolari:
                st.markdown("---")
                st.markdown(f"### 📁 Mevcut Kayıtlı Gruplar ve Kadrolar ({aktif_asama})")
                gosterilecek_gruplar_klasor = dogal_sirala([g for g in st.session_state.takim_kadrolari.keys() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
                for g_isim in gosterilecek_gruplar_klasor:
                    f_turu = st.session_state.grup_formatlari.get(g_isim, "3 Maçlık (2 Tek, 1 Çift)")
                    f_kat = st.session_state.grup_kategorileri.get(g_isim, "Erkekler")
                    f_yas = st.session_state.grup_yas_gruplari.get(g_isim, "Yaş Belirtme")
                    
                    with st.expander(f"📁 {g_isim} ({f_yas} | {f_kat} | {f_turu})"):
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

   # --- SAYFA 2: SKOR GİRİŞİ ---
    elif menu_secim == "✍️ Skor Girişi":
        if st.session_state.admin_mi:
            st.info("💡 **Not:** Kaptanların girdiği isimler onaylandıktan sonra buraya otomatik düşer. Kaydedilen skorlar anında puan durumuna yansır.")
            if not st.session_state.skor_tablosu.empty:
                gecerli_gruplar_t2 = [g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama]
                
                if not gecerli_gruplar_t2:
                    st.info(f"{aktif_asama} için kayıtlı grup bulunmamaktadır.")
                else:
                    gruplar = dogal_sirala(gecerli_gruplar_t2)
                    secilen_grup = st.selectbox("Grup Seç:", gruplar, key="skor_grup_sec")
                    
                    df_grup = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == secilen_grup].copy()
                    aktif_gunler = sorted(df_grup['Gün'].unique(), key=lambda x: int(x.split('.')[0]) if '.' in x else 99)
                    
                    secilen_gun = st.selectbox("Müsabaka Günü:", aktif_gunler)
                    df_gun = df_grup[df_grup['Gün'] == secilen_gun]
                    format_secimi = st.session_state.grup_formatlari.get(secilen_grup, "3 Maçlık (2 Tek, 1 Çift)")
                    
                    form_verileri = {}
                    current_eslesme = None  # GÖRSEL AYRAÇ İÇİN TAKİPÇİ
                    
                    for idx, row in sort_maclar(df_gun).iterrows():
                        # 1. GÖRSEL AYRAÇ: YENİ BİR TAKIM MAÇI BAŞLADIĞINDA ŞERİT AT
                        if row['Eşleşme'] != current_eslesme:
                            current_eslesme = row['Eşleşme']
                            st.markdown(f"""
                            <div style='background: linear-gradient(90deg, #0B3B24 0%, #1a6b44 100%); color: white; padding: 8px 15px; border-radius: 6px; margin-top: 25px; margin-bottom: 15px; font-size: 15px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.15);'>
                                🎾 TAKIM EŞLEŞMESİ: {row['Takım 1']} vs {row['Takım 2']} <span style='font-size:12px; font-weight:normal; opacity:0.8; margin-left:10px;'>(Kayıt: {current_eslesme})</span>
                            </div>
                            """, unsafe_allow_html=True)

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
                        
                        grup_kadro_dict = st.session_state.takim_kadrolari.get(secilen_grup, {})
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
                        st.divider()

                    eslesme_dict = {}
                    for idx, g_row in form_verileri.items():
                        row_data = df_gun.loc[idx]
                        eslesme = row_data["Eşleşme"]
                        brans = row_data["Branş"]
                        if eslesme not in eslesme_dict:
                            eslesme_dict[eslesme] = {"T1": {"isim": row_data["Takım 1"], "secimler": {}}, "T2": {"isim": row_data["Takım 2"], "secimler": {}}}
                        eslesme_dict[eslesme]["T1"]["secimler"][brans] = g_row["T1_Oyuncu"]
                        eslesme_dict[eslesme]["T2"]["secimler"][brans] = g_row["T2_Oyuncu"]
                
                    grup_kadro_dict = st.session_state.takim_kadrolari.get(secilen_grup, {})
                    
                    for eslesme, data in eslesme_dict.items():
                        for team_key in ["T1", "T2"]:
                            takim_ismi = data[team_key]["isim"]
                            havuz = grup_kadro_dict.get(takim_ismi, [])
                            secimler = data[team_key]["secimler"]
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
                                    
                                    toplam_c1 = yeni_ranking[c1_list[0]] + yeni_ranking[c1_list[1]]
                                    toplam_c2 = yeni_ranking[c2_list[0]] + yeni_ranking[c2_list[1]]
                                    
                                    if toplam_c1 > toplam_c2:
                                        uyarilar.append(f"Çiftler Sıralama Hatası: Seçilen 4 oyuncu arasındaki güç dengesine göre, 1. Çiftler daha güçlü veya eşit (Toplam: {toplam_c1}) olmalıdır. Mevcut durumda 2. Çiftler (Toplam: {toplam_c2}) daha güçlü görünüyor.")
                            
                            if uyarilar: st.warning(f"⚠️ **Sıralama Uyarısı ({takim_ismi} | Eşleşme: {eslesme}):**\n\n" + "\n".join([f"- {u}" for u in uyarilar]) + "\n\n*(Başhakem olarak bu uyarıya rağmen kaydetme yetkiniz bulunmaktadır.)*")
                    
                    if st.button("✅ Tüm Skorları ve Esameleri Kaydet (Maç Programına Yansıt)"):
                        hata_mesajlari = []
                        for idx, guncel_row in form_verileri.items():
                            mac_tanimi = f"{secilen_gun} - {st.session_state.skor_tablosu.loc[idx]['Branş']}"
                            
                            s1t1, s1t2 = guncel_row["1.Set T1"], guncel_row["1.Set T2"]
                            s2t1, s2t2 = guncel_row["2.Set T1"], guncel_row["2.Set T2"]
                            s3t1, s3t2 = guncel_row["3.Set T1"], guncel_row["3.Set T2"]
                            durum = guncel_row["Durum"]
                            
                            ok1, msg1 = set_gecerli_mi(s1t1, s1t2, durum=durum)
                            ok2, msg2 = set_gecerli_mi(s2t1, s2t2, durum=durum)
                            ok3, msg3 = set_gecerli_mi(s3t1, s3t2, is_set3=True, durum=durum)
                            
                            if not ok1: hata_mesajlari.append(f"{mac_tanimi} Set 1: {msg1}")
                            if not ok2: hata_mesajlari.append(f"{mac_tanimi} Set 2: {msg2}")
                            if not ok3: hata_mesajlari.append(f"{mac_tanimi} Set 3: {msg3}")
                            
                            if durum == "Tamamlandı":
                                t1_s1_kazandi = s1t1 > s1t2
                                t2_s1_kazandi = s1t2 > s1t1
                                t1_s2_kazandi = s2t1 > s2t2
                                t2_s2_kazandi = s2t2 > s2t1
                                
                                if (t1_s1_kazandi and t1_s2_kazandi) or (t2_s1_kazandi and t2_s2_kazandi): 
                                    if s3t1 != 0 or s3t2 != 0:
                                        hata_mesajlari.append(f"{mac_tanimi}: Maç 2-0 bittiği için 3. sete skor girilemez.")
                                
                                elif (t1_s1_kazandi and t2_s2_kazandi) or (t2_s1_kazandi and t1_s2_kazandi):
                                    if s3t1 == 0 and s3t2 == 0:
                                        hata_mesajlari.append(f"{mac_tanimi}: Setlerde 1-1 eşitlik var, 3. set skoru girilmelidir.")
                        
                        if hata_mesajlari:
                            for h in hata_mesajlari: st.error(h)
                        else:
                            for idx, guncel_row in form_verileri.items():
                                eslesme_val = guncel_row["Eşleşme"]
                                match_key = f"{secilen_grup}_{secilen_gun}_{eslesme_val}"
                                
                                st.session_state.skor_tablosu.at[idx, "T1_Oyuncu"] = guncel_row["T1_Oyuncu"]
                                st.session_state.skor_tablosu.at[idx, "T2_Oyuncu"] = guncel_row["T2_Oyuncu"]
                                st.session_state.skor_tablosu.at[idx, "1.Set T1"] = guncel_row["1.Set T1"]
                                st.session_state.skor_tablosu.at[idx, "1.Set T2"] = guncel_row["1.Set T2"]
                                st.session_state.skor_tablosu.at[idx, "2.Set T1"] = guncel_row["2.Set T1"]
                                st.session_state.skor_tablosu.at[idx, "2.Set T2"] = guncel_row["2.Set T2"]
                                st.session_state.skor_tablosu.at[idx, "3.Set T1"] = guncel_row["3.Set T1"]
                                st.session_state.skor_tablosu.at[idx, "3.Set T2"] = guncel_row["3.Set T2"]
                                st.session_state.skor_tablosu.at[idx, "Durum"] = guncel_row["Durum"]
                                st.session_state.skor_tablosu.at[idx, "STB"] = guncel_row["STB"]
                                
                                if guncel_row["T1_Oyuncu"] or guncel_row["T2_Oyuncu"]:
                                    st.session_state.esame_onayli[match_key] = True

                            if ortak_veriyi_kaydet():
                                st.success("Veriler ve Manuel Esameler başarıyla kaydedilip Maç Programına yansıtıldı!")
                                st.rerun()
                            else:
                                st.error("⚠️ Sistem şu an meşgul. Çakışma önlendi, lütfen tekrar deneyin.")

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
            else:
                st.info("Aktif grup bulunamadı.")
        else:
            st.warning("🔒 Skor ve esame giriş paneli dışarıya kapalıdır. Lütfen giriş yapınız.")

    # --- SAYFA: HAKEM YÖNETİMİ ---
    elif menu_secim == "👮‍♂️ Hakem Yönetimi":
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
# --- SAYFA 3: PUAN DURUMU ---
    elif menu_secim == "🏆 Puan Durumu":
        if not st.session_state.skor_tablosu.empty:
            tab_puan, tab_klasman = st.tabs(["📊 Grup Puan Durumları", "Nihai Klasman"])
            
            # === BİRİNCİ SEKME: STANDART PUAN DURUMU ===
            with tab_puan:
                gecerli_gruplar_t3 = [g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama]
                df_asama_t3 = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'].isin(gecerli_gruplar_t3)]
                
                if not df_asama_t3.empty:
                    tum_stats = hesapla_tum_puan_durumu(df_asama_t3)
                    mevcut_gruplar = dogal_sirala(list(tum_stats['Grup'].unique()))
                    
                    secim_opsiyonlari = ["Tüm Grupları Göster"] + mevcut_gruplar
                    secilen_gruplar = st.multiselect("🔍 Görüntülenecek Grupları Seçin:", options=secim_opsiyonlari, default=["Tüm Grupları Göster"])
                    gosterilecek_gruplar = mevcut_gruplar if "Tüm Grupları Göster" in secilen_gruplar or len(secilen_gruplar) == 0 else [g for g in secilen_gruplar if g != "Tüm Grupları Göster"]

                    pdf_gruplar_data = {}
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
                                
                            with t_ic2:
                                df_gp_matches = df_asama_t3[df_asama_t3['Grup'] == gp]
                                matris_takimlar = dogal_sirala(list(set(df_gp_matches['Takım 1']).union(set(df_gp_matches['Takım 2']))))
                                
                                html_matrix = render_html_matrix(matris_takimlar, df_gp_matches)
                                st.markdown(html_matrix, unsafe_allow_html=True)
                                
                                st.write("")
                                matris_pdf_bytes = generate_matrix_pdf(gp, matris_takimlar, df_gp_matches)
                                st.download_button(label="📥 Matrisi İndir (PDF - Sade Görünüm)", data=matris_pdf_bytes, file_name=f"matris_{gp}.pdf", mime="application/pdf", key=f"mat_pdf_{gp}")
                            
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
                        combined_pdf_bytes = generate_combined_standings_pdf(pdf_gruplar_data)
                        st.download_button(label=f"📥 Seçili Grupların Puan Durumunu Tek PDF Olarak İndir", data=combined_pdf_bytes, file_name=f"puan_durumu_toplu.pdf", mime="application/pdf", key="pdf_puan_toplu")
                    
                    st.markdown("---")
                    with st.expander("⚖️ Gelişmiş Averaj ve Mini Lig Hesaplayıcı"):
                        st.info("ℹ️ Üçlü veya dörtlü averaj kilitlenmelerinde bir grup ve sadece averaja dahil edilecek takımları seçin. Sistem, dışarıdaki takımlarla oynanan maçları yoksayarak yepyeni bir Mini Lig oluşturur. Bu bilgiye bakarak üstteki 'Başhakem Sıralama Paneli'nden tabloyu dizebilirsiniz.")
                        
                        avg_gruplar = dogal_sirala(list(df_asama_t3['Grup'].unique()))
                        sec_avg_grup = st.selectbox("Averaj Hesaplanacak Grubu Seçin:", ["Seçiniz"] + avg_gruplar, key="avg_grup_sec")
                        
                        if sec_avg_grup != "Seçiniz":
                            grup_maclari_avg = df_asama_t3[df_asama_t3['Grup'] == sec_avg_grup]
                            takimlar_avg = dogal_sirala(list(set(grup_maclari_avg['Takım 1']).union(set(grup_maclari_avg['Takım 2']))))
                            
                            secilen_takimlar_avg = st.multiselect("Averaja Kalmış (Kendi aralarında hesaplanacak) Takımları Seçin:", options=takimlar_avg)
                            
                            if len(secilen_takimlar_avg) >= 2:
                                if st.button("🧮 Seçili Takımların Kendi Arasındaki Averajını Hesapla (Mini Lig)"):
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
                                            
                                            st.success(f"✅ {sec_avg_grup} - Mini Lig Puan Durumu (Sadece seçili takımlar)")
                                            st.dataframe(mini_grup_df, use_container_width=True)
                            elif len(secilen_takimlar_avg) == 1:
                                st.warning("Averaj hesaplamak için en az 2 takım seçmelisiniz.")
                                
            # === İKİNCİ SEKME: ŞEREF KÜRSÜSÜ VE NİHAİ KLASMAN ===
            with tab_klasman:
                st.markdown("### 🏆 Turnuva Sonu Nihai Klasman Vitrini")
                if aktif_asama != "2. Aşama":
                    st.info("ℹ️ Nihai klasman sıralamaları sadece '2. Aşama' tamamlandıktan sonra oluşturulur.")
                else:
                    st.info("Bu vitrin, maçları ve onayları tamamen bitmiş olan kategorilerin şampiyonlarını ve play-out (düşme/kalma) durumlarını listeler. PDF çıktısı alırken listeden istediklerinizi veya tümünü seçebilirsiniz.")
                    
                    # 1. Hangi kategorilerin tüm grupları tamamlanmış bul
                    kat_gruplari_map = {}
                    for gp in mevcut_gruplar:
                        g_kat = st.session_state.grup_kategorileri.get(gp, "Erkekler")
                        g_yas = st.session_state.grup_yas_gruplari.get(gp, "Yaş Belirtme")
                        etiket = f"{g_yas} {g_kat}" if g_yas != "Yaş Belirtme" else f"{g_kat}"
                        if etiket not in kat_gruplari_map:
                            kat_gruplari_map[etiket] = []
                        kat_gruplari_map[etiket].append(gp)
                        
                    tamamlanan_kategoriler = []
                    for kat_ad, gruplar_listesi in kat_gruplari_map.items():
                        # O kategorideki TÜM grupların grup_tamamlandi değeri True mu?
                        herkes_tamam_mi = all(st.session_state.grup_tamamlandi.get(g, False) for g in gruplar_listesi)
                        if herkes_tamam_mi:
                            tamamlanan_kategoriler.append(kat_ad)
                            
                    if not tamamlanan_kategoriler:
                        st.warning("⏳ Henüz tüm grupları 'Tamamlandı' olarak işaretlenmiş (kilitlenmiş) bir kategori bulunmuyor. Lütfen önce Puan Durumu tablosundan ilgili grupları kilitleyin.")
                    else:
                        sec_klasmanlar = st.multiselect("🔍 Sonuçlarını Görmek ve Yazdırmak İstediğiniz Kategorileri Seçin:", options=sorted(tamamlanan_kategoriler), default=sorted(tamamlanan_kategoriler))
                        dusme_hatti = st.number_input("🔴 Play-out Gruplarında İlk Kaç Takım Ligde Kalacak? (Kırmızı Çizgi)", min_value=1, value=2, step=1, key="klasman_dusme_hatti")
                        
                        pdf_icin_hazir_veriler = {}
                        
                        for secilen_kategori in sec_klasmanlar:
                            with st.expander(f"🏅 {secilen_kategori} Nihai Sıralaması", expanded=True):
                                birinciler = []
                                ikinciler = []
                                playoutlar = []
                                
                                for gp in kat_gruplari_map[secilen_kategori]:
                                    statu = st.session_state.grup_statuleri.get(gp, "Play-out Grubu (Düşme Hattı)")
                                    if "Birinciler" in statu: birinciler.append(gp)
                                    elif "İkinciler" in statu: ikinciler.append(gp)
                                    else: playoutlar.append(gp)
                                        
                                current_rank = 1
                                kat_verisi = {"birinciler": [], "ikinciler": [], "ligde_kalanlar": [], "dusenler": []}
                                
                                if birinciler:
                                    st.markdown("##### 🏆 BİRİNCİLER GRUBU (Şampiyonluk ve Madalya)")
                                    for bg in dogal_sirala(birinciler):
                                        grup_df = tum_stats[tum_stats['Grup'] == bg].drop(columns=['Grup'])
                                        grup_df = sirala_grup_df(grup_df, bg)
                                        
                                        for idx, row in grup_df.iterrows():
                                            takim = row['Takım']
                                            kat_verisi["birinciler"].append(takim)
                                            
                                            madalya = ""
                                            if current_rank == 1: madalya = "🥇 (Şampiyon)"
                                            elif current_rank == 2: madalya = "🥈 (İkinci)"
                                            elif current_rank == 3: madalya = "🥉 (Üçüncü)"
                                            elif current_rank == 4: madalya = "🏅 (Dördüncü)"
                                            
                                            st.markdown(f"**{current_rank}. Sıra:** {takim} {madalya}")
                                            current_rank += 1
                                            
                                if ikinciler:
                                    st.markdown("---")
                                    st.markdown("##### 🥈 İKİNCİLER GRUBU (Klasman)")
                                    for ig in dogal_sirala(ikinciler):
                                        grup_df = tum_stats[tum_stats['Grup'] == ig].drop(columns=['Grup'])
                                        grup_df = sirala_grup_df(grup_df, ig)
                                        
                                        for idx, row in grup_df.iterrows():
                                            takim = row['Takım']
                                            kat_verisi["ikinciler"].append(takim)
                                            st.markdown(f"**{current_rank}. Sıra:** {takim}")
                                            current_rank += 1
                                
                                if playoutlar:
                                    for p_grup in playoutlar:
                                        grup_df = tum_stats[tum_stats['Grup'] == p_grup].drop(columns=['Grup'])
                                        grup_df = sirala_grup_df(grup_df, p_grup)
                                        
                                        for idx, row in grup_df.iterrows():
                                            if idx <= dusme_hatti:
                                                kat_verisi["ligde_kalanlar"].append(f"{row['Takım']} *(Grubu: {p_grup})*")
                                            else:
                                                kat_verisi["dusenler"].append(f"{row['Takım']} *(Grubu: {p_grup})*")
                                                
                                    st.markdown("---")
                                    st.markdown("##### 🟢 LİGDE KALANLAR (Play-Out Üst Sıralar)")
                                    if kat_verisi["ligde_kalanlar"]:
                                        for takim in dogal_sirala(kat_verisi["ligde_kalanlar"]):
                                            st.markdown(f"- {takim}")
                                    else:
                                        st.caption("Ligde kalan takım bulunamadı.")
                                        
                                    st.markdown("---")
                                    st.markdown("##### 🔴 LİGDEN DÜŞENLER (Play-Out Alt Sıralar)")
                                    if kat_verisi["dusenler"]:
                                        for takim in dogal_sirala(kat_verisi["dusenler"]):
                                            st.markdown(f"- {takim}")
                                    else:
                                        st.caption("Düşme hattında takım bulunamadı.")
                                        
                                pdf_icin_hazir_veriler[secilen_kategori] = kat_verisi
                                
                        if pdf_icin_hazir_veriler:
                            st.markdown("<br>", unsafe_allow_html=True)
                            toplu_pdf_bytes = generate_toplu_klasman_pdf(pdf_icin_hazir_veriler)
                            st.download_button(
                                label="📥 Seçili Kategorilerin Nihai Klasman Raporunu İndir (PDF)", 
                                data=toplu_pdf_bytes, 
                                file_name=f"turnuva_nihai_klasman.pdf", 
                                mime="application/pdf", 
                                key="pdf_toplu_klasman_btn",
                                type="primary",
                                use_container_width=True
                            )
        else:
            st.info(f"Bu aşamada henüz maç bulunmuyor.")
    # --- SAYFA 4: TAKIM KADROLARI (DİKEY LİSTE) ---
    elif menu_secim == "🛡️ Takım Kadroları":
        st.markdown(f"### 🛡️ Takımlar ve Oyuncu Kadroları ({aktif_asama})")
        if st.session_state.takim_kadrolari:
            gosterilecek_gruplar_klasor = dogal_sirala([g for g in st.session_state.takim_kadrolari.keys() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
            
            if not gosterilecek_gruplar_klasor:
                st.info(f"{aktif_asama} için kayıtlı takım bulunmamaktadır.")
            else:
                for g_isim in gosterilecek_gruplar_klasor:
                    f_turu = st.session_state.grup_formatlari.get(g_isim, "3 Maçlık (2 Tek, 1 Çift)")
                    f_kat = st.session_state.grup_kategorileri.get(g_isim, "Erkekler")
                    f_yas = st.session_state.grup_yas_gruplari.get(g_isim, "Yaş Belirtme")
                    
                    with st.expander(f"📁 {g_isim} ({f_yas} | {f_kat} | {f_turu})"):
                        g_kadro = st.session_state.takim_kadrolari[g_isim]
                        for t_isim in dogal_sirala(list(g_kadro.keys())):
                            st.markdown(f"**🛡️ {t_isim}**")
                            st.write(", ".join(g_kadro[t_isim]) if g_kadro[t_isim] else "Oyuncu yok")
                            st.markdown("---")
        else:
            st.info("Kayıtlı takım bulunmamaktadır.")

    # --- SAYFA 5: MAÇ PROGRAMI ---
    elif menu_secim == "📅 Maç Programı":
        tab_gunluk, tab_genel = st.tabs(["🗓️ Günlük Akış (Tarihe Göre)", "📋 Tüm Maçların Genel Durumu"])
        
        with tab_genel:
            st.markdown(f"### 📋 {aktif_asama} - Tüm Maçların Genel Durumu")
            
            gecerli_gruplar_genel = [g for g in st.session_state.grup_asamalari.keys() if st.session_state.grup_asamalari[g] == aktif_asama]
            df_hepsi = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'].isin(gecerli_gruplar_genel)]
            
            if df_hepsi.empty:
                st.info(f"{aktif_asama} için henüz oluşturulmuş bir fikstür/maç bulunmuyor.")
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
                st.info("Bu aşama için henüz maç planlanmadı.")
            st.markdown("---")
    
            if not st.session_state.skor_tablosu.empty:
                turkce_gunler = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
                
                if st.session_state.admin_mi:
                    if 'expand_all' not in st.session_state: st.session_state.expand_all = False
                    
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
                            if not df_team_summary.empty:
                                ozet_satiri = df_team_summary[(df_team_summary['Grup'] == grup_adi) & (df_team_summary['Eşleşme'] == eslesme_adi)]
                                if not ozet_satiri.empty:
                                    val = ozet_satiri.iloc[0]['Skor']
                                    if val != "Oynanmadı": takim_skoru_etiketi = f"  🟢 SKOR: {val}"
                            
                            kort = grup_df.iloc[0]['Kort']
                            tarih = grup_df.iloc[0]['Tarih']
                            saat = grup_df.iloc[0]['Maç Saati']
                            takim1 = grup_df.iloc[0]['Takım 1']
                            takim2 = grup_df.iloc[0]['Takım 2']
                            mevcut_hakem = grup_df.iloc[0]['Hakem']
                            if pd.isna(mevcut_hakem) or mevcut_hakem == "": mevcut_hakem = "Atanmadı"
                            
                            expander_title = f"{saat} | {kort} | {grup_adi} | {takim1} - {takim2}{takim_skoru_etiketi} (👮‍♂️ {mevcut_hakem})"
                            
                            with st.expander(expander_title, expanded=st.session_state.expand_all):
                                c_k, c_s, c_h = st.columns(3)
                                secilen_kort = c_k.text_input("📍 Kort (Tüm maçlara uygulanır):", value=kort, key=f"kort_{grup_adi}_{eslesme_adi}_{formatted_tarih}")
                                secilen_saat = c_s.text_input("⏰ Maç Saati (Tüm maçlara uygulanır):", value=saat, key=f"saat_{grup_adi}_{eslesme_adi}_{formatted_tarih}")
                                opts = ["Atanmadı"] + st.session_state.hakem_listesi
                                idx_h = opts.index(mevcut_hakem) if mevcut_hakem in opts else 0
                                secilen_hakem = c_h.selectbox("👮‍♂️ Hakem (Tüm maçlara uygulanır):", options=opts, index=idx_h, key=f"hakem_{grup_adi}_{eslesme_adi}_{formatted_tarih}")
                                
                                grup_df_ordered = sort_maclar(grup_df)[["Branş", "T1 Oyuncu", "T2 Oyuncu", "Skor", "Grup", "Gün", "Eşleşme", "Takım 1", "Takım 2", "Tarih", "Gün Adı", "Kazanan", "Kort", "Maç Saati", "Hakem"]]
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
    
                    st.markdown("---")
                    st.markdown("### ⚙️ Görünüm ve Çıktı Ayarları")
                    if st.button("🔄 Tüm Bireysel Maçları Ekranda Göster / Gizle"):
                        st.session_state.expand_all = not st.session_state.expand_all; st.rerun()
                    
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
                                baslik_metni = f"Mac Sonuclari - {formatted_tarih}"
                                dosya_adi = f"mac_sonuclari_{formatted_tarih}.pdf"
                                buton_adi = "📥 Günün Sonuçlarını PDF Olarak İndir"
                            else:
                                baslik_metni = f"Mac Programi - {formatted_tarih}"
                                dosya_adi = f"mac_programi_{formatted_tarih}.pdf"
                                buton_adi = "📥 Maç Programını PDF Olarak İndir"
                                
                            pdf_bytes_admin = generate_pdf(final_pdf_df, baslik_metni, not_metni=pdf_notu)
                            st.download_button(buton_adi, data=pdf_bytes_admin, file_name=dosya_adi, mime="application/pdf", key="pdf_admin")
    
                else:
                    st.markdown(f"### 📋 {formatted_tarih} Tarihli Maç Akışı ({aktif_asama})")
                    if df_gunluk_safe.empty:
                        st.info("Bu tarihte planlanmış maç bulunmamaktadır.")
                    else:
                        st.divider()
                        for (grup_adi, eslesme_adi), grup_df in df_gunluk_safe.groupby(['Grup', 'Eşleşme']):
                            takim_skoru_etiketi = ""
                            if not df_team_summary.empty:
                                ozet_satiri = df_team_summary[(df_team_summary['Grup'] == grup_adi) & (df_team_summary['Eşleşme'] == eslesme_adi)]
                                if not ozet_satiri.empty:
                                    val = ozet_satiri.iloc[0]['Skor']
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
                            expander_title = f"🎾 {saat} | {kort} | {grup_adi} | {takim1} - {takim2}{takim_skoru_etiketi}{hakem_baslik_etiketi}"
                            
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
            else:
                st.info("Gruplar oluşturulmadan maç programı aktif edilemez.")                     

    # --- SAYFA 6: DUYURULAR ---
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

# --- SAYFA 7: YÖNETİM & DOSYA İŞLEMLERİ ---
    elif menu_secim == "⚙️ Yönetim & Dosya":
        st.subheader(f"⚙️ Gelişmiş Yönetim Paneli ({aktif_asama})")

        if st.session_state.admin_mi:
            
            with st.expander("🔑 Kaptan Şifreleri (PIN) Yönetimi", expanded=False):
                st.info("ℹ️ Turnuvaya katılan her takıma otomatik 4 haneli PIN üretilir. Kaptanlar bu şifreyle sisteme girip kendi esamelerini teslim edebilirler.")
                
                tum_takim_listesi = dogal_sirala(list(st.session_state.takim_havuzu.keys()))
                for g_n, g_k in st.session_state.takim_kadrolari.items():
                    for t in g_k.keys():
                        if t not in tum_takim_listesi: tum_takim_listesi.append(t)
                        
                if st.button("🚀 Tüm Takımlara 4 Haneli PIN Üret (Mevcutları Koru)", type="primary"):
                    for t in tum_takim_listesi:
                        if t not in st.session_state.takim_pinleri:
                            st.session_state.takim_pinleri[t] = random.randint(1000, 9999)
                    if ortak_veriyi_kaydet():
                        st.success("Tüm takımlar için şifreler başarıyla üretildi!")
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
                            
                            # --- YENİ EKLENEN: SADECE 2. AŞAMADA ÇIKAN STATÜ SEÇİMİ ---
                            grup_statusu = "Play-out Grubu (Düşme Hattı)"
                            if aktif_asama == "2. Aşama":
                                mevcut_statu = st.session_state.grup_statuleri.get(sec_g, "Play-out Grubu (Düşme Hattı)")
                                statu_opts = ["Birinciler Grubu (Kürsü)", "İkinciler Grubu (Orta Klasman)", "Play-out Grubu (Düşme Hattı)"]
                                s_idx = statu_opts.index(mevcut_statu) if mevcut_statu in statu_opts else 2
                                rup_statusu = st.radio("🏅 Grup Statüsü (Bu grubun amacı nedir?):", statu_opts, horizontal=True, index=s_idx, key=f"edit_statu_{sec_g}")

                            fikstur_sifirlanacak_mi = (yeni_grup_tipi != tip_liste[tip_idx]) or (yeni_format != mevcut_format)
                            if fikstur_sifirlanacak_mi:
                                st.warning("⚠️ DİKKAT: Grup tipini veya maç formatını değiştirdiniz! Kaydettiğinizde bu grubun eski fikstürü ve skorları TAMAMEN SİLİNİP, yeni ayarlarla baştan oluşturulacaktır.")

                            st.markdown("---")
                            mevcut_takim_isimleri = list(m_kadrolar.keys())
                            beklenen_yeni_sayi = int(yeni_grup_tipi[0])
                            yeni_k_yapisi = {}; isim_degisiklikleri = {}
                            
                            for i in range(beklenen_yeni_sayi):
                                esk_ad = mevcut_takim_isimleri[i] if i < len(mevcut_takim_isimleri) else f"Yeni Takım {i+1}"
                                
                                # --- GÜVENLİ AÇILIR PENCERE VE BYE MANTIĞI ---
                                tum_takimlar = dogal_sirala(list(st.session_state.takim_havuzu.keys()))
                                bye_opt = "--- BOŞ (BYE) ---"
                                if bye_opt not in tum_takimlar: tum_takimlar.insert(0, bye_opt)
                                if esk_ad not in tum_takimlar: tum_takimlar.insert(1, esk_ad)
                                
                                c_a, c_b = st.columns([1, 2])
                                with c_a:
                                    y_ad = st.selectbox(f"{i+1}. Takım Seçimi", options=tum_takimlar, index=tum_takimlar.index(esk_ad), key=f"ad_{sec_g}_{i}")
                                    
                                    if i < len(mevcut_takim_isimleri) and y_ad != esk_ad: 
                                        isim_degisiklikleri[esk_ad] = y_ad
                                        
                                        # --- OTOMATİK OYUNCU DOLDURMA SİHİRBAZI ---
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
                                
                                # --- GRUPLARIN ÜST ÜSTE BİNMESİNİ ÖNLEYEN GÜVENLİK DUVARI ---
                                if g_hedef != sec_g and g_hedef in st.session_state.takim_kadrolari:
                                    st.error(f"⚠️ KRİTİK HATA: '{g_hedef}' adında bir grup zaten sistemde mevcut! İki grubu birleştiremezsiniz, lütfen farklı bir ad girin.")
                                else:
                                    kullanilan_baska_takimlar_tab6 = {}
                                    for g_n, g_k in st.session_state.takim_kadrolari.items():
                                        g_kat = st.session_state.grup_kategorileri.get(g_n, "Erkekler")
                                        g_asam = st.session_state.grup_asamalari.get(g_n, "1. Aşama")
                                        if g_n != sec_g and g_kat == yeni_kategori and g_asam == aktif_asama:
                                            for t_n in g_k.keys(): kullanilan_baska_takimlar_tab6[t_n] = g_n
                                    
                                    # --- BYE (BOŞ) TAKIMININ ÇAKIŞMA HESABINDAN MUAF TUTULMASI ---
                                    cakisanlar_tab6 = [t for t in list(yeni_k_yapisi.keys()) if t in kullanilan_baska_takimlar_tab6 and t != bye_opt]
                                    if cakisanlar_tab6:
                                        hata_msj = ", ".join([f"'{t}' ({kullanilan_baska_takimlar_tab6[t]})" for t in cakisanlar_tab6])
                                        st.error(f"⚠️ Hata: Eklemek veya değiştirmek istediğiniz takım(lar) {yeni_kategori} kategorisinde ({aktif_asama}) zaten başka gruplarda kayıtlı!\nÇakışanlar: {hata_msj}")
                                    else:
                                        if fikstur_sifirlanacak_mi:
                                            # GARANTİLİ SİLME YÖNTEMİ: İsimle değil, ID'lerle vuruyoruz
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
                                            st.session_state.grup_statuleri[g_hedef] = grup_statusu # YENİ GRUP STATÜSÜNÜ KAYDET
                                            
                                            if sec_g != g_hedef:
                                                if sec_g in st.session_state.takim_kadrolari: del st.session_state.takim_kadrolari[sec_g]
                                                if sec_g in st.session_state.grup_formatlari: del st.session_state.grup_formatlari[sec_g]
                                                if sec_g in st.session_state.grup_kategorileri: del st.session_state.grup_kategorileri[sec_g]
                                                if sec_g in st.session_state.grup_asamalari: del st.session_state.grup_asamalari[sec_g]
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
                                            
                                        else:
                                            st.session_state.takim_kadrolari[sec_g] = yeni_k_yapisi
                                            st.session_state.grup_kategorileri[sec_g] = yeni_kategori
                                            st.session_state.grup_asamalari[sec_g] = aktif_asama
                                            st.session_state.grup_yas_gruplari[sec_g] = yeni_yas
                                            st.session_state.grup_statuleri[sec_g] = grup_statusu # MEVCUT GRUBUN STATÜSÜNÜ GÜNCELLE
                                            
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
                        # GARANTİLİ SİLME YÖNTEMİ: İsimle değil, ID'lerle vuruyoruz
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
                        if secilen_sil_grup in st.session_state.grup_statuleri: del st.session_state.grup_statuleri[secilen_sil_grup] # EKLENDİ
                        
                        # --- HAYALET ESAMELERİN TEMİZLİĞİ ---
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
                    "hakem_pinleri": st.session_state.get("hakem_pinleri", {})
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
                                "takim_pinleri": {}, "esame_kasasi": {}, "esame_onayli": {}, "mac_programi": [], "hakem_listesi": [], "hakem_pinleri": {}
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
