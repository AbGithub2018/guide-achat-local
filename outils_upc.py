# Fichier : outils_upc.py
import streamlit as st
import pandas as pd

def determiner_pays_upc_theorique(code_upc):
    """Analyse purement théorique des 3 premiers chiffres GS1."""
    if pd.isna(code_upc):
        return "Inconnu"
    code_propre = "".join(filter(str.isdigit, str(code_upc)))
    if not code_propre or len(code_propre) < 3:
        return "Inconnu"
    if len(code_propre) == 11:
        code_propre = "0" + code_propre
    try:
        prefixe = int(code_propre[:3])
    except ValueError:
        return "Inconnu"
    
    if 0 <= prefixe <= 19 or 30 <= prefixe <= 39 or 50 <= prefixe <= 139:
        return "États-Unis / Canada"
    elif prefixe == 754 or prefixe == 755:
        return "Canada (GS1 Canada)"
    elif 300 <= prefixe <= 379:
        return "France"
    elif 400 <= prefixe <= 440:
        return "Allemagne"
    elif 800 <= prefixe <= 839:
        return "Italie"
    elif 690 <= prefixe <= 699:
        return "Chine"
    else:
        return "Autre international"

# --- Interface utilisateur ---
st.set_page_config(page_title="Validateur de Données UPC", layout="wide")
st.title("⚜️ Validateur et Générateur d'Impact Québécois")
st.write("Ce script utilise vos corrections manuelles pour certifier la provenance réelle face au code UPC.")

# Zone de téléversement
fichier_uploade = st.file_uploader("Glissez votre fichier Excel (.xlsx) ici :", type=["xlsx"])

if fichier_uploade is not None:
    try:
        # Lecture de la feuille corrigée 'Sheet1'
        df_origine = pd.read_excel(fichier_uploade, sheet_name="Sheet1", dtype=str)
        
        # Nettoyage des colonnes pour éviter les espaces invisibles
        df_origine.columns = df_origine.columns.str.strip()
        
        # Vérification des colonnes nécessaires
        colonnes_requises = ['code_upc', 'nom', 'siege_social', 'lieu_usine', 'entreprise_province_etat']
        manquantes = [col for col in colonnes_requises if col not in df_origine.columns]
        
        if manquantes:
            st.error(f"Il manque des colonnes essentielles dans votre onglet Sheet1 : {manquantes}")
        else:
            with st.spinner("Analyse croisée de vos données en cours..."):
                df_validation = pd.DataFrame()
                
                # Reprise des informations de base
                df_validation['code_upc'] = df_origine['code_upc']
                df_validation['nom'] = df_origine['nom']
                
                # 1. Calcul de la provenance administrative brute
                df_validation['pays_upc_theorique'] = df_origine['code_upc'].apply(determiner_pays_upc_theorique)
                
                # 2. Validation de l'impact local réel basé sur VOS corrections
                def valider_impact_quebec(row):
                    prov_etat = str(row.get('entreprise_province_etat', '')).strip().lower()
                    siege = str(row.get('siege_social', '')).strip().lower()
                    usine = str(row.get('lieu_usine', '')).strip().lower()
                    nom_produit = str(row.get('nom', '')).strip().lower()
                    
                    # Détection des mots-clés du Québec dans vos données corrigées
                    if any(x in prov_etat or x in siege or x in usine or x in nom_produit for x in ['québec', 'quebec', 'qc', 'anjou', 'saint-jérôme', 'sainte-anne']):
                        return "⚜️ Emploi Québec Confirmé"
                    elif "ontario" in prov_etat or "ontario" in siege or "saskatchewan" in prov_etat or "manitoba" in siege:
                        return "🍁 Économie Canadienne Hors-QC"
                    else:
                        return "🌍 International"
                
                df_validation['impact_local_reel'] = df_origine.apply(valider_impact_quebec, axis=1)
                
                # 3. Génération des détails explicatifs pour les consommateurs
                def generer_explication(row):
                    if "Emploi Québec" in valider_impact_quebec(row):
                        return f"Génère de l'emploi local. Usine/Ferme : {row['lieu_usine']} ; Siège : {row['siege_social']}"
                    else:
                        return f"Marque internationale contrôlée par {row['entreprise_proprietaire']} ({row['entreprise_province_etat']})"
                
                df_validation['fiche_consommateur'] = df_origine.apply(generer_explication, axis=1)
                
                st.success("🎉 Analyse croisée effectuée !")
                
                # Aperçu du tableau de validation qui ira dans le 3e onglet
                st.write("### Aperçu des données qui seront enregistrées dans l'onglet 'Resultats_UPC' :")
                st.dataframe(df_validation)
                
                # Exportation au format Excel propre
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_validation.to_excel(writer, index=False, sheet_name='Resultats_UPC')
                data_excel = output.getvalue()
                
                st.download_button(
                    label="📥 Télécharger le fichier pour votre 3e onglet (Resultats_UPC)",
                    data=data_excel,
                    file_name="validation_produits_upc.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
    except Exception as e:
        st.error(f"Une erreur est survenue lors de la validation : {e}")
