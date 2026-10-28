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
        lat_centre = float(point_origine["Latitude"].iloc[0])
        lon_centre = float(point_origine["Longitude"].iloc[0])
        st.sidebar.caption(f"Position détectée : {point_origine['Ville'].iloc[0]}")

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
# COLONNE DE GAUCHE : FORMULAIRE AVEC CATÉGORIES + RECAPITULATIF & COMPARAISON
# =========================================================================
with col_gauche:
    st.markdown("<h2 style='font-size: 28px; margin-bottom: 0px;'>🔍 Étape 1 : Saisie de ma liste d'épicerie</h2>", unsafe_allow_html=True)

    with st.expander("➕ Ajouter un rabais trouvé à ma liste", expanded=True):
        st.markdown(f"<p style='font-size: 18px;'>Magasin sélectionné : <strong>{banniere_active}</strong></p>", unsafe_allow_html=True)

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
                        "catégorie": categorie,
                        "produit": nom_article,
                        "prix": prix_article,
                    }
                )
                st.toast("Article enregistré dans la commande !", icon="✅")
                st.rerun()
            else:
                st.warning("Veuillez entrer un nom d'article.")

    st.write("---")

    st.markdown("<h2 style='font-size: 28px; margin-bottom: 15px;'>🛍️ Récapitulatif de ma commande & Facture</h2>", unsafe_allow_html=True)
    
    if st.session_state["panier_achats"]:
        df_panier = pd.DataFrame(st.session_state["panier_achats"])
        
        # 1. Préparation du tableau d'affichage des articles
        df_affichage = df_panier.rename(columns={
            "magasin": "Magasin",
            "catégorie": "Catégorie",
            "produit": "Article",
            "prix": "Prix"
        })
        df_affichage["Prix"] = df_affichage["Prix"].map("{:.2f} $".format)
        st.dataframe(df_affichage, use_container_width=True, hide_index=True)
        
        # 2. BLOC DE COMPARAISON AUTOMATIQUE PAR BANNIÈRE
        st.write("---")
        st.markdown("<h3 style='font-size: 20px; margin-bottom: 10px;'>📊 Comparatif des dépenses par bannière :</h3>", unsafe_allow_html=True)
        
        # On calcule la somme cumulée pour chaque magasin unique dans la liste
        df_comparatif = df_panier.groupby("magasin")["prix"].sum().reset_index()
        
        # On affiche chaque magasin avec un marqueur visuel et son sous-total
        for _, rangee in df_comparatif.iterrows():
            magasin_nom = rangee["magasin"]
            total_magasin = rangee["prix"]
            st.markdown(f"🔹 Total estimé chez **{magasin_nom}** : `{total_magasin:.2f} $`")
        
        # 3. Montant total global écrit en très gros
        st.markdown(
            f"<h1 style='font-size: 32px; color: #1E3A8A; margin-top: 15px;'>💰 Montant total de la commande : {df_panier['prix'].sum():.2f} $</h1>", 
            unsafe_allow_html=True
        )

        if st.button("🗑️ Vider complètement la commande", use_container_width=True):
            st.session_state["panier_achats"] = []
            st.rerun()
    else:
        st.info("Aucun article dans la commande actuellement.")

# =========================================================================
# COLONNE DE DROITE : ACCÈS SITES OFFICIELS + LISEUSE DE PHOTOS D'ORIGINE
# =========================================================================
with col_droite:
    st.subheader(f"📸 Circulaire visuelle : {banniere_active}")

    cle_recherche = str(banniere_active).upper().strip()
    url_base_site = LIENS_OFFICIELS.get(cle_recherche, "https://google.com")
    code_postal_url = urllib.parse.quote(code_recherche)
    
    if cle_recherche in ["MARCHÉ AMI", "MARCHÉ BONICHOIX", "MARCHÉ RICHELIEU", "MARCHÉ TRADITION", "COSTCO"]:
        url_final_site = f"https://google.com/maps/search/?api=1&query={urllib.parse.quote(f'{banniere_active} {code_recherche}')}"
    elif "superc" in url_base_site or "metro" in url_base_site:
        url_final_site = f"{url_base_site}?search={code_postal_url}"
    elif "maxi" in url_base_site or "provigo" in url_base_site:
        url_final_site = f"{url_base_site}?searchQuery={code_postal_url}"
    elif "walmart" in url_base_site or "gianttiger" in url_base_site:
        url_final_site = f"{url_base_site}?q={code_postal_url}"
    elif "dollarama" in url_base_site:
        url_final_site = f"{url_base_site}?localisation={code_postal_url}"
    else:
        url_final_site = url_base_site

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.link_button("🌐 Site général de la bannière", url_base_site, use_container_width=True)
    with col_l2:
        st.link_button(f"📍 Trouver ma succursale", url_final_site, type="primary", use_container_width=True)

    st.write("---")

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
                image_aliment = Image.open(os.path.join(chemin_dossier_images, photo))

                with grille_visuelle[index % 2]:
                    st.image(image_aliment, use_container_width=True)

                    if st.button(f"➕ Ajouter ce spécial", key=f"btn_photo_{index}", use_container_width=True, type="primary"):
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
                                nom_automatique = nom_complet_sans_ext.replace("_", " ").capitalize()
                        else:
                            prix_automatique = 0.00
                            nom_automatique = nom_complet_sans_ext.replace("_", " ").capitalize()

                        st.session_state["panier_achats"].append({
                            "magasin": banniere_active,
                            "catégorie": "🍎 Circulaire Visuelle",
                            "produit": nom_automatique,
                            "prix": prix_automatique,
                        })
                        st.toast(f"✅ {nom_automatique} ajouté au panier !", icon="🛒")
                        st.rerun()
                    st.write("")
        else:
            st.info("Aucune photo dans ce dossier pour le moment.")
    else:
        st.warning(f"Dossier introuvable : {DOSSIER_BANNIERES}/{nom_sous_dossier}")
