import os
import re
import pandas as pd
import streamlit as st
import uuid

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
    html = '<div style="overflow-x: auto; white-space: nowrap; padding-bottom: 10px;">'
    html += '<table style="width:100%; border-collapse: collapse; text-align:center; font-family: sans-serif; font-size: 14px;">'
    html += '<tr style="background-color: rgba(128,128,128,0.1);">'
    html += '<th style="border: 1px solid rgba(128,128,128,0.3); padding: 10px;">Takımlar</th>'
    for t in takimlar:
        html += f'<th style="border: 1px solid rgba(128,128,128,0.3); padding: 10px;">{t}</th>'
    html += '</tr>'

    on_hesap_sonuclari = {}
    for (t_a, t_b), group_df in df_grup.groupby(['Takım 1', 'Takım 2']):
        match_key = tuple(sorted([t_a, t_b]))
        if match_key not in on_hesap_sonuclari:
            aradaki_maclar = df_grup[((df_grup['Takım 1'] == match_key[0]) & (df_grup['Takım 2'] == match_key[1])) | 
                                     ((df_grup['Takım 1'] == match_key[1]) & (df_grup['Takım 2'] == match_key[0]))]
            stats = hesapla_tum_puan_durumu(aradaki_maclar)
            on_hesap_sonuclari[match_key] = stats

    for t1 in takimlar:
        html += f'<tr><td style="border: 1px solid rgba(128,128,128,0.3); padding: 10px; font-weight: bold; background-color: rgba(128,128,128,0.1);">{t1}</td>'
        for t2 in takimlar:
            if t1 == t2:
                html += '<td style="border: 1px solid rgba(128,128,128,0.3); padding: 10px; background-color: rgba(128,128,128,0.2);"><b>X</b></td>'
            else:
                match_key = tuple(sorted([t1, t2]))
                matches = df_grup[((df_grup['Takım 1'] == t1) & (df_grup['Takım 2'] == t2)) | ((df_grup['Takım 1'] == t2) & (df_grup['Takım 2'] == t1))]
                
                if matches.empty:
                    html += '<td style="border: 1px solid rgba(128,128,128,0.3); padding: 10px;"></td>'
                else:
                    temp_stats = on_hesap_sonuclari.get(match_key, pd.DataFrame())
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
    html += '</table></div>'
    return html
    
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
                        t1_set += 1
                        t1_oyun = s1_t1 + s2_t1 + 1
                        t2_oyun = max(0, (s1_t2 + s2_t2) - 1)
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
                            t2_oyun = s1_t2 + s2_t2 + 1
                            t1_oyun = max(0, (s1_t1 + s2_t1) - 1)
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

    def get_singles_win(row, team_idx):
        brans = str(row.get('Branş', '')).lower()
        if "tek" in brans:
            if team_idx == 1 and row['T1_Match_Win'] > row['T2_Match_Win']: return 1
            if team_idx == 2 and row['T2_Match_Win'] > row['T1_Match_Win']: return 1
        return 0

    df['T1_Singles_Win'] = df.apply(lambda r: get_singles_win(r, 1), axis=1)
    df['T2_Singles_Win'] = df.apply(lambda r: get_singles_win(r, 2), axis=1)

    seriler = df.groupby(['Grup', 'Gün', 'Eşleşme', 'Takım 1', 'Takım 2']).agg({
        'T1_Match_Win': 'sum', 'T2_Match_Win': 'sum', 
        'T1_Set_Skor': 'sum', 'T2_Set_Skor': 'sum', 
        'T1_Oyun': 'sum', 'T2_Oyun': 'sum',
        'T1_Match_Point': 'sum', 'T2_Match_Point': 'sum',
        'T1_Singles_Win': 'sum', 'T2_Singles_Win': 'sum'
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
                else: 
                    if r['T1_Singles_Win'] > r['T2_Singles_Win']: return 1, 0
                    elif r['T2_Singles_Win'] > r['T1_Singles_Win']: return 0, 1
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

# ==============================================================================
# 🚀 AKILLI AVERAJ VE ÇOKLU AVERAJ SIRALAMA MOTORU
# ==============================================================================
def sirala_grup_df(grup_df, gp, ham_maclar_df=None):
    if gp in st.session_state.grup_siralamalari and st.session_state.grup_siralamalari[gp]:
        manuel_sira = st.session_state.grup_siralamalari[gp]
        grup_df['Sıra_Degeri'] = grup_df['Takım'].apply(lambda x: manuel_sira.index(x) if x in manuel_sira else 999)
        grup_df = grup_df.sort_values(by=['Sıra_Degeri', 'Galibiyet', 'Maç Av.', 'Set Av.', 'Oyun Av.'], ascending=[True, False, False, False, False]).drop(columns=['Sıra_Degeri'])
        grup_df.index = range(1, len(grup_df) + 1)
        return grup_df

    grup_df = grup_df.copy()
    
    if ham_maclar_df is None and 'skor_tablosu' in st.session_state:
        ham_maclar_df = st.session_state.skor_tablosu[st.session_state.skor_tablosu['Grup'] == gp]

    # --- GRUBUN TAMAMLANMA KONTROLÜ (Skor girilmemiş maç var mı?) ---
    admin_kilidi = st.session_state.get('grup_tamamlandi', {}).get(gp, False)
    grup_bitti_mi = admin_kilidi
    
    if not grup_bitti_mi and ham_maclar_df is not None and not ham_maclar_df.empty:
        biten_mac_sayisi = 0
        for _, r in ham_maclar_df.iterrows():
            d = str(r.get('Durum', 'Tamamlandı'))
            try:
                s1_1, s1_2 = int(r.get('1.Set T1', 0)), int(r.get('1.Set T2', 0))
            except:
                s1_1, s1_2 = 0, 0
                
            if "W/O" in d or "Ret." in d or s1_1 > 0 or s1_2 > 0 or d == "Çift Taraflı W/O":
                biten_mac_sayisi += 1
                
        if biten_mac_sayisi == len(ham_maclar_df):
            grup_bitti_mi = True

    siralanmis_takimlar = []
    kura_gerekir_mesajlari = []
    averaj_mesajlari = []
    grup_averaj_tablolari = {}

    unique_galibiyetler = sorted(grup_df['Galibiyet'].unique(), reverse=True)

    for gal in unique_galibiyetler:
        alt_kumul = grup_df[grup_df['Galibiyet'] == gal]
        
        if len(alt_kumul) <= 1:
            for _, row in alt_kumul.iterrows():
                siralanmis_takimlar.append(row['Takım'])
        
        elif len(alt_kumul) == 2:
            t_list = alt_kumul['Takım'].tolist()
            t1, t2 = t_list[0], t_list[1]
            
            h2h_winner = None
            if ham_maclar_df is not None and not ham_maclar_df.empty:
                aradaki_maclar = ham_maclar_df[
                    ((ham_maclar_df['Takım 1'] == t1) & (ham_maclar_df['Takım 2'] == t2)) | 
                    ((ham_maclar_df['Takım 1'] == t2) & (ham_maclar_df['Takım 2'] == t1))
                ]
                if not aradaki_maclar.empty:
                    stats = hesapla_tum_puan_durumu(aradaki_maclar)
                    if not stats.empty and len(stats) >= 2:
                        r1 = stats[stats['Takım'] == t1].iloc[0]['Galibiyet'] if not stats[stats['Takım'] == t1].empty else 0
                        r2 = stats[stats['Takım'] == t2].iloc[0]['Galibiyet'] if not stats[stats['Takım'] == t2].empty else 0
                        if r1 > r2: h2h_winner = t1
                        elif r2 > r1: h2h_winner = t2

            if h2h_winner:
                loser = t2 if h2h_winner == t1 else t1
                r_w = alt_kumul[alt_kumul['Takım'] == h2h_winner].iloc[0]
                r_l = alt_kumul[alt_kumul['Takım'] == loser].iloc[0]
                
                loser_better_gen = False
                if r_l['Maç Av.'] > r_w['Maç Av.']: loser_better_gen = True
                elif r_l['Maç Av.'] == r_w['Maç Av.'] and r_l['Set Av.'] > r_w['Set Av.']: loser_better_gen = True
                elif r_l['Maç Av.'] == r_w['Maç Av.'] and r_l['Set Av.'] == r_w['Set Av.'] and r_l['Oyun Av.'] > r_w['Oyun Av.']: loser_better_gen = True
                
                if loser_better_gen:
                    averaj_mesajlari.append(f"ℹ️ <b>İkili Averaj Bilgisi:</b> {h2h_winner}, genel averajı {loser} takımından düşük olmasına rağmen kendi aralarındaki maçı kazandığı için üst sıraya yerleştirilmiştir.")
                
                siralanmis_takimlar.append(h2h_winner)
                siralanmis_takimlar.append(loser)
            else:
                sorted_alt = alt_kumul.sort_values(by=['Maç Av.', 'Set Av.', 'Oyun Av.'], ascending=False)
                if len(sorted_alt) == 2 and sorted_alt.iloc[0]['Maç Av.'] == sorted_alt.iloc[1]['Maç Av.'] and sorted_alt.iloc[0]['Set Av.'] == sorted_alt.iloc[1]['Set Av.'] and sorted_alt.iloc[0]['Oyun Av.'] == sorted_alt.iloc[1]['Oyun Av.']:
                    kura_gerekir_mesajlari.append(f"⚠️ {t1} ve {t2} arasında tüm averajlar eşit, kura gerekebilir!")
                for _, row in sorted_alt.iterrows():
                    siralanmis_takimlar.append(row['Takım'])

        else:
            t_list = alt_kumul['Takım'].tolist()
            toplam_takim_sayisi = len(grup_df)
            
            if len(alt_kumul) == toplam_takim_sayisi:
                sorted_alt = alt_kumul.sort_values(by=['Maç Av.', 'Set Av.', 'Oyun Av.'], ascending=False)
                
                t_top = sorted_alt.iloc[0]
                t_bot = sorted_alt.iloc[-1]
                if t_top['Maç Av.'] == t_bot['Maç Av.'] and t_top['Set Av.'] == t_bot['Set Av.'] and t_top['Oyun Av.'] == t_bot['Oyun Av.']:
                    kura_gerekir_mesajlari.append(f"⚠️ Bu grupta tüm takımların genel averajları tamamen eşittir. Kura çekimi gerekmektedir!")
                
                for _, row in sorted_alt.iterrows():
                    siralanmis_takimlar.append(row['Takım'])
            else:
                coklu_averaj_cozuldumu = False
                if ham_maclar_df is not None and not ham_maclar_df.empty:
                    coklu_maclar = ham_maclar_df[
                        ham_maclar_df['Takım 1'].isin(t_list) & ham_maclar_df['Takım 2'].isin(t_list)
                    ]
                    if not coklu_maclar.empty:
                        coklu_stats = hesapla_tum_puan_durumu(coklu_maclar)
                        if not coklu_stats.empty and len(coklu_stats) == len(t_list):
                            sorted_coklu = coklu_stats.sort_values(by=['Galibiyet', 'Maç Av.', 'Set Av.', 'Oyun Av.'], ascending=False)
                            
                            top_gal = sorted_coklu.iloc[0]['Galibiyet']
                            bottom_gal = sorted_coklu.iloc[-1]['Galibiyet']
                            top_mac_av = sorted_coklu.iloc[0]['Maç Av.']
                            bottom_mac_av = sorted_coklu.iloc[-1]['Maç Av.']
                            top_set_av = sorted_coklu.iloc[0]['Set Av.']
                            bottom_set_av = sorted_coklu.iloc[-1]['Set Av.']
                            top_oyun_av = sorted_coklu.iloc[0]['Oyun Av.']
                            bottom_oyun_av = sorted_coklu.iloc[-1]['Oyun Av.']
                            
                            isim_map = {3: "Üçlü", 4: "Dörtlü", 5: "Beşli", 6: "Altılı"}
                            averaj_baslik = isim_map.get(len(t_list), f"{len(t_list)}'li")
                            
                            coklu_sira = sorted_coklu['Takım'].tolist()
                            
                            if top_gal == bottom_gal and top_mac_av == bottom_mac_av and top_set_av == bottom_set_av and top_oyun_av == bottom_oyun_av:
                                kura_gerekir_mesajlari.append(f"⚠️ Bu grupta ({', '.join(t_list)}) {averaj_baslik.lower()} averaj tüm kriterlere rağmen çözülememiştir, kura gerekebilir!")
                                
                                mini_tablo_df = sorted_coklu.drop(columns=['Grup'])
                                mini_tablo_df.index = range(1, len(mini_tablo_df) + 1)
                                grup_averaj_tablolari[f"({', '.join(t_list)}) Takımları {averaj_baslik} Averaj Tablosu (Kör Düğüm)"] = mini_tablo_df
                            else:
                                # --- DÜZELTME: Kısmi Eşitlikte Doğrudan Kuraya Yönlendirme ---
                                for idx in range(len(sorted_coklu) - 1):
                                    t1_k = sorted_coklu.iloc[idx]
                                    t2_k = sorted_coklu.iloc[idx + 1]
                                    if t1_k['Maç Av.'] == t2_k['Maç Av.'] and t1_k['Set Av.'] == t2_k['Set Av.'] and t1_k['Oyun Av.'] == t2_k['Oyun Av.']:
                                        kura_gerekir_mesajlari.append(f"⚠️ {averaj_baslik} averaj tablosunda {t1_k['Takım']} ve {t2_k['Takım']} takımları ayrışamamıştır. Kural gereği ikili averaja dönülmez, bu iki takım arasında kura çekimi yapılmalıdır.")
                                # -------------------------------------------------------------

                                sira_degisti_mi = False
                                for i in range(len(coklu_sira)):
                                    for j in range(i + 1, len(coklu_sira)):
                                        t_ust = coklu_sira[i]
                                        t_alt = coklu_sira[j]
                                        
                                        r_ust = alt_kumul[alt_kumul['Takım'] == t_ust].iloc[0]
                                        r_alt = alt_kumul[alt_kumul['Takım'] == t_alt].iloc[0]
                                        
                                        alt_daha_iyi = False
                                        if r_alt['Maç Av.'] > r_ust['Maç Av.']: alt_daha_iyi = True
                                        elif r_alt['Maç Av.'] == r_ust['Maç Av.'] and r_alt['Set Av.'] > r_ust['Set Av.']: alt_daha_iyi = True
                                        elif r_alt['Maç Av.'] == r_ust['Maç Av.'] and r_alt['Set Av.'] == r_ust['Set Av.'] and r_alt['Oyun Av.'] > r_ust['Oyun Av.']: alt_daha_iyi = True
                                        
                                        if alt_daha_iyi:
                                            sira_degisti_mi = True
                                            break
                                    if sira_degisti_mi:
                                        break

                                if sira_degisti_mi:
                                    averaj_mesajlari.append(f"ℹ️ <b>{averaj_baslik} Averaj Bilgisi:</b> Bu grupta {', '.join(t_list)} takımları arasında puan eşitliği yaşanmış ve sıralama genel averaja bakılmaksızın <b>kendi aralarındaki maçlara</b> göre yeniden belirlenmiştir.")
                                    mini_tablo_df = sorted_coklu.drop(columns=['Grup'])
                                    mini_tablo_df.index = range(1, len(mini_tablo_df) + 1)
                                    grup_averaj_tablolari[f"({', '.join(t_list)}) Takımları {averaj_baslik} Averaj Tablosu"] = mini_tablo_df

                            for t_adi in coklu_sira:
                                siralanmis_takimlar.append(t_adi)
                            coklu_averaj_cozuldumu = True

                if not coklu_averaj_cozuldumu:
                    sorted_alt = alt_kumul.sort_values(by=['Maç Av.', 'Set Av.', 'Oyun Av.'], ascending=False)
                    for _, row in sorted_alt.iterrows():
                        siralanmis_takimlar.append(row['Takım'])

    grup_df['Sıra_Degeri'] = grup_df['Takım'].apply(lambda x: siralanmis_takimlar.index(x) if x in siralanmis_takimlar else 999)
    grup_df = grup_df.sort_values(by=['Sıra_Degeri']).drop(columns=['Sıra_Degeri'])
    grup_df.index = range(1, len(grup_df) + 1)

    if "kura_uyarilari" not in st.session_state:
        st.session_state.kura_uyarilari = {}
    if kura_gerekir_mesajlari and grup_bitti_mi:
        st.session_state.kura_uyarilari[gp] = " ".join(kura_gerekir_mesajlari)
    elif gp in st.session_state.kura_uyarilari:
        del st.session_state.kura_uyarilari[gp]
        
    if "averaj_bilgileri" not in st.session_state:
        st.session_state.averaj_bilgileri = {}
    if averaj_mesajlari and grup_bitti_mi:
        st.session_state.averaj_bilgileri[gp] = "<br>".join(averaj_mesajlari)
    elif gp in st.session_state.averaj_bilgileri:
        del st.session_state.averaj_bilgileri[gp]
        
    if "grup_averaj_tablolari" not in st.session_state:
        st.session_state.grup_averaj_tablolari = {}
    if grup_averaj_tablolari and grup_bitti_mi:
        st.session_state.grup_averaj_tablolari[gp] = grup_averaj_tablolari
    elif gp in st.session_state.grup_averaj_tablolari:
        del st.session_state.grup_averaj_tablolari[gp]

    return grup_df
