import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Recherche géolocalisée de commerces au Québec",
    page_icon="🍎",
    layout="wide"
)

# --- DICTIONNAIRE DE CORRESPONDANCE DES URLS ---
BANNIERE_URLS = {
    "IGA": "https://iga.net",
    "SUPER C": "https://superc.ca",
    "METRO": "https://metro.ca",
    "MAXI": "https://maxi.ca",
    "PROVIGO": "https://provigo.ca",
    "DOLLARAMA": "https://dollarama.com",
    "MARCHE AMI": "https://marcheami.ca",
    "TIGRE GEANT": "https://gianttiger.com",
    "WALMART": "https://walmart.ca",
    "COSTCO": "https://costco.ca",
    "MARCHE TRADITION": "https://marchetradition.com",
    "MARCHE BONICHOIX": "https://bonichoix.com",
    "MARCHE RICHELIEU": "https://marcherichelieu.com",
    "MARCHE ADONIS": "https://groupeadonis.ca"
}

# --- FONCTION DE CALCUL DE DISTANCE (HAVERSINE) ---
def calculer_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance en kilomètres entre deux points de coordonnées géographiques."""
    R = 6371.0  # Rayon de la Terre en kilomètres
    
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
        # Fichier 1 : Chargement des coordonnées géographiques (Séparateur ;)
        df_coords = pd.read_csv('codes_qc.csv', sep=';')
        # Fichier 2 : Chargement des magasins disponibles (Séparateur , par défaut)
        df_magasins = pd.read_csv('disponibilite_magasins.csv')
        
        # Nettoyage préventif des colonnes de codes postaux (MAJUSCULES et SANS ESPACES)
        df_coords['Code postal'] = df_coords['Code postal'].astype(str).str.replace(" ", "").str.upper()
        df_magasins['Code postal'] = df_magasins['Code postal'].astype(str).str.replace(" ", "").str.upper()
        
        return df_coords, df_magasins
    except Exception as e:
        st.error(f"Erreur lors de la lecture des fichiers : {e}")
        return None, None

df_coords, df_magasins = charger_donnees()

# Si les fichiers n'ont pas pu charger, on arrête le script proprement
if df_coords is None or df_magasins is None:
    st.stop()

# --- BARRE LATÉRALE : CRITÈRES DE RECHERCHE ---
st.sidebar.header("Critères de recherche")

# Saisie du code postal
saisie_utilisateur = st.sidebar.text_input("Entrez votre code postal (ex: G0M 1G0)", "G0M1G0")
# Nettoyage immédiat de la saisie utilisateur
code_recherche = saisie_utilisateur.replace(" ", "").upper()

# Curseur de rayon de recherche
rayon_max = st.sidebar.slider("Rayon maximum de recherche (km)", min_value=5, max_value=100, value=25, step=5)

# Filtre par bannière
bannieres_disponibles = ["Toutes les bannières"] + sorted(list(df_magasins['Nom_Commerce'].dropna().unique()))
banniere_selectionnee = st.sidebar.selectbox("Filtrer par bannière :", bannieres_disponibles)


# --- ZONE PRINCIPALE : RÉSULTATS ---
st.title("🍎 Recherche géolocalisée de commerces au Québec")

if code_recherche:
    # 1. Trouver les coordonnées GPS du code postal recherché
    point_origine = df_coords[df_coords['Code postal'] == code_recherche]
    
    if not point_origine.empty:
        # Extraction de la latitude et longitude d'origine
        lat_centre = point_origine.iloc[0]['Latitude']
        lon_centre = point_origine.iloc[0]['Longitude']
        ville_centre = point_origine.iloc[0]['Ville']
        
        st.info(f"📍 Position détectée : **{ville_centre}** ({saisie_utilisateur.upper()})")
        
        # 2. Associer chaque magasin à ses coordonnées GPS via son code postal
        # On fusionne temporairement les magasins avec le référentiel des coordonnées géographiques
        df_magasins_gps = pd.merge(df_magasins, df_coords, on='Code postal', how='inner', suffixes=('', '_Ref'))
        
        # 3. Calculer la distance pour chaque magasin trouvé
        df_magasins_gps['Distance_KM'] = calculer_distance(
            lat_centre, lon_centre, 
            df_magasins_gps['Latitude'], df_magasins_gps['Longitude']
        )
        
        # 4. Filtrer les résultats selon les choix de l'utilisateur (Rayon et Bannière)
        resultats_filtres = df_magasins_gps[df_magasins_gps['Distance_KM'] <= rayon_max]
        
        if banniere_selectionnee != "Toutes les bannières":
            resultats_filtres = resultats_filtres[resultats_filtres['Nom_Commerce'] == banniere_selectionnee]
            
        # Trier du plus proche au plus lointain
        resultats_filtres = resultats_filtres.sort_values(by='Distance_KM')
        
        # 5. Affichage des résultats
        if not resultats_filtres.empty:
            st.success(f"🎉 {len(resultats_filtres)} commerce(s) trouvé(s) dans un rayon de {rayon_max} km.")
            
            # Grille visuelle propre pour afficher les commerces
            for index, rangee in resultats_filtres.iterrows():
                nom_magasin = rangee['Nom_Commerce']
                adresse = rangee.get('Adresse_Rue', 'Adresse non disponible')
                municipalite = rangee.get('Municipalite', '')
                distance = rangee['Distance_KM']
                
                # Bloc visuel pour un magasin
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"### **{nom_magasin}**")
                        st.write(f"📍 {adresse}, {municipalite} *(à {distance:.1f} km)*")
                    
                    with col2:
                        # Logique d'affichage dynamique du lien vers les spéciaux
                        cle_banniere = str(nom_magasin).strip().upper()
                        if cle_banniere in BANNIERE_URLS:
                            url_circulaire = BANNIERE_URLS[cle_banniere]
                            st.link_button(f"🔗 Circulaire {nom_magasin}", url_circulaire, use_container_width=True)
                        else:
                            st.caption("Aucun lien disponible")
                            
                    st.divider() # Ligne de séparation entre les commerces
        else:
            st.warning(f"Aucun commerce ne correspond à vos critères dans un rayon de {rayon_max} km.")
            
    else:
        st.error("❌ Code postal introuvable ou invalide dans la base de données du Québec.")
