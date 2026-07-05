# --- ESAME HİYERARŞİSİ UYARI KONTROLÜ (KAYDI ENGELLEMEZ) ---
            eslesme_dict = {}
            for idx, g_row in form_verileri.items():
                row_data = df_gun.loc[idx]
                eslesme = row_data["Eşleşme"]
                brans = row_data["Branş"]
                
                if eslesme not in eslesme_dict:
                    eslesme_dict[eslesme] = {
                        "T1": {"isim": row_data["Takım 1"], "secimler": {}}, 
                        "T2": {"isim": row_data["Takım 2"], "secimler": {}}
                    }
                
                eslesme_dict[eslesme]["T1"]["secimler"][brans] = g_row["T1_Oyuncu"]
                eslesme_dict[eslesme]["T2"]["secimler"][brans] = g_row["T2_Oyuncu"]
            
            grup_kadro_dict = st.session_state.takim_kadrolari.get(secilen_grup, {})
            for eslesme, data in eslesme_dict.items():
                for team_key in ["T1", "T2"]:
                    takim_ismi = data[team_key]["isim"]
                    havuz = grup_kadro_dict.get(takim_ismi, [])
                    secimler = data[team_key]["secimler"]
                    
                    # Oyuncu isimlerini çekiyoruz
                    o1 = secimler.get("1. Tekler")
                    o2 = secimler.get("2. Tekler")
                    o3 = secimler.get("3. Tekler")
                    
                    r1 = havuz.index(o1) if o1 in havuz else -1
                    r2 = havuz.index(o2) if o2 in havuz else -1
                    r3 = havuz.index(o3) if o3 in havuz else -1
                    
                    uyarilar = []
                    
                    # YENİ MANTIK (Tersten Sıralama): 
                    # 1. Tekler en alt sırada (yüksek indeks), 3. Tekler en üst sırada (düşük indeks) olmalı.
                    # Beklenen geçerli durum: r1 > r2 > r3
                    
                    if r1 != -1 and r2 != -1 and r1 <= r2:
                        uyarilar.append(f"1. Tekler ({o1}), 2. Tekler ({o2}) oyuncusundan listede daha alt sırada yer almalıdır.")
                    if r2 != -1 and r3 != -1 and r2 <= r3:
                        uyarilar.append(f"2. Tekler ({o2}), 3. Tekler ({o3}) oyuncusundan listede daha alt sırada yer almalıdır.")
                    if r1 != -1 and r3 != -1 and r2 == -1 and r1 <= r3:
                        uyarilar.append(f"1. Tekler ({o1}), 3. Tekler ({o3}) oyuncusundan listede daha alt sırada yer almalıdır.")
                        
                    if uyarilar:
                        # Uyarıları alt alta maddeler halinde yazdırarak okunabilirliği artırıyoruz
                        hata_mesaji = "\n".join([f"• {u}" for u in uyarilar])
                        st.warning(f"⚠️ **Takım İçi Sıralama Uyarısı ({takim_ismi} | Eşleşme: {eslesme}):**\n\n{hata_mesaji}\n\n*(Kayıt işlemi yapılabilir, bu sadece bilgi uyarısıdır.)*")
            # --- KONTROL BİTİŞ ---
