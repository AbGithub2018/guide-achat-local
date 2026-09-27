import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="🤖 Auto-Priorité Restreint", layout="centered")
st.title("🎯 Ciblage Ultra-Sélectif des Essentiels")
st.write("Ce script affine la sélection pour ne garder que les produits les plus importants.")

# 1. Connexion en direct sans cache
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    df.columns = [c.strip().lower() for c in df.columns]
    st.success("✅ Connexion à la base de données réussie.")
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# 2. Mots-clés très précis pour réduire le volume
st.markdown("### 📋 Liste restreinte des essentiels :")
mots_cles_strictes = [
    "lait 2%", "lait 1%", "lait ecresme", "lait de vache",
    "pain blanc", "pain tranche", "pain de menage",
    "oeufs gros", "oeuf gros",
    "beurre sal", "beurre non sal",
    "riz blanc", "riz long", "riz jasmin",
    "papier hygi", "papier de toilette",
    "mouchoirs en boite", "kleenex boite",
    "essuie-tout", "essuietout",
    "beurre d'arachide", "beurre de peanut",
    "saumon frais", "filet de saumon",
    "laitue romaine", "salade frisee",
    "sac de patates", "pommes de terre", "sac de carottes"
]
st.write(", ".join(mots_cles_strictes))

# 3. Bouton d'action
if st.button("🚀 Réduire et mettre à jour la sélection dans le Nuage", type="primary"):
    with st.spinner("Filtrage chirurgical de vos 10 445 produits..."):
        
        # On nettoie d'abord l'ancienne sélection de 1000 produits
        df['priorite'] = ""
        
        # Application du nouveau filtre strict
        masque_strict = df['nom'].astype(str).str.lower().str.contains("|".join(mots_cles_strictes), na=False)
        
        # On marque d'un "Oui"
        df.loc[masque_strict, 'priorite'] = "Oui"
        total_restreint = len(df[df['priorite'] == "Oui"])
        
        try:
            # Envoi vers Google Sheets
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.balloons()
            st.success(f"🎉 Parfait ! Nous sommes passés de 1000 à {total_restreint} produits essentiels dans votre Google Sheet.")
            
            # Aperçu des lignes sélectionnées
            st.markdown("### 🔍 Aperçu de la nouvelle liste de course du robot :")
            st.dataframe(df[df['priorite'] == "Oui"][['code_upc', 'nom', 'priorite']], use_container_width=True)
            
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")
