import streamlit as st
import pandas as pd

# Configuration de la page Streamlit (Propre et centrée pour l'utilisateur)
st.set_page_config(page_title="Mon Guide Achat Local", page_icon="🛒", layout="centered")

st.title("🛒 Trouver mes bannières locales")
st.write("Entrez votre code postal pour lister les enseignes d'alimentation disponibles dans votre secteur et accéder à leurs sites.")

# --- BASE DE DONNÉES TEXTUELLE (Simulée pour le test - Sera liée à votre Google Sheets) ---
# Chaque ligne représente une bannière réelle avec son site web et les secteurs (RTA) où elle est présente.
DONNEES_COMMERCES = [
    {"Bannière": "Maxi", "Type": "Supermarché", "Site Web": "https://maxi.ca", "Secteurs": ["G5Y", "G5X", "G6E", "G1K", "H2W"]},
    {"Bannière": "Super C", "Type": "Supermarché", "Site Web": "https://superc.ca", "Secteurs": ["G5Y", "G6E", "G1K", "H2W"]},
    {"Bannière": "IGA", "Type": "Supermarché", "Site Web": "https://iga.net", "Secteurs": ["G5Y", "G5X", "G6B", "G1K", "H2W"]},
    {"Bannière": "Metro", "Type": "Supermarché", "Site Web": "https://metro.ca", "Secteurs": ["G5Y", "G6B", "G1K", "H2W"]},
    {"Bannière": "Dollarama", "Type": "Magasin à rabais (Aliments)", "Site Web": "https://dollarama.com", "Secteurs": ["G5Y", "G5X", "G6B", "G6E", "G1K", "H2W"]},
    {"Bannière": "Tigre Géant", "Type": "Magasin à rabais (Aliments)", "Site Web": "https://gianttiger.com", "Secteurs": ["G5Y", "G1K", "H2W"]},
    {"Bannière": "Walmart Supercentre", "Type": "Grande surface", "Site Web": "https://walmart.ca", "Secteurs": ["G5Y", "G1K", "H2W"]},
    {"Bannière": "Les Pères Nature", "Type": "Marché local / Fruiterie", "Site Web": "https://lesperesnature.com", "Secteurs": ["G5Y"]},
]

# Convertir la liste en DataFrame Pandas pour pouvoir la filtrer facilement
df_commerces = pd.DataFrame(DONNEES_COMMERCES)

# --- INTERFACE UTILISATEUR ---

# Champ de saisie simple
cp_saisi = st.text_input("Entrez votre code postal (ex: G5Y 6H3) :", value="G5Y 6H3")

if cp_saisi.strip():
    # Nettoyage de l'entrée et extraction de la RTA (3 premiers caractères, ex: G5Y)
    cp_propre = cp_saisi.strip().replace(" ", "").upper()
    rta_utilisateur = cp_propre[:3] if len(cp_propre) >= 3 else ""
    
    if len(rta_utilisateur) == 3:
        # Filtrer le tableau : on garde uniquement les lignes où le secteur de l'utilisateur est présent
        df_filtre = df_commerces[df_commerces['Secteurs'].apply(lambda x: rta_utilisateur in x)]
        
        if not df_filtre.empty:
            st.subheader(f"🏬 Enseignes disponibles autour de {rta_utilisateur} :")
            st.write("Cliquez sur le bouton d'une bannière pour visiter son site internet officiel.")
            
            # Affichage sous forme de liste propre avec des boutons d'action individuels
            for index, row in df_filtre.iterrows():
                # Création d'un encadré visuel pour chaque commerce
                with st.container():
                    col_info, col_lien = st.columns([3, 2])
                    
                    with col_info:
                        st.markdown(f"**{row['Bannière']}**")
                        st.caption(f"Catégorie : {row['Type']}")
                        
                    with col_lien:
                        # Bouton natif Streamlit qui ouvre le lien dans un nouvel onglet de façon 100% sécurisée
                        st.link_button(f"🌐 Visiter {row['Bannière']}", row['Site Web'], use_container_width=True)
                    
                    st.markdown(" ") # Petit espace de séparation
        else:
            st.info(f"Aucune bannière enregistrée pour le secteur {rta_utilisateur} dans notre base de test.")
    else:
        st.warning("Veuillez entrer un code postal complet (Format: A1B 2C3).")
