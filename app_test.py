import os
import urllib.parse
import pandas as pd
import streamlit as st
from PIL import Image

# Importation de vos fonctions géographiques depuis fonctions_geo.py
from fonctions_geo import calculer_distance, charger_donnees

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Planificateur Budget Épicerie",
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
# SECTION À GAUCHE : BARRE LATÉRALE PROPRE
# =========================================================================
st.sidebar.markdown("<h2 style='font-size: 22px; color: #1E3A8A; margin-bottom: 10px;'>⚙️ Critères de recherche</h2>", unsafe_allow_html=True)
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

st.sidebar.markdown("<h3 style='font-size: 18px; color: #1E3A8A;'>📍 Commerces à proximité</h3>", unsafe_allow_html=True)
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
                    f"**{nom_magasin}** ({distance:.1f} km)<br/><small style='color: #6B7280;'>{rangee.get('Adresse_Rue', '')}</small>",
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
# =========================================================================
# EN-TÊTE PRINCIPAL LOOK APPLICATION BANDEAU BLEU
# =========================================================================
st.markdown(
    """
    <div style="background-color: #1E3A8A; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 36px; font-weight: bold;">🍎 Mon Planificateur Anti-Inflation</h1>
        <p style="color: #E0E7FF; margin: 5px 0 0 0; font-size: 16px;">Comparez vos bannières et optimisez votre facture d'épicerie gratuitement</p>
    </div>
    """,
    unsafe_allow_html=True
)

# LA LIGNE ROUGE FLUIDE
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
# COLONNE DE GAUCHE : FORMULAIRE EN CARTES + RECU DE FACTURE STYLE TICKET
# =========================================================================
with col_gauche:
    with st.container(border=True):
        st.markdown("<h2 style='font-size: 24px; color: #1E3A8A; font-weight: 600; margin-top: 0px;'>🔍 Étape 1 : Saisie de ma liste</h2>", unsafe_allow_html=True)
        
        st.markdown(
            f"""
            <div style="background-color: #EFF6FF; padding: 10px; border-left: 5px solid #3B82F6; border-radius: 4px; margin-bottom: 15px;">
                <span style="color: #1E40AF; font-weight: bold; font-size: 16px;">🛒 Magasin actif : {banniere_active}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        categorie = st.selectbox(
            "Sélectionner le rayon :",
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

        if st.button("✨ Enregistrer l'article", use_container_width=True):
            if nom_article:
                st.session_state["panier_achats"].append(
                    {
                        "magasin": banniere_active,
                        "catégorie": categorie,
                        "produit": nom_article,
                        "prix": prix_article,
                    }
                )
                st.toast("Article enregistré !", icon="✅")
                st.rerun()
            else:
                st.warning("Veuillez entrer un nom d'article.")

    st.write("")

    with st.container(border=True):
        st.markdown("<h2 style='font-size: 24px; color: #1E3A8A; font-weight: 600; margin-top: 0px;'>🛍️ Ma facture d'épicerie simulée</h2>", unsafe_allow_html=True)
        
        if st.session_state["panier_achats"]:
            df_panier = pd.DataFrame(st.session_state["panier_achats"])
            
            df_affichage = df_panier.rename(columns={
                "magasin": "Magasin",
                "catégorie": "Rayon",
                "produit": "Article",
                "prix": "Prix"
            })
            df_affichage["Prix"] = df_affichage["Prix"].map("{:.2f} $".format)
            st.dataframe(df_affichage, use_container_width=True, hide_index=True)
            
            st.markdown("<h4 style='font-size: 16px; color: #4B5563; font-weight: bold; margin-top: 15px;'>📊 Répartition de mes dépenses par enseigne :</h4>", unsafe_allow_html=True)
            df_comparatif = df_panier.groupby("magasin")["prix"].sum().reset_index()
            
            for _, rangee in df_comparatif.iterrows():
                magasin_nom = rangee["magasin"]
                total_magasin = rangee["prix"]
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; background-color: #F9FAFB; padding: 6px 12px; border-radius: 4px; margin-bottom: 4px; border: 1px solid #E5E7EB;">
                        <span style="font-weight: 500;">Sous-total <strong>{magasin_nom}</strong></span>
                        <span style="font-family: monospace; font-weight: bold; color: #111827;">{total_magasin:.2f} $</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            
            st.markdown(
                f"""
                <div style="background-color: #FEF2F2; border: 2px dashed #EF4444; padding: 15px; border-radius: 8px; text-align: center; margin-top: 20px; margin-bottom: 15px;">
                    <span style="color: #991B1B; font-size: 16px; font-weight: bold; display: block; text-transform: uppercase; letter-spacing: 1px;">Estimation totale cumulée</span>
                    <span style="color: #DC2626; font-size: 36px; font-weight: 900; font-family: monospace;">{df_panier['prix'].sum():.2f} $</span>
                </div>
                """, 
                unsafe_allow_html=True
            )

            if st.button("🗑️ Réinitialiser ma liste", use_container_width=True):
                st.session_state["panier_achats"] = []
                st.rerun()
        else:
            st.info("Votre liste d'épicerie est vide pour le moment. Trouvez des rabais à droite et ajoutez-les ici !")

# =========================================================================
# COLONNE DE DROITE : CONFIGURATION DE LA LISEUSE VISUELLE D'ORIGINE
# =========================================================================
with col_droite:
    st.subheader(f"📸 Circulaire visuelle : {banniere_active}")

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
                        st.toast(f"✅ {nom_automatique} ajouté !", icon="🛒")
                        st.rerun()
                    st.write("")
        else:
            st.info("Aucune photo dans ce dossier pour le moment.")
    else:
        st.warning(f"Dossier introuvable : {DOSSIER_BANNIERES}/{nom_sous_dossier}")
