import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
import numpy as np
from PIL import Image

# Configuration initiale de l'application
st.set_page_config(page_title="Acheter Québécois & Canadien", page_icon="📦", layout="wide")

# Injection CSS pour rendre la barre de saisie très visible sur mobile et PC
st.html("""
<style>
    .stTextInput label p { font-size: 24px !important; font-weight: bold !important; color: #003366 !important; }
    .stTextInput input { font-size: 26px !important; padding: 15px !important; height: 65px !important; font-weight: bold !important; letter-spacing: 2px !important; }
</style>
""")

def charger_donnees():
    """Se connecte au Google Sheet et nettoie la structure de données."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_initial = conn.read(worksheet="Sheet1")
    
        if df_initial is None or df_initial.empty:
            st.error("⚠️ Le fichier Google Sheet lu est vide. Vérifiez l'onglet 'Sheet1'.")
            return pd.DataFrame()

        df_initial = df_initial.astype(str)
        df_initial.columns = [c.strip().lower() for c in df_initial.columns]
        
        # Formatage de sécurité pour les codes CUP
        if 'code_upc' in df_initial.columns:
            df_initial['code_upc'] = df_initial['code_upc'].replace(r'\.0$', '', regex=True).str.strip()
        else:
            df_initial['code_upc'] = ""
        
        # Nettoyage des chaînes vides pour les colonnes de prix
        for col_prix in ['prix_iga', 'prix_super_c', 'prix_maxi', 'prix_metro']:
            if col_prix not in df_initial.columns:
                df_initial[col_prix] = ""
            df_initial[col_prix] = df_initial[col_prix].replace('nan', '').str.strip()
            
        # Unification de l'en-tête de distribution
        if 'distribution' not in df_initial.columns and 'reseau_distribution' in df_initial.columns:
            df_initial['distribution'] = df_initial['reseau_distribution']
        elif 'distribution' not in df_initial.columns:
            df_initial['distribution'] = ""
            
        df_initial['distribution'] = df_initial['distribution'].replace('nan', '').str.strip()      
        return df_initial
    except Exception as e:
        st.error(f"❌ Erreur de lecture : {e}")
        return pd.DataFrame()

def sauvegarder_donnees(df_a_enregistrer):
    """Met à jour le Google Sheet avec la nouvelle dataframe."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet="Sheet1", data=df_a_enregistrer)
        return True
    except Exception as e:
        st.error(f"❌ Erreur de sauvegarde réelle : {e}")
        return False

# Initialisation des variables d'état (Session State)
if 'df_produits' not in st.session_state:
    st.session_state['df_produits'] = charger_donnees()

if 'banniere_active' not in st.session_state:
    st.session_state['banniere_active'] = "Tous"

if 'code_scanne' not in st.session_state:
    st.session_state['code_scanne'] = ""

df = st.session_state['df_produits']
# Barre latérale pour le filtrage par origine géographique
st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 22px;'>🌐 Filtrer par origine</h2>")

if 'entreprise_pays' in df.columns:
    liste_pays = ["Tous"] + sorted([str(p) for p in df['entreprise_pays'].unique() if pd.notna(p) and p != ""])
    choix_pays = st.sidebar.selectbox("Filtrer par Pays propriétaire :", liste_pays)
    df_filtre = df[df['entreprise_pays'] == choix_pays] if choix_pays != "Tous" else df.copy()
else:
    df_filtre = df.copy()

if 'entreprise_province_etat' in df_filtre.columns:
    liste_prov = ["Toutes"] + sorted([str(p) for p in df_filtre['entreprise_province_etat'].unique() if pd.notna(p) and p != ""])
    choix_prov = st.sidebar.selectbox("Filtrer par Province / État :", liste_prov)
    if choix_prov != "Toutes":
        df_filtre = df_filtre[df_filtre['entreprise_province_etat'] == choix_prov]

# Titre principal de la zone de contenu
st.html("<h1 style='text-align: center; color: #003366; font-family: sans-serif;'>⚜️ MON GUIDE D'ACHAT LOCAL 🍁</h1>")
st.html("<p style='text-align: center; font-size: 16px; color: #666;'>Scannez un code-barres pour valider l'origine et gérer vos prix d'épicerie.</p>")

with st.expander("ℹ️ Comment utiliser l'application et économiser ?"):
    st.markdown("""
    ### 🛒 Protégeons notre portefeuille, encourageons l'achat local !
    1. **Recherchez un produit :** Tapez un mot-clé ou scannez le code CUP.
    2. **Identifiez la provenance :** Repérez les drapes et badges (Québec ⚜️, Canada 🍁).
    3. **Comparez les prix :** Voyez d'un coup d'œil quelle bannière est la moins chère.
    """)

# Sélection rapide de l'enseigne d'épicerie active
st.markdown("### 🏪 Choix rapide de votre bannière d'épicerie :")
col_iga, col_maxi, col_metro, col_super_c, col_walmart, col_tous = st.columns(6)

if col_iga.button("🔴 IGA", use_container_width=True): st.session_state['banniere_active'] = "IGA"
if col_maxi.button("🟡 Maxi", use_container_width=True): st.session_state['banniere_active'] = "Maxi"
if col_metro.button("🟢 Metro", use_container_width=True): st.session_state['banniere_active'] = "Metro"
if col_super_c.button("🔵 Super C", use_container_width=True): st.session_state['banniere_active'] = "Super_C"
if col_walmart.button("🔵 Walmart", use_container_width=True): st.session_state['banniere_active'] = "Walmart"
if col_tous.button("🔄 Toutes", use_container_width=True): st.session_state['banniere_active'] = "Tous"

banniere = st.session_state['banniere_active']

# Application du filtre de bannière sur la dataframe
if banniere != "Tous" and 'distribution' in df_filtre.columns:
    nom_banniere_recherche = banniere.replace('_', ' ')
    condition_distribution = df_filtre['distribution'].str.lower().str.contains(nom_banniere_recherche.lower(), na=False)
    df_filtre = df_filtre[condition_distribution]
# Création des onglets pour le mode clavier ou le mode appareil photo
onglet_clavier, onglet_camera = st.tabs(["⌨️ Recherche manuelle", "📷 Caméra Scanner (Intégré)"])

with onglet_camera:
    st.markdown("### 📷 Prenez le code-barres en photo")
    st.info("Alignez le code-barres du produit au centre de l'écran et prenez la photo.")
    
    # Bouton officiel de Streamlit
    photo_produit = st.camera_input("👉 Cliquez ici pour ouvrir l'appareil photo", key="camera_officielle_samsung")
    
    if photo_produit:
        # Lecture universelle de la photo prise par le téléphone
        image_pil = Image.open(photo_produit)
        
        # Importation locale sécurisée de pyzbar
        from pyzbar.pyzbar import decode
        
        # Lancement de l'analyse automatique de la photo
        codes_detectes = decode(image_pil)
        
        if codes_detectes:
            # Récupération du code trouvé et conversion en texte propre
            code_cam_detecte = str(codes_detectes[0].data.decode('utf-8')).strip()
            st.session_state['code_scanne'] = code_cam_detecte
            st.success(f"✅ Code CUP détecté : {code_cam_detecte}")
            st.rerun()
        else:
            st.warning("⚠️ Code-barres illisible. Reprenez la photo en reculant le produit à 20-30 cm pour éviter le flou de l'objectif.")

with onglet_clavier:
    valeur_champ = st.session_state['code_scanne'] if st.session_state['code_scanne'] else ""
    saisie_utilisateur = st.text_input("👉 TAPEZ UN NOM DE PRODUIT OU UN CODE CUP :", value=valeur_champ, key="champ_recherche_manuel")
    
    if saisie_utilisateur:
        st.session_state['code_scanne'] = saisie_utilisateur.strip()

saisie_net = st.session_state['code_scanne']

resultats = None
message_erreur_recherche = None

if saisie_net:
    try:
        cup_saisi = str(int(float(saisie_net))).strip()
    except ValueError:
        cup_saisi = saisie_net

    if 'code_upc' in df_filtre.columns:
        recherche_cup = df[df['code_upc'] == cup_saisi]
        if not recherche_cup.empty:
            resultats = recherche_cup
        else:
            if 'nom' in df_filtre.columns:
                recherche_texte = df_filtre[df_filtre['nom'].str.lower().str.contains(saisie_net.lower().strip(), na=False, regex=False)]
                if not recherche_texte.empty:
                    df_filtre = recherche_texte
                    if len(recherche_texte) == 1:
                        resultats = recherche_texte
                else:
                    message_erreur_recherche = f"⚠️ Aucun produit ne correspond à '{saisie_net}'."
# Préparation des colonnes à afficher dans le tableau de résultats
colonnes_prix_tableau = ['prix_iga', 'prix_super_c', 'prix_maxi', 'prix_metro']
colonnes_dispo = [c for c in ['code_upc', 'nom', 'entreprise_proprietaire', 'entreprise_province_etat', 'distribution'] if c in df_filtre.columns]
df_affichage = df_filtre[colonnes_dispo + [c for c in colonnes_prix_tableau if c in df_filtre.columns]].copy()

for c in df_affichage.columns:
    df_affichage[c] = df_affichage[c].astype(str).replace('nan', '')

config_colonnes = {
    "code_upc": st.column_config.TextColumn("Code CUP"),
    "nom": st.column_config.TextColumn("Nom du produit", width="large"),
    "entreprise_proprietaire": st.column_config.TextColumn("Entreprise"),
    "entreprise_province_etat": st.column_config.TextColumn("Province/État"),
    "distribution": st.column_config.TextColumn("Réseau"),
    "prix_iga": st.column_config.TextColumn("Prix IGA"),
    "prix_super_c": st.column_config.TextColumn("Prix Super C"),
    "prix_maxi": st.column_config.TextColumn("Prix Maxi"),
    "prix_metro": st.column_config.TextColumn("Prix Metro")
}

st.markdown("---")
selection_tableau = None 

# Gestion de l'affichage adaptatif du tableau interactif
if not saisie_net or (not df_filtre.empty and len(df_filtre) < len(df)):
    selection_tableau = st.dataframe(
        df_affichage, column_config=config_colonnes, use_container_width=True,
        hide_index=True, selection_mode="single-row", on_select="rerun", key="tableau_consommateur"
    )
else:
    if message_erreur_recherche and not saisie_net.isdigit():
        st.warning(message_erreur_recherche)

    # FORMULAIRE DE CRÉATION POUR NOUVEAU PRODUIT INCONNU
    if saisie_net.isdigit() and len(saisie_net) >= 10:
        st.info(f"📦 Le code CUP **{saisie_net}** est introuvable dans la base.")
        with st.form(key="formulaire_nouveau_produit", clear_on_submit=True):
            nom_nouveau = st.text_input("Nom exact du produit")
            cup_final = st.text_input("Code CUP", value=saisie_net, disabled=True)
            entreprise = st.text_input("Entreprise propriétaire / Marque")
            province = st.text_input("Province / État (ex: Québec)")
            pays = st.text_input("Pays", value="Canada")
            distribution = st.text_input("Réseau d'épicerie")
            
            st.write("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1: prix_iga = st.text_input("Prix IGA ($)")
            with col2: prix_superc = st.text_input("Prix Super C ($)")
            with col3: prix_maxi = st.text_input("Prix Maxi ($)")
            with col4: prix_metro = st.text_input("Prix Metro ($)")
            
            bouton_creer = st.form_submit_button("🚀 Enregistrer le nouveau produit dans Google Sheets", type="primary", use_container_width=True)
            
            if bouton_creer and nom_nouveau:
                nouvelle_ligne = {
                    'code_upc': cup_final, 'nom': nom_nouveau.strip(), 'entreprise_proprietaire': entreprise.strip(),
                    'entreprise_province_etat': province.strip(), 'entreprise_pays': pays.strip(), 'distribution': distribution.strip(),
                    'prix_iga': prix_iga.strip(), 'prix_super_c': prix_superc.strip(), 'prix_maxi': prix_maxi.strip(), 'prix_metro': prix_metro.strip()
                }
                st.session_state['df_produits'] = pd.concat([st.session_state['df_produits'], pd.DataFrame([nouvelle_ligne])], ignore_index=True)
                if sauvegarder_donnees(st.session_state['df_produits']):
                    st.success("🎉 Nouveau produit enregistré avec succès !")
                    st.session_state['code_scanne'] = ""
                    time.sleep(1)
                    st.rerun()

# Capture de la ligne sélectionnée manuellement dans le tableau
if selection_tableau and "rows" in selection_tableau["selection"] and selection_tableau["selection"]["rows"]:
    index_ligne_cliquee = selection_tableau["selection"]["rows"][0]
    cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
    resultats = df[df['code_upc'] == cup_selectionne]

# AFFICHAGE DE LA FICHE DÉTAILLÉE DU PRODUIT TROUVÉ
if resultats is not None and not resultats.empty:
    st.markdown("---")
    index_produit_reel = resultats.index[0]
    row = resultats.iloc[0]
    
    prov = str(row.get('entreprise_province_etat', '')).strip()
    pays = str(row.get('entreprise_pays', '')).strip()
    
    if "québec" in prov.lower():
        couleur_boite, couleur_texte, verdict = "#e1f5fe", "#0d47a1", "⚜️ PRODUIT QUÉBÉCOIS"
    elif "canada" in pays.lower():
        couleur_boite, couleur_texte, verdict = "#e8f5e9", "#1b5e20", "🍁 PRODUIT CANADIEN"
    else:
        couleur_boite, couleur_texte, verdict = "#fafafa", "#424242", "🌍 PROPRIÉTÉ ÉTRANGÈRE"

    st.html(f"""
    <div style="background-color: {couleur_boite}; padding: 22px; border-radius: 10px; border-left: 12px solid {couleur_texte}; font-family: Arial, sans-serif;">
        <h3 style="color: {couleur_texte}; margin-top: 0;">{verdict}</h3>
        <p style="font-size: 22px; font-weight: bold; margin-bottom: 5px;">📦 {row.get('nom', 'Sans nom')}</p>
        <p style="font-size: 18px; font-weight: bold; color: #d32f2f;">🔢 CUP : {row.get('code_upc', 'Inconnu')}</p>
        <div style="margin: 10px 0; display: flex; gap: 10px; flex-wrap: wrap;">
            <span>🔴 IGA : {row.get('prix_iga', 'Non inscrit')}</span> | 
            <span>🔵 SUPER C : {row.get('prix_super_c', 'Non inscrit')}</span> | 
            <span>🟡 MAXI : {row.get('prix_maxi', 'Non inscrit')}</span> | 
            <span>🟢 METRO : {row.get('prix_metro', 'Non inscrit')}</span>
        </div>
    </div>
    """)

    # Formulaire collaboratif de mise à jour des prix
    with st.form("formulaire_prix_epicerie"):
        st.write("#### 📝 Mettre à jour les prix de ce produit :")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        nouveau_iga = col_p1.text_input("Prix IGA ($)", value=row.get('prix_iga', ''))
        nouveau_super_c = col_p2.text_input("Prix Super C ($)", value=row.get('prix_super_c', ''))
        nouveau_maxi = col_p3.text_input("Prix Maxi ($)", value=row.get('prix_maxi', ''))
        nouveau_metro = col_p4.text_input("Prix Metro ($)", value=row.get('prix_metro', ''))
        
        bouton_soumettre = st.form_submit_button("💾 Enregistrer les nouveaux prix", type="primary", use_container_width=True)

    if bouton_soumettre:
        st.session_state['df_produits'].at[index_produit_reel, 'prix_iga'] = nouveau_iga.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_super_c'] = nouveau_super_c.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_maxi'] = nouveau_maxi.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_metro'] = nouveau_metro.strip()
        
        if sauvegarder_donnees(st.session_state['df_produits']):
            st.success("Prix synchronisés avec Google Sheets !")
            st.session_state['code_scanne'] = ""
            time.sleep(0.5)
            st.rerun()

st.caption(f"Filtre actif : Enseigne -> {banniere.upper()}")
