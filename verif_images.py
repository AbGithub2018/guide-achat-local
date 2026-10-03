import os
import requests
import pandas as pd
import streamlit as st

def lancer_analyse():
    st.write("🚀 Connexion à votre Google Sheet et démarrage de l'analyse...")
    
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_produits = conn.read(worksheet="Sheets") 
    
    colonne_code = 'code_upc' 
    
    if colonne_code not in df_produits.columns:
        st.error(f"❌ La colonne '{colonne_code}' n'existe pas dans votre onglet Sheets.")
        return

    produits_a_corriger = []
    
    # Mode TEST : on analyse seulement les 20 premiers produits
    for index, row in df_produits.head(20).iterrows():
        valeur_cellule = row[colonne_code]
        if pd.isna(valeur_cellule):
            continue
            
        cup_actuel = str(valeur_cellule).strip()
        if cup_actuel.endswith('.0'):
            cup_actuel = cup_actuel[:-2]
            
        if not cup_actuel or cup_actuel == "nan" or cup_actuel == "":
            continue

        # Vérification 1 : Dossier local
        image_locale_existe = False
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            if os.path.exists(os.path.join("images", f"{cup_actuel}{ext}")):
                image_locale_existe = True
                break
                
        if image_locale_existe:
            continue

        # Vérification 2 : Open Food Facts
        url_api = f"https://openfoodfacts.org{cup_actuel}.json"
        headers = {"User-Agent": "AchatQuebecMaintenance - robert.st.jules@gmail.com"}
        
        try:
            res = requests.get(url_api, headers=headers, timeout=2).json()
            if res.get("status") == 1 and "product" in res:
                img_url = res["product"].get("image_url")
                if not img_url:
                    produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Image manquante"})
                else:
                    meta = requests.head(img_url, timeout=2)
                    poids = int(meta.headers.get("Content-Length", 0))
                    if poids < 15000:
                        produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Qualité médiocre"})
            else:
                produits_a_corriger.append({"code_upc": cup_actuel, "Nom": row.get("Nom_Produit", ""), "Raison": "Inconnu sur OFF"})
        except Exception:
            pass

    # Affichage du résultat directement sur votre écran web !
    if produits_a_corriger:
        df_erreurs = pd.DataFrame(produits_a_corriger)
        st.success(f"🎯 Analyse terminée ! Voici les produits à corriger parmi les 20 premiers :")
        st.dataframe(df_erreurs) # Affiche le tableau d'erreurs sur votre écran
        
        # Permet de télécharger le fichier Excel/CSV en un clic !
        csv = df_erreurs.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger la liste de travail (CSV)", data=csv, file_name="produits_a_remplacer.csv", mime="text/csv")
    else:
        st.balloons()
        st.success("🎉 Toutes les images analysées sont parfaites !")
