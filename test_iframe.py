import streamlit as st

st.title("Test d'ouverture d'onglet unique (Version JavaScript)")
st.write("Ce bouton utilise JavaScript pour recycler la même fenêtre.")

# URL de test
url_super_c = "https://superc.ca"

# Bouton avec fonction JavaScript intégrée au clic
bouton_js_html = f"""
<div style="display: flex; justify-content: center; margin-top: 20px;">
    <button onclick="
        if (!window.monOngletCirculaire || window.monOngletCirculaire.closed) {{
            window.monOngletCirculaire = window.open('{url_super_c}', 'circulaire_unique');
        }} else {{
            window.monOngletCirculaire.location.href = '{url_super_c}';
            window.monOngletCirculaire.focus();
        }}
    " style="
        cursor: pointer;
        border: none;
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
        📍 Voir ma succursale (Test JS)
    </button>
</div>
"""

# Injection du code
st.markdown(bouton_js_html, unsafe_allow_html=True)
