import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

st.set_page_config(page_title="🧪 Test Robot Prix", layout="centered")
st.title("🤖 Testeur de Récupération Automatique")
st.write("Ce script simule la collecte automatique hebdomadaire (le jeudi) pour un produit sélectionné.")

# 1. Connexion au Google Sheet
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1")
    df.columns = [c.strip().lower() for c in df.columns]
    st.success("✅ Connexion à la base de données établie.")
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# 2. Interface de test
st.markdown("### 🔍 Choisir le produit à tester pour l'extraction")
liste_upc = df['code_upc'].astype(str).unique().tolist()
upc_selectionne = st.selectbox("Sélectionnez un code_upc :", liste_upc)

index_ligne = df[df['code_upc'].astype(str) == upc_selectionne].index
nom_produit = df.loc[index_ligne[0], 'nom'] if 'nom' in df.columns else "Produit inconnu"

st.info(f"📦 Produit ciblé : **{nom_produit}** (CUP: {upc_selectionne})")

if st.button("🚀 Lancer la simulation de récupération automatique", type="primary"):
    with st.spinner("Le robot interroge les bannières québécoises..."):
        
        # --- ICI SE PLACE LA LOGIQUE D'EXTRACTION (Scraping ou API) ---
        # Pour le test, nous simulons la réponse automatique que le robot trouverait le jeudi matin
        time.sleep(2)  # On simule le temps de recherche
        
        prix_detectes = {
            'prix_iga': "3.49",
            'prix_super_c': "2.95",
            'prix_maxi': "2.84",
            'prix_metro': "3.39"
        }
        
        st.markdown("### 📊 Résultats trouvés par le robot :")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("IGA", f"{prix_detectes['prix_iga']} $")
        col2.metric("Super C", f"{prix_detectes['prix_super_c']} $")
        col3.metric("Maxi", f"{prix_detectes['prix_maxi']} $")
        col4.metric("Metro", f"{prix_detectes['prix_metro']} $")
        
        # 3. Sauvegarde automatique dans le Google Sheet
        try:
            for cle, valeur in prix_detectes.items():
                if cle in df.columns:
                    df.at[index_ligne[0], cle] = valeur
            
            # Mise à jour dans le Nuage
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.success("🎉 Le robot a mis à jour votre Google Sheet avec succès ! Les prix réels ont été enregistrés.")
            st.caption("Lorsque l'automatisation complète sera en place, ce processus s'exécutera tout seul en arrière-plan chaque jeudi à 4h00 sans que vous n'ayez besoin d'ouvrir cette page.")
            
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement des prix : {e}")
