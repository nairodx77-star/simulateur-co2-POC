import streamlit as st
import pandas as pd

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="Simulateur GRDF CO₂", layout="wide")
st.title("🔵 Simulateur Gains CO₂ – GRDF")

# ==============================
# CHARGEMENT DES DONNÉES EXCEL
# ==============================
@st.cache_data
def load_data():
    xls = pd.ExcelFile("Référentiel données décarbonation GRDF.xlsx")
    perf = pd.read_excel(xls, "1.2 bis Perf relatives PCS", header=None)
    factors = pd.read_excel(xls, "D.1. Facteur d'émissions", header=None)
    return perf, factors

perf, factors = load_data()

# ==============================
# EXTRACTION MATRICES
# ==============================
def extract_matrix(start_row, label):
    """Extrait une matrice de performances relatives pour un type de bâtiment"""
    block = perf.iloc[start_row-5:start_row+50, :].reset_index(drop=True)

    # Chercher la ligne "Solution posée" partout
    row_pose_candidates = block.applymap(lambda x: isinstance(x, str) and "Solution posée" in x)
    coords = list(zip(*row_pose_candidates.values.nonzero()))

    if not coords:
        # fallback : chercher "Solution initiale"
        row_init_candidates = block.applymap(lambda x: isinstance(x, str) and "Solution initiale" in x)
        coords_init = list(zip(*row_init_candidates.values.nonzero()))
        if coords_init:
            row_pose = coords_init[0][0] + 2   # souvent 2 lignes plus bas
        else:
            return [], [], pd.DataFrame()
    else:
        row_pose = coords[0][0]

    # Solutions initiales (col 3 sinon col 1)
    sols_init = block.iloc[row_pose+2:, 3].dropna().tolist()
    if not sols_init:
        sols_init = block.iloc[row_pose+2:, 1].dropna().tolist()

    # Solutions posées = en-têtes juste après "Solution posée"
    sols_pose = block.iloc[row_pose+1].dropna().tolist()
    sols_pose = [s for s in sols_pose if isinstance(s, str)][1:]  # ignorer 1ère cellule vide

    # Matrice
    mat = block.iloc[row_pose+2:row_pose+2+len(sols_init), 4:4+len(sols_pose)]
    mat.index = sols_init[:len(mat)]
    mat.columns = sols_pose
    return sols_init, sols_pose, mat

# Construire dictionnaire des bâtiments
bat_matrices = {}
for label, row in {
    "Maison individuelle": 18,
    "Appartement indiv": 45,
    "Appartement coll": 62,
    "Bâtiment tertiaire": 80
}.items():
    sols_init, sols_apres, mat = extract_matrix(row, label)
    if sols_init and sols_apres and not mat.empty:
        bat_matrices[label] = (sols_init, sols_apres, mat)

# Vérifier qu’on a au moins un bâtiment valide
if not bat_matrices:
    st.error("⚠️ Impossible d’extraire les matrices depuis l’Excel. Vérifie la structure du fichier.")
    st.stop()

# ==============================
# EXTRACTION FACTEURS D'ÉMISSION
# ==============================
def get_factor(keyword, default):
    mask = factors.applymap(lambda x: isinstance(x,str) and keyword.lower() in x.lower())
    coords = list(zip(*mask.values.nonzero()))
    if coords:
        r = coords[0][0]
        row_vals = factors.iloc[r].tolist()
        for v in row_vals:
            if isinstance(v,(int,float)):
                return float(v)
    return default

FE_GAZ = get_factor("Gaz naturel PCI", 0.239)
FE_ELEC = get_factor("Electricité", 0.058)
FE_BIOMETH = 0.0417

# ==============================
# INTERFACE UTILISATEUR
# ==============================
bat = st.selectbox("Type de bâtiment", list(bat_matrices.keys()))

sols_init, sols_apres, mat = bat_matrices[bat]
sol_init = st.selectbox("Solution AVANT rénovation", sols_init)
sol_final = st.selectbox("Solution APRÈS rénovation", sols_apres)

conso = st.number_input("Consommation avant (kWh PCI/an)", min_value=1000, value=20000, step=500)
gaz_vert = st.slider("% Gaz vert", 0, 100, 0)

hybride = st.radio("Solution hybride ?", ["Non","Oui"])
if hybride == "Oui":
    colh1, colh2 = st.columns(2)
    part_elec = colh1.slider("Répartition électricité (%)", 0, 100, 50)
    part_gaz = 100 - part_elec
    colh2.write(f"Répartition gaz : {part_gaz}%")
else:
    part_elec, part_gaz = 0, 100

# ==============================
# CALCUL GAIN ÉNERGÉTIQUE
# ==============================
try:
    gain_auto = mat.loc[sol_init, sol_final]
    gain_auto = float(gain_auto) if isinstance(gain_auto,(int,float)) else 0
except Exception:
    gain_auto = 0

gain_user = st.number_input("Surcharge % gain (laisser 0 pour auto)", value=0.0)
gain_ener = gain_user if gain_user != 0 else gain_auto

# ==============================
# CALCULS CO2
# ==============================
conso_avant_mwh = conso/1000
conso_apres_mwh = conso_avant_mwh * (1 + gain_ener)

# Émissions avant (100% gaz naturel)
emissions_avant = conso_avant_mwh * FE_GAZ

# Facteur gaz avec biométhane
fe_gaz_mix = FE_GAZ*(1-gaz_vert/100) + FE_BIOMETH*(gaz_vert/100)

# Émissions après
if hybride == "Oui":
    emissions_apres = (conso_apres_mwh * part_gaz/100) * fe_gaz_mix \
                    + (conso_apres_mwh * part_elec/100) * FE_ELEC
else:
    # si PAC → tout à l’électricité
    if "PAC" in sol_final:
        emissions_apres = conso_apres_mwh * FE_ELEC
    else:
        emissions_apres = conso_apres_mwh * fe_gaz_mix

gain_co2 = emissions_avant - emissions_apres

# ==============================
# AFFICHAGE RÉSULTATS
# ==============================
st.subheader("📊 Résultats")
col1, col2, col3 = st.columns(3)
col1.metric("Conso AVANT (MWh)", f"{conso_avant_mwh:.1f}")
col2.metric("Émissions AVANT (tCO₂/an)", f"{emissions_avant:.2f}")
col3.metric("Émissions APRÈS (tCO₂/an)", f"{emissions_apres:.2f}")

st.metric("✅ Gain CO₂ (t/an)", f"{gain_co2:.2f}")
