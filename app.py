import streamlit as st
import pandas as pd
import re

# Configuration de la page
st.set_page_config(page_title="Comparateur Épicerie Québec", page_icon="⚜️", layout="wide")

st.title("⚜️ Outil de Provenance Alimentaire & Comparateur (Québec)")
st.write("Analysez notre base de données de plus de 10 000 produits pour savoir où va votre argent.")

# Chargement intelligent de la base complète
@st.cache_data
def charger_et_analyser_base():
    url_sheet = "https://docs.google.com/spreadsheets/d/1-Xv0jRlYyIGZN5TdeS_fhNAWAnP7kQmbJmADUxpZJGc/gviz/tq?tqx=out:csv&gid=1814577010"
    try:
        # Essai 1 : Lecture standard (Séparateur Virgule)
        df = pd.read_csv(url_sheet)
        df.columns = df.columns.str.strip()
        
        # Si la colonne unique contient des espaces, c'est que Google a mal séparé (format TSV/Tabulation)
        if len(df.columns) == 1 and (' ' in df.columns[0] or '\t' in df.columns[0]):
            # Essai 2 : On force la séparation par espace/tabulation si tout est collé
            df = pd.read_csv(url_sheet, sep=r'\s+', engine='python')
            df.columns = df.columns.str.strip()

        # Si 'code_upc' n'est toujours pas isolé, on force le découpage propre
        if 'code_upc' not in df.columns:
            # On récupère le flux brut et on essaie de forcer le séparateur tabulation explicite
            df = pd.read_csv(url_sheet, sep='\t')
            df.columns = df.columns.str.strip()

        # Nettoyage final des en-têtes en minuscules pour éviter les erreurs de casse
        df.columns = df.columns.str.lower()
        
        # Validation finale
        if 'code_upc' not in df.columns:
            st.error(f"Colonnes introuvables. Colonnes lues par le script : {list(df.columns[:3])}...")
            return None
        
        # Identification de la colonne nom (gère 'nom' ou 'nom du produit')
        col_nom = 'nom' if 'nom' in df.columns else df.columns[1]
        
        # Standardisation des codes UPC
        def nettoyer_upc(val):
            val_str = str(val).strip()
            if "E+" in val_str or "," in val_str:
                return "Erreur format Excel"
            return re.sub(r'\D', '', val_str).zfill(12) if any(c.isdigit() for c in val_str) else "Invalide"
            
        df['upc_propre'] = df['code_upc'].apply(nettoyer_upc)
        
        # Règle de classification
        def determiner_provenance_ligne(row):
            pays = str(row.get('entreprise_pays', '')).strip().lower()
            nom_produit = str(row.get(col_nom, '')).strip().lower()
            
            if "québec" in pays or "qc" in pays or "québec" in nom_produit or "du québec" in nom_produit:
                return "Fabriqué au Québec ⚜️"
            elif "canada" in pays or "canadien" in pays:
                return "Canada 🇨🇦"
            elif "états-unis" in pays or "usa" in pays or "united states" in pays:
                return "États-Unis 🇺🇸"
            else:
                return "Autre / À valider 🌍"
                
        df['provenance_estimee'] = df.apply(determiner_provenance_ligne, axis=1)
        # On renomme la colonne nom dynamiquement pour la suite du script
        df = df.rename(columns={col_nom: 'nom'})
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
    recherche = st.text_input("Entrez un nom de produit ou un code UPC :", "")
    
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
