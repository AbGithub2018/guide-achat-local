import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

def obtenir_coordonnees(code_postal, pays="Canada"):
    """
    Convertit un code postal en coordonnées GPS (Latitude, Longitude)
    via l'API gratuite Nominatim (OpenStreetMap).
    """
    # L'User-Agent est obligatoire et doit être unique pour respecter les règles d'OSM
    geolocator = Nominatim(user_agent="mon_application_gratuite_de_commerces_v1")
    
    try:
        requete = f"{code_postal}, {pays}"
        emplacement = geolocator.geocode(requete)
        if emplacement:
            return emplacement.latitude, emplacement.longitude
        else:
            print(f"[-] Code postal introuvable : {code_postal}")
            return None, None
    except GeocoderTimedOut:
        print("[-] Le service de géocodage a expiré. Réessayez.")
        return None, None

def chercher_commerces_proximite(lat, lon, rayon_metres=5000):
    """
    Cherche les épiceries et supermarchés dans un rayon donné 
    autour des coordonnées GPS via l'API gratuite Overpass.
    """
    url_overpass = "https://overpass-api.de"
    
    # Requête Overpass QL : recherche les 'supermarket' et 'grocery'
    # autour des coordonnées (lat, lon) dans le rayon spécifié
    requete_overpass = f"""
    [out:json][timeout:25];
    (
      node["shop"="supermarket"](around:{rayon_metres},{lat},{lon});
      way["shop"="supermarket"](around:{rayon_metres},{lat},{lon});
      node["shop"="grocery"](around:{rayon_metres},{lat},{lon});
      way["shop"="grocery"](around:{rayon_metres},{lat},{lon});
    );
    out body;
    >;
    out skel qt;
    """
    
    response = requests.post(url_overpass, data={'data': requete_overpass})
    
    if response.status_code == 200:
        donnees = response.json()
        commerces = []
        
        for element in donnees.get('elements', []):
            tags = element.get('tags', {})
            nom = tags.get('name', 'Commerce sans nom')
            rue = tags.get('addr:street', '')
            numero = tags.get('addr:housenumber', '')
            adresse = f"{numero} {rue}".strip() if rue else "Adresse non renseignée"
            
            commerces.append({"nom": nom, "adresse": adresse})
            
        return commerces
    else:
        print(f"[-] Erreur de l'API Overpass : {response.status_code}")
        return []

# --- ZONE DE TEST ---
if __name__ == "__main__":
    # Exemple avec le code postal par défaut (Saint-Georges, QC)
    CODE_POSTAL_TEST = "G5Y 7W1" 
    PAYS_TEST = "Canada"
    RAYON = 5000 # 5 kilomètres
    
    print(f"[+] Recherche des coordonnées pour le code postal : {CODE_POSTAL_TEST}...")
    latitude, longitude = obtenir_coordonnees(CODE_POSTAL_TEST, PAYS_TEST)
    
    if latitude and longitude:
        print(f"[+] Coordonnées trouvées : Lat {latitude}, Lng {longitude}")
        print(f"[+] Recherche des épiceries à moins de {RAYON/1000} km...")
        
        resultats = chercher_commerces_proximite(latitude, longitude, RAYON)
        
        if resultats:
            print(f"\n[+] {len(resultats)} commerces trouvés :")
            for index, commerce in enumerate(resultats, 1):
                print(f"{index}. {commerce['nom']} — {commerce['adresse']}")
        else:
            print("[-] Aucun commerce trouvé dans ce rayon.")
