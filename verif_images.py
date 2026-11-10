import os
import requests
import pandas as pd
import streamlit as st

# Configuration de la page du site de maintenance
st.set_page_config(page_title="Maintenance - Achat Québec", page_icon="🛠️")
st.title("🛠️ Outil de Contrôle de Qualité des Images")
st.write("Ce site analyse vos produits pour trouver les photos manquantes ou floues.")

# Bouton pour lancer l'action
if st.button("🚀 Démarrer l'analyse des 200 produits suivants", type="primary"):
    
    with st.spinner("Connexion à votre Google Sheet et analyse des images en cours..."):
        
        # 1. Connexion à votre Google Sheet (onglet 'Sheets')
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_produits = conn.read(worksheet="Sheet1") 
        
        colonne_code = 'code_upc' 
        
        if colonne_code not in df_produits.columns:
            st.error(f"❌ La colonne '{colonne_code}' n'existe pas dans votre onglet Sheets.")
        else:
            produits_a_corriger = []
            
            # Définition automatique de l'emplacement du dossier "images" juste à côté du script
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

                # Étape 1 : On vérifie si l'image existe déjà localement sur le PC
                image_locale_existe = False
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    if os.path.exists(os.path.join(dossier_photos, f"{cup_actuel}{ext}")):
                        image_locale_existe = True
                        break
                        
                if image_locale_existe:
                    continue # L'image est déjà sur le PC, on passe au produit suivant !

                # Étape 2 : L'image n'est pas sur le PC, on interroge l'API v0 originale
                url_api = f"https://openfoodfacts.org/api/v0/product/{cup_actuel}.json"
                headers = {"User-Agent": "AchatQuebecMaintenance - robert.st.jules@gmail.com"}
                
                try:
                    res = requests.get(url_api, headers=headers, timeout=3).json()
                    if res.get("status") == 1 and "product" in res:
                        img_url = res["product"].get("image_url")
                        
                        if not img_url:
                            produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Image manquante sur OFF"})
                        else:
                            # TÉLÉCHARGEMENT DIRECT SANS REQUÊTE HEAD
                            reponse_image = requests.get(img_url, timeout=5)
                            img_data = reponse_image.content
                            vrai_poids = len(img_data)
                            
                            if vrai_poids < 15000:
                                produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Qualité médiocre sur OFF (< 15 Ko)"})
                            else:
                                # L'IMAGE EST BONNE : ENREGISTREMENT EN SÉCURITÉ EN .JPG
                                chemin_sauvegarde = os.path.join(dossier_photos, f"{cup_actuel}.jpg")
                                with open(chemin_sauvegarde, "wb") as handler:
                                    handler.write(img_data)
                    else:
                        produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Produit inconnu sur OFF"})
                except Exception as e:
                    produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": f"Erreur technique : {str(e)}"})

            # 3. Affichage des anomalies à l'écran
            if produits_a_corriger:
                df_erreurs = pd.DataFrame(produits_a_corriger)
                st.success(f"🎯 Analyse terminée ! Voici les anomalies détectées :")
                st.dataframe(df_erreurs) 
                
                csv = df_erreurs.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Télécharger la liste de travail (CSV)", data=csv, file_name="produits_a_remplacer.csv", mime="text/csv")
            else:
                st.balloons()
                st.success("🎉 Félicitations ! Toutes les images manquantes de bonne qualité ont été téléchargées.")
