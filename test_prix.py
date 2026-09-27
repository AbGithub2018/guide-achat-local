import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import requests

st.set_page_config(page_title="🤖 Robot Réel IGA", layout="centered")
st.title("🤖 Robot d'extraction Réel - IGA")
st.write("Ce script interroge en direct le site d'IGA pour trouver le vrai prix du produit.")

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
st.markdown("### 🔍 Choisir le produit à tester pour l'extraction")
liste_upc = df['code_upc'].astype(str).unique().tolist()
upc_selectionne = st.selectbox("Sélectionnez un code_upc :", liste_upc)

index_ligne = df[df['code_upc'].astype(str) == upc_selectionne].index
nom_produit = df.loc[index_ligne, 'nom'].values[0] if 'nom' in df.columns and len(index_ligne) > 0 else "Produit inconnu"

st.info(f"📦 Produit ciblé : **{nom_produit}** (CUP: {upc_selectionne})")

# 3. Bouton d'action réel
if st.button("🚀 Interroger le site d'IGA en direct", type="primary"):
    with st.spinner("Le robot cherche le produit sur le site d'IGA..."):
        
        # 🟢 REQUÊTE DIRECTE SUR L'API PUBLIQUE D'IGA
        # Nous nettoyons le code UPC pour la recherche (enlèvement du 0 devant si nécessaire)
        upc_clean = upc_selectionne.strip()
        url_api_iga = f"https://www.iga.net/api/fr/Search/GetResults?searchTerm={upc_clean}"
        
            headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "fr-CA,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
        
        prix_iga_reel = "Non trouvé"
        
        try:
            reponse = requests.get(url_api_iga, headers=headers, timeout=15)
            if reponse.status_code == 200:
                donnees = reponse.json()
                
                # Extraction du prix depuis les résultats de recherche IGA
                if donnees.get('Products') and len(donnees['Products']) > 0:
                    premier_produit = donnees['Products'][0]
                    # IGA retourne souvent le prix sous forme de nombre (ex: 3.99)
                    montant = premier_produit.get('Price')
                    if montant:
                        prix_iga_reel = f"{montant:.2f}"
                else:
                    # Deuxième tentative si le CUP complet ne donne rien (recherche par nom)
                    st.warning("⚠️ Recherche exacte par CUP infructueuse, tentative avec les 11 premiers chiffres...")
                    url_api_iga_courte = f"https://iga.net{upc_clean[1:]}"
                    reponse2 = requests.get(url_api_iga_courte, headers=headers, timeout=15)
                    donnees2 = reponse2.json()
                    if donnees2.get('Products') and len(donnees2['Products']) > 0:
                        prix_iga_reel = f"{donnees2['Products'][0].get('Price'):.2f}"
                        
        except Exception as e:
            st.error(f"❌ Erreur lors de la communication avec IGA : {e}")

        # Assemblage des résultats (IGA réel, les autres restent simulés pour l'instant)
        prix_detectes = {
            'prix_iga': prix_iga_reel,
            'prix_super_c': "2.95",
            'prix_maxi': "2.84",
            'prix_metro': "3.39"
        }
        
        # Affichage à l'écran
        st.markdown("### 📊 Résultats obtenus :")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("IGA (EN DIRECT !)", f"{prix_detectes['prix_iga']} $")
        col2.metric("Super C (Simulé)", f"{prix_detectes['prix_super_c']} $")
        col3.metric("Maxi (Simulé)", f"{prix_detectes['prix_maxi']} $")
        col4.metric("Metro (Simulé)", f"{prix_detectes['prix_metro']} $")
        
        # 4. Sauvegarde automatique si un prix a été trouvé
        if prix_iga_reel != "Non trouvé":
            try:
                if 'prix_iga' in df.columns:
                    df.at[index_ligne, 'prix_iga'] = prix_iga_reel
                
                conn.update(worksheet="Sheet1", data=df)
                st.cache_data.clear()
                st.success(f"🎉 Succès ! Le vrai prix d'IGA ({prix_iga_reel} $) a été enregistré dans le Nuage !")
            except Exception as e:
                st.error(f"Erreur d'enregistrement : {e}")
        else:
            st.error("❌ Le robot n'a pas réussi à capturer le prix sur le site d'IGA. Le site bloque peut-être la requête automatisée.")
