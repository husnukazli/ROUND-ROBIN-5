import os
import re
from fpdf import FPDF

FONT_YUKLENDI = os.path.exists("arial.ttf")
FONT_BOLD_YUKLENDI = os.path.exists("arialbd.ttf")

def dogal_sirala(liste):
    def _natural_keys(text):
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]
    return sorted(liste, key=_natural_keys)

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

def generate_combined_standings_pdf(gruplar_dict, manuel_gruplar=None):
    if manuel_gruplar is None:
        manuel_gruplar = []
        
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    setup_pdf_fonts(pdf)
    
    for grup_adi, df in gruplar_dict.items():
        satir_sayisi = len(df)
        
        ekstra_pay = 10 if grup_adi in manuel_gruplar else 0
        gerekli_yukseklik = 10 + 8 + (satir_sayisi * 8) + 10 + ekstra_pay 
        
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
                
        if grup_adi in manuel_gruplar:
            pdf.ln(2)
            apply_font(pdf, bold=True, size=9)
            pdf.set_text_color(200, 50, 50)
            pdf.cell(0, 6, to_pdf_text("* Not: Bu grupta averaj eşitliği veya Başhakem kararıyla Manuel Sıralama uygulanmıştır."), ln=True, align='L')
            pdf.set_text_color(0, 0, 0)
        
        pdf.ln(5)
    return get_pdf_bytes(pdf)

def _klasman_sayfasi_ciz(pdf, kategori_adi, birinciler_liste, ikinciler_liste, ligde_kalanlar, dusenler):
    apply_font(pdf, bold=True, size=16)
    pdf.cell(0, 8, to_pdf_text("TÜRKİYE TENİS FEDERASYONU"), ln=True, align='C')
    apply_font(pdf, bold=False, size=12)
    pdf.cell(0, 6, to_pdf_text("Takım Şampiyonası Resmi Sonuç Bildirgesi"), ln=True, align='C')
    pdf.line(10, pdf.get_y()+2, 200, pdf.get_y()+2)
    pdf.ln(10)

    apply_font(pdf, bold=True, size=14)
    pdf.cell(0, 10, to_pdf_text(f"KATEGORİ: {kategori_adi.upper()} - NİHAİ KLASMAN"), ln=True, align='C')
    pdf.ln(5)

    current_rank = 1

    if birinciler_liste:
        pdf.set_fill_color(220, 220, 220)
        apply_font(pdf, bold=True, size=11)
        pdf.cell(0, 8, to_pdf_text("ŞAMPİYONLUK KÜRSÜSÜ"), border=1, ln=True, fill=True, align='L')
        apply_font(pdf, bold=False, size=11)
        pdf.ln(2)
        for takim in birinciler_liste:
            unvan = ""
            if current_rank == 1: unvan = " (Şampiyon)"
            elif current_rank == 2: unvan = " (İkinci)"
            elif current_rank == 3: unvan = " (Üçüncü)"
            elif current_rank == 4: unvan = " (Dördüncü)"
            pdf.cell(0, 7, to_pdf_text(f"  {current_rank}. Sıra: {takim}{unvan}"), ln=True)
            current_rank += 1
        pdf.ln(5)

    if ikinciler_liste:
        pdf.set_fill_color(235, 235, 235)
        apply_font(pdf, bold=True, size=11)
        pdf.cell(0, 8, to_pdf_text("İKİNCİLER GRUBU (Klasman)"), border=1, ln=True, fill=True, align='L')
        apply_font(pdf, bold=False, size=11)
        pdf.ln(2)
        for takim in ikinciler_liste:
            pdf.cell(0, 7, to_pdf_text(f"  {current_rank}. Sıra: {takim}"), ln=True)
            current_rank += 1
        pdf.ln(5)

    if ligde_kalanlar:
        pdf.set_fill_color(245, 245, 245)
        apply_font(pdf, bold=True, size=11)
        pdf.cell(0, 8, to_pdf_text("LİGDE KALANLAR (Play-Out Üst Sıralar)"), border=1, ln=True, fill=True, align='L')
        apply_font(pdf, bold=False, size=11)
        pdf.ln(2)
        for takim in dogal_sirala(ligde_kalanlar):
            pdf.cell(0, 7, to_pdf_text(f"  - {takim}"), ln=True)
        pdf.ln(5)

    if dusenler:
        pdf.set_fill_color(245, 245, 245)
        apply_font(pdf, bold=True, size=11)
        pdf.cell(0, 8, to_pdf_text("LİGDEN DÜŞENLER (Play-Out Alt Sıralar)"), border=1, ln=True, fill=True, align='L')
        apply_font(pdf, bold=False, size=11)
        pdf.ln(2)
        for takim in dogal_sirala(dusenler):
            pdf.cell(0, 7, to_pdf_text(f"  - {takim}"), ln=True)


def generate_klasman_pdf(kategori_adi, birinciler_liste, ikinciler_liste, ligde_kalanlar, dusenler):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    setup_pdf_fonts(pdf)
    _klasman_sayfasi_ciz(pdf, kategori_adi, birinciler_liste, ikinciler_liste, ligde_kalanlar, dusenler)
    return get_pdf_bytes(pdf)

def generate_toplu_klasman_pdf(kategoriler_verisi):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    setup_pdf_fonts(pdf)

    for kat_adi, veriler in kategoriler_verisi.items():
        pdf.add_page()
        _klasman_sayfasi_ciz(
            pdf, kat_adi,
            veriler.get("birinciler", []),
            veriler.get("ikinciler", []),
            veriler.get("ligde_kalanlar", []),
            veriler.get("dusenler", [])
        )

    return get_pdf_bytes(pdf)

def draw_matrix_pdf(grup_adi, takimlar, matrix):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    setup_pdf_fonts(pdf)
    
    apply_font(pdf, bold=True, size=14)
    pdf.cell(0, 8, to_pdf_text(f"{grup_adi} - Takım Maçları Matrisi"), ln=True, align='C')
    
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
            val = ""
            if t1 in matrix.index and t2 in matrix.columns:
                val = str(matrix.at[t1, t2])
            if val and val != "nan":
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
        
        current_x = x_start
        for t2 in takimlar:
            current_x += col_width
            val = ""
            if t1 in matrix.index and t2 in matrix.columns:
                val = str(matrix.at[t1, t2])
            
            pdf.rect(current_x, y_start, col_width, row_height)
            pdf.set_xy(current_x, y_start + 2.5)
            
            if val == "X":
                pdf.set_xy(current_x, y_start + (row_height/2) - 2)
                apply_font(pdf, bold=True, size=11)
                pdf.cell(col_width, 4, "X", align='C')
            elif val != "" and val != "nan":
                lines = val.split('\n')
                apply_font(pdf, bold=True, size=10.5)
                pdf.cell(col_width, 4.5, to_pdf_text(lines[0]), align='C', ln=2)
                apply_font(pdf, bold=False, size=7.5)
                for line in lines[1:]:
                    pdf.cell(col_width, 4, to_pdf_text(line), align='C', ln=2)
        
        pdf.set_xy(10, y_start + row_height)
        
    return get_pdf_bytes(pdf)

def generate_mac_sonuc_belgesi(eslesmeler_listesi):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    setup_pdf_fonts(pdf)
    
    for eslesme in eslesmeler_listesi:
        pdf.add_page() 
        
        grup_adi = eslesme.get("Grup", "")
        tarih = eslesme.get("Tarih", "")
        saat = eslesme.get("Maç Saati", "")
        kort = eslesme.get("Kort", "")
        takim1 = eslesme.get("Takım 1", "")
        takim2 = eslesme.get("Takım 2", "")
        hakem = eslesme.get("Hakem", "")
        alt_maclar = eslesme.get("Alt Maclar", [])
        t1_kadro = eslesme.get("T1_Kadro", [])
        t2_kadro = eslesme.get("T2_Kadro", [])
        
        # --- 1. ÜST BİLGİ ALANI (Saat Sol, Grup Orta, Kort Sağ, Hakem Sağ Alt) ---
        apply_font(pdf, bold=True, size=14)
        y_header = pdf.get_y()
        
        # Sol: Saat
        pdf.set_xy(10, y_header)
        saat_metni = f"Saat: {saat}" if saat else "Saat: ...."
        pdf.cell(60, 8, to_pdf_text(saat_metni), ln=0, align='L')
        
        # Orta: Grup Adı
        pdf.set_xy(10, y_header)
        pdf.cell(190, 8, to_pdf_text(grup_adi), ln=0, align='C')
        
        # Sağ: Kort
        pdf.set_xy(140, y_header)
        kort_metni = f"Kort: {kort}" if kort else "Kort: ...."
        pdf.cell(60, 8, to_pdf_text(kort_metni), ln=1, align='R')
        
        # Alt Satır (Tarih Orta, Hakem Sağ)
        y_subheader = pdf.get_y()
        apply_font(pdf, bold=True, size=12) 
        
        # Orta: Tarih
        pdf.set_xy(10, y_subheader)
        if tarih:
            pdf.cell(190, 6, to_pdf_text(tarih), ln=0, align='C')
        
        # Sağ Alt: Hakem
        pdf.set_xy(140, y_subheader)
        hakem_isim = hakem if hakem and hakem != "Atanmadı" else ".................."
        pdf.cell(60, 6, to_pdf_text(f"Hakem: {hakem_isim}"), ln=1, align='R')
            
        pdf.ln(6)
        
        # --- 2. TAKIMLAR VE BÜYÜTÜLMÜŞ SKOR KUTUSU ---
        apply_font(pdf, bold=True, size=12)
        pdf.cell(65, 8, to_pdf_text(f"[  ]   {takim1}"), ln=0, align='L')
        pdf.cell(65, 8, to_pdf_text(f"[  ]   {takim2}"), ln=0, align='L')
        # Skor kutuları büyütüldü
        pdf.cell(60, 8, to_pdf_text("SKOR: [        ] - [        ]"), ln=1, align='R')
        
        pdf.ln(3)
        
        apply_font(pdf, bold=True, size=10)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(30, 8, to_pdf_text("Maç Türü"), border=1, fill=True, align='C')
        pdf.cell(50, 8, to_pdf_text("1. Takım Oyuncusu"), border=1, fill=True, align='C')
        pdf.cell(50, 8, to_pdf_text("2. Takım Oyuncusu"), border=1, fill=True, align='C')
        pdf.cell(15, 8, to_pdf_text("1. S"), border=1, fill=True, align='C')
        pdf.cell(15, 8, to_pdf_text("2. S"), border=1, fill=True, align='C')
        pdf.cell(15, 8, to_pdf_text("3. S"), border=1, fill=True, align='C')
        pdf.cell(15, 8, to_pdf_text("Skor"), border=1, fill=True, align='C')
        pdf.ln()
        
        apply_font(pdf, bold=False, size=10)
        
        # ==============================================================================
        # === BAŞLANGIÇ: MAÇ TÜRÜ MANTIK DEĞİŞİKLİĞİ ===
        # ==============================================================================
        if not alt_maclar:
            alt_maclar = [{"Branş": "2. Tekler"}, {"Branş": "1. Tekler"}, {"Branş": "Çiftler"}]
            
        is_beslik_format = len(alt_maclar) > 3
            
        for mac in alt_maclar:
            brans = mac.get("Branş", "")
            
            alt_etiket = ""
            if is_beslik_format:
                if "3. Tekler" in brans: alt_etiket = "(1 Nolu)"
                elif "2. Tekler" in brans: alt_etiket = "(2 Nolu)"
                elif "1. Tekler" in brans: alt_etiket = "(3 Nolu)"
                elif "2. Çiftler" in brans: alt_etiket = "(Sıra Top. Yüksek)"
                elif "1. Çiftler" in brans: alt_etiket = "(Sıra Top. Düşük)"
            else:
                if "2. Tekler" in brans: alt_etiket = "(1 Nolu)"
                elif "1. Tekler" in brans: alt_etiket = "(2 Nolu)"
                # Çiftler için alt etiket boş kalacak
                
            brans_metni = f"{brans}\n{alt_etiket}" if alt_etiket else brans
            
            is_ciftler = "Çiftler" in brans
            satir_h = 16 if is_ciftler else 12 
            
            x = pdf.get_x()
            y = pdf.get_y()
        # ==============================================================================
        # === BİTİŞ: MAÇ TÜRÜ MANTIK DEĞİŞİKLİĞİ ===
        # ==============================================================================
            
            pdf.rect(x, y, 30, satir_h)
            pdf.set_xy(x, y + (satir_h/2) - 4)
            
            # Çiftler alt yazısı uzun olabileceği için fontu ufaltalım
            if is_ciftler:
                apply_font(pdf, bold=False, size=7.5)
            else:
                apply_font(pdf, bold=False, size=9)
                
            pdf.multi_cell(30, 4, to_pdf_text(brans_metni), align='C')
            apply_font(pdf, bold=False, size=10) # Geri al
            
            pdf.rect(x + 30, y, 50, satir_h)
            pdf.rect(x + 80, y, 50, satir_h)
            
            if is_ciftler:
                pdf.set_xy(x + 30, y)
                pdf.cell(50, 8, to_pdf_text(" [  ] "), border='B', align='L')
                pdf.set_xy(x + 30, y + 8)
                pdf.cell(50, 8, to_pdf_text(""), border=0, align='L')
                
                pdf.set_xy(x + 80, y)
                pdf.cell(50, 8, to_pdf_text(" [  ] "), border='B', align='L')
                pdf.set_xy(x + 80, y + 8)
                pdf.cell(50, 8, to_pdf_text(""), border=0, align='L')
            else:
                pdf.set_xy(x + 30, y)
                pdf.cell(50, satir_h, to_pdf_text(" [  ] "), align='L')
                
                pdf.set_xy(x + 80, y)
                pdf.cell(50, satir_h, to_pdf_text(" [  ] "), align='L')
                
            pdf.set_xy(x + 130, y)
            pdf.rect(x + 130, y, 15, satir_h)
            pdf.rect(x + 145, y, 15, satir_h)
            pdf.rect(x + 160, y, 15, satir_h)
            pdf.rect(x + 175, y, 15, satir_h)
            
            pdf.set_y(y + satir_h)
            
        pdf.ln(6) 
        
        # --- 4. OYUNCU LİSTELERİ ---
        apply_font(pdf, bold=True, size=9)
        pdf.cell(95, 5, to_pdf_text(f"{takim1} Oyuncu Listesi:"), align='L')
        pdf.cell(95, 5, to_pdf_text(f"{takim2} Oyuncu Listesi:"), align='L')
        pdf.ln(5)
        
        apply_font(pdf, bold=False, size=8.5)
        max_kadro_len = max(len(t1_kadro), len(t2_kadro)) if (t1_kadro or t2_kadro) else 1
        for i in range(max_kadro_len):
            p1 = f"{i+1}. {t1_kadro[i]}" if i < len(t1_kadro) else ""
            p2 = f"{i+1}. {t2_kadro[i]}" if i < len(t2_kadro) else ""
            pdf.cell(95, 5, to_pdf_text(p1), align='L')
            pdf.cell(95, 5, to_pdf_text(p2), align='L')
            pdf.ln(5)
            
        pdf.ln(8) 
        
        # --- 5. KAZANAN TAKIM VE BÜYÜTÜLMÜŞ GENEL SKOR KUTUSU ---
        apply_font(pdf, bold=True, size=11)
        pdf.cell(130, 8, to_pdf_text("KAZANAN TAKIM: ..........................................................................."), ln=0)
        pdf.cell(60, 8, to_pdf_text("GENEL SKOR: [        ] - [        ]"), ln=1, align='R')
        
        pdf.ln(10) 
        
        apply_font(pdf, bold=True, size=10)
        pdf.cell(63, 5, to_pdf_text(f"{takim1} Kaptanı"), align='C')
        pdf.cell(64, 5, to_pdf_text("Müsabaka Hakemi"), align='C')
        pdf.cell(63, 5, to_pdf_text(f"{takim2} Kaptanı"), align='C')
        pdf.ln(5)
        
        apply_font(pdf, bold=False, size=9)
        pdf.cell(63, 5, to_pdf_text("İmza"), align='C')
        hakem_isim = hakem if hakem and hakem != "Atanmadı" else "İmza"
        pdf.cell(64, 5, to_pdf_text(hakem_isim), align='C')
        pdf.cell(63, 5, to_pdf_text("İmza"), align='C')
        
        # --- 6. İMZALAR İLE NOTLAR ARASINDAKİ BOŞLUĞU AÇMA ---
        pdf.ln(30) # İmza atmak için rahatça 3 cm boşluk bırakıldı
        
        apply_font(pdf, bold=True, size=10)
        pdf.cell(0, 6, to_pdf_text("NOTLAR:"), ln=True)
        pdf.set_font(style="")
        for _ in range(3):
            pdf.cell(0, 6, to_pdf_text("........................................................................................................................................................................................................"), ln=True)

    return get_pdf_bytes(pdf)
# ==============================================================================
# === BİTİŞ: MAÇ SONUÇ BELGESİ (PDF) GÜNCELLEMESİ ===
# ==============================================================================
