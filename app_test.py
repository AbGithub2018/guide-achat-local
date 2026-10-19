import streamlit as st
import pandas as pd
import numpy as np
import urllib.parse

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Recherche géolocalisée et Budget Épicerie",
    page_icon="🍎",
    layout="wide"
)

# --- INITIALISATION DE LA MÉMOIRE DE SESSION ---
if "panier_achats" not in st.session_state:
    st.session_state["panier_achats"] = []

# --- DICTIONNAIRE DES LIENS D'INTÉGRATION FLIPP (REEBEE) ---
FLIPP_EMBED_URLS = {
    "IGA": "https://flipp.com",
    "SUPER C": "https://flipp.com",
    "METRO": "https://flipp.com",
    "MAXI": "https://flipp.com",
    "PROVIGO": "https://flipp.com",
    "DOLLARAMA": "https://flipp.com",
    "TIGRE GEANT": "https://flipp.com",
    "TIGRE GÉANT": "https://flipp.com",
    "WALMART": "https://flipp.com",
    "COSTCO": "https://flipp.com",
    "MARCHE TRADITION": "https://flipp.com",
    "MARCHÉ TRADITION": "https://flipp.com",
    "MARCHE BONICHOIX": "https://flipp.com",
    "MARCHÉ BONICHOIX": "https://flipp.com",
    "MARCHE RICHELIEU": "https://flipp.com",
    "MARCHÉ RICHELIEU": "https://flipp.com",
    "MARCHE ADONIS": "https://flipp.com"
}

# --- FONCTION DE CALCUL DE DISTANCE (HAVERSINE) ---
def calculer_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# --- CHARGEMENT SÉCURISÉ DES DONNÉES ---
@st.cache_data
def charger_donnees():
    try:
        df_coords = pd.read_csv('codes_qc.csv', sep=';')
        df_magasins = pd.read_csv('disponibilite_magasins.csv')
        df_coords['Code postal'] = df_coords['Code postal'].astype(str).str.replace(" ", "").str.upper()
        df_magasins['Code postal'] = df_magasins['Code postal'].astype(str).str.replace(" ", "").str.upper()
        return df_coords, df_magasins
    except Exception as e:
        st.error(f"Erreur lors de la lecture des fichiers : {e}")
        return None, None

df_coords, df_magasins = charger_donnees()

if df_coords is None or df_magasins is None:
    st.stop()

# --- BARRE LATÉRALE : FILTRES ---
st.sidebar.header("Critères de recherche")
saisie_utilisateur = st.sidebar.text_input("Entrez votre code postal (ex: G0M 1G0)", "G0M1G0")
code_recherche = saisie_utilisateur.replace(" ", "").upper()
rayon_max = st.sidebar.slider("Rayon maximum de recherche (km)", min_value=5, max_value=100, value=25, step=5)

bannieres_disponibles = ["Toutes les bannières"] + sorted(list(df_magasins['Nom_Commerce'].dropna().unique()))
banniere_selectionnee = st.sidebar.selectbox("Filtrer par bannière :", bannieres_disponibles)

# --- RECHERCHE DE LA BANNIÈRE À AFFICHER DANS LA LISEUSE ---
banniere_active = "MAXI"  # Par défaut à l'ouverture
if banniere_selectionnee != "Toutes les bannières":
    banniere_active = banniere_selectionnee

# --- ZONE PRINCIPALE ---
st.title("🍎 Planificateur de Budget Épicerie")

# Redirection vers votre application officielle
st.link_button(
    "⚙️ Ouvrir l'application Mon Guide d'Achat Local (Scanner un Code-Barres / Pays d'Origine)", 
    "https://achatquebec.streamlit.app",
    type="primary",
    use_container_width=True
)
st.write("---")

# --- DIVISION DE L'ÉCRAN PRINCIPAL EN DEUX MOITIÉS (50% / 50%) ---
col_gauche, col_droite = st.columns([1.0, 1.0])

# =========================================================================
# COLONNE DE GAUCHE : RECHERCHE GÉOLOCALISÉE ET FORMULAIRE DE LISTE
# =========================================================================
with col_gauche:
    st.subheader("🔍 Étape 1 : Saisie de ma liste d'épicerie")
    
    # Formulaire d'ajout rapide d'un article
    with st.expander("➕ Ajouter un rabais trouvé à ma liste", expanded=True):
        liste_bannieres_quebec = sorted(list(df_magasins['Nom_Commerce'].dropna().unique()))
        magasin_choisi = st.selectbox("Sélectionner le magasin :", [""] + liste_bannieres_quebec)
        nom_produit = st.text_input("Nom de l'article :", placeholder="Ex: Poitrines de poulet, Beurre...")
        prix_produit = st.number_input("Prix en spécial ($) :", min_value=0.00, value=0.00, step=0.05, format="%.2f")
        
        if magasin_choisi != "":
            banniere_active = magasin_choisi
            
        if st.button("Enregistrer l'article", use_container_width=True):
            if magasin_choisi == "":
                st.error("Veuillez sélectionner un magasin.")
            elif nom_produit.strip() == "":
                st.error("Veuillez entrer le nom d'un produit.")
            elif prix_produit <= 0:
                st.error("Veuillez entrer un prix valide.")
            else:
                nouvel_achat = {
                    "magasin": magasin_choisi,
                    "produit": nom_produit.strip(),
                    "prix": prix_produit
                }
                st.session_state["panier_achats"].append(nouvel_achat)
                st.toast(f"✅ {nom_produit} enregistré !", icon="🛒")
                st.rerun()

    # Zone d'affichage dynamique de la liste de courses et de la facture
    if st.session_state["panier_achats"]:
        st.write("### 🛍️ Mon panier de la semaine")
        df_panier = pd.DataFrame(st.session_state["panier_achats"])
        total_facture = df_panier["prix"].sum()
        
        for magasin, groupe in df_panier.groupby("magasin"):
            st.markdown(f"🔹 **{magasin}**")
            for idx, row in groupe.iterrows():
                col_item_text, col_item_check = st.columns([0.6, 0.4])
                with col_item_text:
                    st.write(f"• {row['produit']} — **{row['prix']:.2f} $**")
                with col_item_check:
                    nom_nettoye_url = urllib.parse.quote(row['produit'])
                    st.link_button("🧐 Vérifier l'origine", f"https://achatquebec.streamlit.app/?cup={nom_nettoye_url}", use_container_width=True)
                
        st.markdown(f"### 💰 Total estimé de ma facture : **{total_facture:.2f} $**")
        
        if st.button("🗑️ Vider ma liste d'épicerie", use_container_width=True):
            st.session_state["panier_achats"] = []
            st.rerun()

    st.write("---")
    
    # Affichage des commerces triés géographiquement
    st.subheader("📍 Commerces les plus proches")
    if code_recherche:
        point_origine = df_coords[df_coords['Code postal'] == code_recherche]
        
        if not point_origine.empty:
            # CORRECTION APPLIQUÉE ICI : Ajout du [0] pour indexer correctement la ligne avec .iloc
            lat_centre = float(point_origine.iloc[0]['Latitude'])
            lon_centre = float(point_origine.iloc[0]['Longitude'])
            ville_centre = point_origine.iloc[0]['Ville']
            
            st.caption(f"Position : {ville_centre} ({saisie_utilisateur.upper()})")
            
            df_magasins_gps = pd.merge(df_magasins, df_coords, on='Code postal', how='inner', suffixes=('', '_Ref'))
            df_magasins_gps['Distance_KM'] = calculer_distance(lat_centre, lon_centre, df_magasins_gps['Latitude'], df_magasins_gps['Longitude'])
            
            resultats_filtres = df_magasins_gps[df_magasins_gps['Distance_KM'] <= rayon_max]
            if banniere_selectionnee != "Toutes les bannières":
                resultats_filtres = resultats_filtres[resultats_filtres['Nom_Commerce'] == banniere_selectionnee]
                
            resultats_filtres = resultats_filtres.sort_values(by='Distance_KM')
            
            if not resultats_filtres.empty:
                for index, rangee in resultats_filtres.iterrows():
                    nom_magasin = rangee['Nom_Commerce']
                    adresse = rangee.get('Adresse_Rue', 'Adresse non disponible')
                    distance = rangee['Distance_KM']
                    
                    col_info, col_action = st.columns(2)
                    with col_info:
                        st.markdown(f"**{nom_magasin}** ({distance:.1f} km)<br/><small>{adresse}</small>", unsafe_allow_html=True)
                    with col_action:
                        if st.button("📖 Consulter", key=f"voir_{index}", use_container_width=True):
                            st.session_state["banniere_manuelle"] = nom_magasin
                            st.rerun()
            else:
                st.warning("Aucun commerce trouvé dans ce rayon.")
        else:
            st.error("Code postal introuvable.")

# =========================================================================
# COLONNE DE DROITE : LA CIRCULAIRE INTERACTIVE FLIPP / REEBEE DIRECTE
# =========================================================================
with col_droite:
    if "banniere_manuelle" in st.session_state:
        banniere_active = st.session_state["banniere_manuelle"]

    st.subheader(f"📖 Circulaire en direct : {banniere_active}")
    
    cle_recherche_flipp = str(banniere_active).strip().upper()
    url_embed_flipp = FLIPP_EMBED_URLS.get(cle_recherche_flipp, "https://flipp.com")
    
    st.iframe(url_embed_flipp, height=800)
