import streamlit as st

st.title("Test d'ouverture d'onglet unique")
st.write("Ce bouton va ouvrir Super C. Si vous revenez ici et cliquez à nouveau, il réutilisera le même onglet au lieu d'en ouvrir un deuxième.")

# URL de test (Super C)
url_super_c = "https://superc.ca"

# Bouton HTML stylisé imitant votre bouton rouge original
# L'astuce réside dans target="fenetre_circulaire_unique"
bouton_html = f"""
<div style="display: flex; justify-content: center; margin-top: 20px;">
    <a href="{url_super_c}" target="fenetre_circulaire_unique" style="
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
        📍 Voir ma succursale (Test Onglet Unique)
    </a>
</div>
"""

# Injection du HTML dans l'application Streamlit
st.markdown(bouton_html, unsafe_allow_html=True)
