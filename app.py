import streamlit as st
import pandas as pd
import re

# Configuration de la page Streamlit
st.set_page_config(page_title="Comparateur Épicerie Québec", page_icon="⚜️", layout="wide")

st.title("⚜️ Outil de Vérification et Provenance Alimentaire (Québec)")
st.write("Trouvez d'où provient votre argent et si vos produits font travailler le monde d'ici.")

# Fonction pour charger les données avec mise en cache pour éviter de recharger à chaque clic
@st.cache_data
def charger_donnees():
    url_sheet = "https://google.com"
    try:
        df = pd.read_csv(url_sheet, sep='\t')
        df.columns = df.columns.str.strip()
        
        # Nettoyage et standardisation basique des UPC
        def nettoyer_upc(val):
            val_str = str(val).strip()
            if "E+" in val_str or "," in val_str:
                return "Erreur format"
            return re.sub(r'\D', '', val_str).zfill(12) if any(c.isdigit() for c in val_str) else "Invalide"
            
        df['upc_propre'] = df['code_upc'].apply(nettoyer_upc)
        return df
    except Exception as e:
        st.error(f"Erreur de connexion au Google Sheet : {e}")
        return None

df_produits = charger_donnees()

def detecter_provenance(nom, upc_propre):
    """Détecte l'origine en combinant le nom du produit et les règles UPC GS1."""
    if pd.isna(nom):
        return "Inconnu 🌍", "Gris"
    
    nom_lower = str(nom).lower()
    
    # 1. Analyse textuelle (Prioritaire)
    if any(re.search(kw, nom_lower) for kw in [r"qu[ée]bec", r"qc", r"lac-saint-jean", r"charlevoix", r"estrie", r"st-valentin", r"orléans", r"miel pur"]):
        return "Fabriqué au Québec ⚜️", "Vert"
    if any(re.search(kw, nom_lower) for kw in [r"canada", r"canadien", r"ontario", r"vancouver", r"wonder"]):
        return " Canada 🇨🇦", "Bleu"
    if any(re.search(kw, nom_lower) for kw in [r"usa", r"états-unis", r"californie", r"floride", r"key"]):
        return "États-Unis 🇺🇸", "Rouge"
        
    # 2. Analyse par code UPC si le texte ne dit rien
    if upc_propre.isdigit() and len(upc_propre) >= 3:
        prefixe_2 = int(upc_propre[:2])
        if 0 <= prefixe_2 <= 13:
            return "Enregistré au Canada / USA (Origine exacte à valider sur l'emballage) 🇨🇦🇺🇸", "Orange"
            
    return "Autre provenance / À valider en magasin 🌍", "Gris"

if df_produits is not None:
    # Barre de recherche unique
    recherche = st.text_input("🔍 Recherchez un produit par son nom ou son code-barres (UPC) :", "")

    if recherche:
        recherche_clean = recherche.strip().lower()
        
        # Filtre les données selon le texte ou l'UPC
        resultats = df_produits[
            df_produits['nom'].astype(str).str.lower().str.contains(recherche_clean) |
            df_produits['code_upc'].astype(str).str.contains(recherche_clean)
        ]
        
        if not resultats.empty:
            st.success(f"🎉 {len(resultats)} produit(s) trouvé(s) !")
            
            for idx, row in resultats.head(10).iterrows():
                provenance, couleur = detecter_provenance(row['nom'], row['upc_propre'])
                
                # Mise en page visuelle pour chaque produit trouvé
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.subheader(row['nom'])
                        st.caption(f"Code UPC : {row['code_upc']}")
                    with col2:
                        st.metric(label="Provenance estimée", value=provenance)
                    st.divider()
        else:
            st.warning("Aucun produit ne correspond à votre recherche dans la base actuelle.")
else:
    st.info("Chargement de la base de données...")
