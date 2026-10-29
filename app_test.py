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
# SECTION À GAUCHE : BARRE LATÉRALE PROPRE + BOUTON GUIDE D'ACHAT
# =========================================================================
st.sidebar.markdown("<h2 style='font-size: 22px; color: #1E3A8A; margin-bottom: 10px;'>⚙️ Critères de recherche</h2>", unsafe_allow_html=True)
saisie_utilisateur = st.sidebar.text_input(
    "Entrez votre code postal (ex: G0M 1G0)", "G0M1G0"
)
code_recherche = saisie_utilisateur.replace(" ", "").upper()
rayon_max = st.sidebar.slider(
    "Rayon maximum de recherche (km)", 5, 100, 25, 5
)

# LE BOUTON ROUGE EST PLACÉ ICI POUR OFFRIR UN LOOK ÉPURÉ SUR MOBILE
st.sidebar.write("---")
st.sidebar.link_button(
    "⚙️ Ouvrir l'application Mon Guide d'Achat Local (Scanner / Pays d'Origine)",
    "https://streamlit.app",
    type="primary",
    use_container_width=True,
)

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
        
        bannieres_disponibles = ["Toutes les bannières"] + sorted(
            list(df_magasins["Nom_Commerce"].dropna().unique())
        )
        banniere_selectionnee = st.sidebar.selectbox(
            "Filtrer par bannière :", bannieres_disponibles, index=bannieres_disponibles.index(st.session_state["banniere_manuelle"]) if st.session_state["banniere_manuelle"] in bannieres_disponibles else 0
        )

        if banniere_selectionnee != "Toutes les bannières":
            st.session_state["banniere_manuelle"] = banniere_selectionnee
            resultats_filtres = resultats_filtres[
                resultats_filtres["Nom_Commerce"] == banniere_selectionnee
            ]

        banniere_active = st.session_state["banniere_manuelle"]

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
# EN-TÊTE PRINCIPAL LOOK APPLICATION MOBILE BANDEAU BLEU
# =========================================================================
st.markdown(
    """
    <div style="background-color: #1E3A8A; padding: 15px; border-radius: 10px; margin-bottom: 15px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 26px; font-weight: bold;">🍎 Mon Planificateur Anti-Inflation</h1>
        <p style="color: #E0E7FF; margin: 3px 0 0 0; font-size: 13px;">Optimisez votre facture d'épicerie sur le pouce</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- NOUVEAU MESSAGE DE GUIDAGE POUR LE MODE CÔTE À CÔTE ---
st.markdown(
    f"""
    <div style="background-color: #E0F2FE; border-left: 5px solid #0284C7; padding: 12px; border-radius: 4px; margin-bottom: 15px;">
        <p style="margin: 0; color: #0369A1; font-size: 14px; font-weight: bold;">
            💡 <strong>Astuce multi-fenêtres :</strong> Cliquez sur le bouton rouge dans la colonne de droite pour ouvrir la circulaire. Glissez cet onglet d'application à gauche de votre écran et la circulaire à droite pour travailler côte à côte !
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================================
# 📱 RÉORGANISATION EN ONGLETS POUR CELLULAIRE (FUSION DES ANCIENS ONGLETS 1 & 2)
# =========================================================================
onglet_travail, onglet_facture = st.tabs([
    f"✍️ 1. Préparer mes Rabais ({code_recherche})", 
    "🛍️ 2. Ma Facture Finale"
])

# -------------------------------------------------------------------------
# ONGLET 1 : LA ZONE DE TRAVAIL CÔTE-À-CÔTE (FORMULAIRE À GAUCHE / LIENS À DROITE)
# -------------------------------------------------------------------------
with onglet_travail:
    cle_recherche = str(banniere_active).upper().strip()
    url_base_site = LIENS_OFFICIELS.get(cle_recherche, "https://google.com")
    code_postal_url = urllib.parse.quote(code_recherche)
    
    if cle_recherche in ["MARCHÉ AMI", "MARCHÉ BONICHOIX", "MARCHÉ RICHELIEU", "MARCHÉ TRADITION", "COSTCO"]:
        url_final_site = f"https://google.com{urllib.parse.quote(f'{banniere_active} {code_recherche}')}"
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

    # Création des deux colonnes côte à côte
    col_gauche_formulaire, col_droite_circulaire = st.columns(2)

    # --- COLONNE DE GAUCHE : LE FORMULAIRE DE SAISIE ---
    with col_gauche_formulaire:
        with st.container(border=True):
            st.markdown(f"<h3 style='font-size: 18px; color: #1E3A8A; font-weight: 600; margin-top: 0px;'>✍️ Ajouter un article trouvé</h3>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 14px; margin-bottom: 10px;'>Magasin actif : <strong>{banniere_active}</strong></p>", unsafe_allow_html=True)

            categorie = st.selectbox(
                "Sélectionner le rayon :",
                ["🍎 Fruits et Légumes", "🥩 Viandes et Poissons", "🧀 Produits laitiers", "🍞 Boulangerie", "📦 Épicerie / Boîtes", "🧼 Entretien / Autre"],
                key="select_cat_travail"
            )

            nom_article = st.text_input("Nom de l'article :", placeholder="Ex: Banane, Beurre...", key="input_nom_travail")
            prix_article = st.number_input("Prix en spécial ($) :", value=0.00, step=0.01, key="input_prix_travail")

            if st.button("✨ Enregistrer l'article", use_container_width=True, key="btn_save_travail"):
                if nom_article:
                    st.session_state["panier_achats"].append({
                        "magasin": banniere_active,
                        "catégorie": categorie,
                        "produit": nom_article,
                        "prix": prix_article,
                    })
                    st.toast(f"✅ {nom_article} enregistré !", icon="🛒")
                    st.rerun()
                else:
                    st.warning("Veuillez entrer un nom d'article.")

    # --- COLONNE DE DROITE : L'ACCÈS À LA CIRCULAIRE ---
    with col_droite_circulaire:
        with st.container(border=True):
            st.markdown(f"<h3 style='font-size: 18px; color: #1E3A8A; font-weight: bold; margin-top: 0px;'>🔗 Lien de consultation</h3>", unsafe_allow_html=True)
            
            # Bouton unique intelligent et recyclable
            html_bouton_dynamique = f"""
            <div style="display: flex; justify-content: center; width: 100%; margin: 5px 0;">
                <a href="{url_final_site}" target="succursale_unique" rel="opener" style="
                    text-decoration: none; 
                    padding: 12px 20px; 
                    background-color: #ff4b4b; 
                    color: white; 
                    border: 1px solid #ff4b4b;
                    border-radius: 6px; 
                    font-size: 14px;
                    font-family: sans-serif;
                    font-weight: bold;
                    display: inline-block;
                    text-align: center;
                    box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
                    width: 100%;">
                    📍 Ouvrir la circulaire {banniere_active.title()}
                </a>
            </div>
            """
            st.markdown(html_bouton_dynamique, unsafe_allow_html=True)

        # Affichage des coupures locales si elles existent
        st.write("")
        nom_sous_dossier = str(banniere_active).lower().replace(" ", "_").replace("é", "e").replace("è", "e").replace("à", "a")
        chemin_dossier_images = os.path.join(DOSSIER_BANNIERES, nom_sous_dossier)

        if os.path.exists(chemin_dossier_images):
            fichiers_photos = [f for f in os.listdir(chemin_dossier_images) if f.lower().endswith((".png", ".jpg", ".jpeg"))]

            if fichiers_photos:
                st.markdown("<h4 style='font-size: 15px; margin-top: 10px;'>📸 Coupures de circulaires locales :</h4>", unsafe_allow_html=True)
                grille_visuelle = st.columns(2)
                for index, photo in enumerate(fichiers_photos):
                    image_aliment = Image.open(os.path.join(chemin_dossier_images, photo))

                    with grille_visuelle[index % 2]:
                        st.image(image_aliment, use_container_width=True)

                        if st.button(f"➕ Ajouter", key=f"btn_photo_{index}", use_container_width=True, type="primary"):
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
                with st.container(border=True):
                    st.info("Aucun feuillet visuel téléversé. Utilisez le bouton rouge pour ouvrir le site externe !")
        else:
            with st.container(border=True):
                st.warning(f"Répertoire d'images introuvable : {DOSSIER_BANNIERES}/{nom_sous_dossier}")
# -------------------------------------------------------------------------
# ONGLET 2 : FACTURE SIMULÉE ET COMPARATEUR DE BANNIÈRES (ANCIEN ONGLET 3)
# -------------------------------------------------------------------------
with onglet_facture:
    with st.container(border=True):
        st.markdown("<h3 style='font-size: 20px; color: #1E3A8A; font-weight: 600; margin-top: 0px;'>🛍️ Ma facture d'épicerie simulée</h3>", unsafe_allow_html=True)
        
        if st.session_state["panier_achats"]:
            df_panier = pd.DataFrame(st.session_state["panier_achats"])
            
            df_affichage = df_panier.rename(columns={"magasin": "Magasin", "catégorie": "Rayon", "produit": "Article", "prix": "Prix"})
            df_affichage["Prix"] = df_affichage["Prix"].map("{:.2f} $".format)
            st.dataframe(df_affichage, use_container_width=True, hide_index=True)
            
            st.markdown("<h4 style='font-size: 15px; color: #4B5563; font-weight: bold; margin-top: 10px;'>📊 Répartition de mes dépenses :</h4>", unsafe_allow_html=True)
            df_comparatif = df_panier.groupby("magasin")["prix"].sum().reset_index()
            
            for _, rangee in df_comparatif.iterrows():
                st.markdown(f"🔹 Total estimé chez **{rangee['magasin']}** : `{rangee['prix']:.2f} $`")
            
            st.markdown(
                f"""
                <div style="background-color: #FEF2F2; border: 2px dashed #EF4444; padding: 12px; border-radius: 8px; text-align: center; margin-top: 15px;">
                    <span style="color: #991B1B; font-size: 14px; font-weight: bold; display: block; text-transform: uppercase;">Estimation totale</span>
                    <span style="color: #DC2626; font-size: 30px; font-weight: 900; font-family: monospace;">{df_panier['prix'].sum():.2f} $</span>
                </div>
                """, 
                unsafe_allow_html=True
            )
            st.write("")
            if st.button("🗑️ Réinitialiser ma liste", use_container_width=True, key="btn_mobile_clear"):
                st.session_state["panier_achats"] = []
                st.rerun()
        else:
            st.info("Votre liste d'épicerie est vide. Parcourez l'onglet de préparation pour commencer !")
