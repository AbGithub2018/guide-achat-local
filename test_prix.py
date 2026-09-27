import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import requests

st.set_page_config(page_title="🤖 Robot Double Maxi & Super C", layout="centered")
st.title("🤖 Robot d'extraction - Maxi & Super C")
st.write("Ce script tente d'interroger en même temps Maxi et Super C en direct.")

# 1. Connexion au Google Sheet
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1")
    df.columns = [c.strip().lower() for c in df.columns]
    st.success("✅ Connexion à la base de données établie.")
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# 2. Sélection du produit
st.markdown("### 🔍 Choisir le produit à tester")
liste_upc = df['code_upc'].astype(str).unique().tolist()
upc_selectionne = st.selectbox("Sélectionnez un code_upc :", liste_upc)

index_ligne = df[df['code_upc'].astype(str) == upc_selectionne].index
nom_produit = df.loc[index_ligne, 'nom'].values[0] if 'nom' in df.columns and len(index_ligne) > 0 else "Produit inconnu"

st.info(f"📦 Produit ciblé : **{nom_produit}** (CUP: {upc_selectionne})")

# 3. Bouton d'action réel pour le test simultané
if st.button("🚀 Lancer l'extraction simultanée", type="primary"):
    with st.spinner("Le robot interroge Maxi et Super C en même temps..."):
        
        upc_clean = upc_selectionne.strip()
        
        # --- CONFIGURATION COMMUNE DES SIGNATURES ---
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fr-CA,fr;q=0.9"
        }
        
        prix_maxi_reel = "Non trouvé"
        prix_super_c_reel = "Non trouvé"
        
        # 🟢 RETRAITE 1 : INTERROGATION DE MAXI (LOBLAWS)
        url_maxi = "https://pcexpress.ca"
        payload_maxi = {
            "searchTerm": upc_clean,
            "pagination": {"pageNumber": 1, "pageSize": 1}
        }
        try:
            reponse_maxi = requests.post(url_maxi, json=payload_maxi, headers=headers, timeout=12)
            if reponse_maxi.status_code == 200:
                data_maxi = reponse_maxi.json()
                if data_maxi.get('results') and len(data_maxi['results']) > 0:
                    prod = data_maxi['results'][0]
                    if prod.get('prices') and prod['prices'].get('price'):
                        prix_maxi_reel = f"{prod['prices']['price'].get('value'):.2f}"
        except Exception as e:
            st.warning(f"Maxi indisponible lors de la requête : {e}")

        # 🟢 REQUÊTE 2 : INTERROGATION DE SUPER C
        url_super_c = "https://superc.ca"
        params_super_c = {"q": upc_clean, "lang": "fr"}
        try:
            reponse_sc = requests.get(url_super_c, params=params_super_c, headers=headers, timeout=12)
            if reponse_sc.status_code == 200:
                data_sc = reponse_sc.json()
                if data_sc.get('products') and len(data_sc['products']) > 0:
                    prod_sc = data_sc['products'][0]
                    if prod_sc.get('price'):
                        prix_super_c_reel = f"{prod_sc.get('price'):.2f}"
        except Exception as e:
            st.warning(f"Super C indisponible lors de la requête : {e}")

        # Résultats finaux (On garde IGA et Metro simulés pour ce test)
        prix_detectes = {
            'prix_iga': "3.99",
            'prix_super_c': prix_super_c_reel,
            'prix_maxi': prix_maxi_reel,
            'prix_metro': "3.39"
        }
        
        # Affichage des résultats à l'écran
        st.markdown("### 📊 Résultats obtenus :")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("IGA (Simulé)", f"{prix_detectes['prix_iga']} $")
        col2.metric("Super C (EN DIRECT !)", f"{prix_detectes['prix_super_c']} $")
        col3.metric("Maxi (EN DIRECT !)", f"{prix_detectes['prix_maxi']} $")
        col4.metric("Metro (Simulé)", f"{prix_detectes['prix_metro']} $")
        
        # 4. Sauvegarde automatique des données réelles récoltées
        sauvegarde_effectuee = False
        if prix_maxi_reel != "Non trouvé" or prix_super_c_reel != "Non trouvé":
            try:
                if prix_maxi_reel != "Non trouvé" and 'prix_maxi' in df.columns:
                    df.at[index_ligne, 'prix_maxi'] = prix_maxi_reel
                    sauvegarde_effectuee = True
                if prix_super_c_reel != "Non trouvé" and 'prix_super_c' in df.columns:
                    df.at[index_ligne, 'prix_super_c'] = prix_super_c_reel
                    sauvegarde_effectuee = True
                
                if sauvegarde_effectuee:
                    conn.update(worksheet="Sheet1", data=df)
                    st.cache_data.clear()
                    st.success("🎉 Le robot a mis à jour votre Google Sheet avec les vrais prix trouvés !")
            except Exception as e:
                st.error(f"Erreur d'enregistrement dans Google Sheets : {e}")
        else:
            st.error("❌ Le robot n'a malheureusement capturé aucun prix en direct pour Maxi et Super C.")
