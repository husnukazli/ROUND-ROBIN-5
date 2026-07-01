# --- TAB 1: GRUP AYARLARI ---
with tab1:
    st.subheader("Grup Takımlarını Seç, Kadroları Gir ve Eşleşmeleri Oluştur")
    grup_tipi = st.radio("Kurulacak Grup Tipini Seçin:", ["4'lü Grup", "5'li Grup"], horizontal=True)
    grup_adi = st.text_input("Grup Adı", placeholder="Örn: A Grubu")
    
    beklenen_sayi = 4 if grup_tipi == "4'lü Grup" else 5
    takim_listesi = st.text_area(f"Takım İsimlerini Alt Alta Yazın (Tam olarak {beklenen_sayi} Takım Olmalı)")
    
    # Hizalaması milimetrik olarak düzeltilen 102. satır burasıdır:
    takimlar = [t.strip() for t in takim_listesi.split('\n') if t.strip()]
    
    grup_kadrolari = {}
    kadro_hata = False
    
    if len(takimlar) == beklenen_sayi:
        st.markdown("---")
        st.markdown("### 👥 Oyuncu Kadrolarını Girin (En Fazla 10 Oyuncu, Her Satıra Bir İsim)")
        cols = st.columns(beklenen_sayi)
        for i, t in enumerate(takimlar):
            with cols[i]:
                oyuncular_raw = st.text_area(f"✍️ {t} Kadrosu", key=f"input_kadro_{t}", height=150, placeholder="Oyuncu 1\nOyuncu 2")
                oyuncu_listesi = [o.strip() for o in oyuncular_raw.split('\n') if o.strip()]
                if len(oyuncu_listesi) > 10:
                    st.error(f"❌ {t} takımı 10 oyuncuyu aşamaz! ({len(oyuncu_listesi)} girildi)")
                    kadro_hata = True
                grup_kadrolari[t] = oyuncu_listesi if oyuncu_listesi else ["Belirtilmedi"]

    if st.button("🚀 Eşleşmeleri ve Kadroları Oluştur"):
        if not grup_adi:
            st.error("Lütfen bir grup adı girin.")
        elif not st.session_state.skor_tablosu.empty and grup_adi in st.session_state.skor_tablosu['Grup'].unique():
            st.error(f"❌ Hata: '{grup_adi}' isminde bir grup zaten mevcut!")
        elif len(takimlar) != beklenen_sayi:
            st.error(f"Hata: {beklenen_sayi} takım girmelisiniz. (Şu an: {len(takimlar)})")
        elif kadro_hata:
            st.error("Lütfen 10 oyuncu sınırını aşan takımları düzeltin.")
        else:
            if grup_adi not in st.session_state.takim_kadrolari:
                st.session_state.takim_kadrolari[grup_adi] = grup_kadrolari
            
            yeni_maclar = eslesmeleri_olustur(grup_adi, takimlar, grup_tipi)
            yeni_df = pd.DataFrame(yeni_maclar)
            st.session_state.skor_tablosu = pd.concat([st.session_state.skor_tablosu, yeni_df], ignore_index=True)
            st.session_state.skor_tablosu.index = range(1, len(st.session_state.skor_tablosu) + 1)
            st.success(f"{grup_adi} ve oyuncu kadroları başarıyla oluşturuldu!")
            st.rerun()
