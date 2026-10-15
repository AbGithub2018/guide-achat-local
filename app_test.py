import streamlit as st
import requests
import pandas as pd
import urllib.parse

# Configuration de la page Streamlit
st.set_page_config(page_title="Radar Alimentaire Québec", page_icon="🍲", layout="wide")

st.title("🍲 Radar Alimentaire : Commerces d'alimentation autour de vous")
st.write("Entrez votre code postal pour découvrir tous les points de vente d'aliments dans un rayon de 15 km (Supermarchés, Dollarama, Tigre Géant, etc.).")

# --- BASE DE DONNÉES LOCALE DE GÉOLOCALISATION DES CODES POSTAUX ---
BASE_COORDONNEES = {
    "G5Y": (46.1211, -70.6718),  # Saint-Georges
    "G5X": (46.2000, -70.7667),  # Beauceville
    "G6B": (45.5833, -70.8833),  # Lac-Mégantic
    "G6E": (46.4333, -71.0333),  # Sainte-Marie
    "G1K": (46.8139, -71.2222),  # Québec Centre
    "H2W": (45.5167, -73.5750),  # Montréal
}

def obtenir_centre_gps(code_postal):
    cp_propre = code_postal.strip().replace(" ", "").upper()
    if len(cp_propre) >= 3:
        rta = cp_propre[:3]
        if rta in BASE_COORDONNEES:
            return BASE_COORDONNEES[rta], rta
    return BASE_COORDONNEES["G5Y"], "G5Y (Mode Test - Saint-Georges)"

# --- RECHERCHE ÉLARGIE DES COMMERCES ---
@st.cache_data(show_spinner=False, ttl=300)
def chercher_tous_commerces_alimentaires(lat, lon, rayon_km):
    url_overpass = "https://mail.ru"
    rayon_metres = rayon_km * 1000
    
    requete_overpass = f"""
    [out:json][timeout:30];
    (
      node["shop"="supermarket"](around:{rayon_metres},{lat},{lon});
      way["shop"="supermarket"](around:{rayon_metres},{lat},{lon});
      node["shop"="grocery"](around:{rayon_metres},{lat},{lon});
      way["shop"="grocery"](around:{rayon_metres},{lat},{lon});
      node["shop"="department_store"](around:{rayon_metres},{lat},{lon});
      way["shop"="department_store"](around:{rayon_metres},{lat},{lon});
      node["shop"="variety_store"](around:{rayon_metres},{lat},{lon});
      way["shop"="variety_store"](around:{rayon_metres},{lat},{lon});
      node["shop"="convenience"](around:{rayon_metres},{lat},{lon});
      way["shop"="convenience"](around:{rayon_metres},{lat},{lon});
    );
    out body center;
    """
    
    commerces = []
    urls_a_tester = [url_overpass, "https://overpass-api.de"]
    
    for url in urls_a_tester:
        try:
            response = requests.post(url, data={'data': requete_overpass}, timeout=15)
            if response.status_code == 200:
                donnees = response.json()
                for element in donnees.get('elements', []):
                    tags = element.get('tags', {})
                    e_lat = element.get('lat') or element.get('center', {}).get('lat')
                    e_lon = element.get('lon') or element.get('center', {}).get('lon')
                    
                    if e_lat and e_lon:
                        nom = tags.get('name', 'Commerce d\'alimentation')
                        brand = tags.get('brand', '')
                        
                        if brand and brand.lower() not in nom.lower():
                            nom = f"{brand} ({nom})"
                            
                        rue = tags.get('addr:street', '')
                        numero = tags.get('addr:housenumber', '')
                        adresse = f"{numero} {rue}".strip() if rue else "Adresse non spécifiée"
                        
                        commerces.append({
                            "Nom": nom, 
                            "Adresse": adresse, 
                            "latitude": float(e_lat), 
                            "longitude": float(e_lon)
                        })
                if commerces:
                    break
        except Exception:
            continue
            
    return commerces

# --- INTERFACE GRAPHIQUE STREAMLIT ---

col1, col2 = st.columns(2)

with col1:
    st.subheader("⚙️ Paramètres")
    cp_saisi = st.text_input("Votre code postal :", value="G5Y 6H3")
    rayon = st.slider("Rayon maximal de recherche (km) :", min_value=1, max_value=15, value=15)
    bouton_recherche = st.button("🔍 Lancer la détection", type="primary", use_container_width=True)

with col2:
    if bouton_recherche:
        if not cp_saisi.strip():
            st.warning("Veuillez saisir un code postal.")
        else:
            (target_lat, target_lon), rta_detectee = obtenir_centre_gps(cp_saisi)
            
            with st.spinner("Scan de la zone en cours..."):
                resultats = chercher_tous_commerces_alimentaires(target_lat, target_lon, rayon)
                
            if resultats:
                st.success(f"🎉 {len(resultats)} points de vente d'aliments détectés dans un rayon de {rayon} km autour de {rta_detectee} !")
                df = pd.DataFrame(resultats)
                df = df.drop_duplicates(subset=["Nom", "Adresse"])
                
                st.subheader("🗺️ Carte interactive des points de vente")
                st.map(df, latitude="latitude", longitude="longitude")
                
                st.subheader("📋 Liste complète des commerces détectés")
                st.dataframe(df[["Nom", "Adresse"]], use_container_width=True, hide_index=True)
            else:
                st.info("🗺️ Redirection immédiate vers Google Maps pour l'affichage de tous les commerces alimentaires.")
                
                # Requête de recherche exhaustive demandée : Super C, Dollarama, Tigre Géant, Maxi, etc.
                requete_maps = f"alimentation, supermarché, Dollarama, Tigre Géant, Maxi, Super C près de {cp_saisi.strip().upper()}, QC"
                url_maps = f"https://google.com{urllib.parse.quote(requete_maps)}"
                
                st.write("Pour contourner les limites des serveurs cloud, cliquez ci-dessous pour ouvrir la carte complète avec l'ensemble des supermarchés et magasins à rabais du secteur :")
                
                st.link_button("🌐 Ouvrir la carte complète sur Google Maps", url_maps, type="primary", use_container_width=True)
