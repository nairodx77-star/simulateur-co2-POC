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
# EXTRACTION MATRICES PAR BATIMENT
# ==============================
def extract_matrix(start_row, label):
    """Extrait une matrice de performances relatives pour un type de bâtiment"""
    block = perf.iloc[start_row-2:start_row+20, 0:20].reset_index(drop=True)
    # Solutions initiales (col 3)
    sols_init = block[3].dropna().tolist()[1:]
    # Ligne avec "Solution posée"
    row_pose = block[block[3]=="Solution posée"].index[0]
    sols_pose = block.iloc[row_pose+1, 4:12].dropna().tolist()
    # Matrice
    mat = block.iloc[row_pose+2:row_pose+2+len(sols_init), 4:4+len(sols_pose)]
    mat.index = sols_init[:len(mat)]
    mat.columns = sols_pose
    return sols_init, sols_pose, mat

bat_matrices = {
    "Maison individuelle": extract_matrix(18, "Maison"),
    "Appartement indiv": extract_matrix(45, "Appart indiv"),
    "Appartement coll": extract_matrix(62, "Appart coll"),
    "Bâtiment tertiaire": extract_matrix(80, "Tertiaire")
}

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
