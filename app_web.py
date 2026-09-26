import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
from st_gsheets_connection import GSheetsConnection

# Configuration de la page
st.set_page_config(
    page_title="Mon Guide d'Achat Local",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé pour l'interface
st.html("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .stButton>button {
        background-color: #003366;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 10px 24px;
        font-size: 16px;
    }
    .stButton>button:hover { background-color: #002244; color: white; }
    div[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    .stSelectbox label, .stTextInput label, .stRadio label {
        color: #003366 !important;
        font-weight: bold !important;
        font-size: 16px !important;
    }
    div[data-testid="stDataFrame"] { background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""")
# Initialisation de la connexion Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erreur de connexion aux secrets de l'application : {e}")
    st.stop()

# Chargement de la base de données avec cache
@st.cache_data(ttl=600)
def charger_donnees():
    try:
        df = conn.read(worksheet="sheet1")
        df.columns = df.columns.str.strip()
        
        # S'assurer que le code UPC est traité comme une chaîne de caractères propre
        if 'code_upc' in df.columns:
            df['code_upc'] = df['code_upc'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            # Rétablir les zéros initiaux pour les codes de 11 chiffres transformés par Excel
            df['code_upc'] = df['code_upc'].apply(lambda x: x.zfill(12) if (x.isdigit() and len(x) == 11) else x)
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement de la feuille Google Sheets : {e}")
        return pd.DataFrame()

df_produits = charger_donnees()

# Barre latérale - Navigation principale
st.sidebar.html("<h2 style='color: #003366; font-size: 22px; font-weight: bold; margin-bottom: 20px;'>🧭 Navigation</h2>")
choix_mode = st.sidebar.radio(
    "Choisissez une action :",
    ["🔍 Recherche manuelle", "📸 Scanner un Code-Barres", "➕ Ajouter un produit d'achat local"]
)

# Variables globales de contrôle pour la recherche
saisie_net = None
# CODE DU SCANNEUR LOCAL INTEGRI COMPLETEMENT REPARE
if choix_mode == "📸 Scanner un Code-Barres":
    import cv2
    import numpy as np
    from pyzbar.pyzbar import decode

    st.html("<h2 style='color: #003366; font-size: 28px; font-weight: bold;'>📸 Scanneur Local Haute Performance</h2>")
    st.html("<p style='font-size: 20px; color: #333;'>Prenez une photo nette et horizontale du code-barres avec votre téléphone pour analyser le produit.</p>")
    
    image_chargee = st.file_uploader("Prendre une photo du code-barres", type=["jpg", "jpeg", "png"], key="scanner_camera_local")
    
    if image_chargee:
        file_bytes = np.asarray(bytearray(image_chargee.read()), dtype=np.uint8)
        image_cv = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        st.subheader("📸 Photo transmise :")
        st.image(image_cv, use_container_width=True)
        
        gris = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        _, gris_ameliore = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        with st.spinner("🔍 Décodage du code-barres en cours..."):
            codes_detectes = decode(image_cv)
            if not codes_detectes:
                codes_detectes = decode(gris_ameliore)
                
            if codes_detectes:
                for code in codes_detectes:
                    code_upc_extrait = code.data.decode('utf-8').strip()
                    st.success(f"🎯 Code-barres lu avec succès : {code_upc_extrait}")
                    saisie_net = code_upc_extrait
                    break
            else:
                st.error("❌ Aucun code-barres n'a pu être détecté. Assurez-vous que l'image est bien éclairée, stable et horizontale.")

resultats = None
message_erreur_recherche = None

# Interface pour la recherche manuelle (clavier)
if choix_mode == "🔍 Recherche manuelle":
    st.html("<h1 style='color: #003366; font-size: 32px; font-weight: bold; margin-bottom: 10px;'>🍎 Mon Guide d'Achat Local</h1>")
    st.html("<p style='font-size: 18px; color: #555; margin-bottom: 30px;'>Trouvez instantanément l'origine et le lieu de fabrication de vos produits alimentaires.</p>")
    
    st.html("<h3 style='color: #003366; font-size: 20px; font-weight: bold; margin-bottom: 5px;'>🔍 Rechercher un produit</h3>")
    saisie_utilisateur = st.text_input(
        "Entrez un code UPC (12 chiffres), une marque, une catégorie ou un ingrédient :",
        placeholder="Ex: 064200111011, Biscuits, Fromage, Leclerc...",
        key="barre_recherche_principale"
    )
    if saisie_utilisateur:
        saisie_net = saisie_utilisateur.strip()
# Logique de traitement et affichage des résultats de recherche (Clavier ou Scanneur)
if saisie_net:
    if not df_produits.empty:
        # Recherche par correspondance exacte sur le code UPC (format texte)
        if saisie_net.isdigit():
            saisie_formatee = saisie_net.zfill(12) if len(saisie_net) == 11 else saisie_net
            resultats = df_produits[df_produits['code_upc'] == saisie_formatee]
        
        # Si aucune correspondance exacte d'UPC, faire une recherche textuelle globale
        if resultats is None or resultats.empty:
            masque = (
                df_produits['code_upc'].str.contains(saisie_net, case=False, na=False) |
                df_produits['nom'].str.contains(saisie_net, case=False, na=False) |
                df_produits['entreprise_proprietaire'].str.contains(saisie_net, case=False, na=False) |
                df_produits['lieu_usine'].str.contains(saisie_net, case=False, na=False) |
                df_produits['categorie_produit'].str.contains(saisie_net, case=False, na=False)
            )
            resultats = df_produits[masque]
            
        if resultats.empty:
            message_erreur_recherche = f"🕵️ No produit trouvé pour '{saisie_net}'."
    else:
        message_erreur_recherche = "❌ Impossible d'effectuer la recherche car la base de données est vide."

# Affichage de la fiche produit détaillée
if resultats is not None and not resultats.empty:
    st.html("<h2 style='color: #003366; font-size: 24px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;'>📦 Résultats de l'analyse</h2>")
    
    # Si un seul produit correspond, on affiche sa fiche détaillée stylisée
    if len(resultats) == 1:
        row = resultats.iloc[0]
        
        st.html(f"""
            <div style='background-color: white; padding: 25px; border-radius: 12px; border-left: 8px solid #003366; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px;'>
                <span style='background-color: #e6f0fa; color: #003366; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 14px;'>Code UPC: {row.get('code_upc', 'N/A')}</span>
                <h2 style='margin-top: 10px; color: #333; font-size: 28px; font-weight: bold;'>{row.get('nom', 'Produit Inconnu')}</h2>
                <hr style='border: 0; h2: 1px; background: #eee; margin: 15px 0;'>
                <div style='display: flex; flex-wrap: wrap; gap: 40px;'>
                    <div style='flex: 1; min-width: 250px;'>
                        <p style='margin: 5px 0; font-size: 16px;'><strong style='color: #003366;'>🏭 Lieu de fabrication (Usine) :</strong> <span style='font-size: 18px; font-weight: bold; color: #d32f2f;'>{row.get('lieu_usine', 'Non spécifié')}</span></p>
                        <p style='margin: 5px 0; font-size: 16px;'><strong style='color: #003366;'>🏢 Entreprise propriétaire :</strong> {row.get('entreprise_proprietaire', 'N/A')}</p>
                        <p style='margin: 5px 0; font-size: 16px;'><strong style='color: #003366;'>🗺️ Siège social :</strong> {row.get('siege_social', 'N/A')}</p>
                    </div>
                    <div style='flex: 1; min-width: 250px;'>
                        <p style='margin: 5px 0; font-size: 16px;'><strong style='color: #003366;'>🇨🇦 Provenance de l'entreprise :</strong> {row.get('entreprise_pays', 'N/A')} ({row.get('entreprise_province_etat', 'N/A')})</p>
                        <p style='margin: 5px 0; font-size: 16px;'><strong style='color: #003366;'>🛒 Réseau de distribution :</strong> {row.get('reseau_distribution', 'N/A')}</p>
                        <p style='margin: 5px 0; font-size: 16px;'><strong style='color: #003366;'>🗂️ Catégorie :</strong> {row.get('categorie_produit', 'N/A')}</p>
                    </div>
                </div>
            </div>
        """)
        
        # Zone d'affichage des bannières de prix sous forme de colonnes épurées
        st.html("<h3 style='color: #003366; font-size: 20px; font-weight: bold; margin-bottom: 10px;'>💰 Suivi indicatif des prix enregistrés :</h3>")
        p_iga = row.get('prix_iga', '-')
        p_maxi = row.get('prix_maxi', '-')
        p_metro = row.get('prix_metro', '-')
        p_superc = row.get('prix_superc', '-')
        p_walmart = row.get('prix_walmart', '-')
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(label="IGA (Sobeys)", value=f"{p_iga} $" if p_iga != '-' and str(p_iga).strip() != '' else "-")
        c2.metric(label="Maxi (Loblaw)", value=f"{p_maxi} $" if p_maxi != '-' and str(p_maxi).strip() != '' else "-")
        c3.metric(label="Metro", value=f"{p_metro} $" if p_metro != '-' and str(p_metro).strip() != '' else "-")
        c4.metric(label="Super C", value=f"{p_superc} $" if p_superc != '-' and str(p_superc).strip() != '' else "-")
        c5.metric(label="Walmart", value=f"{p_walmart} $" if p_walmart != '-' and str(p_walmart).strip() != '' else "-")
        
    # Si plusieurs produits correspondent, on affiche le tableau synthétique
    else:
        st.info(f"💡 {len(resultats)} produits correspondent à votre recherche. Sélectionnez votre produit dans la liste ci-dessous :")
        colonnes_visibles = ['code_upc', 'nom', 'entreprise_proprietaire', 'lieu_usine', 'categorie_produit']
        df_affichage = resultats[colonnes_visibles] if all(col in resultats.columns for col in colonnes_visibles) else resultats
        st.dataframe(df_affichage, use_container_width=True, hide_index=True)
# Gestion du cas d'un nouveau produit (Lancement du formulaire collaboratif)
if message_erreur_recherche or (choix_mode == "📸 Scanner un Code-Barres" and saisie_net and (resultats is None or resultats.empty)):
    if message_erreur_recherche and message_erreur_recherche != "Ajout direct":
        st.warning(message_erreur_recherche)
        
    st.html("<div style='background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; font-weight: bold; margin-bottom: 20px;'>🤝 Mode Collaboratif : Aidez la communauté à documenter ce produit !</div>")
    
    # Pré-remplissage automatique de l'UPC si détecté par le clavier ou le scanneur
    upc_propose = saisie_net if (saisie_net and saisie_net.isdigit()) else ""
    
    with st.form("formulaire_ajout_produit", clear_on_submit=True):
        st.html("<h3 style='color: #003366; font-size: 20px; font-weight: bold;'>📝 Formulaire d'enregistrement de produit</h3>")
        
        c_left, c_right = st.columns(2)
        with c_left:
            form_upc = st.text_input("Code UPC (12 chiffres) :", value=upc_propose, max_chars=12)
            form_nom = st.text_input("Nom exact du produit :", placeholder="Ex: Fromage Le Pizy, Biscuits Pattes d'ours...")
            form_proprietaire = st.text_input("Entreprise propriétaire :", placeholder="Ex: Saputo, Fromagerie La Suisse Normande...")
            form_siege = st.text_input("Ville du Siège Social :", placeholder="Ex: Montréal, Saint-Roch-de-l'Achigan...")
            form_pays = st.text_input("Pays de l'entreprise :", value="Canada")
            form_province = st.text_input("Province / État :", value="Québec")
        with c_right:
            form_usine = st.text_input("Lieu de fabrication / Usine (IMPORTANT) :", placeholder="Ex: Fabriqué au Québec, Usine de Joliette...")
            form_reseau = st.text_input("Réseau de distribution :", placeholder="Ex: Metro, IGA, Super C, Maxi...")
            form_cat = st.text_input("Catégorie de produit :", placeholder="Ex: Produits laitiers, Boulangerie, Jus...")
            st.html("<p style='color: #003366; font-weight: bold; margin-bottom: 5px;'>🛒 Prix indicatifs payés en magasin (Optionnel) :</p>")
            form_iga = st.text_input("Prix chez IGA ($) :", placeholder="-")
            form_maxi = st.text_input("Prix chez Maxi ($) :", placeholder="-")
            form_metro = st.text_input("Prix chez Metro ($) :", placeholder="-")
            
        bouton_soumission = st.form_submit_button("💾 Enregistrer le produit dans la base cloud")
        
        if bouton_soumission:
            if not form_upc or not form_nom or not form_usine:
                st.error("⚠️ Les champs 'Code UPC', 'Nom du produit' et 'Lieu de fabrication (Usine)' sont obligatoires.")
            elif not form_upc.isdigit() or len(form_upc) < 11:
                st.error("⚠️ Le code UPC entré est invalide. Il doit être composé uniquement de chiffres.")
            else:
                try:
                    # Formatage de sécurité pour l'UPC à 12 chiffres
                    upc_final = form_upc.zfill(12) if len(form_upc) == 11 else form_upc
                    
                    # Construction de la nouvelle ligne de données
                    nouvelle_ligne = pd.DataFrame([{
                        "code_upc": str(upc_final).strip(),
                        "nom": form_nom.strip(),
                        "entreprise_proprietaire": form_proprietaire.strip(),
                        "siege_social": form_siege.strip(),
                        "entreprise_pays": form_pays.strip(),
                        "entreprise_province_etat": form_province.strip(),
                        "lieu_usine": form_usine.strip(),
                        "reseau_distribution": form_reseau.strip(),
                        "categorie_produit": form_cat.strip(),
                        "prix_iga": form_iga.strip() if form_iga else "-",
                        "prix_maxi": form_maxi.strip() if form_maxi else "-",
                        "prix_metro": form_metro.strip() if form_metro else "-",
                        "prix_superc": "-",
                        "prix_walmart": "-",
                        "date_maj": datetime.now().strftime("%Y-%m-%d")
                    }])
                    
                    # Envoi et écriture en nuage sur Google Sheets
                    conn.create(worksheet="sheet1", data=nouvelle_ligne)
                    st.cache_data.clear()  # Vidange immédiate du cache local pour inclure le produit au prochain scan
                    st.success(f"🎉 Succès ! Le produit '{form_nom}' a été enregistré. Il est maintenant disponible pour toute la communauté québécoise !")
                    st.balloons()
                except Exception as ex:
                    st.error(f"Erreur technique lors de la sauvegarde sur Google Sheets : {ex}")

# Vue par défaut de l'application (Tableau des produits d'achat local récents)
if not saisie_net and choix_mode != "➕ Ajouter un produit d'achat local":
    st.html("<h2 style='color: #003366; font-size: 24px; font-weight: bold; margin-top: 10px; margin-bottom: 15px;'>📋 Répertoire de l'Achat Local</h2>")
    if not df_produits.empty:
        st.write(f"La base de données cloud contient actuellement **{len(df_produits)}** produits alimentaires documentés.")
        colonnes_affichage = ['code_upc', 'nom', 'entreprise_proprietaire', 'lieu_usine', 'categorie_produit']
        df_table = df_produits[colonnes_affichage] if all(col in df_produits.columns for col in colonnes_affichage) else df_produits
        st.dataframe(df_table, use_container_width=True, hide_index=True)
    else:
        st.info("La base de données est actuellement vide ou en cours de chargement.")

# Onglet direct pour l'ajout manuel de produits sans passer par une recherche
if choix_mode == "➕ Ajouter un produit d'achat local" and not saisie_net:
    st.html("<h1 style='color: #003366; font-size: 32px; font-weight: bold;'>➕ Contribuer au Guide</h1>")
    message_erreur_recherche = "Ajout direct"
