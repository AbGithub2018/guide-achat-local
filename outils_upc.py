# Fichier : outil_upc.py
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


def executer_analyse_vers_nouvelle_feuille():
    """
    Lit la Sheet1, calcule les provenances et écrit les résultats
    dans un onglet séparé nommé 'Resultats_UPC'.
    """
    # 1. Utilise la connexion gsheets existante de votre application
    conn = st.connection("gsheets", type="sheets")
    
    # 2. Lecture de la feuille principale 'Sheet1'
    df_origine = conn.read(worksheet="Sheet1", ttl=0)
    
    # 3. Création d'un nouveau tableau contenant UNIQUEMENT le code_upc et sa provenance
    # De cette façon, aucun changement n'est fait sur la feuille d'origine
    df_resultats = pd.DataFrame()
    df_resultats['code_upc'] = df_origine['code_upc']
    df_resultats['provenance_automatique'] = df_origine['code_upc'].apply(determiner_provenance_prefixe)
    
    # 4. Envoi des données dans le nouvel onglet 'Resultats_UPC'
    # Si l'onglet n'existe pas, Google Sheets le créera automatiquement
    conn.update(worksheet="Resultats_UPC", data=df_resultats)
    return "L'onglet 'Resultats_UPC' a été mis à jour avec succès !"


# --- Interface visuelle pour activer le script ---
if __name__ == "__main__":
    st.title("Générateur de Provenance UPC - Mon Guide d'Achat Local")
    st.write("Ce script extrait les codes de **Sheet1** et génère les résultats dans l'onglet **Resultats_UPC**.")
    
    if st.button("Lancer l'analyse et créer la feuille de résultats"):
        with st.spinner("Analyse des codes-barres en cours..."):
            statut = executer_analyse_vers_nouvelle_feuille()
            st.success(statut)
