import os
import requests
import pandas as pd
import streamlit as st

# Configuration de la page du site de maintenance
st.set_page_config(page_title="Maintenance - Achat Québec", page_icon="🛠️")
st.title("🛠️ Outil de Contrôle et Correction des Images")
st.write("Ce site analyse vos produits, télécharge les photos manquantes et remplace celles de mauvaise qualité.")

# Bouton pour lancer l'action
if st.button("🚀 Démarrer l'analyse et la mise à jour des 200 produits suivants", type="primary"):
    
    with st.spinner("Connexion à votre Google Sheet et traitement des images en cours..."):
        
       # FORCE le téléchargement exact dans votre dossier physique sur le bureau
        dossier_photos = "C:\\Users\\Robert\\Desktop\\TRUMP\\acheter canadien ou québécois\\application à créer\\DESCRIPTION DES PRODUITS\\PROJET_UPC\\images"

        
        # Créer le dossier s'il n'existe pas encore
        if not os.path.exists(dossier_photos):
            os.makedirs(dossier_photos)
            
        # 1. Connexion à votre Google Sheet (onglet 'Sheets')
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_produits = conn.read(worksheet="Sheet1") 
        
        colonne_code = 'code_upc' 
        
        if colonne_code not in df_produits.columns:
            st.error(f"❌ La colonne '{colonne_code}' n'existe pas dans votre onglet Sheets.")
        else:
            produits_corriges_ou_presents = []
            produits_en_erreur = []
            
            # Correction de la syntaxe .iloc[800:1000] pour analyser 200 produits
            for index, row in df_produits.iloc[800:1000].iterrows():
                valeur_cellule = row[colonne_code]
                if pd.isna(valeur_cellule):
                    continue
                    
                cup_actuel = str(valeur_cellule).strip()
                if cup_actuel.endswith('.0'):
                    cup_actuel = cup_actuel[:-2]
                    
                if not cup_actuel or cup_actuel == "nan" or cup_actuel == "":
                    continue

                # Détecter si une image locale existe déjà et trouver son extension
                image_locale_existe = False
                extension_locale = ".jpg"
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    if os.path.exists(os.path.join(dossier_photos, f"{cup_actuel}{ext}")):
                        image_locale_existe = True
                        extension_locale = ext
                        break

                # URL de l'API v0
                url_api = f"https://openfoodfacts.org/api/v0/product/{cup_actuel}.json"
                headers = {"User-Agent": "AchatQuebecMaintenance - robert.st.jules@gmail.com"}
                
                try:
                    reponse_api = requests.get(url_api, headers=headers, timeout=2)
                    
                    # CORRECTIF : On s'assure de recevoir du JSON valide pour éviter le crash 'Expecting value'
                    if reponse_api.status_code == 200 and "application/json" in reponse_api.headers.get("Content-Type", ""):
                        res = reponse_api.json()
                    else:
                        produits_en_erreur.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Statut": "Produit introuvable ou erreur de format sur OFF"})
                        continue
                    
                    if res.get("status") == 1 and "product" in res:
                        img_url = res["product"].get("image_url")
                        
                        if not img_url:
                            produits_en_erreur.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Statut": "Aucune image disponible sur Open Food Facts"})
                            continue
                        
                        # Vérifier les métadonnées de l'image distante (poids)
                        meta = requests.head(img_url, timeout=2)
                        poids_distant = int(meta.headers.get("Content-Length", 0))
                        
                        # Déterminer si le téléchargement est nécessaire
                        a_telecharger = False
                        raison = ""
                        
                        if not image_locale_existe:
                            a_telecharger = True
                            raison = "Image manquante localement (Téléchargée)"
                        elif poids_distant >= 15000:
                            a_telecharger = True
                            raison = "Image locale existante remplacée par version HD"
                        else:
                            produits_en_erreur.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Statut": "Image OFF également de mauvaise qualité (< 15 Ko)"})
                            continue

                        if a_telecharger:
                            ext_distante = os.path.splitext(img_url)[1].split('?')[0].lower()
                            if ext_distante not in [".jpg", ".jpeg", ".png", ".webp"]:
                                ext_distante = ".jpg"
                            
                            if image_locale_existe and extension_locale != ext_distante:
                                try:
                                    os.remove(os.path.join(dossier_photos, f"{cup_actuel}{extension_locale}"))
                                except Exception:
                                    pass
                            
                            # Téléchargement et enregistrement dans le bon dossier
                            img_data = requests.get(img_url, timeout=5).content
                            chemin_sauvegarde = os.path.join(dossier_photos, f"{cup_actuel}{ext_distante}")
                            with open(chemin_sauvegarde, "wb") as handler:
                                handler.write(img_data)
                                
                            produits_corriges_ou_presents.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Action": raison, "Poids (octets)": poids_distant})
                    else:
                        produits_en_erreur.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Statut": "Produit inconnu sur Open Food Facts"})
                except Exception as e:
                    produits_en_erreur.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Statut": f"Erreur lors du traitement : {str(e)}"})

            # 2. Affichage des résultats à l'écran
            st.success("🎯 Analyse et mise à jour terminées !")
            
            if produits_corriges_ou_presents:
                st.subheader("✅ Images téléchargées ou mises à jour")
                df_succes = pd.DataFrame(produits_corriges_ou_presents)
                st.dataframe(df_succes)
            
            if produits_en_erreur:
                st.subheader("⚠️ Attention : Produits nécessitant une action manuelle")
                df_erreurs = pd.DataFrame(produits_en_erreur)
                st.dataframe(df_erreurs)
                
                csv = df_erreurs.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Télécharger la liste des anomalies restantes (CSV)", data=csv, file_name="anomalies_images_restantes.csv", mime="text/csv")
                
            if not produits_corriges_ou_presents and not produits_en_erreur:
                st.balloons()
                st.success("🎉 Félicitations ! Aucun produit n'a nécessité de modification dans cette plage.")
