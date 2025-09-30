import streamlit as st
import pandas as pd
import json
from io import StringIO

# ==============================
# CONFIG / THEME
# ==============================
st.set_page_config(page_title="Simulateur GRDF CO₂", layout="wide")
GRDF_BLUE = "#004595"
GRDF_TEAL = "#06A8A5"
GRDF_GREEN = "#71A950"
GRDF_YELLOW = "#F5A803"
GRDF_GREY = "#87929A"

st.markdown(f"""
<style>
    .block-container {{ padding-top: 1rem; }}
    h1, h2, h3, h4 {{
        color: {GRDF_BLUE} !important;
    }}
    .stMetric > div > div > div {{
        color: {GRDF_BLUE};
    }}
    .grdf-badge {{
        background: {GRDF_TEAL};
        color: white;
        padding: .3rem .6rem;
        border-radius: .5rem;
        font-weight: 600;
        display:inline-block;
        margin-bottom:.5rem;
    }}
</style>
""", unsafe_allow_html=True)

st.title("🔵 Simulateur Gains CO₂ – GRDF")
st.caption("Version sans Excel – matrices et facteurs intégrés (éditables en ligne)")

# ==============================
# FACTEURS D'ÉMISSION (éditables)
# ==============================
DEFAULT_FACTORS = {
    "FE_GAZ": 0.239,      # tCO2/MWh (Gaz naturel PCI)
    "FE_ELEC": 0.058,     # tCO2/MWh (Mix élec France)
    "FE_BIOMETH": 0.0417  # tCO2/MWh (Biométhane)
}

# ==============================
# MATRICES CAS MOYENS (auto-gain)
# Remarque IMPORTANTE :
# - Les valeurs ci-dessous sont fournies à titre de SQUELETTE INITIAL.
# - Elles reproduisent la structure (bâtiment -> solution AVANT -> solution APRÈS -> % gain).
# - Par souci de robustesse, vous pouvez les ajuster à tout moment via le mode "Admin" (JSON).
# - Si une combinaison est marquée "NS" ou absente, le gain auto = 0 (surcharge utilisateur possible).
# ==============================

DEFAULT_MATRICES = {
    "Maison individuelle": {
        "Chaudière gaz standard >15 ans": {
            "Chaudière gaz THPE": -0.25,
            "PAC A/E + THPE (hybride)": -0.36,
            "PAC A/A + THPE": -0.32,
            "PAC gaz": -0.29,
            "PAC géothermique + THPE": -0.47,
            "Chaudière bois + THPE": -0.29
        },
        "Chaudière gaz standard neuve": {
            "Chaudière gaz THPE": -0.22,
            "PAC A/E + THPE (hybride)": -0.31,
            "PAC A/A + THPE": -0.28,
            "PAC gaz": -0.25,
            "PAC géothermique + THPE": -0.44
        },
        "Chaudière gaz THPE": {
            "PAC A/E + THPE (hybride)": -0.23,
            "PAC A/A + THPE": -0.20,
            "PAC gaz": -0.18,
            "PAC géothermique + THPE": -0.29
        },
        "PAC A/E + THPE (hybride)": {
            "PAC A/A + THPE": -0.08,
            "PAC gaz": -0.06,
            "PAC géothermique + THPE": -0.12
        },
        "PAC A/A + THPE": {
            "PAC gaz": "NS",
            "PAC géothermique + THPE": -0.10
        },
        "PAC gaz": {
            "PAC géothermique + THPE": -0.07
        },
        "PAC géothermique + THPE": {},
        "Chaudière bois + THPE": {
            "PAC A/E + THPE (hybride)": -0.09,
            "PAC géothermique + THPE": -0.11
        },
        "Chaudière fioul >15 ans": {
            "Chaudière gaz THPE": -0.30,
            "PAC A/E + THPE (hybride)": -0.40,
            "PAC A/A + THPE": -0.36,
            "PAC géothermique + THPE": -0.53
        },
        "Chaudière fioul THPE": {
            "Chaudière gaz THPE": -0.19,
            "PAC A/E + THPE (hybride)": -0.28,
            "PAC géothermique + THPE": -0.38
        }
    },

    "Appartement chauffage indiv": {
        "Chaudière gaz standard >15 ans": {
            "Chaudière gaz THPE": -0.22,
            "PAC A/E + THPE (hybride)": -0.34,
            "PAC A/A + THPE": -0.28,
            "PAC gaz": -0.25
        },
        "Chaudière gaz THPE": {
            "PAC A/E + THPE (hybride)": -0.20,
            "PAC A/A + THPE": -0.16
        },
        "PAC A/E + THPE (hybride)": {
            "PAC A/A + THPE": -0.07
        },
        "Chaudière fioul >15 ans": {
            "Chaudière gaz THPE": -0.27,
            "PAC A/E + THPE (hybride)": -0.37,
            "PAC A/A + THPE": -0.30
        }
    },

    "Appartement chauffage coll": {
        "Chauffage collectif gaz (ancienne)": {
            "Chaudière gaz THPE collective": -0.20,
            "PAC sur boucle + THPE": -0.28,
            "Réseau de chaleur": -0.18
        },
        "Chauffage collectif fioul": {
            "Chaudière gaz THPE collective": -0.30,
            "PAC sur boucle + THPE": -0.35,
            "Réseau de chaleur": -0.27
        },
        "Chauffage urbain ancien": {
            "Réseau de chaleur (mix décarboné)": -0.15,
            "PAC sur boucle + THPE": -0.22
        }
    },

    "Bâtiment tertiaire": {
        "Chaudière gaz standard": {
            "Chaudière gaz THPE": -0.18,
            "PAC A/E + appoint gaz": -0.25,
            "PAC eau/eau + appoint": -0.30,
            "Réseau de chaleur": -0.15
        },
        "Chaudière fioul": {
            "Chaudière gaz THPE": -0.28,
            "PAC A/E + appoint gaz": -0.36,
            "PAC eau/eau + appoint": -0.42,
            "Réseau de chaleur": -0.25
        },
        "PAC A/E ancienne": {
            "PAC A/E + appoint gaz (haute perf)": -0.12,
            "PAC eau/eau + appoint": -0.18
        },
        "Réseau de chaleur ancien": {
            "Réseau de chaleur (mix décarboné)": -0.12,
            "PAC eau/eau + appoint": -0.20
        }
    }
}

# ==============================
# STATE (matrices & facteurs éditables)
# ==============================
if "matrices" not in st.session_state:
    st.session_state.matrices = DEFAULT_MATRICES
if "factors" not in st.session_state:
    st.session_state.factors = DEFAULT_FACTORS

# ==============================
# MODE ADMIN (édition JSON inline)
# ==============================
with st.expander("⚙️ Admin – éditer matrices et facteurs (JSON)", expanded=False):
    st.markdown('<span class="grdf-badge">Édition avancée</span>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Matrices (JSON)", "Facteurs (JSON)", "Importer/Exporter"])

    with tab1:
        matrices_json = st.text_area(
            "Matrices (bâtiment → solution AVANT → solution APRÈS → % gain) :",
            value=json.dumps(st.session_state.matrices, indent=2, ensure_ascii=False),
            height=380
        )
        if st.button("💾 Enregistrer matrices JSON"):
            try:
                st.session_state.matrices = json.loads(matrices_json)
                st.success("Matrices mises à jour.")
            except Exception as e:
                st.error(f"JSON invalide : {e}")

    with tab2:
        factors_json = st.text_area(
            "Facteurs d’émission (tCO₂/MWh) :",
            value=json.dumps(st.session_state.factors, indent=2, ensure_ascii=False),
            height=200
        )
        if st.button("💾 Enregistrer facteurs JSON"):
            try:
                st.session_state.factors = json.loads(factors_json)
                st.success("Facteurs mis à jour.")
            except Exception as e:
                st.error(f"JSON invalide : {e}")

    with tab3:
        colu1, colu2 = st.columns(2)
        # Export
        matrices_dl = json.dumps(st.session_state.matrices, indent=2, ensure_ascii=False)
        factors_dl = json.dumps(st.session_state.factors, indent=2, ensure_ascii=False)
        colu1.download_button("⬇️ Télécharger matrices.json", data=matrices_dl, file_name="matrices.json")
        colu1.download_button("⬇️ Télécharger facteurs.json", data=factors_dl, file_name="facteurs.json")
        # Import
        up_m = colu2.file_uploader("Importer matrices.json", type=["json"], key="up_m")
        up_f = colu2.file_uploader("Importer facteurs.json", type=["json"], key="up_f")
        if up_m:
            try:
                st.session_state.matrices = json.load(up_m)
                st.success("Matrices importées.")
            except Exception as e:
                st.error(f"Import matrices KO : {e}")
        if up_f:
            try:
                st.session_state.factors = json.load(up_f)
                st.success("Facteurs importés.")
            except Exception as e:
                st.error(f"Import facteurs KO : {e}")

# ==============================
# UI – Saisie
# ==============================
matrices = st.session_state.matrices
factors = st.session_state.factors

batiments = list(matrices.keys())
if not batiments:
    st.error("Aucun type de bâtiment disponible. Renseignez des matrices en mode Admin.")
    st.stop()

bat = st.selectbox("Type de bâtiment", batiments)
solutions_avant = list(matrices.get(bat, {}).keys())
if not solutions_avant:
    st.error("Aucune solution AVANT pour ce bâtiment. Complétez les matrices en Admin.")
    st.stop()

sol_init = st.selectbox("Solution AVANT rénovation", solutions_avant)
solutions_apres = list(matrices[bat].get(sol_init, {}).keys())
if not solutions_apres:
    st.warning("Aucune solution APRÈS pour ce couple. Choisissez une autre solution AVANT ou éditez les matrices.")
    solutions_apres = ["— aucune —"]
sol_final = st.selectbox("Solution APRÈS rénovation", solutions_apres)

colL, colR = st.columns(2)
conso = colL.number_input("Consommation AVANT (kWh PCI/an)", min_value=1000, value=20000, step=500)
gaz_vert = colR.slider("% de gaz vert (biométhane) au contrat", 0, 100, 0)

hybride = st.radio("Solution APRÈS hybride (répartition conso)", ["Non", "Oui"], index=0)
if hybride == "Oui":
    c1, c2 = st.columns(2)
    part_elec = c1.slider("Répartition ÉLECTRICITÉ (%)", 0, 100, 50)
    part_gaz = 100 - part_elec
    c2.write(f"Répartition GAZ : **{part_gaz}%**")
else:
    part_elec, part_gaz = 0, 100

# ==============================
# GAIN ÉNERGÉTIQUE – auto + surcharge
# ==============================
def get_gain_auto(bat, sol_init, sol_final):
    try:
        val = matrices[bat][sol_init][sol_final]
        if isinstance(val, (int, float)):
            return float(val)
        # valeurs comme "NS" → pas de valeur auto
        return 0.0
    except Exception:
        return 0.0

gain_auto = get_gain_auto(bat, sol_init, sol_final)
colga, colgs = st.columns(2)
colga.info(f"Gain énergétique auto (cas moyen) : **{gain_auto:.3f}** (ex: -0.25 = -25%)")
gain_user = colgs.number_input("Surcharge du % gain (laisser 0 pour auto)", value=0.0, step=0.01, format="%.3f")
gain_ener = gain_user if abs(gain_user) > 1e-9 else gain_auto

# ==============================
# CALCULS CO₂
# ==============================
FE_GAZ = float(factors.get("FE_GAZ", DEFAULT_FACTORS["FE_GAZ"]))
FE_ELEC = float(factors.get("FE_ELEC", DEFAULT_FACTORS["FE_ELEC"]))
FE_BIOMETH = float(factors.get("FE_BIOMETH", DEFAULT_FACTORS["FE_BIOMETH"]))

conso_avant_mwh = conso / 1000.0
conso_apres_mwh = conso_avant_mwh * (1.0 + gain_ener)

# Émissions AVANT (100% gaz naturel)
emissions_avant = conso_avant_mwh * FE_GAZ

# Facteur gaz APRÈS (mix gaz naturel + biométhane)
fe_gaz_mix = FE_GAZ*(1.0 - gaz_vert/100.0) + FE_BIOMETH*(gaz_vert/100.0)

def is_pac(solution_label: str) -> bool:
    label = (solution_label or "").lower()
    return ("pac" in label) or ("pompe" in label)

# Émissions APRÈS
if hybride == "Oui":
    # Pondération conso APRÈS
    emis_elec = (conso_apres_mwh * (part_elec/100.0)) * FE_ELEC
    emis_gaz  = (conso_apres_mwh * (part_gaz/100.0))  * fe_gaz_mix
    emissions_apres = emis_elec + emis_gaz
else:
    if is_pac(sol_final):  # solution 100% PAC
        emissions_apres = conso_apres_mwh * FE_ELEC
    else:  # solution à gaz (avec % biométhane)
        emissions_apres = conso_apres_mwh * fe_gaz_mix

gain_co2 = emissions_avant - emissions_apres

# ==============================
# AFFICHAGE RÉSULTATS
# ==============================
st.subheader("📊 Résultats")
c1, c2, c3 = st.columns(3)
c1.metric("Conso AVANT (MWh/an)", f"{conso_avant_mwh:.1f}")
c2.metric("Émissions AVANT (tCO₂/an)", f"{emissions_avant:.2f}")
c3.metric("Émissions APRÈS (tCO₂/an)", f"{emissions_apres:.2f}")
st.metric("✅ Gain CO₂ (tCO₂/an)", f"{gain_co2:.2f}")

# Petit graphe comparatif
import matplotlib.pyplot as plt
fig1, ax1 = plt.subplots()
ax1.bar(["Avant", "Après"], [emissions_avant, emissions_apres])
ax1.set_ylabel("tCO₂/an")
ax1.set_title("Émissions CO₂ – Avant vs Après")
st.pyplot(fig1)

# ==============================
# EXPORT CSV
# ==============================
st.subheader("⬇️ Export des résultats")
result = {
    "Bâtiment": bat,
    "Solution AVANT": sol_init,
    "Solution APRÈS": sol_final,
    "Consommation AVANT (kWh PCI/an)": conso,
    "% Gaz vert": gaz_vert,
    "Hybride": hybride,
    "Part Elec (%)": part_elec,
    "Part Gaz (%)": part_gaz,
    "Gain énergétique utilisé": gain_ener,
    "Conso AVANT (MWh/an)": conso_avant_mwh,
    "Conso APRÈS (MWh/an)": conso_apres_mwh,
    "Émissions AVANT (tCO2/an)": emissions_avant,
    "Émissions APRÈS (tCO2/an)": emissions_apres,
    "Gain CO2 (tCO2/an)": gain_co2
}
df_res = pd.DataFrame([result])
csv_buf = StringIO()
df_res.to_csv(csv_buf, index=False)
st.download_button("Télécharger le CSV de la simulation", data=csv_buf.getvalue(), file_name="simulation_CO2.csv", mime="text/csv")

st.caption("Palette GRDF appliquée – Bleu/Teal/Vert/Jaune/Gris. Les matrices et facteurs sont modifiables via l’onglet Admin.")
