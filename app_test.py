import pandas as pd
import streamlit as st

# Configuration de la page
st.set_page_config(page_title="Moteur de Recherche - Codes Postaux Québec", layout="wide")
st.title("CA Moteur de Recherche - Codes Postaux Québec")
st.caption("Ce prototype utilise les données géographiques nettoyées de GeoNames combinées aux bannières locales.")

# 1. Chargement et nettoyage de votre base de données officielle (Le repère)
@st.cache_data
def charger_base_bannieres():
    try:
        # Lecture du fichier mis en place sur votre GitHub
        df_bannieres = pd.read_csv("codes_qc.csv")
        
        # Standardisation des colonnes pour éviter les problèmes de majuscules/minuscules
        df_bannieres.columns = df_bannieres.columns.str.strip()
        
        # Nettoyage du code postal (ex: "G0M 0A1" -> "G0M0A1") pour une fusion parfaite
        if 'Code postal' in df_bannieres.columns:
            df_bannieres['Code_Unique'] = df_bannieres['Code postal'].astype(str).str.replace(" ", "").str.upper()
        elif 'code_postal' in df_bannieres.columns:
            df_bannieres['Code_Unique'] = df_bannieres['code_postal'].astype(str).str.replace(" ", "").str.upper()
        else:
            # Si la colonne s'appelle autrement, on prend la première colonne du fichier
            df_bannieres['Code_Unique'] = df_bannieres.iloc[:, 1].astype(str).str.replace(" ", "").str.upper()
            
        return df_bannieres
    except Exception as e:
        st.error(f"Erreur lors du chargement de codes_qc.csv : {e}")
        return None

# Chargement initial des données
df_repere = charger_base_bannieres()

# 2. Zone de recherche pour l'utilisateur
recherche = st.text_input("Rechercher par Code Postal (ex: G5Y ou G0M 0A1) ou par Ville :").strip().upper()

# 3. Traitement et filtrage des données
if df_repere is not None and recherche:
    
    # Enlève les espaces de la recherche de l'utilisateur pour être plus flexible
    recherche_nettoyee = recherche.replace(" ", "")
    
    # Filtrage : On cherche si ça correspond au début du code postal ou au nom de la ville
    # Vérification du nom de la colonne Ville/Town
    colonne_ville = 'Ville' if 'Ville' in df_repere.columns else ('ville' if 'ville' in df_repere.columns else None)
    
    if colonne_ville:
        masque_recherche = (
            df_repere['Code_Unique'].str.startswith(recherche_nettoyee) | 
            df_repere[colonne_ville].astype(str).str.upper().str.contains(recherche)
        )
    else:
        masque_recherche = df_repere['Code_Unique'].str.startswith(recherche_nettoyee)
        
    df_filtré = df_repere[masque_recherche].copy()
    
    # 4. Affichage des résultats
    if not df_filtré.empty:
        nb_correspondances = len(df_filtré)
        st.subheader(f"📍 Résultats ({nb_correspondances} correspondances)")
        
        # Détermination de la colonne de bannière
        # Si vous n'avez pas encore d'informations de bannières dans le CSV, on crée une simulation réaliste
        colonnes_banniere_possibles = ['Banniere', 'Bannière', 'banniere', 'bannière']
        colonne_banniere_trouvee = next((col for col in colonnes_banniere_possibles if col in df_filtré.columns), None)
        
        if not colonne_banniere_trouvee:
            # Si la colonne n'existe pas encore dans votre fichier, Python la génère dynamiquement pour le test !
            # Cela permet de voir le résultat immédiatement selon l'UDL (ex: G0M 0A1 vs G0M 0A2)
            df_filtré['Bannière'] = df_filtré['Code postal'].apply(
                lambda x: f"Bannière Spécifique Zone {str(x).upper()}"
            )
        
        # Préparation du tableau final à afficher au consommateur (on retire la colonne technique)
        df_affichage = df_filtré.drop(columns=['Code_Unique'], errors='ignore')
        
        # Affichage du tableau final interactif
        st.dataframe(df_affichage, use_container_width=True)
        
    else:
        st.warning("Aucune correspondance trouvée. Vérifiez l'orthographe ou le code postal saisi.")
        
elif df_repere is not None:
    st.info("Veuillez saisir un code postal ou une ville ci-dessus pour afficher les bannières correspondantes.")
