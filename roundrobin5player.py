import streamlit as st

st.set_page_config(page_title="Tenis Turnuva", layout="wide")
st.title("🎾 Tenis Turnuvası Yönetim Sistemi")

# Veriyi saklamak için session_state
if 'takimlar' not in st.session_state:
    st.session_state.takimlar = {f"Grup {i}": ["Takım 1", "Takım 2", "Takım 3", "Takım 4"] for i in range(1, 5)}

tabs = st.tabs(["Grup 1", "Grup 2", "Grup 3", "Grup 4"])

for i, tab in enumerate(tabs):
    grup_id = f"Grup {i+1}"
    with tab:
        st.subheader(f"{grup_id} Takım İsimleri")
        for t in range(4):
            st.session_state.takimlar[grup_id][t] = st.text_input(
                f"Takım {t+1} İsmi", 
                value=st.session_state.takimlar[grup_id][t], 
                key=f"{grup_id}_t{t}"
            )
        
        st.divider()
        st.subheader(f"{grup_id} Maç Programı")
        
        t = st.session_state.takimlar[grup_id]
        program = {
            "1. Gün": [(t[0], t[3]), (t[1], t[2])],
            "2. Gün": [(t[0], t[1]), (t[2], t[3])],
            "3. Gün": [(t[0], t[2]), (t[1], t[3])]
        }
        
        for gun, maclar in program.items():
            with st.expander(f"{gun} Maçları"):
                for m1, m2 in maclar:
                    st.write(f"#### {m1} vs {m2}")
                    # Her maç türü için ayrı bir yapı
                    for mac_turu in ["Tekler 1", "Tekler 2", "Çiftler"]:
                        st.write(f"**{mac_turu}**")
                        c1, c2, c3, c4 = st.columns(4)
                        # Set skorları için girişler
                        c1.text_input(f"Set 1 (Kazanan)", key=f"{grup_id}_{gun}_{m1}_{mac_turu}_s1w", placeholder="6")
                        c2.text_input(f"Set 1 (Kaybeden)", key=f"{grup_id}_{gun}_{m1}_{mac_turu}_s1l", placeholder="4")
                        c3.text_input(f"Set 2 (Kazanan)", key=f"{grup_id}_{gun}_{m1}_{mac_turu}_s2w", placeholder="6")
                        c4.text_input(f"Set 2 (Kaybeden)", key=f"{grup_id}_{gun}_{m1}_{mac_turu}_s2l", placeholder="3")
                        st.markdown("---")
