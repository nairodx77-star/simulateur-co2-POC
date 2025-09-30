import streamlit as st
import pandas as pd
import json
from io import StringIO

# ==============================
# CONFIG / THEME
# ==============================
st.set_page_config(page_title="Simulateur GRDF CO₂", layout="wide")
GRDF_BLUE = "#004595"; GRDF_TEAL = "#06A8A5"; GRDF_GREEN = "#71A950"; GRDF_YELLOW = "#F5A803"; GRDF_GREY = "#87929A"

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1rem; }}
  h1, h2, h3, h4 {{ color: {GRDF_BLUE} !important; }}
  .stMetric > div > div > div {{ color: {GRDF_BLUE}; }}
  .grdf-badge {{ background:{GRDF_TEAL}; color:white; padding:.3rem .6rem; border-radius:.5rem; font-weight:600; display:inline-block; }}
  .gain-hero {{
      text-align:center; margin: 0.8rem 0 1rem 0;
      font-size: 2.1rem; font-weight: 800; color: {GRDF_GREEN};
      line-height: 1.2;
  }}
  .gain-hero small {{ display:block; font-size: 0.9rem; color: {GRDF_GREY}; font-weight:600; }}
</style>
""", unsafe_allow_html=True)

st.title("🔵 Simulateur Gains CO₂ – GRDF")
st.caption("Version JSON (sans Excel) – matrices & facteurs chargés depuis le repo, éditables en ligne.")

# ==============================
# DEFAULTS (si JSON manquants)
# ==============================
DEFAULT_FACTORS = {"FE_GAZ": 0.239, "FE_ELEC": 0.058, "FE_BIOMETH": 0.0417}

DEFAULT_MATRICES = {
  "Maison individuelle": {
    "Chaudière gaz standard >15 ans": {
      "Chaudière gaz THPE": -0.25, "PAC A/E + THPE (hybride)": -0.36, "PAC A/A + THPE": -0.32,
      "PAC gaz": -0.29, "PAC géothermique + THPE": -0.47, "Chaudière bois + THPE": -0.29
    },
    "Chaudière gaz standard neuve": {
      "Chaudière gaz THPE": -0.22, "PAC A/E + THPE (hybride)": -0.31, "PAC A/A + THPE": -0.28,
      "PAC gaz": -0.25, "PAC géothermique + THPE": -0.44
    },
    "Chaudière gaz THPE": {
      "PAC A/E + THPE (hybride)": -0.23, "PAC A/A + THPE": -0.20, "PAC gaz": -0.18, "PAC géothermique + THPE": -0.29
    },
    "PAC A/E + THPE (hybride)": { "PAC A/A + THPE": -0.08, "PAC gaz": -0.06, "PAC géothermique + THPE": -0.12 },
    "PAC A/A + THPE": { "PAC gaz": "NS", "PAC géothermique + THPE": -0.10 },
    "PAC gaz": { "PAC géothermique + THPE": -0.07 },
    "PAC géothermique + THPE": {},
    "Chaudière bois + THPE": { "PAC A/E + THPE (hybride)": -0.09, "PAC géothermique + THPE": -0.11 },
    "Chaudière fioul >15 ans": {
      "Chaudière gaz THPE": -0.30, "PAC A/E + THPE (hybride)": -0.40, "PAC A/A + THPE": -0.36, "PAC géothermique + THPE": -0.53
    },
    "Chaudière fioul THPE": { "Chaudière gaz THPE": -0.19, "PAC A/E + THPE (hybride)": -0.28, "PAC géothermique + THPE": -0.38 }
  },
  "Appartement chauffage indiv": {
    "Chaudière gaz standard >15 ans": { "Chaudière gaz THPE": -0.22, "PAC A/E + THPE (hybride)": -0.34, "PAC A/A + THPE": -0.28, "PAC gaz": -0.25 },
    "Chaudière gaz THPE": { "PAC A/E + THPE (hybride)": -0.20, "PAC A/A + THPE": -0.16 },
    "PAC A/E + THPE (hybride)": { "PAC A/A + THPE": -0.07 },
    "Chaudière fioul >15 ans": { "Chaudière gaz THPE": -0.27, "PAC A/E + THPE (hybride)": -0.37, "PAC A/A + THPE": -0.30 }
  },
  "Appartement chauffage coll": {
    "Chauffage collectif gaz (ancienne)": { "Chaudière gaz THPE collective": -0.20, "PAC sur boucle + THPE": -0.28, "Réseau de chaleur": -0.18 },
    "Chauffage collectif fioul": { "Chaudière gaz THPE collective": -0.30, "PAC sur boucle + THPE": -0.35, "Réseau de chaleur": -0.27 },
    "Chauffage urbain ancien": { "Réseau de chaleur (mix décarboné)": -0.15, "PAC sur boucle + THPE": -0.22 }
  },
  "Bâtiment tertiaire": {
    "Chaudière gaz standard": { "Chaudière gaz THPE": -0.18, "PAC A/E + appoint gaz": -0.25, "PAC eau/eau + appoint": -0.30, "Réseau de chaleur": -0.15 },
    "Chaudière fioul": { "Chaudière gaz THPE": -0.28, "PAC A/E + appoint gaz": -0.36, "PAC eau/eau + appoint": -0.42, "Réseau de chaleur": -0.25 },
    "PAC A/E ancienne": { "PAC A/E + appoint gaz (haute perf)": -0.12, "PAC eau/eau + appoint": -0.18 },
    "Réseau de chaleur ancien": { "Réseau de chaleur (mix décarboné)": -0.12, "PAC eau/eau + appoint": -0.20 }
  }
}

# ==============================
# LOAD JSON FROM REPO (with fallback)
# ==============================
@st.cache_data
def load_json_file(path, default_dict):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_dict

matrices = load_json_file("matrices.json", DEFAULT_MATRICES)
factors  = load_json_file("facteurs.json", DEFAULT_FACTORS)

# ==============================
# ADMIN (éditer / importer / exporter)
# ==============================
with st.expander("⚙️ Admin – matrices & facteurs (JSON)"):
    st.markdown('<span class="grdf-badge">Édition avancée</span>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Matrices", "Facteurs", "Importer/Exporter"])

    with t1:
        txt = st.text_area("Matrices JSON :", value=json.dumps(matrices, indent=2, ensure_ascii=False), height=360)
        if st.button("Mettre à jour (session) – matrices"):
            try:
                matrices = json.loads(txt)
                st.success("Matrices mises à jour (session). Utilisez 'Exporter' pour sauvegarder.")
            except Exception as e:
                st.error(f"JSON invalide : {e}")

    with t2:
        txtf = st.text_area("Facteurs JSON :", value=json.dumps(factors, indent=2, ensure_ascii=False), height=180)
        if st.button("Mettre à jour (session) – facteurs"):
            try:
                factors = json.loads(txtf)
                st.success("Facteurs mis à jour (session). Utilisez 'Exporter' pour sauvegarder.")
            except Exception as e:
                st.error(f"JSON invalide : {e}")

    with t3:
        colA, colB = st.columns(2)
        colA.download_button("⬇️ matrices.json", data=json.dumps(matrices, indent=2, ensure_ascii=False),
                             file_name="matrices.json", mime="application/json")
        colA.download_button("⬇️ facteurs.json", data=json.dumps(factors, indent=2, ensure_ascii=False),
                             file_name="facteurs.json", mime="application/json")
        upM = colB.file_uploader("Importer matrices.json", type="json", key="upM")
        upF = colB.file_uploader("Importer facteurs.json", type="json", key="upF")
        if upM:
            try:
                matrices = json.load(upM); st.success("Matrices importées (session).")
            except Exception as e:
                st.error(f"Import matrices KO : {e}")
        if upF:
            try:
                factors = json.load(upF); st.success("Facteurs importés (session).")
            except Exception as e:
                st.error(f"Import facteurs KO : {e}")

# ==============================
# UI – Saisie
# ==============================
batiments = list(matrices.keys())
if not batiments:
    st.error("Aucun bâtiment disponible. Ajoutez des matrices en Admin.")
    st.stop()

bat = st.selectbox("Type de bâtiment", batiments)
solutions_avant = list(matrices.get(bat, {}).keys())
if not solutions_avant:
    st.error("Aucune solution AVANT pour ce bâtiment.")
    st.stop()

sol_init = st.selectbox("Solution AVANT rénovation", solutions_avant)
solutions_apres = list(matrices[bat].get(sol_init, {}).keys())
if not solutions_apres:
    st.warning("Aucune solution APRÈS pour ce choix. Modifiez 'AVANT' ou complétez les matrices.")
    solutions_apres = ["— aucune —"]
sol_final = st.selectbox("Solution APRÈS rénovation", solutions_apres)

cL, cR = st.columns(2)
conso = cL.number_input("Consommation AVANT (kWh PCI/an)", min_value=1000, value=20000, step=500)
gaz_vert = cR.slider("% de gaz vert (biométhane) au contrat", 0, 100, 0)

hybride = st.radio("Solution APRÈS hybride (répartition conso)", ["Non", "Oui"], index=0)
if hybride == "Oui":
    h1, h2 = st.columns(2)
    part_elec = h1.slider("Répartition ÉLECTRICITÉ (%)", 0, 100, 50)
    part_gaz = 100 - part_elec
    h2.write(f"Répartition GAZ : **{part_gaz}%**")
else:
    part_elec, part_gaz = 0, 100

# ==============================
# Gain énergétique auto + surcharge
# ==============================
def get_gain_auto(b, s_init, s_final):
    try:
        v = matrices[b][s_init][s_final]
        return float(v) if isinstance(v, (int, float)) else 0.0
    except Exception:
        return 0.0

gain_auto = get_gain_auto(bat, sol_init, sol_final)
gA, gB = st.columns(2)
gA.info(f"Gain énergétique auto (cas moyen) : **{gain_auto:.3f}** (ex: -0.25 = -25%)")
gain_user = gB.number_input("Surcharge du % gain (laisser 0 pour auto)", value=0.0, step=0.01, format="%.3f")
gain_ener = gain_user if abs(gain_user) > 1e-9 else gain_auto

# ==============================
# Calculs CO₂
# ==============================
FE_GAZ = float(factors.get("FE_GAZ", DEFAULT_FACTORS["FE_GAZ"]))
FE_ELEC = float(factors.get("FE_ELEC", DEFAULT_FACTORS["FE_ELEC"]))
FE_BIOMETH = float(factors.get("FE_BIOMETH", DEFAULT_FACTORS["FE_BIOMETH"]))

conso_avant_mwh = conso / 1000.0
conso_apres_mwh = conso_avant_mwh * (1.0 + gain_ener)

# Émissions AVANT = 100% gaz naturel
emissions_avant = conso_avant_mwh * FE_GAZ

# Gaz mix APRÈS (biométhane inclus)
fe_gaz_mix = FE_GAZ * (1 - gaz_vert/100.0) + FE_BIOMETH * (gaz_vert/100.0)

def is_pac(label: str) -> bool:
    s = (label or "").lower()
    return ("pac" in s) or ("pompe" in s)

if hybride == "Oui":
    emis_elec = (conso_apres_mwh * (part_elec/100.0)) * FE_ELEC
    emis_gaz  = (conso_apres_mwh * (part_gaz/100.0))  * fe_gaz_mix
    emissions_apres = emis_elec + emis_gaz
else:
    emissions_apres = conso_apres_mwh * FE_ELEC if is_pac(sol_final) else conso_apres_mwh * fe_gaz_mix

gain_co2 = emissions_avant - emissions_apres

# ==============================
# HERO – Gain CO₂ mis en avant
# ==============================
st.markdown(f'<div class="gain-hero">🌿 Gain CO₂ : {gain_co2:.2f} t/an<small>(différence entre émissions AVANT et APRÈS)</small></div>', unsafe_allow_html=True)

# ==============================
# Résultats + Mini-graphe responsive
# ==============================
st.subheader("📊 Résultats détaillés")
c1, c2, c3 = st.columns(3)
c1.metric("Conso AVANT (MWh/an)", f"{conso_avant_mwh:.1f}")
c2.metric("Émissions AVANT (tCO₂/an)", f"{emissions_avant:.2f}")
c3.metric("Émissions APRÈS (tCO₂/an)", f"{emissions_apres:.2f}")

# Mini-graphe aligné à gauche (compact mais lisible)
df_chart = pd.DataFrame({
    "Phase": ["Avant", "Après"],
    "tCO₂/an": [emissions_avant, emissions_apres]
}).set_index("Phase")

col_graph, col_blank = st.columns([1, 3])  # 1/4 largeur pour le graphe
with col_graph:
    st.bar_chart(df_chart, height=600)  # hauteur augmentée pour lisibilité


# ==============================
# Export CSV
# ==============================
st.subheader("⬇️ Export des résultats")
data = {
  "Bâtiment": bat, "Solution AVANT": sol_init, "Solution APRÈS": sol_final,
  "Conso AVANT (kWh PCI/an)": conso, "% Gaz vert": gaz_vert,
  "Hybride": hybride, "Part Elec (%)": part_elec, "Part Gaz (%)": part_gaz,
  "Gain énergétique utilisé": gain_ener, "Conso AVANT (MWh/an)": conso_avant_mwh,
  "Conso APRÈS (MWh/an)": conso_apres_mwh, "Émissions AVANT (tCO₂/an)": emissions_avant,
  "Émissions APRÈS (tCO₂/an)": emissions_apres, "Gain CO₂ (tCO₂/an)": gain_co2
}
csv = StringIO(); pd.DataFrame([data]).to_csv(csv, index=False)
st.download_button("Télécharger le CSV", data=csv.getvalue(), file_name="simulation_CO2.csv", mime="text/csv")
