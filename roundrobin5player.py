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
from fpdf import FPDF

# --- GENEL SAYFA AYARLARI ---
st.set_page_config(page_title="Tenis Turnuva Otomasyonu", page_icon="🎾", layout="wide", initial_sidebar_state="collapsed")

# --- GENEL STİLLER (HER İKİ MOD İÇİN ORTAK) ---
st.markdown("""
<style>
    /* Sadece en alttaki Streamlit reklamını her zaman gizliyoruz */
    footer {visibility: hidden !important;}
    
    /* Ana Ekran Gerçek Devasa Buton Stilleri */
    .stButton > button {
        border-radius: 12px;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        min-height: 80px; 
    }
    .stButton > button p {
        font-size: 18px !important;
        font-weight: 600 !important;
        white-space: pre-wrap !important; 
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# --- SADECE MİSAFİR MODU İÇİN GİZLİLİK KALKANI ---
if not st.session_state.get("admin_mi", False):
    st.markdown("""
    <style>
        /* Misafirler için Streamlit üst menülerini, GitHub ikonlarını ve ayarları tamamen gizleme */
        [data-testid="stToolbar"] {visibility: hidden !important;}
        [data-testid="stDecoration"] {visibility: hidden !important;}
        [data-testid="stStatusWidget"] {visibility: hidden !important;}
        #MainMenu {visibility: hidden !important;}
        header {visibility: hidden !important;}
    </style>
    """, unsafe_allow_html=True)

VERI_DOSYASI = "tenis_grup_turnuvasi_veri.json"
BELGELER_KLASORU = "turnuva_belgeleri"

if not os.path.exists(BELGELER_KLASORU):
    os.makedirs(BELGELER_KLASORU)

# ==============================================================================
# SİSTEM FONKSİYONLARI (ORTAK VERİ YAZMA, OKUMA VE PDF)
# ==============================================================================

def dogal_sirala(liste):
    def _natural_keys(text):
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]
    return sorted(liste, key=_natural_keys)

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

def pdf_cell_fit(pdf, w, h, txt, border=1, align='C', is_bold=False):
    size = 10 if is_bold else 9
    apply_font(pdf, bold=is_bold, size=size)
    while pdf.get_string_width(to_pdf_text(txt)) > (w - 2) and size > 5:
        size -= 0.5
        apply_font(pdf, bold=is_bold, size=size)
    pdf.cell(w, h, to_pdf_text(txt), border=border, align=align)
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

def generate_pdf(df, baslik):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    setup_pdf_fonts(pdf)
    
    apply_font(pdf, bold=True, size=14)
    pdf.cell(0, 10, to_pdf_text(baslik), ln=True, align='C')
    pdf.ln(5)
    
    if len(df.columns) > 0:
        col_widths = get_proportional_widths(pdf, df)
        
        for i, col in enumerate(df.columns): 
            pdf_cell_fit(pdf, col_widths[i], 10, col, is_bold=True)
        pdf.ln()
        
        for _, row in df.iterrows():
            for i, item in enumerate(row): 
                text = str(item)
                is_bold = False
                
                if text.startswith("**") and text.endswith("**"):
                    text = text[2:-2]
                    is_bold = True
                
                if is_bold and FONT_YUKLENDI and not FONT_BOLD_YUKLENDI:
                    text = f"{text} *" 
                    
                pdf_cell_fit(pdf, col_widths[i], 8, text, is_bold=is_bold)
            pdf.ln()
    return bytes(pdf.output())

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
    return bytes(pdf.output())

# --- MATRİS VE HESAPLAMA İÇİN YARDIMCI MOTORLAR ---
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
    
    is_stb = bool(row.get('STB', False))
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

    if durum == "Takım 1 Kazandı (Ret.)": score_str += " Ret." if is_t1 else " (Ret.)"
    elif durum == "Takım 2 Kazandı (Ret.)": score_str += " (Ret.)" if is_t1 else " Ret."

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
                    
                    for _, row in matches.iterrows():
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
    matrix = pd.DataFrame(index=takimlar, columns=takimlar)
    matrix = matrix.fillna("")
    for t in takimlar: matrix.at[t, t] = "X"
    
    for (t1, t2), group in df_grup.groupby(['Takım 1', 'Takım 2']):
        t1_total, t2_total = 0, 0
        for _, row in group.iterrows():
            w1, w2 = hesapla_mac_kazanani(row)
            t1_total += w1; t2_total += w2
        if t1_total > 0 or t2_total > 0:
            matrix.at[t1, t2] = f"{t1_total} - {t2_total}"
            matrix.at[t2, t1] = f"{t2_total} - {t1_total}"
            
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    setup_pdf_fonts(pdf)
    
    apply_font(pdf, bold=True, size=14)
    pdf.cell(0, 10, to_pdf_text(f"{grup_adi} - Takım Maçları Matrisi"), ln=True, align='C')
    pdf.ln(5)
    
    cols = ["Takımlar"] + takimlar
    col_width = 190 / len(cols) 
    
    for col in cols:
        pdf_cell_fit(pdf, col_width, 10, col, is_bold=True)
    pdf.ln()
    
    for t1 in takimlar:
        pdf_cell_fit(pdf, col_width, 8, t1, is_bold=True)
        for t2 in takimlar:
            val = matrix.at[t1, t2]
            pdf_cell_fit(pdf, col_width, 8, val, is_bold=False)
        pdf.ln()
    return bytes(pdf.output())

# --- YENİLENMİŞ (AĞIRLIKLI PUAN, OYNANAN MAÇ VE AVERAJ) MOTORU ---
def hesapla_tum_puan_durumu(df_girdi):
    if df_girdi.empty: return pd.DataFrame()
    df = df_girdi.copy()
    
    def satir_hesapla(row):
        durum = str(row.get('Durum', 'Tamamlandı'))
        if durum == "Takım 1 (W/O)": durum = "Takım 2 Kazandı (W/O)"
        elif durum == "Takım 2 (W/O)": durum = "Takım 1 Kazandı (W/O)"
        elif durum == "Takım 1 (Ret.)": durum = "Takım 2 Kazandı (Ret.)"
        elif durum == "Takım 2 (Ret.)": durum = "Takım 1 Kazandı (Ret.)"

        is_stb = bool(row.get('STB', False))

        if durum == "Çift Taraflı W/O": return pd.Series([0, 0, 0, 0])
        if durum == "Takım 1 Kazandı (W/O)": return pd.Series([12, 0, 2, 0])
        if durum == "Takım 2 Kazandı (W/O)": return pd.Series([0, 12, 0, 2])

        s1_t1, s1_t2 = int(row['1.Set T1']), int(row['1.Set T2'])
        s2_t1, s2_t2 = int(row['2.Set T1']), int(row['2.Set T2'])
        s3_t1, s3_t2 = int(row['3.Set T1']), int(row['3.Set T2'])

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
                t2_set += 1; t2_oyun += max(0, (6 if s2_t1 <= 4 else 7) - s2_t1)
                if t1_set == 1 and t2_set == 1:
                    t2_set += 1; t2_oyun += 1 if is_stb else 6
                return pd.Series([t1_oyun, t2_oyun, t1_set, t2_set])
                
            if t1_set == 1 and t2_set == 1:
                if is_stb:
                    if t1_s3_win: t1_set += 1
                    elif t2_s3_win: t2_set += 1
                    else:
                        t2_set += 1; t2_oyun += 1
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
    
    # Oynanan Maç (Takım Eşleşmesi) Hesaplaması
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

def ortak_veriyi_kaydet():
    data = {
        "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
        "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
        "takim_kadrolari": st.session_state.takim_kadrolari,
        "grup_formatlari": st.session_state.get("grup_formatlari", {}),
        "grup_kategorileri": st.session_state.get("grup_kategorileri", {}),
        "grup_asamalari": st.session_state.get("grup_asamalari", {}),
        "duyuru_metni": st.session_state.get("duyuru_metni", ""),
        "takim_havuzu": st.session_state.get("takim_havuzu", {})
    }
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def ortak_veriyi_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if data.get("skor_tablosu"):
                st.session_state.skor_tablosu = pd.DataFrame(data["skor_tablosu"])
            else:
                st.session_state.skor_tablosu = pd.DataFrame(columns=["Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu", "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2", "Durum", "STB"])
                
            if data.get("mac_programi"):
                mp_df = pd.DataFrame(data["mac_programi"])
                if "T1 Oyuncu" not in mp_df.columns: mp_df["T1 Oyuncu"] = ""; mp_df["T2 Oyuncu"] = ""
                if "Kazanan" not in mp_df.columns: mp_df["Kazanan"] = ""
                st.session_state.mac_programi = mp_df
            else:
                st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Canlı Skor", "Kazanan"])

            st.session_state.takim_kadrolari = data.get("takim_kadrolari", {})
            st.session_state.grup_formatlari = data.get("grup_formatlari", {})
            st.session_state.grup_kategorileri = data.get("grup_kategorileri", {})
            st.session_state.grup_asamalari = data.get("grup_asamalari", {})
            st.session_state.duyuru_metni = data.get("duyuru_metni", "")
            st.session_state.takim_havuzu = data.get("takim_havuzu", {})
        except Exception:
            pass 

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# ==============================================================================
# HAFIZA (SESSION STATE) BAŞLATMA
# ==============================================================================
if "admin_mi" not in st.session_state: st.session_state.admin_mi = False
if "expand_all" not in st.session_state: st.session_state.expand_all = False
if "selected_date_filter" not in st.session_state: st.session_state.selected_date_filter = datetime.date.today()
if "grup_formatlari" not in st.session_state: st.session_state.grup_formatlari = {}
if "grup_kategorileri" not in st.session_state: st.session_state.grup_kategorileri = {}
if "grup_asamalari" not in st.session_state: st.session_state.grup_asamalari = {}
if "duyuru_metni" not in st.session_state: st.session_state.duyuru_metni = ""
if "takim_havuzu" not in st.session_state: st.session_state.takim_havuzu = {}
if "takim_kadrolari" not in st.session_state: st.session_state.takim_kadrolari = {}

if "current_page" not in st.session_state: st.session_state.current_page = "Home"
if "aktif_asama" not in st.session_state: st.session_state.aktif_asama = "1. Aşama"

if 'skor_tablosu' not in st.session_state:
    if os.path.exists(VERI_DOSYASI):
        ortak_veriyi_yukle()
    else:
        st.session_state.skor_tablosu = pd.DataFrame(columns=["Grup", "Gün", "Eşleşme", "Branş", "Takım 1", "Takım 2", "T1_Oyuncu", "T2_Oyuncu", "1.Set T1", "1.Set T2", "2.Set T1", "2.Set T2", "3.Set T1", "3.Set T2", "Durum", "STB"])
        st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Canlı Skor", "Kazanan"])

if 'skor_tablosu' in st.session_state and 'Durum' not in st.session_state.skor_tablosu.columns:
    st.session_state.skor_tablosu['Durum'] = "Tamamlandı"
if 'skor_tablosu' in st.session_state and 'STB' not in st.session_state.skor_tablosu.columns:
    st.session_state.skor_tablosu['STB'] = False

if 'mac_programi' in st.session_state:
    if st.session_state.mac_programi.empty and len(st.session_state.mac_programi.columns) < 5:
         st.session_state.mac_programi = pd.DataFrame(columns=["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Canlı Skor", "Kazanan"])
    else:
        if "T1 Oyuncu" not in st.session_state.mac_programi.columns:
            st.session_state.mac_programi["T1 Oyuncu"] = ""; st.session_state.mac_programi["T2 Oyuncu"] = ""
        if "Kazanan" not in st.session_state.mac_programi.columns:
            st.session_state.mac_programi["Kazanan"] = ""

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
            else: return False, "Süper Tie-Break kurallarına uymuyor (Örn: 10-8 veya 12-10 olmalıdır)."
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
    if grup_tipi == "3'lü Grup":
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
        branslar = ["1. Tekler", "2. Tekler", "3. Tekler", "1. Çiftler", "2. Çiftler"]
    else:
        branslar = ["1. Tekler", "2. Tekler", "Çiftler"]

    program = []
    for m in base_matches:
        for brans in branslar:
            satir = m.copy()
            satir["Branş"] = brans
            satir["Grup"] = grup_adi
            satir.update({
                "T1_Oyuncu": "", "T2_Oyuncu": "",
                "1.Set T1": 0, "1.Set T2": 0, "2.Set T1": 0, "2.Set T2": 0, "3.Set T1": 0, "3.Set T2": 0, "Durum": "Tamamlandı", "STB": False
            })
            program.append(satir)
    return program

# --- SAYFADAN ÇIKIŞ GÜVENLİK UYARISI (SADECE BAŞHAKEM İÇİN) ---
if st.session_state.admin_mi:
    components.html(
        """
        <script>
        const parentWindow = window.parent || window;
        parentWindow.addEventListener("beforeunload", function (e) {
            e.preventDefault();
            e.returnValue = '';
        });
        </script>
        """,
        height=0,
        width=0,
    )

# ==============================================================================
# GLOBAL ÜST BAR VE NAVİGASYON MOTORU
# ==============================================================================
st.markdown("<div style='margin-top: -25px;'></div>", unsafe_allow_html=True)

# 1. SATIR: Sadece Ana Sayfaya Dön Butonu (Alt sayfalardayken görünür)
if st.session_state.current_page != "Home":
    col_back, _ = st.columns([1.5, 8.5])
    with col_back:
        if st.button("⬅️ ANA SAYFA", type="secondary", use_container_width=True):
            st.session_state.current_page = "Home"
            st.rerun()
    st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# 2. SATIR: Aşama Seçici ve Logolar
top_c1, top_c2 = st.columns([4, 3])

with top_c1:
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    asama_c1, asama_c2, _ = st.columns([1.5, 1.5, 3])
    with asama_c1:
        if st.button("1. Aşama", type="primary" if st.session_state.aktif_asama == "1. Aşama" else "secondary", use_container_width=True):
            st.session_state.aktif_asama = "1. Aşama"
            st.rerun()
    with asama_c2:
        if st.button("2. Aşama", type="primary" if st.session_state.aktif_asama == "2. Aşama" else "secondary", use_container_width=True):
            st.session_state.aktif_asama = "2. Aşama"
            st.rerun()

with top_c2:
    ttf_logo_html = ""
    if os.path.exists("TTFLOGO.png"):
        with open("TTFLOGO.png", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ttf_logo_html = f'<img src="data:image/png;base64,{b64}" style="height: 45px; border-radius: 12px; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.2));" alt="TTF Logo">'
    else:
        ttf_logo_html = '<div style="background-color: #0B3B24; color: white; padding: 10px 15px; border-radius: 12px; font-weight: bold; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.3s ease;">🇹🇷 TTF</div>'

    st.markdown(f"""
        <div style="display: flex; gap: 10px; justify-content: flex-end; align-items: center; margin-top: 5px;">
            <a href="https://i-kort.ttf.org.tr/" target="_blank" style="text-decoration: none; display: block; width: 100px;">
                <div style="background-color: #0056b3; color: white; padding: 10px 15px; border-radius: 12px; font-weight: bold; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.3s ease; width: 100%;">
                    🎾 i-Kort
                </div>
            </a>
            <a href="https://www.ttf.org.tr/" target="_blank" style="text-decoration: none; display: inline-block; transition: transform 0.3s ease;">
                {ttf_logo_html}
            </a>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

def render_big_button(icon, title, target_page):
    if st.button(f"{icon}\n{title}", use_container_width=True, key=f"btn_{target_page}"):
        st.session_state.current_page = target_page
        st.rerun()

if st.session_state.current_page == "Home":
    st.markdown("<h1 style='text-align:center;'>🎾 Turnuva Ana Ekranı</h1><br>", unsafe_allow_html=True)
    
    if st.session_state.admin_mi:
        st.markdown("<h4 style='text-align:center;'>👨‍⚖️ Başhakem Kontrol Paneli</h4><br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: render_big_button("👥", "Grup Ayarları", "👥 Grup Ayarları")
        with c2: render_big_button("✍️", "Skor Girişi", "✍️ Skor Girişi")
        with c3: render_big_button("🏆", "Puan Durumu", "🏆 Puan Durumu")
        
        st.write("")
        c4, c5, c6 = st.columns(3)
        with c4: render_big_button("📅", "Maç Programı", "📅 Maç Programı")
        with c5: render_big_button("📢", "Duyurular", "📢 Duyurular")
        with c6: render_big_button("⚙️", "Yönetim & Dosya", "⚙️ Yönetim & Dosya")
        
        st.divider()
        if st.button("🔓 Çıkış Yap (İzleyici Modu)", type="primary"):
            st.session_state.admin_mi = False
            st.rerun()

    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_big_button("🛡️", "Takım Kadroları", "🛡️ Takım Kadroları")
        with c2: render_big_button("🏆", "Puan Durumu", "🏆 Puan Durumu")
        with c3: render_big_button("📅", "Maç Fikstürü", "📅 Maç Programı")
        with c4: render_big_button("📢", "Duyurular", "📢 Duyurular")
        
        st.write("<br><br><br>", unsafe_allow_html=True)
        with st.expander("👨‍⚖️ Yönetici Girişi"):
            girilen_sifre = st.text_input("Şifre:", type="password", key="login_pass")
            if st.button("🔒 Giriş Yap"):
                if girilen_sifre == "zonguldak2026":
                    st.session_state.admin_mi = True
                    st.success("Giriş Başarılı!")
                    st.rerun()
                else:
                    st.error("❌ Hatalı Şifre!")

# ==============================================================================
# ALT SAYFALARIN İÇERİKLERİ
# ==============================================================================
else:
    menu_secim = st.session_state.current_page
    aktif_asama = st.session_state.aktif_asama
    
    st.markdown(f"<h3 style='margin-top: -15px;'>{menu_secim} ({aktif_asama})</h3>", unsafe_allow_html=True)
    st.markdown("---")

    # --- SAYFA 1: GRUP AYARLARI ---
    if menu_secim == "👥 Grup Ayarları":
        if st.session_state.admin_mi:
            st.markdown(f"#### ⚙️ {aktif_asama} - Grup Oluştur veya Düzenle")
            
            mevcut_asama_gruplari = dogal_sirala([g for g, a in st.session_state.grup_asamalari.items() if a == aktif_asama])
            secim_grup_modu = st.selectbox("📝 İşlem Yapılacak Grup:", ["➕ Yeni Grup Oluştur (Elle İsim Yaz)"] + mevcut_asama_gruplari)
            
            if secim_grup_modu == "➕ Yeni Grup Oluştur (Elle İsim Yaz)":
                grup_adi = st.text_input("Yeni Grup Adı:", placeholder="Örn: 35+ Erkekler A Grubu" if aktif_asama == "1. Aşama" else "Örn: 35+ Birinciler Grubu")
                eski_kat = "Erkekler"
                eski_fmt = "3 Maçlık (2 Tek, 1 Çift)"
                eski_tip_idx = 1 if aktif_asama == "1. Aşama" else 1 
                mevcut_kadro = {}
                safe_key = "yeni_grup"
                if aktif_asama == "2. Aşama":
                    st.info("💡 Not: Çakışmayı önlemek için, başka bir 2. Aşama grubuna yerleştirilmiş olan takımlar aşağıdaki listede görünmez.")
            else:
                st.info(f"✏️ Şu an **{secim_grup_modu}** grubunun ayarlarını ve kadrolarını görüntülüyorsunuz. Aşağıdan her şeyi güncelleyebilirsiniz.")
                grup_adi = st.text_input("Grup Adını Düzenle:", value=secim_grup_modu)
                eski_kat = st.session_state.grup_kategorileri.get(secim_grup_modu, "Erkekler")
                eski_fmt = st.session_state.grup_formatlari.get(secim_grup_modu, "3 Maçlık (2 Tek, 1 Çift)")
                mevcut_kadro = st.session_state.takim_kadrolari.get(secim_grup_modu, {})
                takim_sayisi = len(mevcut_kadro)
                safe_key = secim_grup_modu.replace(" ", "_")
                
                tip_liste_gecici = ["3'lü Grup", "4'lü Grup", "5'li Grup", "6'lı Grup"] if aktif_asama == "1. Aşama" else ["3'lü Grup", "4'lü Grup"]
                if takim_sayisi == 3: eski_tip_idx = 0
                elif takim_sayisi == 4: eski_tip_idx = 1
                elif takim_sayisi == 5: eski_tip_idx = 2 if len(tip_liste_gecici) > 2 else 0
                elif takim_sayisi == 6: eski_tip_idx = 3 if len(tip_liste_gecici) > 3 else 0
                else: eski_tip_idx = 0
            
            grup_adi_temiz = grup_adi.strip()
            
            kategori_liste = ["Erkekler", "Kadınlar"]
            def_kat_idx = kategori_liste.index(eski_kat) if eski_kat in kategori_liste else 0
            
            format_liste = ["3 Maçlık (2 Tek, 1 Çift)", "5 Maçlık (3 Tek, 2 Çift)"]
            def_fmt_idx = format_liste.index(eski_fmt) if eski_fmt in format_liste else 0

            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                kategori_secimi = st.radio("Kategori:", kategori_liste, index=def_kat_idx, horizontal=True, key=f"kat_{safe_key}")
            with col_t2:
                tip_liste = ["3'lü Grup", "4'lü Grup", "5'li Grup", "6'lı Grup"] if aktif_asama == "1. Aşama" else ["3'lü Grup", "4'lü Grup"]
                grup_tipi = st.radio("Grup Tipi:", tip_liste, index=eski_tip_idx, horizontal=True, key=f"tip_{safe_key}")
            with col_t3:
                format_secimi = st.radio("Müsabaka Maç Formatı:", format_liste, index=def_fmt_idx, horizontal=True, key=f"fmt_{safe_key}")
            
            fikstur_sifirlanacak_mi = False
            if secim_grup_modu != "➕ Yeni Grup Oluştur (Elle İsim Yaz)":
                if format_secimi != eski_fmt or int(grup_tipi[0]) != takim_sayisi:
                    fikstur_sifirlanacak_mi = True
                    st.warning("⚠️ DİKKAT: Grubun tipini veya maç formatını değiştirdiniz! Kaydettiğiniz an bu grubun fikstürü sıfırlanacak ve baştan oluşturulacaktır.")

            havuz_isimleri = ["✏️ Yeni / Listede Olmayan Takım (Elle Gir)"]
            baska_gruplardaki_takimlar = {}

            for g_n, g_k in st.session_state.takim_kadrolari.items():
                g_kat = st.session_state.grup_kategorileri.get(g_n, "Erkekler")
                g_asam = st.session_state.grup_asamalari.get(g_n, "1. Aşama")
                if g_n != grup_adi_temiz and g_kat == kategori_secimi and g_asam == aktif_asama:
                    for t_n in g_k.keys(): baska_gruplardaki_takimlar[t_n] = g_n
            
            if aktif_asama == "1. Aşama":
                musait_havuz = dogal_sirala([t for t in st.session_state.takim_havuzu.keys() if t not in baska_gruplardaki_takimlar])
                havuz_isimleri += musait_havuz
            else:
                stage1_gruplar = []
                for g in st.session_state.takim_kadrolari.keys():
                    k = st.session_state.grup_kategorileri.get(g, "Erkekler")
                    a = st.session_state.grup_asamalari.get(g, "1. Aşama")
                    if k == kategori_secimi and a == "1. Aşama":
                        stage1_gruplar.append(g)
                        
                df_s1 = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'].isin(stage1_gruplar)]
                stats_s1 = hesapla_tum_puan_durumu(df_s1)
                
                stage2_havuz = []
                if not stats_s1.empty:
                    for gp in dogal_sirala(list(stats_s1['Grup'].unique())):
                        grup_df = stats_s1[stats_s1['Grup'] == gp].sort_values(by=['Galibiyet', 'Maç Av.', 'Oyun Av.'], ascending=False)
                        grup_df.index = range(1, len(grup_df) + 1)
                        for sira, row in grup_df.iterrows():
                            takim = row['Takım']
                            if takim not in baska_gruplardaki_takimlar:
                                if sira == 1: emoji = "🟢"
                                elif sira == 2: emoji = "🔵"
                                elif sira == 3: emoji = "🟡"
                                else: emoji = "🔴"
                                stage2_havuz.append(f"{emoji} {gp} {sira}.si ({takim})")
                havuz_isimleri += stage2_havuz
            
            beklenen_sayi = int(grup_tipi[0])
            st.markdown(f"### 🛡️ Takım ve Kadro Seçimi ({beklenen_sayi} Takım)")
            
            takimlar = []
            grup_kadrolari = {}
            kadro_hata = False
            isim_degisiklikleri = {}
            mevcut_takim_isimleri = list(mevcut_kadro.keys()) if mevcut_kadro else []
            
            cols = st.columns(beklenen_sayi)
            for i in range(beklenen_sayi):
                with cols[i]:
                    st.markdown(f"**{i+1}. Takım**")
                    eski_takim_adi = mevcut_takim_isimleri[i] if i < len(mevcut_takim_isimleri) else ""
                    
                    clean_eski_takim_adi = eski_takim_adi
                    if "(" in eski_takim_adi and ")" in eski_takim_adi:
                        clean_eski_takim_adi = eski_takim_adi.split("(")[-1].split(")")[0].strip()
                    
                    def_secim_idx = 0
                    if clean_eski_takim_adi:
                        for h_idx, h_isim in enumerate(havuz_isimleri):
                            if clean_eski_takim_adi == h_isim or f"({clean_eski_takim_adi})" in h_isim or clean_eski_takim_adi in h_isim:
                                def_secim_idx = h_idx
                                break

                    secim = st.selectbox(f"{i+1}. Takım Seçimi", options=havuz_isimleri, index=def_secim_idx, key=f"sec_{safe_key}_{i}", label_visibility="collapsed")
                    
                    if secim == "✏️ Yeni / Listede Olmayan Takım (Elle Gir)":
                        t_isim = st.text_input("Takım Adı:", value=clean_eski_takim_adi if def_secim_idx==0 else "", key=f"isim_{safe_key}_{i}", placeholder="Takım Adı Yazın")
                        if def_secim_idx == 0 and eski_takim_adi: def_kadro = "\n".join(mevcut_kadro.get(eski_takim_adi, []))
                        else: def_kadro = ""
                    elif aktif_asama == "2. Aşama":
                        if "(" in secim and ")" in secim:
                            t_isim = secim.split("(")[-1].split(")")[0].strip()
                        else:
                            t_isim = secim
                            
                        if t_isim == clean_eski_takim_adi:
                            def_kadro = "\n".join(mevcut_kadro.get(eski_takim_adi, []))
                        else:
                            def_kadro = ""
                            for g_n, g_k in st.session_state.takim_kadrolari.items():
                                if st.session_state.grup_asamalari.get(g_n, "1. Aşama") == "1. Aşama" and t_isim in g_k:
                                    def_kadro = "\n".join(g_k[t_isim])
                                    break
                    else:
                        t_isim = secim
                        if t_isim == clean_eski_takim_adi:
                            def_kadro = "\n".join(mevcut_kadro.get(eski_takim_adi, []))
                        else:
                            def_kadro = "\n".join(st.session_state.takim_havuzu.get(secim, []))
                    
                    oyuncular_raw = st.text_area(f"✍️ Kadro (Her satıra bir kişi)", value=def_kadro, key=f"kadro_{safe_key}_{i}_{secim}", height=150)
                    oyuncu_listesi = [o.strip() for o in oyuncular_raw.split('\n') if o.strip()]
                    if len(oyuncu_listesi) > 10:
                        st.error("Maksimum 10 oyuncu sınırı aşıldı!")
                        kadro_hata = True
                    
                    if t_isim:
                        takimlar.append(t_isim)
                        grup_kadrolari[t_isim] = oyuncu_listesi if oyuncu_listesi else ["Belirtilmedi"]
                        if eski_takim_adi and t_isim != eski_takim_adi:
                            isim_degisiklikleri[eski_takim_adi] = t_isim

            if st.button("🚀 Grubu Kaydet / Güncelle", type="primary"):
                cakisan_takimlar = [t for t in takimlar if t in baska_gruplardaki_takimlar]
                if cakisan_takimlar:
                    hata_detay = ", ".join([f"'{t}' ({baska_gruplardaki_takimlar[t]})" for t in cakisan_takimlar])
                    st.error(f"⚠️ Hata: Girdiğiniz takım(lar) {kategori_secimi} kategorisinde ({aktif_asama}) zaten başka gruplarda kayıtlı!\nÇakışanlar: {hata_detay}")
                elif not grup_adi_temiz or len(takimlar) != beklenen_sayi or kadro_hata or len(set(takimlar)) != beklenen_sayi:
                    st.error("Lütfen grup adını girin, tüm takımları eksiksiz/farklı doldurun ve kurallara uyun.")
                else:
                    is_editing = (secim_grup_modu != "➕ Yeni Grup Oluştur (Elle İsim Yaz)")
                    eski_isim = secim_grup_modu if is_editing else None
                    
                    if is_editing and fikstur_sifirlanacak_mi:
                        st.session_state.skor_tablosu = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] != eski_isim]
                        st.session_state.mac_programi = st.session_state.mac_programi[st.session_state.mac_programi['Grup'] != eski_isim]
                        
                        yeni_df = pd.DataFrame(eslesmeleri_olustur(grup_adi_temiz, takimlar, grup_tipi, format_secimi))
                        if st.session_state.skor_tablosu.empty: st.session_state.skor_tablosu = yeni_df
                        else: st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
                        st.success(f"⚠️ Format değiştiği için {grup_adi_temiz} grubunun fikstürü sıfırlandı ve yeniden oluşturuldu!")
                    
                    elif is_editing and not fikstur_sifirlanacak_mi:
                        if eski_isim != grup_adi_temiz:
                            st.session_state.skor_tablosu.loc[st.session_state.skor_tablosu['Grup'] == eski_isim, 'Grup'] = grup_adi_temiz
                            st.session_state.mac_programi.loc[st.session_state.mac_programi['Grup'] == eski_isim, 'Grup'] = grup_adi_temiz
                        
                        if isim_degisiklikleri:
                            for e_a, y_a in isim_degisiklikleri.items():
                                st.session_state.skor_tablosu.replace({e_a: y_a}, inplace=True)
                                st.session_state.mac_programi.replace({e_a: y_a}, inplace=True)
                        st.success("✅ Kadrolar başarıyla güncellendi, eski fikstür skorları korundu.")
                        
                    elif not is_editing:
                        yeni_df = pd.DataFrame(eslesmeleri_olustur(grup_adi_temiz, takimlar, grup_tipi, format_secimi))
                        if st.session_state.skor_tablosu.empty: st.session_state.skor_tablosu = yeni_df
                        else: st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
                        st.success(f"✅ {grup_adi_temiz} grubu başarıyla oluşturuldu!")

                    if is_editing and eski_isim != grup_adi_temiz:
                        if eski_isim in st.session_state.takim_kadrolari: del st.session_state.takim_kadrolari[eski_isim]
                        if eski_isim in st.session_state.grup_formatlari: del st.session_state.grup_formatlari[eski_isim]
                        if eski_isim in st.session_state.grup_kategorileri: del st.session_state.grup_kategorileri[eski_isim]
                        if eski_isim in st.session_state.grup_asamalari: del st.session_state.grup_asamalari[eski_isim]

                    st.session_state.takim_kadrolari[grup_adi_temiz] = grup_kadrolari
                    st.session_state.grup_formatlari[grup_adi_temiz] = format_secimi
                    st.session_state.grup_kategorileri[grup_adi_temiz] = kategori_secimi
                    st.session_state.grup_asamalari[grup_adi_temiz] = aktif_asama
                    
                    ortak_veriyi_kaydet()
                    st.rerun()

            with st.expander("📥 Excel / CSV'den Takım Havuzu Yükle", expanded=False):
                st.info("ℹ️ Excel'de sütun başlıklarına 'Takım Adı', altındaki satırlara o takımın oyuncularını yazarak havuzunuzu genişletebilirsiniz.")
                uploaded_file = st.file_uploader("Takım listesi yükle", type=["csv", "xlsx"])
                if uploaded_file:
                    try:
                        if uploaded_file.name.endswith('.csv'): df_havuz = pd.read_csv(uploaded_file)
                        else: df_havuz = pd.read_excel(uploaded_file)
                        yeni_havuz = {}
                        for col in df_havuz.columns:
                            if not "Unnamed" in str(col):
                                oyuncular = df_havuz[col].dropna().astype(str).tolist()
                                yeni_havuz[str(col).strip()] = [o.strip() for o in oyuncular if o.strip()]
                        st.session_state.takim_havuzu.update(yeni_havuz)
                        ortak_veriyi_kaydet()
                        st.success(f"✅ {len(yeni_havuz)} takım havuza eklendi.")
                    except Exception as e: st.error(f"Hata: {e}")
                if st.session_state.takim_havuzu:
                    if st.button("🗑️ Havuzu Temizle"):
                        st.session_state.takim_havuzu = {}
                        ortak_veriyi_kaydet(); st.rerun()

            if st.session_state.takim_kadrolari:
                st.markdown("---")
                st.markdown(f"### 📁 Mevcut Kayıtlı Gruplar ve Kadrolar ({aktif_asama})")
                gosterilecek_gruplar_klasor = dogal_sirala([g for g in st.session_state.takim_kadrolari.keys() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
                for g_isim in gosterilecek_gruplar_klasor:
                    f_turu = st.session_state.grup_formatlari.get(g_isim, "3 Maçlık (2 Tek, 1 Çift)")
                    f_kat = st.session_state.grup_kategorileri.get(g_isim, "Erkekler")
                    with st.expander(f"📁 {g_isim} ({f_kat} | {f_turu})"):
                        g_kadro = st.session_state.takim_kadrolari[g_isim]
                        for t_isim in dogal_sirala(list(g_kadro.keys())):
                            st.markdown(f"**🛡️ {t_isim}**")
                            st.write(", ".join(g_kadro[t_isim]) if g_kadro[t_isim] else "Oyuncu yok")
                            st.markdown("---")

        else:
            st.warning("🔒 Bu panel dışarıya kapalıdır. Lütfen giriş yapınız.")

    # --- SAYFA 2: SKOR GİRİŞİ ---
    elif menu_secim == "✍️ Skor Girişi":
        if st.session_state.admin_mi:
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
                    
                    form_verileri = {}
                    for idx, row in df_gun.iterrows():
                        st.markdown(f"**🔹 {row['Branş']} ({row['Eşleşme']})**", unsafe_allow_html=True)
                        
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
                                ayirici1 = ' - ' if ' - ' in eski_kayit1 else ','
                                eski_oyuncular1 = [o.strip() for o in eski_kayit1.split(ayirici1) if o.strip() and o.strip() in t1_havuz and o.strip() != "Seçiniz"]
                                t1_oyuncu = st.multiselect("T1 Oyuncular", options=t1_havuz, default=eski_oyuncular1, max_selections=2, key=f"t1_o_{idx}", label_visibility="collapsed")
                                t1_oyuncu_str = " - ".join(t1_oyuncu)
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
                                ayirici2 = ' - ' if ' - ' in eski_kayit2 else ','
                                eski_oyuncular2 = [o.strip() for o in eski_kayit2.split(ayirici2) if o.strip() and o.strip() in t2_havuz and o.strip() != "Seçiniz"]
                                t2_oyuncu = st.multiselect("T2 Oyuncular", options=t2_havuz, default=eski_oyuncular2, max_selections=2, key=f"t2_o_{idx}", label_visibility="collapsed")
                                t2_oyuncu_str = " - ".join(t2_oyuncu)
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
                            "Durum": secilen_durum, "STB": secilen_stb
                        }
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
                        o1 = secimler.get("1. Tekler"); o2 = secimler.get("2. Tekler"); o3 = secimler.get("3. Tekler")
                        r1 = havuz.index(o1) if o1 in havuz else -1
                        r2 = havuz.index(o2) if o2 in havuz else -1
                        r3 = havuz.index(o3) if o3 in havuz else -1
                        uyarilar = []
                        if r1 != -1 and r2 != -1 and r1 <= r2: uyarilar.append(f"**2. Tekler** oyuncusu ({o2}), **1. Tekler** oyuncusundan ({o1}) daha üst bir esame sırasına sahip olmalıdır.")
                        if r2 != -1 and r3 != -1 and r2 <= r3: uyarilar.append(f"**3. Tekler** oyuncusu ({o3}), **2. Tekler** oyuncusundan ({o2}) daha üst bir esame sırasına sahip olmalıdır.")
                        if r1 != -1 and r3 != -1 and r2 == -1 and r1 <= r3: uyarilar.append(f"**3. Tekler** oyuncusu ({o3}), **1. Tekler** oyuncusundan ({o1}) daha üst bir esame sırasına sahip olmalıdır.")
                        if uyarilar: st.warning(f"⚠️ **Takım İçi Sıralama Uyarısı ({takim_ismi} | Eşleşme: {eslesme}):**\n\n" + "\n".join([f"- {u}" for u in uyarilar]) + "\n\n*(Kayıt işlemi yapılabilir, bu sadece bilgi uyarısıdır.)*")

                if st.button("✅ Tüm Skorları ve Esameleri Kaydet"):
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
                            for k, v in guncel_row.items():
                                st.session_state.skor_tablosu.at[idx, k] = v
                        ortak_veriyi_kaydet()
                        st.success("Veriler başarıyla işlendi ve kaydedildi!")
                        st.rerun()

                st.markdown("---")
                with st.expander(f"📊 {secilen_grup} Anlık Puan Durumu (Görüntülemek için tıklayın)"):
                    df_guncel = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == secilen_grup].copy()
                    if not df_guncel.empty:
                        grup_stats = hesapla_tum_puan_durumu(df_guncel)
                        if not grup_stats.empty:
                            grup_df_display = grup_stats.drop(columns=['Grup']).sort_values(by=['Galibiyet', 'Maç Av.', 'Oyun Av.'], ascending=False)
                            grup_df_display.index = range(1, len(grup_df_display) + 1)
                            st.dataframe(grup_df_display, use_container_width=True)
                        else:
                            st.info("Bu grup için henüz puan durumu oluşmadı.")
            else:
                st.info("Aktif grup bulunamadı.")
        else:
            st.warning("🔒 Skor ve esame giriş paneli dışarıya kapalıdır. Lütfen giriş yapınız.")

    # --- SAYFA 3: PUAN DURUMU ---
    elif menu_secim == "🏆 Puan Durumu":
        if not st.session_state.skor_tablosu.empty:
            gecerli_gruplar_t3 = [g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama]
            df_asama_t3 = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'].isin(gecerli_gruplar_t3)]
            
            if not df_asama_t3.empty:
                tum_stats = hesapla_tum_puan_durumu(df_asama_t3)
                mevcut_gruplar = dogal_sirala(list(tum_stats['Grup'].unique()))
                
                secim_opsiyonlari = ["Tüm Grupları Göster"] + mevcut_gruplar
                secilen_gruplar = st.multiselect("🔍 Görüntülenecek Grupları Seçin (Karşılaştırmak istediklerinizi ekleyebilirsiniz):", options=secim_opsiyonlari, default=["Tüm Grupları Göster"])
                gosterilecek_gruplar = mevcut_gruplar if "Tüm Grupları Göster" in secilen_gruplar or len(secilen_gruplar) == 0 else [g for g in secilen_gruplar if g != "Tüm Grupları Göster"]

                pdf_gruplar_data = {}
                for gp in dogal_sirala(gosterilecek_gruplar):
                    if gp in mevcut_gruplar:
                        g_kat = st.session_state.grup_kategorileri.get(gp, "Erkekler")
                        st.markdown(f"### 🏆 {gp} Puan Durumu ({g_kat})")
                        
                        grup_df = tum_stats[tum_stats['Grup'] == gp].drop(columns=['Grup']).sort_values(by=['Galibiyet', 'Maç Av.', 'Oyun Av.'], ascending=False)
                        grup_df.index = range(1, len(grup_df) + 1)
                        
                        pdf_df = grup_df.reset_index().rename(columns={"index": "Sıra"})
                        pdf_gruplar_data[gp] = pdf_df
                        
                        tab1, tab2 = st.tabs(["🏆 Puan Durumu Tablosu", "📊 Maç Matrisi"])
                        
                        with tab1:
                            st.dataframe(grup_df, use_container_width=True)
                            
                        with tab2:
                            df_gp_matches = df_asama_t3[df_asama_t3['Grup'] == gp]
                            matris_takimlar = dogal_sirala(list(set(df_gp_matches['Takım 1']).union(set(df_gp_matches['Takım 2']))))
                            
                            html_matrix = render_html_matrix(matris_takimlar, df_gp_matches)
                            st.markdown(html_matrix, unsafe_allow_html=True)
                            
                            st.write("")
                            matris_pdf_bytes = generate_matrix_pdf(gp, matris_takimlar, df_gp_matches)
                            st.download_button(label="📥 Matrisi İndir (PDF - Sade Görünüm)", data=matris_pdf_bytes, file_name=f"matris_{gp}.pdf", mime="application/pdf", key=f"mat_pdf_{gp}")
                        
                        st.markdown("<br>", unsafe_allow_html=True)

                if pdf_gruplar_data:
                    st.divider()
                    combined_pdf_bytes = generate_combined_standings_pdf(pdf_gruplar_data)
                    st.download_button(label=f"📥 Seçili Grupların Puan Durumunu Tek PDF Olarak İndir", data=combined_pdf_bytes, file_name=f"puan_durumu_toplu.pdf", mime="application/pdf", key="pdf_puan_toplu")
                
                st.markdown("---")
                with st.expander("⚖️ Gelişmiş Averaj ve Mini Lig Hesaplayıcı"):
                    st.info("ℹ️ Üçlü veya dörtlü averaj kilitlenmelerinde bir grup ve sadece averaja dahil edilecek takımları seçin. Sistem, dışarıdaki takımlarla oynanan maçları yoksayarak yepyeni bir Mini Lig oluşturur.")
                    
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
                    with st.expander(f"📁 {g_isim} ({f_kat} | {f_turu})", expanded=False):
                        g_kadro = st.session_state.takim_kadrolari[g_isim]
                        for t_isim in dogal_sirala(list(g_kadro.keys())):
                            st.markdown(f"**🛡️ {t_isim}**")
                            st.write(", ".join(g_kadro[t_isim]) if g_kadro[t_isim] else "Oyuncu yok")
                            st.markdown("---")
        else:
            st.info("Kayıtlı takım bulunmamaktadır.")

    # --- SAYFA 5: MAÇ PROGRAMI ---
    elif menu_secim == "📅 Maç Programı":
        gosterim_sekli = st.radio("👁️ Fikstür ve PDF Gösterim Şekli:", ["Bireysel Maçlar (Tekler/Çiftler Skorları)", "Takım Maçları (Genel Skor)"], horizontal=True)
        is_bireysel = "Bireysel" in gosterim_sekli
        st.markdown("---")

        st.markdown("### 📅 Maç Olan Günler (Filtre)")
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
        if 'expand_all' not in st.session_state: st.session_state.expand_all = False
        if st.button("🔄 Arayüzde Maçları Göster/ Gizle"):
            st.session_state.expand_all = not st.session_state.expand_all; st.rerun()

        if not st.session_state.skor_tablosu.empty:
            turkce_gunler = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
            secilen_tarih = st.date_input("🗓️ Program Yapılacak / Görüntülenecek Tarih:", value=st.session_state.selected_date_filter)
            st.session_state.selected_date_filter = secilen_tarih
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
                        st.session_state.mac_programi.at[idx, "Canlı Skor"] = "Çift Taraflı W/O"
                        st.session_state.mac_programi.at[idx, "Kazanan"] = ""
                    elif durum == "Takım 1 Kazandı (W/O)":
                        st.session_state.mac_programi.at[idx, "Canlı Skor"] = "W/O"
                        st.session_state.mac_programi.at[idx, "Kazanan"] = "T1"
                    elif durum == "Takım 2 Kazandı (W/O)":
                        st.session_state.mac_programi.at[idx, "Canlı Skor"] = "W/O"
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
                            
                            st.session_state.mac_programi.at[idx, "Canlı Skor"] = skor_str
                            
                            if durum == "Takım 1 Kazandı (Ret.)":
                                st.session_state.mac_programi.at[idx, "Kazanan"] = "T1"
                            elif durum == "Takım 2 Kazandı (Ret.)":
                                st.session_state.mac_programi.at[idx, "Kazanan"] = "T2"
                            else:
                                t1_set_sayisi = (s1t1 > s1t2) + (s2t1 > s2t2) + (s3t1 > s3t2)
                                t2_set_sayisi = (s1t2 > s1t1) + (s2t2 > s2t1) + (s3t2 > s3t1)
                                st.session_state.mac_programi.at[idx, "Kazanan"] = "T1" if t1_set_sayisi >= 2 else ("T2" if t2_set_sayisi >= 2 else "")
                        else:
                            st.session_state.mac_programi.at[idx, "Canlı Skor"] = "Oynanmadı"
                            st.session_state.mac_programi.at[idx, "Kazanan"] = ""

            df_gunluk = st.session_state.mac_programi[(st.session_state.mac_programi['Tarih'] == formatted_tarih) & (st.session_state.mac_programi['Grup'].isin(gecerli_gruplar_t4))].copy()
            
            df_team_summary_list = []
            for (saat, tarih, gun, kort, grup, match_gun, eslesme, takim1, takim2), g_df in df_gunluk.groupby(
                ['Maç Saati', 'Tarih', 'Gün Adı', 'Kort', 'Grup', 'Gün', 'Eşleşme', 'Takım 1', 'Takım 2']
            ):
                played = (g_df['Canlı Skor'] != 'Oynanmadı').sum()
                
                if played == 0:
                    team_score = "Oynanmadı"
                    team_winner = ""
                else:
                    t1_match_wins = (g_df['Kazanan'] == 'T1').sum()
                    t2_match_wins = (g_df['Kazanan'] == 'T2').sum()
                    team_score = f"{t1_match_wins}-{t2_match_wins}"
                    
                    eslesen_skorlar = st.session_state.skor_tablosu[
                        (st.session_state.skor_tablosu['Grup'] == grup) & 
                        (st.session_state.skor_tablosu['Gün'] == match_gun) & 
                        (st.session_state.skor_tablosu['Eşleşme'] == eslesme)
                    ]
                    
                    team_winner = ""
                    if not eslesen_skorlar.empty:
                        temp_stats = hesapla_tum_puan_durumu(eslesen_skorlar)
                        if not temp_stats.empty:
                            t1_row = temp_stats[temp_stats['Takım'] == takim1]
                            t2_row = temp_stats[temp_stats['Takım'] == takim2]
                            if not t1_row.empty and not t2_row.empty:
                                if t1_row.iloc[0]['Galibiyet'] > t2_row.iloc[0]['Galibiyet']: team_winner = "T1"
                                elif t2_row.iloc[0]['Galibiyet'] > t1_row.iloc[0]['Galibiyet']: team_winner = "T2"

                    df_team_summary_list.append({
                        "Maç Saati": saat, "Tarih": tarih, "Gün Adı": gun, "Kort": kort,
                        "Grup": grup, "Gün": match_gun, "Branş": "Genel Skor", "Eşleşme": eslesme,
                        "Takım 1": takim1, "Takım 2": takim2, "T1 Oyuncu": "-", "T2 Oyuncu": "-",
                        "Canlı Skor": team_score, "Kazanan": team_winner
                    })
            df_team_summary = pd.DataFrame(df_team_summary_list)
            
            if st.session_state.admin_mi:
                st.markdown("### 📥 PDF İndirme Ayarları")
                tum_kolonlar = ["Maç Saati", "Tarih", "Gün Adı", "Kort", "Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "Canlı Skor", "Kazanan"]
                
                if not is_bireysel:
                    tum_kolonlar = [c for c in tum_kolonlar if c not in ["T1 Oyuncu", "T2 Oyuncu"]]
                    
                secilen_pdf_cols = st.multiselect("PDF'e eklenecek sütunları seçin:", options=tum_kolonlar, default=["Maç Saati", "Kort", "Grup", "Branş", "Takım 1", "Takım 2", "Canlı Skor"])

                if is_bireysel:
                    df_pdf_export = df_gunluk.copy()
                    if not df_pdf_export.empty:
                        for i in df_pdf_export.index:
                            win = df_pdf_export.at[i, 'Kazanan']
                            if win == 'T1':
                                df_pdf_export.at[i, 'Takım 1'] = f"**{df_pdf_export.at[i, 'Takım 1']}**"
                                if 'T1 Oyuncu' in df_pdf_export.columns and df_pdf_export.at[i, 'T1 Oyuncu']: 
                                    df_pdf_export.at[i, 'T1 Oyuncu'] = f"**{df_pdf_export.at[i, 'T1 Oyuncu']}**"
                            elif win == 'T2':
                                df_pdf_export.at[i, 'Takım 2'] = f"**{df_pdf_export.at[i, 'Takım 2']}**"
                                if 'T2 Oyuncu' in df_pdf_export.columns and df_pdf_export.at[i, 'T2 Oyuncu']: 
                                    df_pdf_export.at[i, 'T2 Oyuncu'] = f"**{df_pdf_export.at[i, 'T2 Oyuncu']}**"
                else:
                    df_pdf_export = df_team_summary.copy()
                    if not df_pdf_export.empty:
                        for i in df_pdf_export.index:
                            win = df_pdf_export.at[i, 'Kazanan']
                            if win == 'T1': df_pdf_export.at[i, 'Takım 1'] = f"**{df_pdf_export.at[i, 'Takım 1']}**"
                            elif win == 'T2': df_pdf_export.at[i, 'Takım 2'] = f"**{df_pdf_export.at[i, 'Takım 2']}**"

                st.markdown(f"### ➕ {formatted_tarih} Tarihine Maç Ekle ({aktif_asama})")
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
                                    "Takım 1": r['Takım 1'], "Takım 2": r['Takım 2'], "T1 Oyuncu": "", "T2 Oyuncu": "", "Canlı Skor": "Oynanmadı", "Kazanan": ""
                                })
                            
                            st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, pd.DataFrame(yeni_kayitlar)], ignore_index=True)
                            ortak_veriyi_kaydet()
                            st.success(f"Eşleşmeye ait {len(yeni_kayitlar)} maç başarıyla eklendi!")
                            st.rerun()

                if not df_gunluk.empty:
                    st.markdown("### 📋 Günlük Akış Editörü")
                    mac_sil_secenekler = ["Seçiniz"] + [f"{r['Maç Saati']} - {r['Kort']} | {r['Grup']} | {r['Takım 1']} vs {r['Takım 2']} ({r['Branş']})" for idx, r in df_gunluk.iterrows()]
                    secilen_program_mac = st.selectbox("⛔ Programdan Kaldırılacak Maçı Seçin:", mac_sil_secenekler, key="program_mac_sil_selectbox")
                    if secilen_program_mac != "Seçiniz":
                        secilen_idx_in_df = mac_sil_secenekler.index(secilen_program_mac) - 1
                        actual_match_idx = df_gunluk.index[secilen_idx_in_df]
                        if st.button("❌ Seçilen Maçı Programdan Kaldır"):
                            st.session_state.mac_programi.drop(index=actual_match_idx, inplace=True); st.session_state.mac_programi.reset_index(drop=True, inplace=True); ortak_veriyi_kaydet(); st.rerun()
                    st.divider()
                    
                    if not df_pdf_export.empty and secilen_pdf_cols:
                        pdf_bytes_admin = generate_pdf(df_pdf_export[secilen_pdf_cols], f"Mac Programi - {formatted_tarih}")
                        st.download_button("📥 Programı PDF Olarak İndir", data=pdf_bytes_admin, file_name=f"mac_programi_{formatted_tarih}.pdf", mime="application/pdf", key="pdf_admin")
                    
                    edited_dfs = []
                    for (grup_adi, eslesme_adi), grup_df in df_gunluk.groupby(['Grup', 'Eşleşme']):
                        kort = grup_df.iloc[0]['Kort']
                        tarih = grup_df.iloc[0]['Tarih']
                        gun_adi_val = grup_df.iloc[0]['Gün Adı']
                        takim1 = grup_df.iloc[0]['Takım 1']
                        takim2 = grup_df.iloc[0]['Takım 2']
                        
                        expander_title = f"{kort} | {tarih} | {gun_adi_val} | {grup_adi} | {takim1} - {takim2}"
                        
                        with st.expander(expander_title, expanded=st.session_state.expand_all):
                            e_df = st.data_editor(
                                grup_df, 
                                use_container_width=True, 
                                num_rows="dynamic", 
                                disabled=["Grup", "Gün", "Branş", "Eşleşme", "Takım 1", "Takım 2", "T1 Oyuncu", "T2 Oyuncu", "Canlı Skor", "Kazanan"], 
                                key=f"editor_{grup_adi}_{eslesme_adi}_{formatted_tarih}"
                            )
                            edited_dfs.append(e_df)

                    if st.button("💾 Değişiklikleri Kaydet"):
                        if edited_dfs:
                            guncel_program = pd.concat(edited_dfs)
                            st.session_state.mac_programi.drop(index=df_gunluk.index, inplace=True)
                            guncel_program['Tarih'] = guncel_program['Tarih'].fillna(formatted_tarih)
                            st.session_state.mac_programi = pd.concat([st.session_state.mac_programi, guncel_program]).reset_index(drop=True)
                            ortak_veriyi_kaydet()
                            st.success("Güncellendi!")
                            st.rerun()

            else:
                st.markdown(f"### 📋 {formatted_tarih} Tarihli Maç Akışı ({aktif_asama})")
                if df_gunluk.empty:
                    st.info("Bu tarihte planlanmış maç bulunmamaktadır.")
                else:
                    st.divider()
                    if is_bireysel:
                        for (grup_adi, eslesme_adi), grup_df in df_gunluk.groupby(['Grup', 'Eşleşme']):
                            kort = grup_df.iloc[0]['Kort']
                            tarih = grup_df.iloc[0]['Tarih']
                            gun_adi_val = grup_df.iloc[0]['Gün Adı']
                            takim1 = grup_df.iloc[0]['Takım 1']
                            takim2 = grup_df.iloc[0]['Takım 2']
                            
                            expander_title = f"{kort} | {tarih} | {gun_adi_val} | {grup_adi} | {takim1} - {takim2}"
                            with st.expander(expander_title, expanded=st.session_state.expand_all):
                                html_rows = ""
                                for _, row in grup_df.iterrows():
                                    skor = str(row.get('Canlı Skor', 'Oynanmadı'))
                                    skor_html = f"<span style='color:#28a745; font-weight:bold;'>{skor}</span>" if skor not in ["Oynanmadı", ""] else "<i>Bekleniyor</i>"
                                    t1_o = html.escape(str(row.get('T1 Oyuncu', '')).strip())
                                    t2_o = html.escape(str(row.get('T2 Oyuncu', '')).strip())
                                    
                                    if row.get('Kazanan') == 'T1': t1_o = f"<b>{t1_o}</b>"
                                    elif row.get('Kazanan') == 'T2': t2_o = f"<b>{t2_o}</b>"
                                    
                                    html_rows += f"<tr><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{row['Branş']}</td><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{t1_o} / {t2_o}</td><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{skor_html}</td></tr>"
                                
                                st.markdown(f"""
                                <table style="width:100%; border-collapse: collapse; font-family: sans-serif;">
                                    <tr><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Branş</th><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Oyuncular</th><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Skor</th></tr>
                                    {html_rows}
                                </table>
                                """, unsafe_allow_html=True)
                    else:
                        if not df_team_summary.empty:
                            for (grup_adi, eslesme_adi), grup_df in df_team_summary.groupby(['Grup', 'Eşleşme']):
                                row = grup_df.iloc[0]
                                skor = str(row['Canlı Skor'])
                                skor_html = f"<span style='color:#28a745; font-weight:bold;'>{skor}</span>" if skor != "Oynanmadı" else "<i>Bekleniyor</i>"
                                t1_n = html.escape(str(row['Takım 1']))
                                t2_n = html.escape(str(row['Takım 2']))
                                
                                if row['Kazanan'] == 'T1': t1_n = f"<b>{t1_n}</b>"
                                elif row['Kazanan'] == 'T2': t2_n = f"<b>{t2_n}</b>"
                                
                                html_rows = f"<tr><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>Takım Karşılaşması</td><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{t1_n} / {t2_n}</td><td style='border:1px solid rgba(128,128,128,0.3); padding:5px;'>{skor_html}</td></tr>"
                                
                                expander_title = f"{row['Kort']} | {row['Tarih']} | {row['Gün Adı']} | {grup_adi} | {row['Takım 1']} - {row['Takım 2']}"
                                with st.expander(expander_title, expanded=st.session_state.expand_all):
                                    st.markdown(f"""
                                    <table style="width:100%; border-collapse: collapse; font-family: sans-serif;">
                                        <tr><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Branş</th><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Takımlar</th><th style="border:1px solid rgba(128,128,128,0.3); padding:5px; background-color: rgba(128, 128, 128, 0.1);">Skor</th></tr>
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
                ortak_veriyi_kaydet()
                st.success("Duyuru metni başarıyla güncellendi!")
            
            st.markdown("---")
            st.markdown("### 📄 Turnuva Belgeleri Ekle (Çoklu Yükleme)")
            st.info("Kural kitapçığı veya yönetmelik gibi PDF dosyalarını sisteme buradan yükleyebilirsiniz.")
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
            st.markdown("### 🗑️ Grup Silme İşlemleri")
            if not st.session_state.skor_tablosu.empty:
                silinecek_gruplar = dogal_sirala([g for g in st.session_state.skor_tablosu['Grup'].unique() if st.session_state.grup_asamalari.get(g, "1. Aşama") == aktif_asama])
                secilen_sil_grup = st.selectbox("Silinecek Grubu Seçin:", ["Seçiniz"] + silinecek_gruplar, key="grup_sil_secim")
                
                if secilen_sil_grup != "Seçiniz":
                    st.warning(f"⚠️ DİKKAT: '{secilen_sil_grup}' grubunu ve bu gruba ait tüm fikstür/kadro kayıtlarını kalıcı olarak sileceksiniz!")
                    
                    if st.button(f"🚨 '{secilen_sil_grup}' Grubunu Tamamen Sil"):
                        st.session_state.skor_tablosu = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] != secilen_sil_grup]
                        st.session_state.mac_programi = st.session_state.mac_programi[st.session_state.mac_programi['Grup'] != secilen_sil_grup]
                        
                        if secilen_sil_grup in st.session_state.takim_kadrolari: del st.session_state.takim_kadrolari[secilen_sil_grup]
                        if secilen_sil_grup in st.session_state.grup_formatlari: del st.session_state.grup_formatlari[secilen_sil_grup]
                        if secilen_sil_grup in st.session_state.grup_kategorileri: del st.session_state.grup_kategorileri[secilen_sil_grup]
                        if secilen_sil_grup in st.session_state.grup_asamalari: del st.session_state.grup_asamalari[secilen_sil_grup]
                        
                        ortak_veriyi_kaydet()
                        st.success(f"'{secilen_sil_grup}' grubu sistemden başarıyla silindi!")
                        st.rerun()
            else:
                st.info(f"{aktif_asama} için silinecek herhangi bir grup bulunmuyor.")

            st.markdown("---")

            st.markdown("### 💾 Yedekleme Paneli")
            c_sv, c_ld = st.columns(2)
            with c_sv:
                export_data = {
                    "skor_tablosu": st.session_state.skor_tablosu.to_dict(orient="records"),
                    "mac_programi": st.session_state.mac_programi.to_dict(orient="records"),
                    "takim_kadrolari": st.session_state.takim_kadrolari,
                    "grup_formatlari": st.session_state.get("grup_formatlari", {}),
                    "grup_kategorileri": st.session_state.get("grup_kategorileri", {}),
                    "grup_asamalari": st.session_state.get("grup_asamalari", {}),
                    "duyuru_metni": st.session_state.duyuru_metni,
                    "takim_havuzu": st.session_state.get("takim_havuzu", {})
                }
                st.download_button("📥 Turnuva Veritabanını İndir (.json)", data=json.dumps(export_data, ensure_ascii=False, indent=4), file_name="tenis_grup_turnuva_yedek.json", mime="application/json")
            with c_ld:
                up_file = st.file_uploader("Geri Yüklemek İçin Yedek Dosyası Seçin:", type=["json"])
                if up_file is not None and st.button("📤 Seçilen Yedeği Sisteme Entegre Et"):
                    try:
                        d = json.load(up_file)
                        st.session_state.skor_tablosu = pd.DataFrame(d["skor_tablosu"])
                        st.session_state.mac_programi = pd.DataFrame(d["mac_programi"])
                        st.session_state.takim_kadrolari = d["takim_kadrolari"]
                        st.session_state.grup_formatlari = d.get("grup_formatlari", {})
                        st.session_state.grup_kategorileri = d.get("grup_kategorileri", {})
                        st.session_state.grup_asamalari = d.get("grup_asamalari", {})
                        st.session_state.duyuru_metni = d.get("duyuru_metni", "")
                        st.session_state.takim_havuzu = d.get("takim_havuzu", {})
                        ortak_veriyi_kaydet()
                        st.success("Yedek başarıyla yüklendi!")
                        st.rerun()
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
                    if os.path.exists(VERI_DOSYASI): os.remove(VERI_DOSYASI)
                    if os.path.exists(BELGELER_KLASORU): shutil.rmtree(BELGELER_KLASORU)
                    st.session_state.clear()
                    st.session_state.confirm_reset = False
                    st.success("Tüm veritabanı başarıyla temizlendi!")
                    st.rerun()
                if col_hayir.button("❌ Vazgeç"):
                    st.session_state.confirm_reset = False
                    st.rerun()
