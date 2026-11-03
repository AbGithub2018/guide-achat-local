# Fichier : outils_upc.py
import pandas as pd
import streamlit as st

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


def executer_analyse_sans_connecteur(url_partage_sheet):
    """
    Lit la Sheet1 via son URL de partage public, calcule les provenances
    et prépare le tableau final.
    """
    # Étape essentielle : On transforme l'URL de partage en lien de téléchargement direct CSV
    url_csv = url_partage_sheet.replace("/edit?usp=sharing", "/export?format=csv&gid=0")
    
    # Lecture de la feuille principale 'Sheet1' sans avoir besoin de la bibliothèque gsheets
    df_origine = pd.read_csv(url_csv, dtype={"code_upc": str})
    
    # S'assurer que la colonne existe
    if 'code_upc' not in df_origine.columns:
        raise ValueError("La colonne 'code_upc' est introuvable dans Sheet1. Vérifiez l'orthographe.")
        
    # Création du tableau de résultats propre
    df_resultats = pd.DataFrame()
    df_resultats['code_upc'] = df_origine['code_upc']
    df_resultats['provenance_automatique'] = df_origine['code_upc'].apply(determiner_provenance_prefixe)
    
    return df_resultats


# --- Interface visuelle pour activer le script ---
if __name__ == "__main__":
    st.title("Générateur de Provenance UPC")
    st.write("Ce script extrait les codes de **Sheet1** et génère les résultats pour l'onglet **Resultats_UPC**.")
    
    # Collez ici l'URL de partage de votre Google Sheet 'produits_enrichis'
    # (Celle que vous obtenez en cliquant sur le bouton bleu "Partager" dans Google)
    url_fiche = st.text_input(
        "Entrez l'URL de partage de votre Google Sheet :",
        value="https://google.com"
    )
    
    if st.button("Lancer l'analyse des codes"):
        with st.spinner("Analyse des codes-barres en cours..."):
            try:
                df_final = executer_analyse_sans_connecteur(url_fiche)
                st.success("Analyse terminée avec succès !")
                
                # Affiche un aperçu des résultats directement dans votre Streamlit pour valider
                st.write("### Aperçu des résultats calculés :")
                st.dataframe(df_final.head(10))
                
                st.info("💡 Étape finale : Copiez ces lignes ou téléchargez-les pour les coller dans votre 3e onglet 'Resultats_UPC'.")
                
            except Exception as e:
                st.error(f"Une erreur est survenue lors de la lecture : {e}")
