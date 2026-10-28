import os
import urllib.parse
import pandas as pd
import streamlit as st
from PIL import Image

# Importation de vos fonctions géographiques depuis fonctions_geo.py
from fonctions_geo import calculer_distance, charger_donnees

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Planificateur Budget Épicerie",
    page_icon="🍎",
    layout="wide",
)

# --- INITIALISATION SÉCURISÉE DES MÉMOIRES ---
if "panier_achats" not in st.session_state:
    st.session_state["panier_achats"] = []

if "banniere_manuelle" not in st.session_state:
    st.session_state["banniere_manuelle"] = "SUPER C"

DOSSIER_BANNIERES = "bannieres"

# =========================================================================
# 🌐 DICTIONNAIRE DES URLS OFFICIELLES DES SITES DE BANNIÈRES
# =========================================================================
LIENS_OFFICIELS = {
    "SUPER C": "https://superc.ca",
    "MAXI": "https://maxi.ca",
    "IGA": "https://iga.net",
    "PROVIGO": "https://provigo.ca",
    "METRO": "https://metro.ca",
    "MARCHÉ ADONIS": "https://groupeadonis.ca",
    "MARCHÉ AMI": "https://marcheami.ca",
    "MARCHÉ BONICHOIX": "https://bonichoix.com",
    "MARCHÉ RICHELIEU": "https://marcherichelieu.ca",
    "MARCHÉ TRADITION": "https://marchetradition.com",
    "WALMART": "https://walmart.ca",
    "COSTCO": "https://costco.ca",
    "TIGRE GÉANT": "https://gianttiger.com",
    "DOLLARAMA": "https://dollarama.com"
}

# --- CHARGEMENT DES DONNÉES ---
df_coords, df_magasins = charger_donnees()
if df_coords is None or df_magasins is None:
    st.stop()
import os
import urllib.parse
import pandas as pd
import streamlit as st
from PIL import Image

# Importation de vos fonctions géographiques depuis fonctions_geo.py
from fonctions_geo import calculer_distance, charger_donnees

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Planificateur Budget Épicerie",
    page_icon="🍎",
    layout="wide",
)

# --- INITIALISATION SÉCURISÉE DES MÉMOIRES ---
if "panier_achats" not in st.session_state:
    st.session_state["panier_achats"] = []

if "banniere_manuelle" not in st.session_state:
    st.session_state["banniere_manuelle"] = "SUPER C"

DOSSIER_BANNIERES = "bannieres"

# =========================================================================
# 🌐 DICTIONNAIRE DES URLS OFFICIELLES DES SITES DE BANNIÈRES
# =========================================================================
LIENS_OFFICIELS = {
    "SUPER C": "https://superc.ca",
    "MAXI": "https://maxi.ca",
    "IGA": "https://iga.net",
    "PROVIGO": "https://provigo.ca",
    "METRO": "https://metro.ca",
    "MARCHÉ ADONIS": "https://groupeadonis.ca",
    "MARCHÉ AMI": "https://marcheami.ca",
    "MARCHÉ BONICHOIX": "https://bonichoix.com",
    "MARCHÉ RICHELIEU": "https://marcherichelieu.ca",
    "MARCHÉ TRADITION": "https://marchetradition.com",
    "WALMART": "https://walmart.ca",
    "COSTCO": "https://costco.ca",
    "TIGRE GÉANT": "https://gianttiger.com",
    "DOLLARAMA": "https://dollarama.com"
}

# --- CHARGEMENT DES DONNÉES ---
df_coords, df_magasins = charger_donnees()
if df_coords is None or df_magasins is None:
    st.stop()
# =========================================================================
# EN-TÊTE PRINCIPAL LOOK APPLICATION MOBILE BANDEAU BLEU
# =========================================================================
st.markdown(
    """
    <div style="background-color: #1E3A8A; padding: 15px; border-radius: 10px; margin-bottom: 15px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 26px; font-weight: bold;">🍎 Mon Planificateur Anti-Inflation</h1>
        <p style="color: #E0E7FF; margin: 3px 0 0 0; font-size: 13px;">Optimisez votre facture d'épicerie sur le pouce</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- MESSAGE DE GUIDAGE MOBILE BIEN VISIBLE ---
st.markdown(
    f"""
    <div style="background-color: #FFFBEB; border-left: 5px solid #F59E0B; padding: 12px; border-radius: 4px; margin-bottom: 15px;">
        <p style="margin: 0; color: #B45309; font-size: 14px; font-weight: bold;">
            📱 Mode Cellulaire : Cliquez d'abord sur le menu de gauche (bouton en haut à gauche) pour entrer votre code postal, ajuster la distance et ouvrir notre Guide d'Achat Local !
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================================
# 📱 RÉORGANISATION EN ONGLETS POUR CELLULAIRE
# =========================================================================
onglet_circulaire, onglet_saisie, onglet_facture = st.tabs([
    f"📸 1. Regarder la Circulaire ({code_recherche})", 
    "✍️ 2. Écrire mes Rabais", 
    "🛍️ 3. Ma Facture"
])

# -------------------------------------------------------------------------
# ONGLET 1 : ACCÈS DIRECT SÉCURISÉ AUX BOUTONS + LISEUSE DE PHOTOS
# -------------------------------------------------------------------------
with onglet_circulaire:
    
    # 1. Résolution dynamique de l'URL par magasin et code postal
    cle_recherche = str(banniere_active).upper().strip()
    url_base_site = LIENS_OFFICIELS.get(cle_recherche, "https://google.com")
    code_postal_url = urllib.parse.quote(code_recherche)
    
    if cle_recherche in ["MARCHÉ AMI", "MARCHÉ BONICHOIX", "MARCHÉ RICHELIEU", "MARCHÉ TRADITION", "COSTCO"]:
        url_final_site = f"https://google.com/maps/search/?api=1&query={urllib.parse.quote(f'{banniere_active} {code_recherche}')}"
    elif "superc" in url_base_site or "metro" in url_base_site:
        url_final_site = f"{url_base_site}?search={code_postal_url}"
    elif "maxi" in url_base_site or "provigo" in url_base_site:
        url_final_site = f"{url_base_site}?searchQuery={code_postal_url}"
    elif "walmart" in url_base_site or "gianttiger" in url_base_site:
        url_final_site = f"{url_base_site}?q={code_postal_url}"
    elif "dollarama" in url_base_site:
        url_final_site = f"{url_base_site}?localisation={code_postal_url}"
    else:
        url_final_site = url_base_site

    # 2. PANNEAU DE LIENS OFFICIELS (Rétabli et sécurisé contre les blocages)
    with st.container(border=True):
        st.markdown(f"<h3 style='font-size: 18px; color: #1E3A8A; font-weight: bold; margin-top: 0px;'>🔗 Circulaire en ligne : {banniere_active}</h3>", unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.link_button("🌐 Ouvrir le site général", url_base_site, use_container_width=True)
        with col_btn2:
            st.link_button(f"📍 Voir ma succursale", url_final_site, type="primary", use_container_width=True)

    st.write("")

    # 3. Affichage de vos photos locales si présentes
    nom_sous_dossier = str(banniere_active).lower().replace(" ", "_").replace("é", "e").replace("è", "e").replace("à", "a")
    chemin_dossier_images = os.path.join(DOSSIER_BANNIERES, nom_sous_dossier)

    if os.path.exists(chemin_dossier_images):
        fichiers_photos = [f for f in os.listdir(chemin_dossier_images) if f.lower().endswith((".png", ".jpg", ".jpeg"))]

        if fichiers_photos:
            st.markdown("<h4 style='font-size: 16px; margin-top: 10px;'>📸 Coupures de circulaires locales :</h4>", unsafe_allow_html=True)
            grille_visuelle = st.columns(2)
            for index, photo in enumerate(fichiers_photos):
                image_aliment = Image.open(os.path.join(chemin_dossier_images, photo))

                with grille_visuelle[index % 2]:
                    st.image(image_aliment, use_container_width=True)

                    if st.button(f"➕ Ajouter", key=f"btn_photo_{index}", use_container_width=True, type="primary"):
                        nom_complet_sans_ext, _ = os.path.splitext(str(photo))
                        
                        if "_" in nom_complet_sans_ext:
                            parties = nom_complet_sans_ext.split("_", 1)
                            premier_morceau = parties[0]
                            reste_du_texte = parties[1]
                            
                            try:
                                prix_automatique = float(premier_morceau)
                                nom_automatique = reste_du_texte.replace("_", " ").capitalize()
                            except ValueError:
                                prix_automatique = 0.00
                                nom_automatique = nom_complet_sans_ext.replace("_", " ").capitalize()
                        else:
                            prix_automatique = 0.00
                            nom_automatique = nom_complet_sans_ext.replace("_", " ").capitalize()

                        st.session_state["panier_achats"].append({
                            "magasin": banniere_active,
                            "catégorie": "🍎 Circulaire Visuelle",
                            "produit": nom_automatique,
                            "prix": prix_automatique,
                        })
                        st.toast(f"✅ {nom_automatique} ajouté !", icon="🛒")
                        st.rerun()
                    st.write("")
        else:
            with st.container(border=True):
                st.info("Aucun feuillet visuel cette semaine. Cliquez sur le bouton rouge du haut pour ouvrir le site de l'épicerie !")
    else:
        with st.container(border=True):
            st.warning(f"Répertoire d'images introuvable : {DOSSIER_BANNIERES}/{nom_sous_dossier}")

# -------------------------------------------------------------------------
# ONGLET 2 : FORMULAIRE DE SAISIE DE RABAIS
# -------------------------------------------------------------------------
with onglet_saisie:
    with st.container(border=True):
        st.markdown("<h3 style='font-size: 20px; color: #1E3A8A; font-weight: 600; margin-top: 0px;'>✍️ Ajouter un article trouvé</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 15px;'>Magasin sélectionné : <strong>{banniere_active}</strong></p>", unsafe_allow_html=True)

        categorie = st.selectbox(
            "Sélectionner le rayon :",
            ["🍎 Fruits et Légumes", "🥩 Viandes et Poissons", "🧀 Produits laitiers", "🍞 Boulangerie", "📦 Épicerie / Boîtes", "🧼 Entretien / Autre"],
            key="mobile_select_cat"
        )

        nom_article = st.text_input("Nom de l'article :", placeholder="Ex: Banane, Beurre...", key="input_nom")
        prix_article = st.number_input("Prix en spécial ($) :", value=0.00, step=0.01, key="input_prix")

        if st.button("✨ Enregistrer l'article", use_container_width=True, key="btn_mobile_save"):
            if nom_article:
                st.session_state["panier_achats"].append({
                    "magasin": banniere_active,
                    "catégorie": categorie,
                    "produit": nom_article,
                    "prix": prix_article,
                })
                st.toast("Article enregistré !", icon="✅")
                st.rerun()
            else:
                st.warning("Veuillez entrer un nom d'article.")

# -------------------------------------------------------------------------
# ONGLET 3 : FACTURE SIMULÉE ET COMPARATEUR DE BANNIÈRES
# -------------------------------------------------------------------------
with onglet_facture:
    with st.container(border=True):
        st.markdown("<h3 style='font-size: 20px; color: #1E3A8A; font-weight: 600; margin-top: 0px;'>🛍️ Ma facture d'épicerie simulée</h3>", unsafe_allow_html=True)
        
        if st.session_state["panier_achats"]:
            df_panier = pd.DataFrame(st.session_state["panier_achats"])
            
            df_affichage = df_panier.rename(columns={"magasin": "Magasin", "catégorie": "Rayon", "produit": "Article", "prix": "Prix"})
            df_affichage["Prix"] = df_affichage["Prix"].map("{:.2f} $".format)
            st.dataframe(df_affichage, use_container_width=True, hide_index=True)
            
            st.markdown("<h4 style='font-size: 15px; color: #4B5563; font-weight: bold; margin-top: 10px;'>📊 Répartition de mes dépenses :</h4>", unsafe_allow_html=True)
            df_comparatif = df_panier.groupby("magasin")["prix"].sum().reset_index()
            
            for _, rangee in df_comparatif.iterrows():
                st.markdown(f"🔹 Total estimé chez **{rangee['magasin']}** : `{rangee['prix']:.2f} $`")
            
            st.markdown(
                f"""
                <div style="background-color: #FEF2F2; border: 2px dashed #EF4444; padding: 12px; border-radius: 8px; text-align: center; margin-top: 15px;">
                    <span style="color: #991B1B; font-size: 14px; font-weight: bold; display: block; text-transform: uppercase;">Estimation totale</span>
                    <span style="color: #DC2626; font-size: 30px; font-weight: 900; font-family: monospace;">{df_panier['prix'].sum():.2f} $</span>
                </div>
                """, 
                unsafe_allow_html=True
            )
            st.write("")
            if st.button("🗑️ Réinitialiser ma liste", use_container_width=True, key="btn_mobile_clear"):
