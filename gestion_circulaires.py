# =========================================================================
# DICTIONNAIRES ET BASE DE DONNÉES DES LIENS (CORRECTION DE L'ERREUR 533)
# =========================================================================
liens_circulaires = {
    "super_c": "https://superc.ca",
    "maxi": "https://maxi.ca",
    "walmart": "https://walmart.ca",
    "iga": "https://iga.net",
    "metro": "https://metro.ca",
    "tigre_geant": "https://gianttiger.com",
    "provigo": "https://provigo.ca",
    "costco": "https://costco.ca",
    "dollarama": "https://dollarama.com",
    "marche_adonis": "https://groupeadonis.com",
    "marche_ami": "https://marcheami.ca",
    "marche_bonichoix": "https://www.bonichoix.com/fr/notre-circulaire/",
    "marche_richelieu": "https://marcherichelieu.com",
    # Passerelle invisible (href.li/?) pour contourner définitivement l'erreur 533 de Marché Tradition
    "marche_tradition": "https://href.li"
}

noms_affichage_circulaires = {
    "super_c": "Super C",
    "maxi": "Maxi",
    "walmart": "Walmart",
    "iga": "IGA",
    "metro": "Metro",
    "tigre_geant": "Tigre Géant",
    "provigo": "Provigo",
    "costco": "Costco",
    "dollarama": "Dollarama",
    "marche_adonis": "Marché Adonis",
    "marche_ami": "Marché Ami",
    "marche_bonichoix": "Marché Bonichoix",
    "marche_richelieu": "Marché Richelieu",
    "marche_tradition": "Marché Tradition"
}

# =========================================================================
# FONCTION POUR CRÉER LES BOUTONS HTML SÉCURISÉS (ANTI-BLOCAGE)
# =========================================================================
def generer_bouton_circulaire(nom_magasin, url_cible):
    style_bouton = (
        "display: inline-block; "
        "width: 100%; "
        "text-align: center; "
        "padding: 0.5rem 1rem; "
        "color: #31333F; "                  # Même couleur de texte que Streamlit
        "background-color: #F0F2F6; "        # Même couleur de fond que Streamlit
        "border: 1px solid rgba(49, 51, 63, 0.2); "
        "border-radius: 0.5rem; "
        "text-decoration: none; "
        "font-weight: 500; "
        "margin-bottom: 10px;"
    )
    return f'<a href="{url_cible}" target="_blank" rel="noreferrer" style="{style_bouton}">📖 {nom_magasin}</a>'
