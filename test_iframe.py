import streamlit as st

st.title("Test d'intégration de Circulaire")

# Testez avec l'URL de votre choix
url_test = "https://superc.ca" 

st.components.v1.html(
    f'<iframe src="{url_test}" width="100%" height="600" style="border:none;"></iframe>',
    height=600
)
