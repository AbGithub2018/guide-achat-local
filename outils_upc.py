# Fichier : outils_upc.py
import streamlit as st
import pandas as pd
import urllib.parse
import time
import requests
import re
import os
from streamlit_gsheets import GSheetsConnection

def determiner_provenance_prefixe(code_upc):
    """
    Analyse les 3 premiers chiffres d'un code UPC 
    pour trouver le pays du siège social de la marque.
    """
    code_propre = str(code_upc).strip().replace(" ", "").replace("-", "")
    
    if not code_propre or len(code_propre) < 3:
        return "Inconnu / Code invalide"
        
    if len(code_propre) == 11:
        code_propre = "0" + code_propre

    try:
        prefixe = int(code_propre[:3])
    except ValueError:
        return "Code invalide (lettres)"
    
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


def executer_analyse_vers_nouvelle_feuille():
    """
    Lit la Sheet1, calcule les provenances et écrit les résultats
    directement dans le 3e onglet 'Resultats_UPC'.
    """
    # MODIFICATION ICI : On force l'utilisation de la configuration nommée "gsheets" 
    # pour récupérer automatiquement le lien du fichier défini dans vos secrets de production.
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Lecture de la feuille principale 'Sheet1'
    df_origine = conn.read(worksheet="Sheet1", ttl=0, dtype={"code_upc": str})
    
    # S'assurer que la colonne existe
    if 'code_upc' not in df_origine.columns:
        raise ValueError("La colonne 'code_upc' est introuvable dans Sheet1. Vérifiez l'orthographe.")
    
    # Création du tableau de résultats propre (sans modifier Sheet1)
    df_resultats = pd.DataFrame()
    df_resultats['code_upc'] = df_origine['code_upc']
    df_resultats['provenance_automatique'] = df_origine['code_upc'].apply(determiner_provenance_prefixe)
    
    # Envoi AUTOMATIQUE des données dans le 3e onglet 'Resultats_UPC'
    conn.update(worksheet="Resultats_UPC", data=df_resultats)
    return df_resultats


# --- Interface visuelle du script ---
st.title("Générateur de Provenance UPC")
st.write("Ce script extrait les codes de **Sheet1** et met à jour automatiquement l'onglet **Resultats_UPC**.")

if st.button("Lancer l'analyse automatique"):
    with st.spinner("Connexion à Google Sheets et calcul des codes..."):
        try:
            df_final = executer_analyse_vers_nouvelle_feuille()
            st.success("🎉 L'onglet 'Resultats_UPC' a été mis à jour avec succès dans votre Google Sheet !")
            
            # Affichage de validation à l'écran
            st.write("### Aperçu des données enregistrées :")
            st.dataframe(df_final.head(10))
            
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")
