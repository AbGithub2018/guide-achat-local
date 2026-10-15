import streamlit as st
import pandas as pd

# Configuration de la page Streamlit
st.set_page_config(page_title="Mon Guide Achat Local", page_icon="🛒", layout="centered")

st.title("🛒 Trouver mes bannières locales")
st.write("Entrez votre code postal pour lister les enseignes d'alimentation disponibles dans votre secteur au Québec.")

# --- BASE DE DONNÉES DE TOUTES LES ENSEIGNES DU QUÉBEC ---
# Pour étendre l'application à toute la province, on associe les bannières aux premières lettres des codes postaux du Québec.
# G = Est et Centre du Québec (Beauce, Québec, Saguenay, etc.)
# J = Ouest et Nord du Québec (Gatineau, Abitibi, Laurentides, Estrie, etc.)
# H = Île de Montréal et Laval
DONNEES_COMMERCES_QC = [
    {"Bannière": "Maxi", "Type": "Supermarché", "Site Web": "https://maxi.ca", "Regions": ["G", "J", "H"]},
    {"Bannière": "Super C", "Type": "Supermarché", "Site Web": "https://superc.ca", "Regions": ["G", "J", "H"]},
    {"Bannière": "IGA", "Type": "Supermarché", "Site Web": "https://iga.net", "Regions": ["G", "J", "H"]},
    {"Bannière": "Metro", "Type": "Supermarché", "Site Web": "https://metro.ca", "Regions": ["G", "J", "H"]},
    {"Bannière": "Dollarama", "Type": "Magasin à rabais (Aliments)", "Site Web": "https://dollarama.com", "Regions": ["G", "J", "H"]},
    {"Bannière": "Tigre Géant", "Type": "Magasin à rabais (Aliments)", "Site Web": "https://gianttiger.com", "Regions": ["G", "J"]},
    {"Bannière": "Walmart Supercentre", "Type": "Grande surface", "Site Web": "https://walmart.ca", "Regions": ["G", "J", "H"]},
    {"Bannière": "Provigo", "Type": "Supermarché", "Site Web": "https://provigo.ca", "Regions": ["G", "J", "H"]},
    {"Bannière": "Admar / Marché Richelieu", "Type": "Épicerie de proximité", "Site Web": "https://marcherichelieu.ca", "Regions": ["G", "J"]},
]

df_commerces = pd.DataFrame(DONNEES_COMMERCES_QC)

# --- INTERFACE UTILISATEUR ---

# Champ de saisie utilisateur
cp_saisi = st.text_input("Entrez votre code postal (ex: G5Y 6H3, H2W 1A2, J9T 3A1) :", value="G5Y 6H3")

if cp_saisi.strip():
    # Nettoyage de l'entrée utilisateur
    cp_propre = cp_saisi.strip().replace(" ", "").upper()
    
    # Validation du format québécois (les codes postaux du Québec commencent majoritairement par G, H ou J)
    if len(cp_propre) >= 3 and cp_propre[0] in ["G", "H", "J"]:
        premiere_lettre = cp_propre[0]
        rta_complete = cp_propre[:3]
        
        # Filtrer les commerces selon la région du Québec détectée
        df_filtre = df_commerces[df_commerces['Regions'].apply(lambda x: premiere_lettre in x)]
        
        if not df_filtre.empty:
            st.subheader(f"🏬 Enseignes disponibles dans le secteur {rta_complete} :")
            st.write("Cliquez sur le bouton d'une bannière pour visiter son site internet officiel.")
            
            # Affichage dynamique sous forme de liste épurée
            for index, row in df_filtre.iterrows():
                with st.container():
                    col_info, col_lien = st.columns([2, 1])
                    
                    with col_info:
                        st.markdown(f"**{row['Bannière']}**")
                        st.caption(f"Catégorie : {row['Type']}")
                        
                    with col_lien:
                        st.link_button(f"🌐 Visiter {row['Bannière']}", row['Site Web'], use_container_width=True)
                    
                    st.markdown(" ") # Espacement discret
        else:
            st.info(f"Aucune bannière répertoriée pour cette région.")
    else:
        st.warning("Veuillez entrer un code postal valide du Québec (commençant par G, H ou J).")
