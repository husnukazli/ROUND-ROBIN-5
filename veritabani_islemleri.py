import os
import json
import pandas as pd
import uuid
import base64
import streamlit as st
from supabase import create_client, Client

SISTEM_KLASORU = os.path.dirname(os.path.abspath(__file__))
BELGELER_KLASORU = os.path.join(SISTEM_KLASORU, "turnuva_belgeleri")

if not os.path.exists(BELGELER_KLASORU):
    os.makedirs(BELGELER_KLASORU)

@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.warning(f"⚠️ Supabase bağlantısı kurulamadı ({e}). Çevrimdışı moda geçmeniz gerekebilir.")
        return None

supabase = init_supabase()

def safe_val(val, default=""):
    if pd.isna(val) or val is None: return default
    return val

def safe_int(val, default=0):
    if pd.isna(val) or val is None or val == "": return default
    try: return int(val)
    except: return default

# 🚀 HIZLANDIRMA: Opsiyonel 'guncellenen_mac_idleri' parametresi eklendi
def ortak_veriyi_kaydet(guncellenen_mac_idleri=None):
    mac_kayitlari = []
    
    if not st.session_state.skor_tablosu.empty:
        # 1. Önce ID'si olmayan yeni maçlar varsa (ilk kurulum) onlara UUID ata
        missing_id_mask = st.session_state.skor_tablosu['id'].isna() | (st.session_state.skor_tablosu['id'] == "")
        if missing_id_mask.any():
            for idx in st.session_state.skor_tablosu[missing_id_mask].index:
                st.session_state.skor_tablosu.at[idx, 'id'] = str(uuid.uuid4())
                
        # 2. Eğer özel olarak güncellenen ID'ler verildiyse, sadece onları filtrele (Kurye Mantığı)
        df_islem = st.session_state.skor_tablosu
        if guncellenen_mac_idleri:
            df_islem = df_islem[df_islem['id'].isin(guncellenen_mac_idleri)]
            
        # Sadece filtrelenmiş (veya tüm) satırları Supabase formatına çevir
        for idx, row in df_islem.iterrows():
            mac_kayitlari.append({
                "id": str(row.get("id")),
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
        "grup_statuleri": st.session_state.get("grup_statuleri", {}),
        "takim_pinleri": st.session_state.get("takim_pinleri", {}),
        "esame_kasasi": st.session_state.get("esame_kasasi", {}),
        "esame_onayli": st.session_state.get("esame_onayli", {}),
        "mac_programi": mp_records,
        "hakem_listesi": st.session_state.get("hakem_listesi", []),
        "hakem_pinleri": st.session_state.get("hakem_pinleri", {}),
        "grup_gun_takvimi": st.session_state.get("grup_gun_takvimi", {}),
        "yayinlanan_gunler": st.session_state.get("yayinlanan_gunler", {})
    }
    
    ayarlar["sistem_kilitli"] = st.session_state.get("sistem_kilitli", False)
    cevrimdisi = st.session_state.get("cevrimdisi_mod", False)
    
    if cevrimdisi:
        cevrimdisi_veri = {"maclar": st.session_state.skor_tablosu.to_dict('records'), "ayarlar": ayarlar}
        try:
            yerel_dosya = os.path.join(SISTEM_KLASORU, "cevrimdisi_veritabani.json")
            with open(yerel_dosya, "w", encoding="utf-8") as f:
                json.dump(cevrimdisi_veri, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            st.error(f"Yerel (çevrimdışı) kayıt hatası: {e}")
            return False
    else:
        if not supabase: return False
        try:
            # 🚀 GÜVENLİK VE YAZMA SINIRI: Verileri 500'lük paketler (chunk) halinde gönder
            if mac_kayitlari:
                chunk_size = 500
                for i in range(0, len(mac_kayitlari), chunk_size):
                    chunk = mac_kayitlari[i:i + chunk_size]
                    supabase.table("maclar").upsert(chunk).execute()
                    
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
            except Exception as e:
                st.error(f"⚠️ Yerel (çevrimdışı) veritabanı okunamadı: {e}. Turnuva verileri boş görünüyor olabilir!")
    else:
        if supabase:
            try:
                res = supabase.table("turnuva_ayarlari").select("*").eq("id", 1).execute()
                if res.data: data = res.data[0]
                
                # 🚀 SUPABASE OKUMA SINIRI: 1000'erli paketler halinde tüm veriyi çeken döngü
                all_matches = []
                start = 0
                limit = 1000
                while True:
                    maclar_res = supabase.table("maclar").select("*").range(start, start + limit - 1).execute()
                    if not maclar_res.data:
                        break
                    all_matches.extend(maclar_res.data)
                    # Gelen veri limitin altındaysa son sayfaya gelinmiştir, döngüyü kır
                    if len(maclar_res.data) < limit:
                        break
                    start += limit
                
                if all_matches:
                    maclar_data = all_matches

            except Exception as e:
                st.error(f"⚠️ Supabase'ten veri okunamadı: {e}. Turnuva verileri boş görünüyor olabilir!")

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
        st.session_state.grup_statuleri = data.get("grup_statuleri", {})
        st.session_state.takim_pinleri = data.get("takim_pinleri", {})
        st.session_state.esame_kasasi = data.get("esame_kasasi", {})
        st.session_state.esame_onayli = data.get("esame_onayli", {})
        st.session_state.hakem_listesi = data.get("hakem_listesi", [])
        st.session_state.hakem_pinleri = data.get("hakem_pinleri", {})
        st.session_state.grup_gun_takvimi = data.get("grup_gun_takvimi", {})
        st.session_state.yayinlanan_gunler = data.get("yayinlanan_gunler", {})
    
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
