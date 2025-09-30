import streamlit as st
import pandas as pd
import json
from io import StringIO
import altair as alt

# ==============================
# THEME / CONFIG
# ==============================
st.set_page_config(page_title="Simulateur GRDF CO₂", layout="wide")
GRDF_BLUE = "#004595"; GRDF_TEAL = "#06A8A5"; GRDF_GREEN = "#71A950"; GRDF_YELLOW = "#F5A803"; GRDF_GREY = "#87929A"

st.markdown(f"""
<style>
  .block-container {{ padding-top: .5rem; }}
  h1, h2, h3, h4 {{ color: {GRDF_BLUE} !important; }}
  .gain-hero {{
      text-align:center; margin: .8rem 0 1rem 0;
      font-size: 2.1rem; font-weight: 800; color: {GRDF_GREEN};
      line-height: 1.2;
  }}
  .gain-hero small {{ display:block; font-size: 0.9rem; color: {GRDF_GREY}; font-weight:600; }}
  .admin-box .stButton>button {{ width:100%; margin-bottom:.35rem; }}
</style>
""", unsafe_allow_html=True)

# ==============================
# EN-TÊTE AVEC LOGOS
# ==============================
col_logo1, col_spacer, col_logo2 = st.columns([1, 5, 1])
with col_logo1:
    st.image("Grdf.png", width=120)
with col_logo2:
    st.image("Simulateur.png", width=120)

st.title("🔵 Simulateur Gains CO₂ – GRDF")
st.caption("Version JSON (sans Excel) – matrices & facteurs chargés depuis le repo, éditables en ligne.")

# ==============================
# DEFAULTS (fallback si JSON manquants)
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
    "PAC A/A + THPE": { "PAC gaz": "NA", "PAC géothermique + THPE": -0.10 },
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
    "Chauffage collectif gaz (ancienne)": { "Chaudière gaz THPE collective": -0.20, "PAC sur boucle + THPE": -0.28, "Réseau de chaleur (mix décarboné)": -0.18 },
    "Chauffage collectif fioul": { "Chaudière gaz THPE collective": -0.30, "PAC sur boucle + THPE": -0.35, "Réseau de chaleur (mix décarboné)": -0.27 },
    "Chauffage urbain ancien": { "Réseau de chaleur (mix décarboné)": -0.15, "PAC sur boucle + THPE": -0.22 }
  },
  "Bâtiment tertiaire": {
    "Chaudière gaz standard >15 ans": {
      "Chaudière gaz standard neuve": -0.12, "Chaudière gaz THPE": -0.18,
      "Chaudière THPE + chauffe-eau solaire": -0.22, "PAC gaz": -0.20, "PAC A/E + THPE (PAC hybride)": -0.30
    },
    "Chaudière gaz standard neuve": {
      "Chaudière gaz THPE": -0.10, "Chaudière THPE + chauffe-eau solaire": -0.15,
      "PAC gaz": -0.12, "PAC A/E + THPE (PAC hybride)": -0.25
    },
    "Chaudière gaz THPE": {
      "Chaudière THPE + chauffe-eau solaire": -0.08, "PAC gaz": -0.10, "PAC A/E + THPE (PAC hybride)": -0.20
    },
    "PAC gaz": { "PAC A/E + THPE (PAC hybride)": -0.15 },
    "Chaudière fioul standard >15 ans": {
      "Chaudière gaz standard neuve": -0.20, "Chaudière gaz THPE": -0.28,
      "Chaudière THPE + chauffe-eau solaire": -0.32, "PAC gaz": -0.30, "PAC A/E + THPE (PAC hybride)": -0.42
    },
    "Chaudière fioul THPE": {
      "Chaudière gaz THPE": -0.18, "Chaudière THPE + chauffe-eau solaire": -0.22,
      "PAC gaz": -0.20, "PAC A/E + THPE (PAC hybride)": -0.35
    }
  }
}

# ==============================
# JSON LOADING (sans cache) + bouton reload
# ==============================
def load_json_file(path, default_dict):
    """Charge le JSON depuis le repo à chaque run (sans cache)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            st.session_state[f"{path}_source"] = "fichier"
            return data
    except Exception:
        st.session_state[f"{path}_source"] = "defaut"
        return default_dict

matrices = load_json_file("matrices.json", DEFAULT_MATRICES)
factors  = load_json_file("facteurs.json", DEFAULT_FACTORS)

# ==============================
# UTILS (NA/NS filtering, audit)
# ==============================
def is_numeric(x) -> bool:
    return isinstance(x, (int, float)) and pd.notna(x)

def applicable_after_options(mats: dict, bat: str, sol_init: str) -> list[str]:
    try:
        mapping = mats[bat][sol_init]
        return [k for k, v in mapping.items() if is_numeric(v)]
    except Exception:
        return []

def audit_matrix(mats: dict) -> dict:
    report = {}
    for bat, m in mats.items():
        issues = []
        for sol_init, mapping in m.items():
            if not isinstance(mapping, dict):
                issues.append(f"{sol_init} → mapping non dict")
                continue
            if not any(is_numeric(v) for v in mapping.values()):
                issues.append(f"{sol_init} → aucune solution APRÈS applicable (tout NA/NS ?)")
        if issues:
            report[bat] = issues
    return report

def get_gain_auto(b, s_init, s_final):
    try:
        v = matrices[b][s_init][s_final]
        return float(v) if is_numeric(v) else 0.0
    except Exception:
        return 0.0

# ==============================
# UI – Saisie (placeholders + compatibilité)
# ==============================
batiments = list(matrices.keys())
if not batiments:
    st.error("Aucun bâtiment disponible. Ajoutez des matrices en Admin.")
    st.stop()

bat = st.selectbox("Type de bâtiment", batiments)

solutions_avant = list(matrices.get(bat, {}).keys())
sol_init = st.selectbox(
    "Solution AVANT rénovation",
    options=solutions_avant,
    index=None,
    placeholder="— Sélectionner une solution AVANT —"
)

solutions_apres_applicables = applicable_after_options(matrices, bat, sol_init) if sol_init else []
sol_final = st.selectbox(
    "Solution APRÈS rénovation",
    options=solutions_apres_applicables,
    index=None,
    placeholder="— Sélectionner une solution APRÈS —",
    disabled=(not sol_init)
)

if not sol_init:
    st.info("Choisis d’abord une **solution AVANT** pour voir les options **APRÈS** applicables.")
elif not sol_final:
    st.info("Choisis une **solution APRÈS** pour lancer les calculs.")

# ==============================
# PARAMÈTRES / CALCULS uniquement si 2 choix faits
# ==============================
if sol_init and sol_final:
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

    gain_auto = get_gain_auto(bat, sol_init, sol_final)
    gA, gB = st.columns(2)
    gA.info(f"Gain énergétique auto (cas moyen) : **{gain_auto:.3f}** (ex: -0.25 = -25%)")
    gain_user = gB.number_input("Surcharge du % gain (laisser 0 pour auto)", value=0.0, step=0.01, format="%.3f")
    gain_ener = gain_user if abs(gain_user) > 1e-9 else gain_auto

    FE_GAZ = float(factors.get("FE_GAZ", DEFAULT_FACTORS["FE_GAZ"]))
    FE_ELEC = float(factors.get("FE_ELEC", DEFAULT_FACTORS["FE_ELEC"]))
    FE_BIOMETH = float(factors.get("FE_BIOMETH", DEFAULT_FACTORS["FE_BIOMETH"]))

    conso_avant_mwh = conso / 1000.0
    conso_apres_mwh = conso_avant_mwh * (1.0 + gain_ener)

    emissions_avant = conso_avant_mwh * FE_GAZ
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

    # HERO – Gain CO2
    st.markdown(f'<div class="gain-hero">🌿 Gain CO₂ : {gain_co2:.2f} t/an<small>(Émissions AVANT − APRÈS)</small></div>', unsafe_allow_html=True)

    # Résultats
    st.subheader("📊 Résultats détaillés")
    m1, m2, m3 = st.columns(3)
    m1.metric("Conso AVANT (MWh/an)", f"{conso_avant_mwh:.1f}")
    m2.metric("Émissions AVANT (tCO₂/an)", f"{emissions_avant:.2f}")
    m3.metric("Émissions APRÈS (tCO₂/an)", f"{emissions_apres:.2f}")

    # Graphique Altair à gauche (Avant rouge clair, Après vert)
    df_chart = pd.DataFrame({"Phase": ["Avant", "Après"], "tCO₂/an": [emissions_avant, emissions_apres]})
    chart = alt.Chart(df_chart).mark_bar().encode(
        x=alt.X("Phase", sort=["Avant", "Après"], axis=alt.Axis(title=None)),
        y=alt.Y("tCO₂/an", axis=alt.Axis(title="tCO₂/an")),
        color=alt.condition(alt.datum.Phase == "Avant", alt.value("#FF9999"), alt.value("#71A950"))
    ).properties(height=600, width=150)

    col_graph, _ = st.columns([1, 3])  # graphe à gauche
    with col_graph:
        st.altair_chart(chart, use_container_width=False)

    # Export CSV
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

# ==============================
# ⚙️ Administration (bas gauche)
# ==============================
st.markdown("---")
col_admin, _ = st.columns([1, 3])
with col_admin:
    with st.expander("⚙️ Administration", expanded=False):
        st.markdown('<div class="admin-box">', unsafe_allow_html=True)

        # Bouton Admin JSON (ouvre éditeur)
        if st.button("📂 Admin – matrices & facteurs (JSON)"):
            st.session_state["show_admin"] = True

        # Recharger JSON (forcer relecture fichiers)
        if st.button("🔄 Recharger matrices & facteurs JSON"):
            st.rerun()

        # Audit JSON
        rep = audit_matrix(matrices)
        if not rep:
            st.success("✅ JSON OK : chaque 'Avant' a au moins une 'Après' applicable.")
        else:
            st.warning("⚠️ Anomalies détectées :")
            for bat_r, issues in rep.items():
                st.write(f"**{bat_r}**")
                for msg in issues:
                    st.write("•", msg)

        st.markdown('</div>', unsafe_allow_html=True)

        # === Éditeur JSON (s’ouvre depuis le bouton) ===
        if st.session_state.get("show_admin"):
            st.write("---")
            st.subheader("Édition JSON (session)")
            tab1, tab2, tab3 = st.tabs(["Matrices", "Facteurs", "Importer/Exporter"])

            with tab1:
                txt = st.text_area("Matrices JSON :", value=json.dumps(matrices, indent=2, ensure_ascii=False), height=360)
                if st.button("Enregistrer matrices (session)"):
                    try:
                        matrices = json.loads(txt)
                        st.success("Matrices mises à jour (session). Téléchargez puis commitez le fichier pour pérenniser.")
                    except Exception as e:
                        st.error(f"JSON invalide : {e}")

            with tab2:
                txtf = st.text_area("Facteurs JSON :", value=json.dumps(factors, indent=2, ensure_ascii=False), height=180)
                if st.button("Enregistrer facteurs (session)"):
                    try:
                        factors = json.loads(txtf)
                        st.success("Facteurs mis à jour (session). Téléchargez puis commitez le fichier pour pérenniser.")
                    except Exception as e:
                        st.error(f"JSON invalide : {e}")

            with tab3:
                cA, cB = st.columns(2)
                cA.download_button("⬇️ matrices.json", data=json.dumps(matrices, indent=2, ensure_ascii=False),
                                   file_name="matrices.json", mime="application/json")
                cA.download_button("⬇️ facteurs.json", data=json.dumps(factors, indent=2, ensure_ascii=False),
                                   file_name="facteurs.json", mime="application/json")
                upM = cB.file_uploader("Importer matrices.json", type="json", key="upM")
                upF = cB.file_uploader("Importer facteurs.json", type="json", key="upF")
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
# CRÉDIT (photo cliquable en bas à gauche)
# ==============================
st.markdown(
    """
    <div style='position: fixed; bottom: 15px; left: 15px;'>
        <a href="https://www.jedha.co/formation-ia/les-10-meilleurs-generateurs-de-code-ia-gratuits-en-2024" target="_blank">
            <img src="dorian.png" width="60" style="border-radius:50%; border:2px solid #004595;" />
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
