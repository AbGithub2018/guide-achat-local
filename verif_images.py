import os
import requests
import pandas as pd
import streamlit as st

def verifier_base_images():
    print("🚀 Connexion à votre Google Sheet et démarrage de l'analyse...")
    
    # 1. Connexion à votre Google Sheet (onglet 'Sheets')
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_produits = conn.read(worksheet="Sheets") 
    
    # Ajustement du nom exact de votre colonne de codes-barres
    colonne_code = 'code_upc' 
    
    if colonne_code not in df_produits.columns:
        print(f"❌ Erreur : La colonne '{colonne_code}' n'existe pas dans votre onglet Sheets.")
        print(f"Colonnes disponibles : {list(df_produits.columns)}")
        return

    produits_a_corriger = []
    total_produits = len(df_produits)
    
    print(f"📋 {total_produits} produits trouvés. Analyse en cours...")

    for index, row in df_produits.iterrows():
        valeur_cellule = row[colonne_code]
        
        # Nettoyage de la valeur (enlève les espaces et les éventuels '.0' des formats nombres)
        if pd.isna(valeur_cellule):
            continue
            
        cup_actuel = str(valeur_cellule).strip()
        if cup_actuel.endswith('.0'):
            cup_actuel = cup_actuel[:-2]
            
        if not cup_actuel or cup_actuel == "nan" or cup_actuel == "":
            continue

        # Vérification 1 : Est-ce que l'image existe déjà dans votre dossier local ?
        image_locale_existe = False
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            if os.path.exists(os.path.join("images", f"{cup_actuel}{ext}")):
                image_locale_existe = True
                break
                
        if image_locale_existe:
            continue # Déjà corrigé localement, on passe au suivant

        # Vérification 2 : Analyser l'image sur Open Food Facts
        url_api = f"https://openfoodfacts.org/api/v0/product/{cup_actuel}.json"
        headers = {"User-Agent": "AchatQuebecMaintenance - robert.st.jules@gmail.com"}
        
        try:
            res = requests.get(url_api, headers=headers, timeout=2).json()
            if res.get("status") == 1 and "product" in res:
                img_url = res["product"].get("image_url")
                
                if not img_url:
                    # Cas A : Aucune image disponible sur OFF
                    produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Image manquante sur OFF"})
                else:
                    # Cas B : Image existante mais de mauvaise qualité (trop légère)
                    meta = requests.head(img_url, timeout=2)
                    poids = int(meta.headers.get("Content-Length", 0))
                    
                    if poids < 15000: # Moins de 15 Ko = qualité médiocre
                        produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": f"Qualité médiocre ({round(poids/1024, 1)} Ko)"})
            else:
                # Cas C : Produit introuvable sur OFF
                produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Produit inconnu sur OFF"})
                
        except Exception:
            pass

    # 3. Création du fichier de rapport sur votre ordinateur
    if produits_a_corriger:
        df_erreurs = pd.DataFrame(produits_a_corriger)
        df_erreurs.to_csv("produits_a_remplacer.csv", index=False, encoding="utf-8-sig")
        print(f"\n🎯 Terminé ! Le fichier 'produits_a_remplacer.csv' a été créé sur votre ordinateur.")
        print(f"Il contient les {len(df_erreurs)} produits prioritaires à corriger.")
    else:
        print("\n🎉 Félicitations ! Toutes les images analysées sont de bonne qualité.")

if __name__ == "__main__":
    verifier_base_images()
