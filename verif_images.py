import os
import requests
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Configuration de la page du site de maintenance
st.set_page_config(page_title="Maintenance - Achat Québec", page_icon="🛠️")
st.title("🛠️ Outil de Contrôle et Correction des Images")
st.write("Ce site analyse vos produits, télécharge les photos manquantes et remplace celles de mauvaise qualité.")

# Bouton pour lancer l'action
if st.button("🚀 Démarrer l'analyse et la mise à jour des 200 produits suivants", type="primary"):
    with st.spinner("Connexion à votre Google Sheet et traitement des images en cours..."):
        
        # CHEMIN RELATIF AUTOMATIQUE : 
        # dossier_actuel cible dynamiquement le dossier "PROJET_UPC" où se trouve ce script
        dossier_actuel = os.path.dirname(os.path.abspath(__file__))
        # dossier_photos cible le dossier "images" situé juste à côté du script
        dossier_photos = os.path.join(dossier_actuel, "images")
        
        if not os.path.exists(dossier_photos):
            os.makedirs(dossier_photos)

        # 1. Connexion à Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_produits = conn.read(worksheet="Sheet1")
        colonne_code = 'code_upc'
        
        if colonne_code not in df_produits.columns:
            st.error(f"❌ La colonne '{colonne_code}' n'existe pas dans votre onglet Sheets.")
        else:
            produits_corriges_ou_presents = []
            produits_en_erreur = []

            # Analyse de la plage 1000 à 1200 (200 produits)
            for index, row in df_produits.iloc[1000:1200].iterrows():
                valeur_cellule = row[colonne_code]
                if pd.isna(valeur_cellule):
                    continue
                
                # Nettoyage du code-barres
                cup_actuel = str(valeur_cellule).strip()
                if cup_actuel.endswith('.0'):
                    cup_actuel = cup_actuel[:-2]
                if not cup_actuel or cup_actuel in ["nan", ""]:
                    continue

                # Détection de l'existence d'une image locale
                image_locale_existe = False
                extension_locale = ".jpg"
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    if os.path.exists(os.path.join(dossier_photos, f"{cup_actuel}{ext}")):
                        image_locale_existe = True
                        extension_locale = ext
                        break

                # URL de l'API v3 ciblée spécifiquement sur le Canada
                url_api = f"https://ca.openfoodfacts.org/api/v3/product/{cup_actuel}.json"
                headers = {"User-Agent": "AchatQuebecMaintenance - robert.st.jules@gmail.com"}
                
                try:
                    reponse_api = requests.get(url_api, headers=headers, timeout=3)
                    
                    if reponse_api.status_code != 200 or "application/json" not in reponse_api.headers.get("Content-Type", ""):
                        produits_en_erreur.append({
                            "code_upc": cup_actuel, 
                            "Nom": row.get("Nom_Produit", ""), 
                            "Statut": f"Erreur de connexion API ({reponse_api.status_code})"
                        })
                        continue

                    res = reponse_api.json()
                    
                    # Vérification du statut de la réponse API v3
                    if res.get("status") == "failure" or "product" not in res:
                        produits_en_erreur.append({
                            "code_upc": cup_actuel, 
                            "Nom": row.get("Nom_Produit", ""), 
                            "Statut": "Produit inconnu sur Open Food Facts"
                        })
                        continue

                    # Récupération de l'URL de l'image principale
                    img_url = res["product"].get("image_url")
                    if not img_url:
                        produits_en_erreur.append({
                            "code_upc": cup_actuel, 
                            "Nom": row.get("Nom_Produit", ""), 
                            "Statut": "Aucune image disponible sur Open Food Facts"
                        })
                        continue

                    # Vérification du poids de l'image distante via une requête HEAD (ultra rapide)
                    meta = requests.head(img_url, timeout=3)
                    poids_distant = int(meta.headers.get("Content-Length", 0))

                    # Logique de décision pour exécuter le téléchargement
                    a_telecharger = False
                    raison = ""
                    
                    if not image_locale_existe:
                        a_telecharger = True
                        raison = "Image manquante localement (Téléchargée)"
                    elif poids_distant >= 15000:
                        a_telecharger = True
                        raison = "Image locale existante remplacée par version HD"
                    else:
                        produits_en_erreur.append({
                            "code_upc": cup_actuel, 
                            "Nom": row.get("Nom_Produit", ""), 
                            "Statut": "Image OFF également de mauvaise qualité (< 15 Ko)"
                        })
                        continue

                    # Processus de téléchargement
                    if a_telecharger:
                        # Extraction propre et sécurisée de l'extension
                        nom_fich, ext_brute = os.path.splitext(img_url)
                        ext_distante = ext_brute.split('?')[0].lower()
                        
                        if ext_distante not in [".jpg", ".jpeg", ".png", ".webp"]:
                            ext_distante = ".jpg"

                        # Nettoyage de l'ancienne extension si elle a changé
                        if image_locale_existe and extension_locale != ext_distante:
                            try:
                                os.remove(os.path.join(dossier_photos, f"{cup_actuel}{extension_locale}"))
                            except Exception:
                                pass

                        # Téléchargement et écriture finale sur le disque
                        img_data = requests.get(img_url, timeout=5).content
                        chemin_sauvegarde = os.path.join(dossier_photos, f"{cup_actuel}{ext_distante}")
                        with open(chemin_sauvegarde, "wb") as handler:
                            handler.write(img_data)

                        # Succès : Le produit est classé dans la bonne liste
                        produits_corriges_ou_presents.append({
                            "code_upc": cup_actuel, 
                            "Nom": row.get("Nom_Produit", ""), 
                            "Action": raison, 
                            "Poids (octets)": poids_distant
                        })

                except Exception as e:
                    produits_en_erreur.append({
                        "code_upc": cup_actuel, 
                        "Nom": row.get("Nom_Produit", ""), 
                        "Statut": f"Erreur lors du traitement : {str(e)}"
                    })

            # 2. Affichage des blocs de résultats à l'écran
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
                st.download_button(
                    "📥 Télécharger la liste des anomalies restantes (CSV)", 
                    data=csv, 
                    file_name="anomalies_images_restantes.csv", 
                    mime="text/csv"
                )

            if not produits_corriges_ou_presents and not produits_en_erreur:
                st.balloons()
                st.success("🎉 Félicitations ! Aucun produit n'a nécessité de modification dans cette plage.")
