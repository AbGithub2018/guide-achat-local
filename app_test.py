import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Recherche géolocalisée de commerces au Québec",
    page_icon="🍎",
    layout="wide"
)

# --- INITIALISATION DE LA LISTE D'ÉPICERIE (MÉMOIRE SESSION) ---
if "liste_epicerie" not in st.session_state:
    st.session_state["liste_epicerie"] = []

# --- DICTIONNAIRE DE CORRESPONDANCE DES URLS ---
BANNIERE_URLS = {
    "IGA": "https://www.iga.ca/fr/circulaire",
    "SUPER C": "https://www.superc.ca/circulaire",
    "METRO": "https://www.metro.ca/circulaire",
    "MAXI": "https://maxi.ca",
    "PROVIGO": "https://provigo.ca",
    "DOLLARAMA": "https://www.dollarama.com/fr-ca/",
    "MARCHE AMI": "https://www.marcheami.ca/circulaire",
    "MARCHÉ AMI": "https://www.marcheami.ca/circulaire",
    "TIGRE GEANT": "https://gianttiger.com",
    "TIGRE GÉANT": "https://gianttiger.com",
    "WALMART": "https://walmart.ca",
    "COSTCO": "https://www.costco.ca/grocery-household.html?langId=-25",
    "MARCHE TRADITION": "https://marchetradition.com",
    "MARCHÉ TRADITION": "https://marchetradition.com",
    "MARCHE BONICHOIX": "https://www.bonichoix.com/fr/notre-circulaire/",
    "MARCHÉ BONICHOIX": "https://www.bonichoix.com/fr/notre-circulaire/",
    "MARCHE RICHELIEU": "https://www.marcherichelieu.ca/circulaire",
    "MARCHÉ RICHELIEU": "https://www.marcherichelieu.ca/circulaire",
    "MARCHE ADONIS": "https://groupeadonis.ca/circulaire"
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

# --- BARRE LATÉRALE : CRITÈRES ET RECHERCHE ---
st.sidebar.header("Critères de recherche")
saisie_utilisateur = st.sidebar.text_input("Entrez votre code postal (ex: G0M 1G0)", "G0M1G0")
code_recherche = saisie_utilisateur.replace(" ", "").upper()
rayon_max = st.sidebar.slider("Rayon maximum de recherche (km)", min_value=5, max_value=100, value=25, step=5)

bannieres_disponibles = ["Toutes les bannières"] + sorted(list(df_magasins['Nom_Commerce'].dropna().unique()))
banniere_selectionnee = st.sidebar.selectbox("Filtrer par bannière :", bannieres_disponibles)

# --- BARRE LATÉRALE : AFFICHAGE DE LA LISTE D'ÉPICERIE ---
st.sidebar.write("---")
st.sidebar.header("📝 Ma liste de magasins")

if st.session_state["liste_epicerie"]:
    # Zone de texte optionnelle pour ajouter une note (ex: des articles à acheter)
    st.sidebar.caption("Magasins sélectionnés pour votre tournée :")
    for item_ajoute in st.session_state["liste_epicerie"]:
        st.sidebar.write(f"- {item_ajoute}")
        
    st.sidebar.write("")
    # Bouton pour vider le panier
    if st.sidebar.button("🗑️ Vider la liste", use_container_width=True):
        st.session_state["liste_epicerie"] = []
        st.rerun()
else:
    st.sidebar.caption("Votre liste est vide. Utilisez le bouton ➕ sous les commerces trouvés pour planifier votre épicerie.")


# --- ZONE PRINCIPALE ---
st.title("🍎 Recherche géolocalisée de commerces au Québec")

if code_recherche:
    point_origine = df_coords[df_coords['Code postal'] == code_recherche]
    
    if not point_origine.empty:
        lat_centre = float(point_origine.iloc[0]['Latitude'])
        lon_centre = float(point_origine.iloc[0]['Longitude'])
        ville_centre = point_origine.iloc[0]['Ville']
        
        st.info(f"📍 Position détectée : **{ville_centre}** ({saisie_utilisateur.upper()})")
        
        df_magasins_gps = pd.merge(df_magasins, df_coords, on='Code postal', how='inner', suffixes=('', '_Ref'))
        df_magasins_gps['Distance_KM'] = calculer_distance(
            lat_centre, lon_centre, 
            df_magasins_gps['Latitude'], df_magasins_gps['Longitude']
        )
        
        resultats_filtres = df_magasins_gps[df_magasins_gps['Distance_KM'] <= rayon_max]
        if banniere_selectionnee != "Toutes les bannières":
            resultats_filtres = resultats_filtres[resultats_filtres['Nom_Commerce'] == banniere_selectionnee]
            
        resultats_filtres = resultats_filtres.sort_values(by='Distance_KM')
        
        if not resultats_filtres.empty:
            st.success(f"🎉 {len(resultats_filtres)} commerce(s) trouvé(s) dans un rayon de {rayon_max} km.")
            
            # --- CARTE SIMPLIFIÉE STABLE ---
            df_carte = resultats_filtres[['Latitude', 'Longitude']].copy()
            df_carte.columns = ['latitude', 'longitude']
            st.map(df_carte, size=20, color="#FF0000")
            
            st.write("---")
            
            # Grille visuelle sous la carte
            for index, rangee in resultats_filtres.iterrows():
                nom_magasin = rangee['Nom_Commerce']
                adresse = rangee.get('Adresse_Rue', 'Adresse non disponible')
                municipalite = rangee.get('Municipalite', '')
                distance = rangee['Distance_KM']
                
                with st.container():
                    col1, col2 = st.columns(2)  # Définition propre des colonnes
                    with col1:
                        st.markdown(f"### **{nom_magasin}**")
                        st.write(f"📍 {adresse}, {municipalite} *(à {distance:.1f} km)*")
                    with col2:
                        st.write("")
                        
                        # Bouton 1 : Lien de la circulaire
                        cle_banniere = str(nom_magasin).strip().upper()
                        if cle_banniere in BANNIERE_URLS:
                            st.link_button(f"🔗 Circulaire {nom_magasin}", BANNIERE_URLS[cle_banniere], use_container_width=True)
                        else:
                            st.caption("Aucun lien disponible")
                        
                        # Bouton 2 : Ajouter à la liste d'épicerie
                        identifiant_bouton = f"btn_liste_{index}"
                        texte_magasin = f"**{nom_magasin}** - {municipalite}"
                        
                        if st.button(f"➕ Planifier ce magasin", key=identifiant_bouton, use_container_width=True):
                            if texte_magasin not in st.session_state["liste_epicerie"]:
                                st.session_state["liste_epicerie"].append(texte_magasin)
                                st.toast(f"✅ {nom_magasin} ajouté à votre sélection !", icon="🛒")
                                st.rerun()  # Force la mise à jour immédiate de la barre latérale
                            else:
                                st.toast("💡 Ce commerce est déjà dans votre liste !", icon="ℹ️")
                                
                    st.divider()
        else:
            st.warning(f"Aucun commerce ne correspond à vos critères dans un rayon de {rayon_max} km.")
    else:
        st.error("❌ Code postal introuvable ou invalide dans la base de données du Québec.")
