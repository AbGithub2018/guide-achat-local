import os
import requests
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Configuration de la page du site de maintenance
st.set_page_config(page_title="Maintenance - Achat Québec", page_icon="🛠️")
st.title("🛠️ Outil de Contrôle de Qualité des Images")
st.write("Ce site analyse vos produits pour trouver les photos manquantes ou floues.")

# Bouton pour lancer l'action
if st.button("🚀 Démarrer l'analyse des 200 produits suivants", type="primary"):
    
    with st.spinner("Connexion à votre Google Sheet et analyse des images en cours..."):
        
        # 1. Connexion à votre Google Sheet (onglet 'Sheets')
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_produits = conn.read(worksheet="Sheet1") 
        
        colonne_code = 'code_upc' 
        
        if colonne_code not in df_produits.columns:
            st.error(f"❌ La colonne '{colonne_code}' n'existe pas dans votre onglet Sheets.")
        else:
            produits_a_corriger = []
            
            # Définition automatique de l'emplacement du dossier "images" à côté du script
            dossier_actuel = os.path.dirname(os.path.abspath(__file__))
            dossier_photos = os.path.join(dossier_actuel, "images")
            if not os.path.exists(dossier_photos):
                os.makedirs(dossier_photos)
            
            # Analyse de la plage (Lignes 1000 à 1200)
            for index, row in df_produits.iloc[1000:1200].iterrows():
                valeur_cellule = row[colonne_code]
                if pd.isna(valeur_cellule):
                    continue
                    
                cup_actuel = str(valeur_cellule).strip()
                if cup_actuel.endswith('.0'):
                    cup_actuel = cup_actuel[:-2]
                    
                if not cup_actuel or cup_actuel in ["nan", ""]:
                    continue

                # Étape 1 : On vérifie si l'image existe déjà sur le PC
                image_locale_existe = False
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    if os.path.exists(os.path.join(dossier_photos, f"{cup_actuel}{ext}")):
                        image_locale_existe = True
                        break
                        
                if image_locale_existe:
                    continue # L'image est déjà sur le PC, on passe au produit suivant !

                # Étape 2 : L'image n'est pas sur le PC, on interroge l'API Canada v3
                url_api = f"https://ca.openfoodfacts.org/api/v3/product/{cup_actuel}.json"
                headers = {"User-Agent": "AchatQuebecMaintenance - robert.st.jules@gmail.com"}
                
                try:
                    res = requests.get(url_api, headers=headers, timeout=3).json()
                    if res.get("status") != "failure" and "product" in res:
                        img_url = res["product"].get("image_url")
                        
                        if not img_url:
                            produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Image manquante sur Open Food Facts"})
                        else:
                            # Vérification du poids de la photo sur l'API
                            meta = requests.head(img_url, timeout=3)
                            poids_distant = int(meta.headers.get("Content-Length", 0))
                            
                            if poids_distant < 15000:
                                produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Qualité médiocre en ligne (< 15 Ko)"})
                            else:
                                # L'IMAGE EN LIGNE EST BONNE (>= 15 Ko) : ON LA TÉLÉCHARGE DANS LE DOSSIER DU PC
                                img_data = requests.get(img_url, timeout=5).content
                                
                                # Extraction propre de l'extension de l'URL (.jpg, .png, etc.)
                                url_sans_param = str(img_url).split('?')[0]
                                ext_distante = os.path.splitext(url_sans_param)[1].lower()
                                if ext_distante not in [".jpg", ".jpeg", ".png", ".webp"]:
                                    ext_distante = ".jpg"
                                    
                                chemin_sauvegarde = os.path.join(dossier_photos, f"{cup_actuel}{ext_distante}")
                                with open(chemin_sauvegarde, "wb") as handler:
                                    handler.write(img_data)
                    else:
                        produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Produit inconnu sur Open Food Facts"})
                except Exception:
                    pass

            # 2. Affichage des anomalies à l'écran (celles qui n'ont pas pu être téléchargées)
            if produits_a_corriger:
                df_erreurs = pd.DataFrame(produits_a_corriger)
                st.success(f"🎯 Analyse terminée ! Voici les anomalies qui nécessitent une action manuelle :")
                st.dataframe(df_erreurs) 
                
                csv = df_erreurs.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Télécharger la liste de travail (CSV)", data=csv, file_name="produits_a_remplacer.csv", mime="text/csv")
            else:
                st.balloons()
                st.success("🎉 Félicitations ! Toutes les images manquantes ont été téléchargées ou vos fichiers locaux sont déjà parfaits.")
