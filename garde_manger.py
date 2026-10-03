import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Phase 2 : Traitement de Masse", layout="wide")
st.title("⚡ Phase 2 : Classification et écriture des 10 460 produits")

def classifier_produit_local(nom):
    """Algorithme local ultra-rapide validé en Phase 1 pour le traitement de masse."""
    nom_minuscule = str(nom).lower()
    
    # 1. Boissons
    if any(m in nom_minuscule for m in ["jus", "boisson", "soda", "eau", "thé", "the", "coffee", "café", "cafe", "juice", "drink", "lemonade", "limonade", "punch"]):
        return "☕ Boissons"
        
    # 2. Protection Garde-manger (Conserves, Pâtes, condiments)
    if any(m in nom_minuscule for m in ["pâte de tomate", "pate de tomate", "sauce", "coulis", "conserve", "mix", "trail", "mélange", "melange", "pasta", "fettuccine", "fettuccina", "spaghetti", "macaroni", "milanaise", "butter"]):
        return "Garde-manger"
        
    # 3. Viandes et poissons
    if any(m in nom_minuscule for m in ["poulet", "bœuf", "boeuf", "beef", "porc", "bacon", "jambon", "thon", "saumon", "saucisse", "crevette", "viande", "jerky", "meat", "foie", "génisse", "genisse"]):
        return "🥩 Viandes et poissons"
        
    # 4. Produits laitiers, Fromages et Oeufs
    if any(m in nom_minuscule for m in ["lait", "yogourt", "yaourt", "yogurt", "skyr", "fromage", "cheese", "beurre", "œuf", "oeuf", "eggs", "cream", "crème", "creme", "margarine"]):
        return "🥛 Produits laitiers et œufs"
        
    # 5. Boulangerie et pâtisserie
    if any(m in nom_minuscule for m in ["pain", "muffin", "brioche", "bagel", "céréale", "gruau", "tarte", "croissant", "biscuit", "biscuits", "loaf", "bread"]):
        return "🍞 Boulangerie et pâtisserie"
        
    # 6. Surgelés
    if any(m in nom_minuscule for m in ["pizza", "frite", "frites", "surgelé", "surgeles", "congelé", "congelés"]):
        return "❄️ Surgelés"
        
    # 7. Fruits et légumes maraîchers bruts
    if any(m in nom_minuscule for m in ["ail", "carotte", "carottes", "oignon", "oignons", "patate", "patates", "tomate", "tomates", "salade", "radis", "concombre", "pomme", "pommes", "banane", "bananes", "citron", "citrons", "fraise", "fraises", "orange", "oranges"]):
        return "🥦 Fruits et légumes"
        
    return "Garde-manger"

# Lecture du Google Sheet d'origine
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1")
    df.columns = [c.strip().lower() for c in df.columns]
    st.success(f"📦 Connexion réussie ! Fichier de {len(df)} produits prêt à être traité.")
except Exception as e:
    st.error(f"❌ Erreur de lecture : {e}")
    st.stop()

st.warning("⚠️ Attention : En cliquant sur le bouton ci-dessous, le script va calculer la catégorie adéquate pour vos 10 460 produits et mettre à jour votre colonne 'categorie' directement dans votre Google Sheet.")

if st.button("💾 Lancer la classification de masse et Enregistrer dans Google Sheet"):
    with st.spinner("Analyse et écriture en cours... Ne fermez pas la page."):
        
        # 1. Calcul instantané de la catégorie pour TOUTES les lignes locales
        df['categorie'] = df['nom'].apply(classifier_produit_local)
        
        # 2. Sauvegarde et mise à jour réelle dans le Google Sheet
        try:
            conn.update(worksheet="Sheet1", data=df)
            st.success("🎉 Traitement terminé ! Les 10 460 catégories ont été enregistrées avec succès dans votre Google Sheet.")
            st.info("💡 Vous pouvez maintenant retourner sur votre application principale 'app_web.py', tout votre catalogue est classé de façon adéquate !")
        except Exception as save_error:
            st.error(f"❌ Erreur lors de l'enregistrement dans le Google Sheet : {save_error}")
