import streamlit as st
import pandas as pd
import urllib.parse

st.title("📍 Localisateur d'Épiceries du Québec")
st.write("Sélectionnez n'importe quelle municipalité officielle pour afficher ses épiceries avec un zoom idéal.")

# 1. Chargement automatique du fichier gouvernemental mis sur votre GitHub
@st.cache_data
def charger_donnees():
    # On charge le fichier en gérant les différents encodages de texte possibles pour les accents
    try:
        df = pd.read_csv("municipalités.csv", encoding="utf-8")
    except FileNotFoundError:
        try:
            df = pd.read_csv("municipalites.csv", encoding="utf-8")
        except FileNotFoundError:
            df = pd.read_csv("municipalites.csv", encoding="latin-1")
    except Exception:
        df = pd.read_csv("municipalités.csv", encoding="latin-1")
    return df

try:
    df_villes = charger_donnees()
    
    # Nettoyage des noms de colonnes pour enlever les espaces ou sauts de ligne invisibles
    df_villes.columns = df_villes.columns.str.strip()

    # 2. Création du menu déroulant trié par ordre alphabétique de toutes les villes du Québec
    liste_villes = sorted(df_villes["Nom de la municipalité"].dropna().unique())
    ville_selectionnee = st.selectbox("Sélectionnez votre municipalité :", liste_villes)

    if ville_selectionnee:
        # 3. Extraction de la ligne correspondant à la ville choisie
        infos_ville = df_villes[df_villes["Nom de la municipalité"] == ville_selectionnee].iloc[0]
        
        # Récupération des coordonnées géographiques exactes du gouvernement
        lat = infos_ville["Latitude du point central"]
        lon = infos_ville["Longitude du point central"]
        
        # Encodage sécurisé du terme de recherche
        terme_recherche = urllib.parse.quote("épiceries")
        
        # 4. L'URL absolue avec le ZOOM FORCÉ (13z = échelle de centre-ville serrée)
        lien_maps = f"https://www.google.com/maps/search/{terme_recherche}/@{lat},{lon},13z"
        
        # 5. Affichage du bouton d'action pour le consommateur
        st.link_button(f"🚀 Ouvrir la carte pour {ville_selectionnee}", lien_maps)

except Exception as e:
    st.error("Erreur lors de la lecture du fichier. Assurez-vous d'avoir téléversé 'municipalités.csv' sur GitHub.")
    st.info("Vérifiez également que les titres de vos colonnes dans le fichier s'appellent exactement : 'Nom de la municipalité', 'Latitude du point central' et 'Longitude du point central'.")
