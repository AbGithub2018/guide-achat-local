import pandas as pd
import streamlit as st  # Ou votre framework d'affichage

# 1. Chargement de votre liste officielle des bannières (téléchargée)
@st.cache_data
def charger_bannieres():
    # Ce fichier contient vos colonnes 'Code postal' et 'Banniere'
    df_bannieres = pd.read_csv("codes_qc.csv")
    # Nettoyage pour s'assurer qu'il n'y a pas d'espaces masqués qui bloquent la recherche
    df_bannieres['Code postal'] = df_bannieres['Code postal'].str.replace(" ", "").str.upper()
    return df_bannieres

# 2. Application de la jointure sur vos résultats GeoNames
def fusionner_bannieres(df_geonames):
    df_bannieres = charger_bannieres()
    
    # On nettoie temporairement les codes postaux de GeoNames pour la correspondance (ex: "G0M 0A1" -> "G0M0A1")
    df_geonames['Code_Nettoye'] = df_geonames['Code postal'].str.replace(" ", "").str.upper()
    
    # La ligne magique : Python associe la bonne bannière à chaque code postal d'un seul coup !
    df_final = pd.merge(df_geonames, df_bannieres[['Code postal', 'Banniere']], 
                         left_on='Code_Nettoye', right_on='Code postal', how='left')
    
    # Nettoyage des colonnes temporaires
    df_final = df_final.drop(columns=['Code_Nettoye', 'Code postal_y'])
    df_final = df_final.rename(columns={'Code postal_x': 'Code postal'})
    
    # Optionnel : Remplir par une valeur si le code postal n'avait pas de bannière attitrée
    df_final['Banniere'] = df_final['Banniere'].fillna("Bannière Générale Québec")
    
    return df_final

# --- SECTION AFFICHAGE DE VOS RÉSULTATS ---
# Au moment d'afficher votre tableau de 48 correspondances (ex: df_resultats) :
df_a_afficher = fusionner_bannieres(df_resultats)

# Affichage du tableau final incluant automatiquement la colonne 'Banniere'
st.dataframe(df_a_afficher)
