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

DOSSIER_BANNIERES = "bannieres"

# =========================================================================
# 🌐 DICTIONNAIRE DES URLS OFFICIELLES DES BANNIÈRES
# =========================================================================
# Ce dictionnaire contient les vrais liens. Les clés sont en MAJUSCULES pour éviter les conflits.
LIENS_OFFICIELS = {
    "SUPER C": {
        "site": "https://superc.ca",
        "speciaux": "https://superc.ca/circulaire"
    },
    "MAXI": {
        "site": "https://maxi.ca",
        "speciaux": "https://maxi.ca/circulaire"
    },
    "IGA": {
        "site": "https://iga.net",
        "speciaux": "https://iga.netfr/circulaire_hebdomadaire"
    },
    "PROVIGO": {
        "site": "https://provigo.ca",
        "speciaux": "https://provigo.ca/circulaire"
    },
    "METRO": {
        "site": "https://metro.ca",
        "speciaux": "https://metro.ca/circulaire"
    },
    "MARCHÉ AMI": {
        "site": "https://marcheami.ca",
        "speciaux": "https://reebee.com"
    },
    "WALMART": {
        "site": "https://walmart.ca",
        "speciaux": "https://walmart.ca/circulaire-flyer"
    },
    "COSTCO": {
        "site": "https://costco.ca",
        "speciaux": "https://costco.ca/circulaires-offres.html"
    },
    "DOLLARAMA": {
        "site": "https://www.dollarama.com/fr-CA",
        "speciaux": "https://doordash.com"
    },
    "TIGRE GÉANT": {
        "site": "https://gianttiger.com",
        "speciaux": "https://gianttiger.com/circulaire"
    }
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
        lat_centre = float(point_origine.iloc[0]["Latitude"])
        lon_centre = float(point_origine.iloc[0]["Longitude"])
        st.sidebar.caption(f"Position détectée : {point_origine.iloc[0]['Ville']}")

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

                st.sidebar.markdown(
                    f"**{nom_magasin}** ({distance:.1f} km)<br/><small>{rangee.get('Adresse_Rue', '')}</small>",
                    unsafe_allow_html=True,
                )
                if st.sidebar.button(
                    "📖 Consulter",
                    key=f"voir_magasin_{index}",
                    use_container_width=True,
                ):
                    st.session_state["banniere_manuelle"] = nom_magasin
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
# COLONNE DE DROITE : ACCÈS DIRECT AUX LIENS DE LA BANNIÈRE (DICTIONNAIRE CORRIGÉ)
# =========================================================================
with col_droite:
    st.subheader(f"📸 Circulaire visuelle : {banniere_active}")

    # Récupération des URLs directement depuis notre dictionnaire interne (LIENS_OFFICIELS)
    # On force en majuscules pour éviter les erreurs d'écriture (ex: "Super C" vs "SUPER C")
    cle_recherche = str(banniere_active).upper().strip()
    config_banniere = LIENS_OFFICIELS.get(cle_recherche, {})

    url_site = config_banniere.get("site")
    url_speciaux = config_banniere.get("speciaux")

    # Si le magasin sélectionné n'est pas répertorié dans le dictionnaire, on crée une recherche Google propre
    if not url_site:
        nom_encode = urllib.parse.quote(banniere_active)
        url_site = f"https://google.com{nom_encode}+epicerie+quebec"
        url_speciaux = f"https://google.com{nom_encode}+circulaire+reebee"

    # Affichage des deux boutons d'action demandés
    st.write("### 🔗 Accès rapide")
    
    col_lien1, col_lien2 = st.columns(2)
    with col_lien1:
        st.link_button(
            "🌐 Site Internet de la bannière",
            url_site,
            use_container_width=True
        )
    with col_lien2:
        st.link_button(
            "🏷️ Lien des spéciaux",
            url_speciaux,
            type="primary",
            use_container_width=True
        )

