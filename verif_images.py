import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Maintenance - Achat Québec", page_icon="🛠️")
st.title("🛠️ Outil de Contrôle de Qualité des Images")

if st.button("🚀 Lancer le test sur la barre Kashi", type="primary"):
    with st.spinner("Analyse du produit Kashi en cours..."):
        
        # Dossier de sauvegarde local
        dossier_actuel = os.path.dirname(os.path.abspath(__file__))
        dossier_photos = os.path.join(dossier_actuel, "images")
        if not os.path.exists(dossier_photos):
            os.makedirs(dossier_photos)
            
        # Code-barres de votre barre Kashi
        cup_test = "056543001013"
        
        # Interrogation directe de l'API v0 originale
        url_api = f"https://ca.openfoodfacts.org/api/v0/product/{cup_actuel}.json"
        headers = {"User-Agent": "AchatQuebecMaintenance - robert.st.jules@gmail.com"}
        
        try:
            res = requests.get(url_api, headers=headers, timeout=5).json()
            if res.get("status") == 1 and "product" in res:
                img_url = res["product"].get("image_url")
                
                if not img_url:
                    st.error("❌ Le serveur n'a pas d'image pour ce produit.")
                else:
                    # Téléchargement immédiat de l'image
                    img_data = requests.get(img_url, timeout=5).content
                    chemin_sauvegarde = os.path.join(dossier_photos, f"{cup_test}.jpg")
                    
                    with open(chemin_sauvegarde, "wb") as handler:
                        handler.write(img_data)
                        
                    st.success(f"🎯 SUCCÈS ! L'image de la barre Kashi a été enregistrée avec succès dans : {chemin_sauvegarde}")
            else:
                st.error("❌ Code-barres introuvable sur le serveur.")
        except Exception as e:
            st.error(f"❌ Erreur technique : {str(e)}")
