import streamlit as st
import pandas as pd
import re

# Configuration de la page
st.set_page_config(page_title="Comparateur Épicerie Québec", page_icon="⚜️", layout="wide")

st.title("⚜️ Outil de Provenance Alimentaire & Comparateur (Québec)")
st.write("Le moteur de recherche est actif. Analyse de la base de données des produits...")

# Lecture directe via l'export CSV de Google Sheets
@st.cache_data
def charger_et_analyser_base():
    # ID de votre document extrait de votre lien
    sheet_id = "1-Xv0jRlYyIGZN5TdeS_fhNAWAnP7kQmbJmADUxpZJGc"
    # URL configurée pour forcer l'export au format CSV (rapide et contourne l'erreur 401)
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        # Lecture directe du flux CSV
        df = pd.read_csv(url_csv)
        
        # Nettoyage et forçage en minuscules des en-têtes de colonnes
        df.columns = df.columns.str.strip().str.lower()
        
        # Détection automatique de la colonne UPC au cas où le nom change
        col_upc = None
        for col in df.columns:
            if 'upc' in col or 'barre' in col:
                col_upc = col
                break
                
        # Détection automatique de la colonne Nom
        col_nom = None
        for col in df.columns:
            if 'nom' in col or 'desc' in col or 'produit' in col:
                col_nom = col
                break

        if col_upc and col_nom:
            df = df.rename(columns={col_upc: 'code_upc', col_nom: 'nom'})
        else:
            st.error(f"Colonnes de base introuvables. Colonnes lues : {list(df.columns[:5])}")
            return None
            
        # Standardisation des codes UPC
        def nettoyer_upc(val):
            val_str = str(val).strip()
            if "E+" in val_str or "," in val_str:
                return "Erreur format Excel"
            return re.sub(r'\D', '', val_str).zfill(12) if any(c.isdigit() for c in val_str) else "Invalide"
            
        df['upc_propre'] = df['code_upc'].apply(nettoyer_upc)
        
        # Règle de classification de provenance basée sur vos colonnes
        def determiner_provenance_ligne(row):
            # Utilisation de la colonne 'entreprise_pays' ou repli si absente
            pays = str(row.get('entreprise_pays', '')).strip().lower()
            nom_produit = str(row.get('nom', '')).strip().lower()
            
            if "québec" in pays or "qc" in pays or "québec" in nom_produit or "du québec" in nom_produit:
                return "Fabriqué au Québec ⚜️"
            elif "canada" in pays or "canadien" in pays:
                return "Canada 🇨🇦"
            elif "états-unis" in pays or "usa" in pays or "united states" in pays:
                return "États-Unis 🇺🇸"
            else:
                return "Autre / À valider 🌍"
                
        df['provenance_estimee'] = df.apply(determiner_provenance_ligne, axis=1)
        return df
    except Exception as e:
        st.error(f"Erreur lors de la lecture de la table : {e}")
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
        st.metric(label="Produits identifiés du Québec ⚜️", value=f"{total_quebec:,}", delta=f"{(total_quebec/total_produits)*100:.1f}% de la base" if total_produits > 0 else "0%")
    with col_m3:
        st.metric(label="Codes UPC brisés par Excel", value=erreurs_upc, delta="- Action requise" if erreurs_upc > 0 else "Parfait", delta_color="inverse")
        
    st.subheader("🌍 Répartition géographique des entreprises propriétaires")
    st.bar_chart(df_complet['provenance_estimee'].value_counts())
    
    st.divider()

    # ---------------------------------------------------------
    # SECTION 2 : RECHERCHE INTERACTIVE POUR LES CONSOMMATEURS
    # ---------------------------------------------------------
    st.header("🔍 Rechercher un produit alimentaire")
    recherche = st.text_input("Entrez un nom de produit ou un code UPC (ex: Clark, Avoine...) :", "")
    
    if recherche:
        recherche_clean = recherche.strip().lower()
        
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
                        st.caption(f"Code UPC : {row['code_upc']}")
                    with c2:
                        st.info(f"**Classification :** \n\n{row['provenance_estimee']}")
                    st.divider()
        else:
            st.warning("Aucun produit ne correspond à votre recherche.")
else:
    st.warning("En attente de la synchronisation des données...")
