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
    url_csv = "https://google.com"
    
    try:
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip().str.lower()
        
        # Identification des colonnes essentielles
        col_upc = next((c for c in df.columns if 'upc' in c or 'barre' in c), None)
        col_nom = next((c for c in df.columns if 'nom' in c or 'desc' in c or 'produit' in c), None)

        if col_upc and col_nom:
            df = df.rename(columns={col_upc: 'code_upc', col_nom: 'nom'})
        else:
            st.error(f"Colonnes critiques introuvables. Colonnes lues : {list(df.columns[:5])}")
            return None
            
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
                    col_info, col_verif = st.columns([2, 1])
                    
                    with col_info:
                        st.markdown("**Description enregistrée dans votre feuille :**")
                        st.info(f"👉 `{nom_actuel}`")
                        
                        # Affichage optionnel des données complémentaires de la ligne
                        if 'entreprise_proprietaire' in row and pd.notna(row['entreprise_proprietaire']):
                            st.write(f"🏢 Marque déclarée : *{row['entreprise_proprietaire']}*")
                    
                    with col_verif:
                        st.markdown("**Outils de validation instantanée :**")
                        if upc not in ["Invalide", "Format Brisé"]:
                            # Lien direct vers Open Food Facts Canada pour valider le texte descriptif exact
                            url_off = f"https://ca-fr.openfoodfacts.org/produit/{upc}"
                            st.link_button("🍎 Valider sur Open Food Facts", url_off)
                            
                            # Recherche Google pré-configurée pour croiser l'UPC avec les circulaires d'épicerie du Québec
                            query_google = urllib.parse.quote(f'"{upc}" site:ca')
                            url_google = f"https://google.com{query_google}"
                            st.link_button("🔍 Chercher chez les détaillants (CA)", url_google)
                        else:
                            st.error("Le code à barres est mal formaté pour être recherché automatiquement.")
                            
                    st.write("---")
        else:
            st.warning("Aucun produit ne correspond à ce critère.")
