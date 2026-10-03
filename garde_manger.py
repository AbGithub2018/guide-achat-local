import streamlit as st
import pandas as pd
import requests
import time
import re
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Test Tri UPC Garde-Manger", layout="wide")
st.title("🧪 Phase 1 : Test de catégorisation par code UPC")

def verifier_par_texte_secours(nom):
    """Système de secours I.A. textuelle (Validé ensemble) si l'UPC est inconnu en ligne."""
    nom_minuscule = str(nom).lower()
    
    if any(m in nom_minuscule for m in ["jus", "boisson", "soda", "eau", "thé", "the", "pepsi", "7up", "soda", "coffee", "café", "cafe"]):
        return "☕ Boissons"
    if any(m in nom_minuscule for m in ["poulet", "bœuf", "boeuf", "beef", "porc", "bacon", "jambon", "thon", "saumon", "saucisse", "crevette", "viande"]):
        return "🥩 Viandes et poissons"
    if any(m in nom_minuscule for m in ["lait", "yogourt", "yaourt", "yogurt", "skyr", "fromage", "cheese", "beurre", "œuf", "oeuf"]):
        return "🥛 Produits laitiers et œufs"
    if any(m in nom_minuscule for m in ["pain", "muffin", "brioche", "bagel", "céréale", "gruau", "tarte", "croissant", "biscuit", "biscuits"]):
        return "🍞 Boulangerie et pâtisserie"
    if any(m in nom_minuscule for m in ["pizza", "frite", "frites", "surgelé", "surgeles"]):
        return "❄️ Surgelés"
    if any(m in nom_minuscule for m in ["ail", "carotte", "carottes", "oignon", "oignons", "patate", "patates", "tomate", "tomates", "salade"]):
        return "🥦 Fruits et légumes"
        
    return "Garde-manger"

def interroger_openfoodfacts(upc, nom_produit):
    """Interroge Open Food Facts par UPC. Si inconnu, bascule sur le secours textuel."""
    if not upc or str(upc).strip() in ["", "nan", "0", "0.0"]:
        return verifier_par_texte_secours(nom_produit)
    
    # Nettoyage et padding strict du code-barres
    upc_brut = str(upc).split('.')[0].strip()
    if upc_brut.isdigit() and len(upc_brut) > 0:
        upc_propre = upc_brut.zfill(12) if len(upc_brut) <= 12 else upc_brut.zfill(13)
    else:
        return verifier_par_texte_secours(nom_produit)
    
    try:
        url = f"https://openfoodfacts.org{upc_propre}.json"
        headers = {"User-Agent": "AchatQuebecTest - Web - Version1.1 - robert.st.jules@gmail.com"}
        reponse = requests.get(url, headers=headers, timeout=2.0)
        
        if reponse.status_code == 200:
            donnees = reponse.json()
            # CORRECTION DU STATUT : Accepte les chiffres (1), textes ("1") ou ("success" / "found")
            statut = donnees.get("status")
            if statut in [1, "1", "success", "found"] and "product" in donnees:
                produit = donnees["product"]
                pnns = produit.get("pnns_groups_1", "").lower()
                
                if "cereals" in pnns or "potatoes" in pnns:
                    return "Garde-manger (Féculents & Grains)"
                elif "beverages" in pnns:
                    return "☕ Boissons"
                elif "fish" in pnns or "meat" in pnns:
                    return "🥩 Viandes et poissons"
                elif "milk" in pnns or "dairy" in pnns or "cheese" in pnns:
                    return "🥛 Produits laitiers et œufs"
                elif "sugary-snacks" in pnns or "fruits" in pnns:
                    if "juice" in produit.get("product_name", "").lower() or "jus" in produit.get("product_name", "").lower():
                        return "☕ Boissons"
                    return "Garde-manger (Sucres, Déjeuners & Conserves)"
                    
                categories_tags = [c.lower() for c in produit.get("categories_tags", [])]
                if any("conserve" in c or "appertis" in c for c in categories_tags):
                    return "Garde-manger (Les Conserves)"
                if any("sauce" in c or "condiment" in c or "epice" in c for c in categories_tags):
                    return "Garde-manger (Matières grasses & Condiments)"
                    
    except Exception:
        pass
    
    # Si l'UPC n'a rien renvoyé ou a planté, le filet de sécurité textuel prend le relais
    return verifier_par_texte_secours(nom_produit)

# 1. Connexion et lecture du fichier réel
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1")
    df.columns = [c.strip().lower() for c in df.columns]
    st.success(f"✅ Connexion réussie ! {len(df)} produits trouvés dans le Google Sheet.")
except Exception as e:
    st.error(f"❌ Erreur de connexion : {e}")
    st.stop()

# 2. Configuration du test
st.subheader("⚙️ Paramètres du test")
taille_echantillon = st.number_input("Nombre de produits à tester pour cet essai :", min_value=1, max_value=100, value=20)

if st.button("🚀 Lancer le test par UPC & Secours"):
    df_test = df.sample(n=int(taille_echantillon), random_state=42).copy()
    
    barre_progression = st.progress(0)
    statut_texte = st.empty()
    
    categories_calculees = []
    
    for i, row in enumerate(df_test.iterrows()):
        idx, data = row
        nom_produit = data.get('nom', 'Nom inconnu')
        upc_produit = data.get('code_upc', '')
        
        statut_texte.text(f"Analyse {i+1}/{taille_echantillon} : {nom_produit} (UPC: {upc_produit})")
        
        cat = interroger_openfoodfacts(upc_produit, nom_produit)
        categories_calculees.append(cat)
        
        time.sleep(0.5)
        barre_progression.progress((i + 1) / taille_echantillon)
        
    df_test['categorie_upc_test'] = categories_calculees
    statut_texte.text("🎉 Test terminé avec succès !")
    
    st.subheader("📊 Résultats comparatifs")
    st.write("Voici la classification obtenue (via Code-barres mondial ou Secours textuel) :")
    
    colonnes_visibles = [c for c in ['code_upc', 'nom', 'entreprise_proprietaire', 'categorie_upc_test'] if c in df_test.columns]
    st.dataframe(df_test[colonnes_visibles], use_container_width=True)
