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
# COLONNE DE GAUCHE : FORMULAIRE MANUEL AVEC CATÉGORIES + FACTURE MONTÉE
# =========================================================================
with col_gauche:
    st.subheader("🔍 Étape 1 : Saisie de ma liste d'épicerie")

    with st.expander("➕ Ajouter un rabais trouvé à ma liste", expanded=True):
        st.write(f"Magasin sélectionné : **{banniere_active}**")

        # 1. Ajout de l'option des catégories demandée dans l'espace central
        categorie = st.selectbox(
            "Catégorie de l'article :",
            [
                "🍎 Fruits et Légumes", 
                "🥩 Viandes et Poissons", 
                "🧀 Produits laitiers", 
                "🍞 Boulangerie", 
                "📦 Épicerie / Boîtes", 
                "🧼 Entretien / Autre"
            ]
        )

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
                        "catégorie": categorie, # On enregistre la catégorie sélectionnée
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
# COLONNE DE DROITE : VOTRE CONFIGURATION D'ORIGINE DE LA LISEUSE
# =========================================================================
with col_droite:
    st.subheader(f"📸 Circulaire visuelle : {banniere_active}")

    # Nettoyage de la chaîne pour le sous-dossier
    nom_sous_dossier = str(banniere_active).lower().replace(" ", "_").replace("é", "e").replace("è", "e").replace("à", "a")
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
                        f"➕ Ajouter ce spécial",
                        key=f"btn_photo_{index}",
                        use_container_width=True,
                        type="primary"
                    ):
                        nom_complet_sans_ext, _ = os.path.splitext(str(photo))
                        
                        if "_" in nom_complet_sans_ext:
                            parties = nom_complet_sans_ext.split("_", 1)
                            premier_morceau = parties[0]
                            reste_du_texte = parties[1]
                            
                            try:
                                prix_automatique = float(premier_morceau)
                                nom_automatique = reste_du_texte.replace("_", " ").capitalize()
                            except ValueError:
                                prix_automatique = 0.00
                                nom_automatique = "Article Circulaire"
                        else:
                            prix_automatique = 0.00
                            nom_automatique = "Article Circulaire"

                        st.session_state["panier_achats"].append(
                            {
                                "magasin": banniere_active,
                                "catégorie": "🍎 Circulaire Visuelle", # Par défaut pour les photos
                                "produit": nom_automatique,
                                "prix": prix_automatique,
                            }
                        )
                        st.toast(f"✅ {nom_automatique} ajouté au panier !", icon="🛒")
                        st.rerun()
                    st.write("")
        else:
            st.info("Aucune photo dans ce dossier pour le moment.")
    else:
        st.warning(f"Dossier introuvable : {DOSSIER_BANNIERES}/{nom_sous_dossier}")
