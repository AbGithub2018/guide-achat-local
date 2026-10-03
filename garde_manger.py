import streamlit as st
import pandas as pd
import requests
import time
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Test Tri UPC Garde-Manger", layout="wide")
st.title("🧪 Phase 1 : Test de catégorisation par code UPC")

def interroger_openfoodfacts(upc):
    """Interroge Open Food Facts pour obtenir le groupe de produits standardisé."""
    if not upc or str(upc).strip() in ["", "nan", "0"]:
        return "🥫 À classer"
    
    # CORRECTIF LIGNE 16 : Extraction propre du code sans la décimale .0
    upc_propre = str(upc).split('.')[0].strip()
    
    try:
        url = f"https://openfoodfacts.org{upc_propre}.json"
        headers = {"User-Agent": "AchatQuebecTest - Web - Version1.0 - robert.st.jules@gmail.com"}
        reponse = requests.get(url, headers=headers, timeout=2.0)
        
        if reponse.status_code == 200:
            donnees = reponse.json()
            if donnees.get("status") == 1 and "product" in donnees:
                produit = donnees["product"]
                pnns = produit.get("pnns_groups_1", "").lower()
                
                if "cereals" in pnns or "potatoes" in pnns:
                    return "Garde-manger (Féculents & Grains)"
                elif "beverages" in pnns:
                    return "Boissons"
                elif "fish" in pnns or "meat" in pnns:
                    return "Viandes et poissons"
                elif "milk" in pnns or "dairy" in pnns or "cheese" in pnns:
                    return "Produits laitiers et œufs"
                elif "sugary-snacks" in pnns or "fruits" in pnns:
                    if "juice" in produit.get("product_name", "").lower():
                        return "Boissons"
                    return "Garde-manger (Sucres & Déjeuners / Conserves)"
                    
                categories_tags = [c.lower() for c in produit.get("categories_tags", [])]
                if any("conserve" in c or "appertis" in c for c in categories_tags):
                    return "Garde-manger (Les Conserves)"
                if any("sauce" in c or "condiment" in c or "epice" in c for c in categories_tags):
                    return "Garde-manger (Matières grasses & Condiments)"
                    
    except Exception:
        pass
    
    return "Garde-manger (À valider en Phase 2)"

# 1. Connexion et lecture du fichier réel
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1")
    df.columns = [c.strip().lower() for c in df.columns]
    st.success(f" Connexion réussie ! {len(df)} produits trouvés dans le Google Sheet.")
except Exception as e:
    st.error(f" Erreur de connexion : {e}")
    st.stop()

# 2. Configuration du test
st.subheader(" Paramètres du test")

# CORRECTIF LIGNE 71 : Utilisation de min_value à la place de min_input
taille_echantillon = st.number_input("Nombre de produits à tester pour cet essai :", min_value=1, max_value=100, value=20)

if st.button(" Lancer le test par UPC"):
    df_test = df.sample(n=int(taille_echantillon), random_state=42).copy()
    
    barre_progression = st.progress(0)
    statut_texte = st.empty()
    
    categories_calculees = []
    
    for i, row in enumerate(df_test.iterrows()):
        idx, data = row
        nom_produit = data.get('nom', 'Nom inconnu')
        upc_produit = data.get('code_upc', '')
        
        statut_texte.text(f"Analyse {i+1}/{taille_echantillon} : {nom_produit} (UPC: {upc_produit})")
        
        cat = interroger_openfoodfacts(upc_produit)
        categories_calculees.append(cat)
        
        time.sleep(0.5)
        barre_progression.progress((i + 1) / taille_echantillon)
        
    df_test['categorie_upc_test'] = categories_calculees
    statut_texte.text(" Test terminé avec succès !")
    
    st.subheader(" Résultats comparatifs")
    st.write("Voici comment l'I.A. Open Food Facts a classé vos produits à partir de leur code UPC :")
    
    colonnes_visibles = [c for c in ['code_upc', 'nom', 'entreprise_proprietaire', 'categorie_upc_test'] if c in df_test.columns]
    st.dataframe(df_test[colonnes_visibles], use_container_width=True)
    
    st.info(" Si ces résultats par UPC vous conviennent, nous pourrons passer à la Phase 2 : appliquer cette logique sur l'ensemble des 10 600 lignes et enregistrer les catégories de façon définitive dans votre Google Sheet.")
