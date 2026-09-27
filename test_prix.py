import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="🤖 Auto-Priorité", layout="centered")
st.title("🤖 Automatisation de vos produits indispensables")
st.write("Ce script marque d'un 'Oui' automatique les articles de votre liste personnalisée.")

# 1. Connexion au Google Sheet
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1")
    df.columns = [c.strip().lower() for c in df.columns]
    st.success("✅ Connexion à la base de données réussie.")
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# 2. Vérification de la colonne
if 'priorite' not in df.columns:
    st.error("❌ Veuillez d'abord renommer la colonne 'prix_produit' par 'priorite' dans votre Google Sheets.")
    st.stop()

# 3. Mots-clés basés exactement sur vos exemples québécois
st.markdown("### 📋 Liste de vos produits ciblés :")
mots_cles = [
    "papier toilette", "papier de toilette", "lait", "pain", "oeuf", "beurre", 
    "riz", "kleenex", "mouchoir", "essuie-tout", "essuietout", "eau", "savon", 
    "patate", "pomme de terre", "carotte", "beurre de peanut", "beurre d'arachide", 
    "poisson", "saumon", "truite", "salade", "laitue"
]
st.write(", ".join(mots_cles))

# 4. Bouton pour lancer le marquage automatique
if st.button("🚀 Lancer le marquage automatique dans le Nuage", type="primary"):
    with st.spinner("Analyse de vos 10 445 produits..."):
        
        # On remet à zéro pour ne garder que votre sélection propre
        df['priorite'] = ""
        
        # Le robot cherche si le nom du produit contient l'un de vos mots-clés
        masque_essentiel = df['nom'].astype(str).str.lower().str.contains("|".join(mots_cles), na=False)
        
        # On inscrit "Oui" sur les lignes trouvées
        df.loc[masque_essentiel, 'priorite'] = "Oui"
        total_marques = len(df[df['priorite'] == "Oui"])
        
        try:
            # Envoi vers Google Sheets
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.balloons()
            st.success(f"🎉 Succès ! {total_marques} produits correspondants ont été marqués 'Oui' dans votre Google Sheet.")
            
            # Aperçu des premiers résultats
            st.markdown("### 🔍 Aperçu des fiches configurées :")
            st.dataframe(df[df['priorite'] == "Oui"][['code_upc', 'nom', 'priorite']].head(30), use_container_width=True)
            
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")
