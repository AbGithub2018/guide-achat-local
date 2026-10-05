import streamlit as st
import pandas as pd
import re
import urllib.parse

# Configuration de la page
st.set_page_config(page_title="Validateur Épicerie Québec", page_icon="⚜️", layout="wide")

st.title("⚜️ Module de Validation des Descriptions par UPC (Québec)")
st.write("Étape 1 : Validation de l'exactitude des noms et descriptions des produits.")

@st.cache_data
def charger_et_analyser_base():
    # ID de votre document et identifiant unique de votre onglet
    sheet_id = "1-Xv0jRlYyIGZN5TdeS_fhNAWAnP7kQmbJmADUxpZJGc"
    gid_id = "1814577010"
    
    # URL officielle d'API (tq) pour extraire le CSV de manière propre sans blocage Google
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid_id}"
  
    try:
        # Lecture directe du flux CSV sécurisé
        df = pd.read_csv(url_csv)
        
        # Nettoyage et forçage en minuscules des en-têtes de colonnes
        df.columns = df.columns.str.strip().str.lower()
        
        # Identification des colonnes essentielles
        col_upc = next((c for c in df.columns if 'upc' in c or 'barre' in c), None)
        col_nom = next((c for c in df.columns if 'nom' in c or 'desc' in c or 'produit' in c), None)

        if col_upc and col_nom:
            df = df.rename(columns={col_upc: 'code_upc', col_nom: 'nom'})
        else:
            st.error(f"Colonnes critiques introuvables. Colonnes lues : {list(df.columns[:3])}")
            return None
            
        # Nettoyage des guillemets résiduels générés par l'export de l'API Google Gviz
        df['nom'] = df['nom'].astype(str).str.strip('"')
        df['code_upc'] = df['code_upc'].astype(str).str.strip('"')
            
        # Nettoyage strict de l'UPC (complété à 12 chiffres)
        def nettoyer_upc(val):
            val_str = str(val).strip()
            if "e+" in val_str.lower() or "," in val_str or val_str == "nan":
                return "Format Brisé"
            clean = re.sub(r'\D', '', val_str)
            return clean.zfill(12) if clean else "Invalide"
            
        df['upc_propre'] = df['code_upc'].apply(nettoyer_upc)
        return df
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return None

df_complet = charger_et_analyser_base()

if df_complet is not None:
    # ---------------------------------------------------------
    # STATISTIQUES DES CODES À BARRES
    # ---------------------------------------------------------
    total = len(df_complet)
    upc_valides = len(df_complet[df_complet['upc_propre'].str.len() == 12])
    upc_brises = len(df_complet[df_complet['upc_propre'] == "Format Brisé"])
    
    st.header("📊 État de santé des codes UPC")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total des lignes", f"{total:,}")
    c2.metric("Codes UPC scannables", f"{upc_valides:,}", f"{(upc_valides/total)*100:.1f}% exploitables")
    c3.metric("Fichiers Excel altérés (Scientific Notation)", upc_brises, delta="- Action requise" if upc_brises > 0 else "Aucun", delta_color="inverse")
    
    st.divider()

    # ---------------------------------------------------------
    # ZONE D'INSPECTION COMMERCIALE
    # ---------------------------------------------------------
    st.header("🔍 Inspecteur de conformité de la description")
    st.write("Saisissez un produit pour vérifier si sa description actuelle correspond aux registres officiels.")
    
    recherche = st.text_input("Entrez un mot-clé ou un UPC exact :", "")
    
    if recherche:
        r_clean = recherche.strip().lower()
        res = df_complet[df_complet['nom'].astype(str).str.lower().str.contains(r_clean) | df_complet['code_upc'].astype(str).str.contains(r_clean)]
        
        if not res.empty:
            st.success(f"🎯 {len(res)} entrée(s) trouvée(s).")
            
            for idx, row in res.head(5).iterrows():
                upc = row['upc_propre']
                nom_actuel = row['nom']
                
                with st.expander(f"📋 {nom_actuel} — (UPC : {row['code_upc']})", expanded=True):
                    col_info, col_verif = st.columns(2)
                    
                    with col_info:
                        st.markdown("**Description enregistrée dans votre feuille :**")
                        st.info(f"👉 `{nom_actuel}`")
                        
                        if 'entreprise_proprietaire' in row and pd.notna(row['entreprise_proprietaire']):
                            marque_propre = str(row['entreprise_proprietaire']).strip('"')
                            st.write(f"🏢 Marque déclarée : *{marque_propre}*")
                    
                    with col_verif:
                        st.markdown("**Outils de validation instantanée :**")
                        if upc not in ["Invalide", "Format Brisé"]:
                            url_off = f"https://openfoodfacts.org{upc}"
                            st.link_button("🍎 Valider sur Open Food Facts", url_off)
                            
                            # URL ultra-simplifiée et pré-nettoyée (sans f-string pour éviter les conflits)
                            url_google = "https://google.com/search?q=" + str(upc)
                            st.link_button("🔍 Chercher chez les détaillants (CA)", url_google)
                        else:
                            st.error("Le code à barres est mal formaté pour être recherché automatiquement.")
                            
                    st.write("---")
        else:
            st.warning("Aucun produit ne correspond à ce critère.")
