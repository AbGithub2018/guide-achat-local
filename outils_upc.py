# Fichier : outils_upc.py
import streamlit as st
import pandas as pd
import re

def determiner_provenance_prefixe(code_upc):
    """Analyse les 3 premiers chiffres pour trouver le pays."""
    if pd.isna(code_upc):
        return "Inconnu / Code vide"
        
    # Nettoyage complet : garde uniquement les chiffres
    code_propre = "".join(filter(str.isdigit, str(code_upc)))
    
    if not code_propre or len(code_propre) < 3:
        return "Inconnu / Code invalide"
        
    if len(code_propre) == 11:
        code_propre = "0" + code_propre

    try:
        prefixe = int(code_propre[:3])
    except ValueError:
        return "Code invalide"
    
    # Plages officielles de préfixes mondiaux GS1
    if 0 <= prefixe <= 19 or 30 <= prefixe <= 39 or 50 <= prefixe <= 139:
        return "États-Unis / Canada"
    elif 20 <= prefixe <= 29 or 40 <= prefixe <= 49:
        return "Usage interne / Magasin"
    elif prefixe == 754 or prefixe == 755:
        return "Canada (GS1 Canada)"
    elif 300 <= prefixe <= 379:
        return "France"
    elif 400 <= prefixe <= 440:
        return "Allemagne"
    elif prefixe == 520 or prefixe == 521:
        return "Grèce"
    elif 800 <= prefixe <= 839:
        return "Italie"
    elif 840 <= prefixe <= 849:
        return "Espagne"
    elif 690 <= prefixe <= 699:
        return "Chine"
    elif 740 <= prefixe <= 746:
        return "Amérique centrale"
    elif prefixe == 779:
        return "Argentine"
    elif prefixe == 780:
        return "Chili"
    else:
        return "Autre provenance internationale"

def extraire_id_sheet(url):
    """Extrait proprement l'identifiant unique du Google Sheet."""
    match = re.search(r"/d/([a-zA-A0-9-_]+)", url)
    if match:
        return match.group(1)
    return None

# --- Interface visuelle ---
st.title("Générateur de Provenance UPC")
st.write("Ce script analyse les codes de votre colonne **code_upc** sans modifier votre fichier d'origine.")

url_votre_sheet = st.text_input("Collez l'URL de votre Google Sheet ici :")

if st.button("Lancer l'analyse des codes"):
    id_sheet = extraire_id_sheet(url_votre_sheet)
    
    if not id_sheet:
        st.error("Veuillez entrer une URL Google Sheets valide.")
    else:
        with st.spinner("Lecture du fichier et analyse des provenances..."):
            try:
                # URL pour lire l'onglet Sheet1 au format CSV proprement
                csv_url = f"https://google.com{id_sheet}/gviz/tq?tqx=out:csv&sheet=Sheet1"
                
                # Lecture des données en forçant le format texte (string) pour préserver les 0 au début des codes
                df_origine = pd.read_csv(csv_url, dtype=str)
                df_origine.columns = df_origine.columns.str.strip()
                
                if 'code_upc' not in df_origine.columns:
                    st.error(f"La colonne 'code_upc' est introuvable dans votre onglet Sheet1. Colonnes détectées : {list(df_origine.columns)}")
                else:
                    # Calcul des résultats
                    df_resultats = pd.DataFrame()
                    df_resultats['code_upc'] = df_origine['code_upc']
                    df_resultats['provenance_automatique'] = df_origine['code_upc'].apply(determiner_provenance_prefixe)
                    
                    st.success("🎉 Analyse terminée avec succès !")
                    
                    # Affichage du résultat à l'écran
                    st.write("### Aperçu des résultats à copier :")
                    st.dataframe(df_resultats)
                    
                    # Option de téléchargement
                    csv_telechargement = df_resultats.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Télécharger les résultats en fichier CSV",
                        data=csv_telechargement,
                        file_name="resultats_upc.csv",
                        mime="text/csv"
                    )
            except Exception as e:
                st.error(f"Impossible d'accéder au fichier. Erreur technique : {e}")
