import streamlit as st
import pandas as pd
import urllib.parse
import re

st.title("📍 Localisateur d'Épiceries du Québec")
st.write("Sélectionnez n'importe quelle municipalité officielle pour afficher ses épiceries avec un zoom idéal.")

# Fonction pour convertir les coordonnées textuelles (ex: 47° 22' 34" N) en nombres décimaux
def dms_a_decimal(coord_str, est_longitude=False):
    try:
        if pd.isna(coord_str):
            return None
        # Extraction de tous les nombres présents dans le texte
        chiffres = [float(x) for x in re.findall(r"\d+", str(coord_str))]
        if len(chiffres) >= 3:
            degres, minutes, secondes = chiffres[0], chiffres[1], chiffres[2]
            decimal = degres + (minutes / 60.0) + (secondes / 3600.0)
            # Au Québec, la longitude est à l'Ouest (O), donc elle doit être négative
            if est_longitude:
                decimal = -decimal
            return decimal
    except Exception:
        return None
    return None

@st.cache_data
def charger_donnees():
    # Chargement en utilisant le point-virgule comme séparateur selon votre image
    try:
        df = pd.read_csv("municipalités.csv", sep=";", encoding="utf-8")
    except FileNotFoundError:
        try:
            df = pd.read_csv("municipalites.csv", sep=";", encoding="utf-8")
        except FileNotFoundError:
            df = pd.read_csv("municipalites.csv", sep=";", encoding="latin-1")
    except Exception:
        df = pd.read_csv("municipalités.csv", sep=";", encoding="latin-1")
    return df

try:
    df_villes = charger_donnees()
    df_villes.columns = df_villes.columns.str.strip()

    # Création de la liste des villes
    liste_villes = sorted(df_villes["Nom de la municipalité"].dropna().unique())
    ville_selectionnee = st.selectbox("Sélectionnez votre municipalité :", liste_villes)

    if ville_selectionnee:
        # Récupération de la ligne de la ville
        infos_ville = df_villes[df_villes["Nom de la municipalité"] == ville_selectionnee].iloc[0]
        
        # Conversion des formats textes en chiffres décimaux
        lat = dms_a_decimal(infos_ville["Latitude"], est_longitude=False)
        lon = dms_a_decimal(infos_ville["Longitude"], est_longitude=True)
        
        if lat and lon:
            terme_recherche = urllib.parse.quote("épiceries")
            # L'URL absolue parfaite avec zoom forcé à 13z
            lien_maps = f"https://www.google.com/maps/search/{terme_recherche}/@{lat},{lon},13z"
            st.link_button(f"🚀 Ouvrir la carte pour {ville_selectionnee}", lien_maps)
        else:
            st.error("Impossible de lire les coordonnées géographiques pour cette municipalité.")

except Exception as e:
    st.error(f"Erreur lors de la configuration de l'application : {e}")
