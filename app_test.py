import os
import urllib.parse
import pandas as pd
import streamlit as st
from PIL import Image

# Importation de vos fonctions géographiques depuis fonctions_geo.py
from fonctions_geo import calculer_distance, charger_donnees

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Recherche géolocalisée et Budget Épicerie",
    page_icon="🍎",
    layout="wide",
)

# --- INITIALISATION SÉCURISÉE DES MÉMOIRES ---
if "panier_achats" not in st.session_state:
    st.session_state["panier_achats"] = []

if "banniere_manuelle" not in st.session_state:
    st.session_state["banniere_manuelle"] = "SUPER C"

# On mémorise l'adresse de la succursale consultée
if "adresse_magasin_actif" not in st.session_state:
    st.session_state["adresse_magasin_actif"] = ""

DOSSIER_BANNIERES = "bannieres"

# =========================================================================
# 🌐 DICTIONNAIRE DES URLS OFFICIELLES DES SITES DE BANNIÈRES
# =========================================================================
LIENS_OFFICIELS = {
    "SUPER C": "https://superc.ca",
    "MAXI": "https://maxi.ca",
    "IGA": "https://iga.net",
    "PROVIGO": "https://provigo.ca",
    "METRO": "https://metro.ca",
    "MARCHÉ ADONIS": "https://groupeadonis.ca",
    "MARCHÉ AMI": "https://marcheami.ca",
    "MARCHÉ BONICHOIX": "https://bonichoix.com",
    "MARCHÉ RICHELIEU": "https://marcherichelieu.ca",
    "MARCHÉ TRADITION": "https://marchetradition.com",
    "WALMART": "https://walmart.ca",
    "COSTCO": "https://costco.ca",
    "TIGRE GÉANT": "https://gianttiger.com",
    "DOLLARAMA": "https://dollarama.com"
}

# --- CHARGEMENT DES DONNÉES ---
df_coords, df_magasins = charger_donnees()
if df_coords is None or df_magasins is None:
    st.stop()

# =========================================================================
# SECTION À GAUCHE : BARRE LATÉRALE (FILTRES + COMMERCES)
# =========================================================================
st.sidebar.header("Critères de recherche")
saisie_utilisateur = st.sidebar.text_input(
    "Entrez votre code postal (ex: G0M 1G0)", "G0M1G0"
)
code_recherche = saisie_utilisateur.replace(" ", "").upper()
rayon_max = st.sidebar.slider(
    "Rayon maximum de recherche (km)", 5, 100, 25, 5
)

bannieres_disponibles = ["Toutes les bannières"] + sorted(
    list(df_magasins["Nom_Commerce"].dropna().unique())
)
banniere_selectionnee = st.sidebar.selectbox(
    "Filtrer par bannière :", bannieres_disponibles
)

if banniere_selectionnee != "Toutes les bannières":
    st.session_state["banniere_manuelle"] = banniere_selectionnee

banniere_active = st.session_state["banniere_manuelle"]

st.sidebar.write("---")

# FLUX GÉOLOCALISÉ DANS LA BARRE DE GAUCHE
st.sidebar.subheader("📍 Commerces les plus proches")
if code_recherche:
    point_origine = df_coords[df_coords["Code postal"] == code_recherche]

    if not point_origine.empty:
        lat_centre = float(point_origine.iloc["Latitude"])
        lon_centre = float(point_origine.iloc["Longitude"])
        st.sidebar.caption(f"Position détectée : {point_origine.iloc['Ville']}")

        df_magasins_gps = pd.merge(
            df_magasins,
            df_coords,
            on="Code postal",
            how="inner",
            suffixes=("", "_Ref"),
        )
        df_magasins_gps["Distance_KM"] = calculer_distance(
            lat_centre,
            lon_centre,
            df_magasins_gps["Latitude"],
            df_magasins_gps["Longitude"],
        )

        resultats_filtres = df_magasins_gps[
            df_magasins_gps["Distance_KM"] <= rayon_max
        ].sort_values(by="Distance_KM")
        if banniere_selectionnee != "Toutes les bannières":
            resultats_filtres = resultats_filtres[
                resultats_filtres["Nom_Commerce"] == banniere_selectionnee
            ]

        if not resultats_filtres.empty:
            for index, rangee in resultats_filtres.iterrows():
                nom_magasin = rangee["Nom_Commerce"]
                distance = rangee["Distance_KM"]
                adresse_rue = rangee.get('Adresse_Rue', '')

                st.sidebar.markdown(
                    f"**{nom_magasin}** ({distance:.1f} km)<br/><small>{adresse_rue}</small>",
                    unsafe_allow_html=True,
                )
                if st.sidebar.button(
                    "📖 Consulter",
                    key=f"voir_magasin_{index}",
                    use_container_width=True,
                ):
                    st.session_state["banniere_manuelle"] = nom_magasin
                    st.session_state["adresse_magasin_actif"] = adresse_rue
                    st.rerun()
                st.sidebar.write("")
        else:
            st.sidebar.warning("Aucun commerce trouvé dans ce rayon.")


# --- EN-TÊTE PRINCIPAL ---
st.title("🍎 Planificateur de Budget Épicerie")

# LA LIGNE ROUGE
st.link_button(
    "⚙️ Ouvrir l'application Mon Guide d'Achat Local (Scanner un Code-Barres / Pays d'Origine)",
    "https://streamlit.app",
    type="primary",
    use_container_width=True,
)
st.write("---")

# --- LES DEUX COLONNES CENTRALES ---
col_gauche, col_droite = st.columns([1.0, 1.0])

# =========================================================================
# COLONNE DE GAUCHE : FORMULAIRE MANUEL + FACTURE MONTÉE
# =========================================================================
with col_gauche:
    st.subheader("🔍 Étape 1 : Saisie de ma liste d'épicerie")

    with st.expander("➕ Ajouter un rabais trouvé à ma liste", expanded=True):
        st.write(f"Magasin sélectionné : **{banniere_active}**")

        nom_article = st.text_input(
            "Nom de l'article :", placeholder="Ex: Banane, Beurre...", key="input_nom"
        )
        prix_article = st.number_input(
            "Prix en spécial ($) :", value=0.00, step=0.01, key="input_prix"
        )

        if st.button("Enregistrer l'article", use_container_width=True):
            if nom_article:
                st.session_state["panier_achats"].append(
                    {
                        "magasin": banniere_active,
                        "produit": nom_article,
                        "prix": prix_article,
                    }
                )
                st.toast("Article enregistré dans la commande !", icon="✅")
                st.rerun()
            else:
                st.warning("Veuillez entrer un nom d'article.")

    st.write("---")

    st.subheader("🛍️ Récapitulatif de ma commande & Facture")
    if st.session_state["panier_achats"]:
        df_panier = pd.DataFrame(st.session_state["panier_achats"])
        st.dataframe(df_panier, use_container_width=True, hide_index=True)
        st.markdown(
            f"### 💰 Montant total de la commande : **{df_panier['prix'].sum():.2f} $**"
        )

        if st.button("🗑️ Vider complètement la commande", use_container_width=True):
            st.session_state["panier_achats"] = []
            st.rerun()
    else:
        st.info("Aucun article dans la commande actuellement.")

# =========================================================================
# COLONNE DE DROITE : ACCÈS DIRECT ET STRICT AUX SITES OFFICIELS
# =========================================================================
with col_droite:
    st.subheader(f"📸 Circulaire visuelle : {banniere_active}")

    cle_recherche = str(banniere_active).upper().strip()
    url_base_site = LIENS_OFFICIELS.get(cle_recherche, "https://google.com")

    adresse_cible = st.session_state["adresse_magasin_actif"]
    
    # Encodage propre des variables pour l'URL
    code_postal_url = urllib.parse.quote(code_recherche)
    adresse_complete_url = urllib.parse.quote(f"{adresse_cible} {code_recherche}".strip())

    # --- STRUCTURE EXACTE DES URLS SELON CHAQUE SITE BANNIÈRE ---
    if "superc" in url_base_site:
        url_final_site = f"https://superc.ca?search={code_postal_url}"
    elif "maxi" in url_base_site:
        url_final_site = f"https://maxi.ca?searchQuery={code_postal_url}"
    elif "provigo" in url_base_site:
        url_final_site = f"https://provigo.ca?searchQuery={code_postal_url}"
    elif "metro" in url_base_site:
        url_final_site = f"https://metro.ca?search={code_postal_url}"
    elif "iga" in url_base_site:
        url_final_site = f"https://iga.net?store_search={code_postal_url}"
    elif "bonichoix" in url_base_site:
        url_final_site = f"https://bonichoix.com?store_search={code_postal_url}"
    elif "marcherichelieu" in url_base_site:
        url_final_site = f"https://marcherichelieu.ca?store_search={code_postal_url}"
    elif "marchetradition" in url_base_site:
        url_final_site = f"https://marchetradition.com?store_search={code_postal_url}"
    elif "walmart" in url_base_site:
        url_final_site = f"https://walmart.ca?q={code_postal_url}"
    elif "gianttiger" in url_base_site:
        url_final_site = f"https://gianttiger.com?q={code_postal_url}"
    elif "dollarama" in url_base_site:
        url_final_site = f"https://dollarama.com?localisation={code_postal_url}"
    elif "adonis" in url_base_site:
        url_final_site = f"https://groupeadonis.ca?search={code_postal_url}"
    else:
        url_final_site = f"{url_base_site}?search={code_postal_url}"

    st.write("### 🔗 Accès direct au magasin sélectionné")
    
    col_lien1, col_lien2 = st.columns(2)
    with col_lien1:
        st.link_button(
