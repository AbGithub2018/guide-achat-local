import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="🧪 Test de Connexion Prix", layout="centered")
st.title("🧪 Script de Test Indépendant")
st.write("Ce script valide l'écriture des prix sans toucher à votre application principale.")

# 1. Connexion et lecture de sécurité
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1")
    df.columns = [c.strip().lower() for c in df.columns]
    st.success("✅ Connexion réussie au Google Sheet !")
except Exception as e:
    st.error(f"❌ Erreur de connexion initiale : {e}")
    st.stop()

# 2. Sélection du produit pour le test
st.markdown("### 1. Choisir le produit à modifier")
liste_upc = df['code_upc'].astype(str).unique().tolist()
upc_test = st.selectbox("Sélectionnez un code_upc pour le test :", liste_upc)

# Trouver la ligne correspondante
index_ligne = df[df['code_upc'].astype(str) == upc_test].index[0]
produit = df.iloc[index_ligne]

st.info(f"📋 Produit sélectionné : **{produit.get('nom', 'Sans nom')}**")

# 3. Formulaire de modification isolé
st.markdown("### 2. Entrez les prix de test")
with st.form("formulaire_test_prix"):
    col1, col2, col3, col4 = st.columns(4)
    nouveau_iga = col1.text_input("IGA ($) :", value=str(produit.get('prix_iga', '')))
    nouveau_super_c = col2.text_input("Super C ($) :", value=str(produit.get('prix_super_c', '')))
    nouveau_maxi = col3.text_input("Maxi ($) :", value=str(produit.get('prix_maxi', '')))
    nouveau_metro = col4.text_input("Metro ($) :", value=str(produit.get('prix_metro', '')))
    
    bouton_tester = st.form_submit_button("🚀 Tester l'enregistrement réel", type="primary")

# 4. Traitement de la sauvegarde de test
if bouton_tester:
    with st.spinner("Envoi des données vers le nuage..."):
        try:
            # Application des valeurs nettoyées sur notre copie locale
            df.at[index_ligne, 'prix_iga'] = nouveau_iga.strip()
            df.at[index_ligne, 'prix_super_c'] = nouveau_super_c.strip()
            df.at[index_ligne, 'prix_maxi'] = nouveau_maxi.strip()
            df.at[index_ligne, 'prix_metro'] = nouveau_metro.strip()
            
            # Envoi forcé vers Google Sheets
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.balloons()
            st.success("🎉 BRAVO ! Les prix ont été modifiés avec succès dans votre Google Sheet.")
            st.write("Vous pouvez aller ouvrir votre fichier Google Sheets pour confirmer le changement.")
            
        except Exception as e:
            st.error(f"❌ L'écriture a échoué. Erreur technique : {e}")
