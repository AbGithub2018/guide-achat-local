@st.cache_data(show_spinner=False)
def obtenir_coordonnees_par_cp(code_postal):
    # 1. On utilise un nom d'application encore plus spécifique (obligatoire pour Nominatim)
    # 2. On augmente explicitement le timeout à 10 secondes (au lieu de 1s par défaut)
    geolocator = Nominatim(
        user_agent="localisateur_epiceries_quebec_production_v2", 
        timeout=10
    )
    try:
        requete = f"{code_postal}, Quebec, Canada"
        emplacement = geolocator.geocode(requete)
        if emplacement:
            return emplacement.latitude, emplacement.longitude
    except Exception as e:
        # En cas de surcharge du serveur open-source, on capture l'erreur proprement 
        # pour éviter le grand message d'erreur rouge à l'écran
        st.sidebar.warning(f"Note technique : Le serveur de géolocalisation est ralenti.")
        return None, None
    return None, None
