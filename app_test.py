import streamlit as st
import requests
import pandas as pd
from pypdf import PdfReader
import re

# Configuration de la page Streamlit
st.set_page_config(page_title="Localisateur d'Épiceries Officiel", page_icon="🛒")

st.title("🛒 Localisateur d'Épiceries du Québec")
st.write("Application synchronisée avec le schéma de tri officiel de Postes Canada.")

# --- CHARGEMENT ET EXTRACTION DU PDF DE POSTES CANADA ---

@st.cache_data(show_spinner=False)
def charger_rta_depuis_pdf(chemin_pdf):
    """
    Parcourt votre PDF officiel, extrait toutes les RTA valides (ex: G5Y) 
    et utilise une API de secours publique pour lier la géolocalisation.
    """
    rta_valides = set()
    try:
        reader = PdfReader(chemin_pdf)
        # Expression régulière pour détecter le format d'une RTA (Lettre-Chiffre-Lettre)
        pattern_rta = re.compile(r'\b[A-Z][0-9][A-Z]\b')
        
        # Lecture de tout le texte de votre document
        for page in reader.pages:
            texte = page.extract_text()
            trouvailles = pattern_rta.findall(texte)
            for rta in trouvailles:
                rta_valides.add(rta)
    except Exception as e:
        st.error(f"Erreur lors de la lecture de votre fichier PDF : {e}")
        
    return rta_valides

# --- GÉOLOCALISATION ET RECHERCHE ---

@st.cache_data(show_spinner=False)
def geolocaliser_rta_officielle(rta):
    """
    Donne les coordonnées de la RTA extraite de votre document.
    Utilise l'API publique de geonames (sans clé) pour éviter les blocages de Nominatim.
    """
    url = f"https://geonames.org{rta}&country=CA&maxRows=1&username=demo"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            donnees = response.json()
            codes = donnees.get('postalCodes', [])
            if codes:
                return float(codes[0]['lat']), float(codes[0]['lng'])
    except Exception:
        pass
    
    # Coordonnées de secours pour Saint-Georges (G5Y) si l'API externe ralentit
    if rta == "G5Y":
        return 46.1167, -70.6667
    return None, None

@st.cache_data(show_spinner=False)
def chercher_epiceries_api(lat, lon, rayon_km=5):
    url_overpass = "https://overpass-api.de"
    rayon_metres = rayon_km * 1000
    
    requete_overpass = f"""
    [out:json][timeout:25];
    (
      node["shop"="supermarket"](around:{rayon_metres},{lat},{lon});
      way["shop"="supermarket"](around:{rayon_metres},{lat},{lon});
      node["shop"="grocery"](around:{rayon_metres},{lat},{lon});
      way["shop"="grocery"](around:{rayon_metres},{lat},{lon});
    );
    out body center;
    """
    try:
        response = requests.post(url_overpass, data={'data': requete_overpass})
        if response.status_code == 200:
            donnees = response.json()
            commerces = []
            for element in donnees.get('elements', []):
                tags = element.get('tags', {})
                e_lat = element.get('lat') or element.get('center', {}).get('lat')
                e_lon = element.get('lon') or element.get('center', {}).get('lon')
                if e_lat and e_lon:
                    nom = tags.get('name', 'Épicerie indépendante')
                    rue = tags.get('addr:street', '')
                    numero = tags.get('addr:housenumber', '')
                    adresse = f"{numero} {rue}".strip() if rue else "Adresse non renseignée"
                    commerces.append({"Nom": nom, "Adresse": adresse, "latitude": float(e_lat), "longitude": float(e_lon)})
            return commerces
    except Exception:
        return []
    return []

# --- INITIALISATION DE VOTRE BASE DE DONNÉES PDF ---
# Assurez-vous que votre fichier est renommé ainsi ou changez le nom ci-dessous
FICHIER_PDF = "Liste-des-RTA-janvier-2026_RThzSs.pdf" 

with st.spinner("Analyse et synchronisation de votre liste Postes Canada..."):
    liste_rta_officielles = charger_rta_depuis_pdf(FICHIER_PDF)

if liste_rta_officielles:
    st.sidebar.success(f"📚 {len(liste_rta_officielles)} régions de tri chargées depuis votre document.")
else:
    st.sidebar.error("Fichier PDF introuvable ou illisible à la racine du projet.")

# --- INTERFACE UTILISATEUR ---

cp_saisi = st.text_input("Entrez votre code postal complet (ex: G5Y 6H3) :", value="G5Y 6H3")
rayon = st.slider("Rayon de recherche (km)", min_value=1, max_value=15, value=5)

if st.button("🔍 Filtrer et chercher", type="primary"):
    cp_propre = cp_saisi.strip().replace(" ", "").upper()
    rta_saisie = cp_propre[:3] if len(cp_propre) >= 3 else ""
    
    # ÉTAPE DE VALIDATION CRUCIALE : L'application vérifie si la RTA existe dans VOTRE document
    if rta_saisie not in liste_rta_officielles:
        st.error(f"❌ Sécurité : La région '{rta_saisie}' n'appartient pas au schéma de tri officiel fourni.")
    else:
        with st.spinner(f"Géolocalisation du secteur officiel {rta_saisie}..."):
            lat, lon = geolocaliser_rta_officielle(rta_saisie)
            
        if lat and lon:
            with st.spinner("Extraction des commerces à proximité..."):
                resultats = chercher_epiceries_api(lat, lon, rayon)
                
            if resultats:
                st.success(f"🎉 Code validé selon votre liste ! {len(resultats)} commerces trouvés autour de {rta_saisie}.")
                df = pd.DataFrame(resultats)
                st.map(df, latitude="latitude", longitude="longitude")
                st.dataframe(df[["Nom", "Adresse"]], use_container_width=True)
            else:
                st.info("Aucune épicerie trouvée dans ce rayon.")
        else:
            st.error("Erreur de connexion lors de la récupération des coordonnées GPS de ce secteur.")
