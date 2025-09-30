import streamlit as st

st.title("🔵 Simulateur Gains CO₂ – GRDF")

batiment = st.selectbox("Type de bâtiment", ["Maison individuelle", "Appartement", "Tertiaire"])
solution_avant = st.text_input("Solution AVANT rénovation")
solution_apres = st.text_input("Solution APRÈS rénovation")
conso = st.number_input("Consommation avant (kWh PCI/an)", min_value=1000, value=20000)
gaz_vert = st.slider("% Gaz vert", 0, 100, 0)

FE_GAZ, FE_ELEC, FE_BIOMETH = 0.239, 0.058, 0.0417
gain_ener = -0.25  # provisoire

conso_apres = conso * (1 + gain_ener)
emissions_avant = conso/1000 * FE_GAZ
fe_mix = FE_GAZ*(1-gaz_vert/100) + FE_BIOMETH*(gaz_vert/100)
emissions_apres = conso_apres/1000 * fe_mix
gain_co2 = emissions_avant - emissions_apres

st.metric("Gain CO₂ (t/an)", f"{gain_co2:.2f}")
