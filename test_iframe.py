import streamlit as st

st.title("Test final d'onglet unique")
st.write("Cette méthode utilise du HTML standard épuré pour contourner les blocages de scripts.")

# URL de test
url_super_c = "https://superc.ca"

# Utilisation d'un lien hypertexte pur stylisé avec rel="opener"
bouton_final_html = f"""
<div style="display: flex; justify-content: center; margin-top: 20px;">
    <a href="{url_super_c}" target="panier_epicerie_unique" rel="opener" style="
        text-decoration: none; 
        padding: 12px 24px; 
        background-color: #ff4b4b; 
        color: white; 
        border-radius: 8px; 
        font-weight: 500; 
        font-family: sans-serif;
        display: inline-block;
        text-align: center;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
        width: 80%;
        max-width: 400px;">
        📍 Voir ma succursale (Test Final)
    </a>
</div>
"""

st.markdown(bouton_final_html, unsafe_allow_html=True)
