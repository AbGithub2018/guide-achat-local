import streamlit as st
import pandas as pd
import re

# Configuration visuelle de la page Streamlit
st.set_page_config(page_title="Comparateur Épicerie Québec", page_icon="⚜️", layout="wide")

st.title("⚜️ Outil de Provenance Alimentaire & Comparateur (Québec)")
st.write("Analysez notre base de données de plus de 10 000 produits pour savoir où va votre argent.")

# Chargement intelligent de la base complète avec l'identifiant gid vérifié
@st.cache_data
def charger_et_analyser_base():
    # URL configurée au format CSV avec le gid exact de votre onglet de données
    url_sheet = "https://google.com"
    try:
        # Lecture directe du flux de données CSV
        df = pd.read_csv(url_sheet)
        
        # Nettoyage des espaces invisibles dans les en-têtes
        df.columns = df.columns.str.strip()
        
        # Validation stricte de la présence des colonnes cibles
        if 'code_upc' not in df.columns or 'nom' not in df.columns:
            st.error(f"Colonnes introuvables. Colonnes lues par le script : {list(df.columns)}")
            return None
        
        # Standardisation des codes UPC (gestion de la notation scientifique Excel)
        def nettoyer_upc(val):
            val_str = str(val).strip()
            if "E+" in val_str or "," in val_str:
                return "Erreur format Excel"
            return re.sub(r'\D', '', val_str).zfill(12) if any(c.isdigit() for c in val_str) else "Invalide"
            
        df['upc_propre'] = df['code_upc'].apply(nettoyer_upc)
        
        # Règle de classification de provenance basée sur votre colonne 'entreprise_pays'
        def determiner_provenance_ligne(row):
            pays = str(row['entreprise_pays']).strip().lower() if pd.notna(row['entreprise_pays']) else ""
            nom_produit = str(row['nom']).strip().lower() if pd.notna(row['nom']) else ""
            
            # Validation locale prioritaire (Québec)
            if "québec" in pays or "qc" in pays or "québec" in nom_produit or "du québec" in nom_produit:
                return "Fabriqué au Québec ⚜️"
            elif "canada" in pays or "canadien" in pays:
                return "Canada 🇨🇦"
            elif "états-unis" in pays or "usa" in pays or "united states" in pays:
                return "États-Unis 🇺🇸"
            elif pays != "":
                return f"Importé ({row['entreprise_pays']}) 🌍"
            else:
                return "Provenance à déterminer 🔎"
                
        df['provenance_estimee'] = df.apply(determiner_provenance_ligne, axis=1)
        return df
    except Exception as e:
        st.error(f"Impossible de se connecter au Google Sheet : {e}")
        return None

# Lancement de l'analyse
df_complet = charger_et_analyser_base()

if df_complet is not None:
    # ---------------------------------------------------------
    # SECTION 1 : TABLEAU DE BORD & STATISTIQUES GLOBALES
    # ---------------------------------------------------------
    st.header("📊 Statistiques de la base de données en direct")
    
    total_produits = len(df_complet)
    total_quebec = len(df_complet[df_complet['provenance_estimee'] == "Fabriqué au Québec ⚜️"])
    erreurs_upc = len(df_complet[df_complet['upc_propre'] == "Erreur format Excel"])
    
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(label="Total des produits référencés", value=f"{total_produits:,}")
    with col_m2:
        st.metric(label="Produits identifiés du Québec ⚜️", value=f"{total_quebec:,}", delta=f"{(total_quebec/total_produits)*100:.1f}% de la base")
    with col_m3:
        st.metric(label="Codes UPC brisés par Excel", value=erreurs_upc, delta="- Action requise" if erreurs_upc > 0 else "Parfait", delta_color="inverse")
        
    st.subheader("🌍 Répartition géographique des entreprises propriétaires")
    st.bar_chart(df_complet['provenance_estimee'].value_counts())
    
    st.divider()

    # ---------------------------------------------------------
    # SECTION 2 : RECHERCHE INTERACTIVE POUR LES CONSOMMATEURS
    # ---------------------------------------------------------
    st.header("🔍 Rechercher un produit alimentaire")
    recherche = st.text_input("Entrez un nom de produit ou un code UPC (ex: Clark, Flocons d'avoine, 663780...) :", "")
    
    if recherche:
        recherche_clean = recherche.strip().lower()
        
        # Filtre de recherche insensible à la casse sur le nom ou le code brut
        resultats = df_complet[
            df_complet['nom'].astype(str).str.lower().str.contains(recherche_clean) |
            df_complet['code_upc'].astype(str).str.contains(recherche_clean)
        ]
        
        if not resultats.empty:
            st.success(f"💡 {len(resultats)} produit(s) trouvé(s) ! Affichage des 10 premiers :")
            
            for idx, row in resultats.head(10).iterrows():
                with st.container():
                    c1, c2 = st.columns()
                    with c1:
                        st.subheader(row['nom'])
                        st.caption(f"Code UPC : {row['code_upc']} | Compagnie : {row.get('entreprise_proprietaire', 'Inconnue')}")
                        if pd.notna(row.get('lieu_usine')):
                            st.write(f"🏢 **Lieu de fabrication :** {row['lieu_usine']}")
                    with c2:
                        st.info(f"**Classification :** \n\n{row['provenance_estimee']}")
                    st.divider()
        else:
            st.warning("Aucun produit ne correspond à votre recherche.")
else:
    st.warning("En attente de la synchronisation des données...")
