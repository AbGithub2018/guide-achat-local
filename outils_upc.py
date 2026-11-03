# Fichier : outils_upc.py
import streamlit as st
import pandas as pd

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

# --- Interface visuelle ---
st.title("Générateur de Provenance UPC")
st.write("Téléchargez votre fichier exporté pour analyser la colonne **code_upc**.")

# Zone de glisser-déposer pour le fichier
fichier_uploade = st.file_uploader("Glissez votre fichier Google Sheet (exporté en Excel .xlsx ou CSV) ici :", type=["xlsx", "csv"])

if fichier_uploade is not None:
    try:
        # Détection automatique du format (Excel ou CSV)
        if fichier_uploade.name.endswith('.xlsx'):
            # Lit l'onglet 'Sheet1' spécifiquement
            df_origine = pd.read_excel(fichier_uploade, sheet_name="Sheet1", dtype=str)
        else:
            df_origine = pd.read_csv(fichier_uploade, dtype=str)
            
        # Nettoyage des espaces dans les noms de colonnes
        df_origine.columns = df_origine.columns.str.strip()
        
        if 'code_upc' not in df_origine.columns:
            st.error(f"La colonne 'code_upc' est introuvable. Colonnes détectées dans le fichier : {list(df_origine.columns)}")
        else:
            # Calcul des résultats
            df_resultats = pd.DataFrame()
            df_resultats['code_upc'] = df_origine['code_upc']
            df_resultats['nom'] = df_origine['nom'] if 'nom' in df_origine.columns else ""
            df_resultats['provenance_automatique'] = df_origine['code_upc'].apply(determiner_provenance_prefixe)
            
            st.success("🎉 Analyse terminée avec succès !")
            
            # Affichage du résultat à l'écran
            st.write("### Aperçu des résultats :")
            st.dataframe(df_resultats)
            
            # Création du bouton de téléchargement direct en Excel pour votre confort
            @st.cache_data
            def convertir_en_excel(df):
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Resultats_UPC')
                return output.getvalue()
                
            try:
                data_excel = convertir_en_excel(df_resultats)
                st.download_button(
                    label="📥 Télécharger le fichier Excel complété",
                    data=data_excel,
                    file_name="resultats_upc.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception:
                # Secours en CSV si xlsxwriter n'est pas installé
                csv_data = df_resultats.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Télécharger les résultats (Format CSV)",
                    data=csv_data,
                    file_name="resultats_upc.csv",
                    mime="text/csv"
                )
                
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")
