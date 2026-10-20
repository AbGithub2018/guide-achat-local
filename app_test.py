import numpy as np
import pandas as pd
import streamlit as st


def calculer_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance en kilomètres entre deux coordonnées GPS."""
    R = 6371.0
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


@st.cache_data
def charger_donnees():
    """Charge et nettoie les fichiers de codes postaux et de magasins."""
    try:
        df_coords = pd.read_csv("codes_qc.csv", sep=";")
        df_magasins = pd.read_csv("disponibilite_magasins.csv")

        df_coords["Code postal"] = (
            df_coords["Code postal"].astype(str).str.replace(" ", "").str.upper()
        )
        df_magasins["Code postal"] = (
            df_magasins["Code postal"].astype(str).str.replace(" ", "").str.upper()
        )
        return df_coords, df_magasins
    except Exception as e:
        st.error(f"Erreur lors de la lecture des fichiers CSV : {e}")
        return None, None
import os
import urllib.parse
import pandas as pd
import streamlit as st
from PIL import Image

# Importation de vos fonctions géographiques depuis le fichier fonctions_geo.py
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

DOSSIER_BANNIERES = "bannieres"

# --- CHARGEMENT DES DONNÉES ---
df_coords, df_magasins = charger_donnees()
if df_coords is None or df_magasins is None:
    st.stop()

# --- BARRE LATÉRALE : FILTRES ---
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

# --- EN-TÊTE PRINCIPAL ---
st.title("🍎 Planificateur de Budget Épicerie")

# LA LIGNE ROUGE (CONSERVÉE)
st.link_button(
    "⚙️ Ouvrir l'application Mon Guide d'Achat Local (Scanner un Code-Barres / Pays d'Origine)",
    "https://streamlit.app",
    type="primary",
    use_container_width=True,
)
st.write("---")

# --- LES DEUX COLONNES ---
col_gauche, col_droite = st.columns([1.0, 1.0])

# =========================================================================
# COLONNE DE GAUCHE : FORMULAIRE ET DISTANCES
# =========================================================================
with col_gauche:
    st.subheader("🔍 Étape 1 : Saisie de ma liste d'épicerie")

    with st.expander("➕ Ajouter un rabais trouvé à ma liste", expanded=True):
        st.write(f"Magasin sélectionné : **{banniere_active}**")

        nom_defaut = st.session_state.get("nom_article_saisi", "")
        prix_defaut = st.session_state.get("prix_article_saisi", 0.00)

        nom_article = st.text_input(
            "Nom de l'article :", value=nom_defaut, key="input_nom"
        )
        prix_article = st.number_input(
            "Prix en spécial ($) :", value=float(prix_defaut), key="input_prix"
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
                st.session_state["nom_article_saisi"] = ""
                st.session_state["prix_article_saisi"] = 0.00
                st.toast("Article enregistré dans la commande !", icon="✅")
                st.rerun()

    st.write("---")

    # ZONE GÉOLOCALISÉE (Boutons Consulter réparés)
    st.subheader("📍 Commerces les plus proches")
    if code_recherche:
        point_origine = df_coords[df_coords["Code postal"] == code_recherche]

        if not point_origine.empty:
            lat_centre = float(point_origine.iloc[0]["Latitude"])
            lon_centre = float(point_origine.iloc[0]["Longitude"])
            st.caption(f"Position détectée : {point_origine.iloc[0]['Ville']}")

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

                    col_info, col_action = st.columns([0.6, 0.4])
                    with col_info:
                        st.markdown(
                            f"**{nom_magasin}** ({distance:.1f} km)<br/><small>{rangee.get('Adresse_Rue', '')}</small>",
                            unsafe_allow_html=True,
                        )
                    with col_action:
                        if st.button(
                            "📖 Consulter",
                            key=f"voir_magasin_{index}",
                            use_container_width=True,
                        ):
                            st.session_state["banniere_manuelle"] = nom_magasin
                            st.rerun()

# =========================================================================
# COLONNE DE DROITE : LISEUSE VISUELLE REEBEE
# =========================================================================
with col_droite:
    st.subheader(f"📸 Circulaire visuelle : {banniere_active}")

    nom_sous_dossier = str(banniere_active).lower().replace(" ", "_")
    chemin_dossier_images = os.path.join(DOSSIER_BANNIERES, nom_sous_dossier)

    if os.path.exists(chemin_dossier_images):
        fichiers_photos = [
            f
            for f in os.listdir(chemin_dossier_images)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]

        if fichiers_photos:
            grille_visuelle = st.columns(2)
            for index, photo in enumerate(fichiers_photos):
                image_aliment = Image.open(
                    os.path.join(chemin_dossier_images, photo)
                )

                with grille_visuelle[index % 2]:
                    st.image(image_aliment, use_container_width=True)

                    if st.button(
                        f"➕ Saisir cet article",
                        key=f"btn_photo_{index}",
                        use_container_width=True,
                    ):
                        nom_nettoye = (
                            os.path.splitext(photo)[0]
                            .replace("_", " ")
                            .capitalize()
                        )
                        st.session_state["nom_article_saisi"] = nom_nettoye
                        st.session_state["prix_article_saisi"] = 0.00
                        st.rerun()
                    st.write("---")
        else:
            st.info("Aucune photo dans ce dossier pour le moment.")
    else:
        st.warning(f"Dossier introuvable : bannieres/{nom_sous_dossier}")

# =========================================================================
# FIN DE PAGE : LE PANIER TOTAL
# =========================================================================
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
