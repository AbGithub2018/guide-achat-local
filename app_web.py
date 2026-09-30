import streamlit as st
import pandas as pd
import time
import requests
from streamlit_gsheets import GSheetsConnection
from streamlit_qrcode_scanner import qrcode_scanner

# 1. UNIQUE CONFIGURATION DE LA PAGE
st.set_page_config(
    page_title="Acheter Québécois & Canadien", 
    page_icon="📦", 
    layout="wide",
    initial_sidebar_state="expanded"
)

code_upc = "code_upc"

# Injection CSS de sécurité maximale : préserve uniquement la flèche de gauche
st.html("""
<style>
    /* 1. Masquer le menu hamburger standard, le footer et le widget de statut */
    #MainMenu, footer { visibility: hidden !important; display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    
    /* 2. Éliminer la présence physique et visuelle des boutons d'édition (crayon, étoile, partage) */
    [data-testid="stHeaderActionElements"], .stAppDeployButton { 
        display: none !important; 
        visibility: hidden !important;
        width: 0px !important;
        height: 0px !important;
    }
    
    /* 3. Masquer complètement le logo GitHub et le badge de visionnage de code */
    .stViewerBadge, .stGitHubIcon, a[href*="github.com"], button[title*="GitHub"] { 
        display: none !important; 
        visibility: hidden !important;
        opacity: 0 !important;
        width: 0px !important;
    }
    
    /* 4. Forcer la zone d'action de droite à s'effacer pour protéger le script */
    header div:nth-child(2) {
        display: none !important;
    }
    
    /* 5. Garder l'en-tête transparent et forcer EXCLUSIVEMENT la flèche > à s'afficher */
    header { background-color: transparent !important; }
    [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
    }
    
    /* 6. Grossir la barre de recherche géante */
    .stTextInput label p { font-size: 24px !important; font-weight: bold !important; color: #003366 !important; }
    .stTextInput input { font-size: 26px !important; padding: 15px !important; height: 65px !important; font-weight: bold !important; letter-spacing: 2px !important; }
    
    /* 7. Grossir de façon spectaculaire les textes des boutons de sélection (Radio) */
    .stRadio label p { font-size: 26px !important; font-weight: bold !important; color: #111111 !important; }
    div[data-testid="stRadioHorizontal"] { gap: 40px !important; }
    
    /* 8. Forcer les colonnes à rester côte à côte (3 par ligne) même sur cellulaire */
    div[data-testid="stColumns"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 10px !important;
    }
    div[data-testid="column"] {
        flex: 1 1 calc(33.333% - 10px) !important;
        min-width: calc(33.333% - 10px) !important;
        max-width: calc(33.333% - 10px) !important;
    }
</style>
""")
def charger_donnees():
    """Se connecte automatiquement au Google Sheet grâce aux secrets de Streamlit Cloud."""
    try:
        conn = st.connection("gsheets", type="streamlit_gsheets.GSheetsConnection")
        df_initial = conn.read(worksheet="Sheet1", ttl="2m")
        if df_initial is None or df_initial.empty:
            st.error("⚠️ Le fichier Google Sheet lu est vide. Vérifiez l'onglet 'Sheet1'.")
            return pd.DataFrame()

        df_initial = df_initial.astype(str)
        
        # Nettoyage automatique des noms de colonnes pour éviter les KeyError
        df_initial.columns = [c.strip().lower() for c in df_initial.columns]
        
        if 'code_upc' in df_initial.columns:
            df_initial['code_upc'] = df_initial['code_upc'].replace(r'\.0$', '', regex=True).str.strip()
        else:
            df_initial['code_upc'] = ""
        
        for col_prix in ['prix_iga', 'prix_super_c', 'prix_maxi', 'prix_metro', 'prix_walmart', 'prix_tigre_geant', 'prix_dollarama', 'prix_provigo']:
            if col_prix not in df_initial.columns:
                df_initial[col_prix] = ""
            df_initial[col_prix] = df_initial[col_prix].fillna("").astype(str).str.strip().replace("nan", "")

        # Sécurité pour la colonne distribution (gère vos deux colonnes E et K)
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
    """Enregistre les prix automatiquement grâce aux secrets de Streamlit Cloud."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet="Sheet1", data=df_a_enregistrer)
        st.cache_data.clear()
        if 'df_produits' in st.session_state:
            del st.session_state['df_produits']
        return True
    except Exception as e:
        st.error(f"❌ Erreur de sauvegarde réelle : {e}")
        return False

# Initialisation et chargement de la base de données en Session Streamlit
if 'df_produits' not in st.session_state:
    st.session_state['df_produits'] = charger_donnees()

# Raccourci vers les données en session
df = st.session_state['df_produits']

if 'banniere_active' not in st.session_state:
    st.session_state['banniere_active'] = "Tous"
st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 22px;'>🌐 Filtrer les produits par pays d'origine</h2>")

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

# 🔑 ZONE ADMINISTRATEUR COMPACTE
st.sidebar.markdown("---") 
with st.sidebar.expander("🔑 Administration"):
    if "admin_connecte" not in st.session_state:
        st.session_state["admin_connecte"] = False

    if not st.session_state["admin_connecte"]:
        mot_de_passe = st.text_input("Entrez le mot de passe de gestion", type="password", key="sidebar_mdp_secret")
        if mot_de_passe == st.secrets["admin"]["password"]:
            st.session_state["admin_connecte"] = True
            st.rerun()
    else:
        st.success("🟢 Mode Admin Actif")
        if st.button("Se déconnecter", type="primary", use_container_width=True):
            st.session_state["admin_connecte"] = False
            st.rerun()
            
        st.markdown("---")
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_actuel = conn.read(ttl=0)
        cup_a_supprimer = st.text_input("code_upc du produit à supprimer", key="cup_delete_input")
        
        if st.button("Supprimer définitivement le produit du Nuage", use_container_width=True):
            if cup_a_supprimer:
                df_nettoye = df_actuel[df_actuel[code_upc].astype(str) != str(cup_a_supprimer)]
                conn.update(data=df_nettoye)
                if 'df_produits' in st.session_state:
                    del st.session_state['df_produits']
                st.success("Produit supprimé avec succès !")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Veuillez entrer un code_upc valide.")

# 📸 RÉSERVATION DE L'ESPACE PHOTO DYNAMIQUE
st.sidebar.markdown("---") 
st.sidebar.subheader("Aperçu du produit")

if "tableau_consommateur" in st.session_state and st.session_state["tableau_consommateur"]["selection"]["rows"]:
    index_ligne = st.session_state["tableau_consommateur"]["selection"]["rows"][0]
    try:
        # Correction d'indexation pour st.dataframe natif
        df_affichage_temp = df_filtre[[c for c in ['code_upc', 'nom', 'entreprise_proprietaire', 'entreprise_province_etat', 'distribution'] if c in df_filtre.columns]].copy()
        raw_cup = df_affichage_temp.iloc[index_ligne]['code_upc']
        cup_actuel = str(int(float(raw_cup))).strip()
        
        if cup_actuel:
            st.sidebar.success(f"📦 Produit détecté : {cup_actuel}")
            with st.sidebar.spinner("Recherche de la photo..."):
                try:
                    url_api = f"https://openfoodfacts.org{cup_actuel}.json"
                    headers = {"User-Agent": "AchatQuebecApp - Web - Version1.0"}
                    reponse = requests.get(url_api, headers=headers, timeout=5)
                    if reponse.status_code == 200:
                        donnees = reponse.json()
                        if donnees.get("status") == 1 and "product" in donnees and "image_url" in donnees["product"]:
                            st.sidebar.image(donnees["product"]["image_url"], caption="Photo officielle OpenFoodFacts", use_container_width=True)
                        else:
                            st.sidebar.warning("⚠️ Photo non disponible dans la base publique.")
                    else:
                        st.sidebar.error("❌ Serveur d'images indisponible.")
                except Exception as e:
                    st.sidebar.error(f"⚠️ Erreur de connexion : {e}")
    except Exception as e:
        pass
# ZONE PRINCIPALE : Entête
st.html("<h1 style='text-align: center; color: #003366; font-family: sans-serif;'>⚜️ MON GUIDE D'ACHAT LOCAL 🍁</h1>")
st.html("<p style='text-align: center; font-size: 16px; color: #666;'>Scannez un code-barres pour valider l'origine et gérer vos prix d'épicerie.</p>")

with st.expander("ℹ️ Comment utiliser l'application et économiser ? (Cliquez pour ouvrir)"):
    st.markdown("""
    ### 🛒 Protégeons notre portefeuille, encourageons l'achat local !
    Bienvenue sur **AchatQuébec**, votre outil citoyen et collaborative pour dénicher les meilleurs prix à l'épicerie tout en gardant notre argent ici.
    
    #### 🕵️‍♂️ Comment ça fonctionne ?
    1. **Recherchez un produit :** Tapez un mot-clé (ex: *pomme*) ou le code_upc.
    2. **Identifiez la provenance :** Repérez les drapeaux et badges (Québec ⚜️, Canada 🍁).
    3. **Comparez les prix :** Voyez d'un coup d'œil quelle bannière est la moins chère.
    """)

st.markdown("### 🏪 Choix rapide de votre bannière d'épicerie :")

# Boutons tactiles
col_iga, col_maxi = st.columns(2)
if col_iga.button("🔴 IGA", use_container_width=True): st.session_state['banniere_active'] = "IGA"
if col_maxi.button("🟡 Maxi", use_container_width=True): st.session_state['banniere_active'] = "Maxi"

col_metro, col_super_c = st.columns(2)
if col_metro.button("🟢 Metro", use_container_width=True): st.session_state['banniere_active'] = "Metro"
if col_super_c.button("🔵 Super C", use_container_width=True): st.session_state['banniere_active'] = "Super_C"

col_walmart, col_tigre = st.columns(2)
if col_walmart.button("🔵 Walmart", use_container_width=True): st.session_state['banniere_active'] = "Walmart"
if col_tigre.button("🐯 Tigre Géant", use_container_width=True): st.session_state['banniere_active'] = "Tigre_Geant"

col_dollarama, col_provigo, col_tous = st.columns(3)
if col_dollarama.button("💵 Dollarama", use_container_width=True): st.session_state['banniere_active'] = "Dollarama"
if col_provigo.button("🟢 Provigo", use_container_width=True): st.session_state['banniere_active'] = "Provigo"
if col_tous.button("🔄 Toutes", use_container_width=True): st.session_state['banniere_active'] = "Tous"

banniere = st.session_state['banniere_active']
if banniere != "Tous" and 'distribution' in df_filtre.columns:
    nom_banniere_recherche = banniere.replace('_', ' ')
    df_filtre = df_filtre[df_filtre['distribution'].str.lower().str.contains(nom_banniere_recherche.lower(), na=False)]
resultats = None
message_erreur_recherche = None
saisie_net = ""

choix_mode = st.radio("👉 MODE DE RECHERCHE :", ["⌨️ Recherche manuelle", "📸 Scanner un Code-Barres"], horizontal=True, label_visibility="collapsed")

if "cup" in st.query_params:
    saisie_net = str(st.query_params["cup"]).strip()
    st.success(f"✅ code_upc détecté : {saisie_net}")

if choix_mode == "⌨️ Recherche manuelle":
    valeur_par_defaut = saisie_net if saisie_net else ""
    saisie = st.text_input("👉 TAPEZ UN NOM DE PRODUIT OU UN code_upc :", value=valeur_par_defaut, key="recherche_cup")    
    if saisie: saisie_net = saisie.strip()
    if "cup" in st.query_params: st.query_params.clear()

elif choix_mode == "📸 Scanner un Code-Barres":
    st.html("<h2 style='color: #003366; font-size: 28px; font-weight: bold;'>📷 Scanneur Local Haute Performance</h2>")
    code_detecte = qrcode_scanner(key="scanner_officiel_live")
    if code_detecte:
        st.success(f"🎉 Code-barres détecté : {code_detecte}")
        st.session_state['code_barre_input'] = str(code_detecte)
        saisie_net = str(code_detecte)

if saisie_net:
    cup_saisi = saisie_net.strip()
    terme_recherche_minuscule = cup_saisi.lower()

    if 'code_upc' in df_filtre.columns:
        recherche_cup = df_filtre[df_filtre['code_upc'].astype(str).str.strip() == cup_saisi]
        if not recherche_cup.empty:
            df_filtre = recherche_cup
            resultats = recherche_cup
        else:
            conditions = pd.Series(False, index=df_filtre.index)
            if 'nom' in df_filtre.columns:
                conditions |= df_filtre['nom'].str.lower().str.contains(terme_recherche_minuscule, na=False, regex=False)
            if 'siege_social' in df_filtre.columns:
                conditions |= df_filtre['siege_social'].str.lower().str.contains(terme_recherche_minuscule, na=False, regex=False)
            if 'lieu_usine' in df_filtre.columns:
                conditions |= df_filtre['lieu_usine'].str.lower().str.contains(terme_recherche_minuscule, na=False, regex=False)
                
            recherche_texte = df_filtre[conditions]
            if not recherche_texte.empty:
                df_filtre = recherche_texte
                if len(recherche_texte) == 1: resultats = recherche_texte
            else:
                message_erreur_recherche = f"⚠️ Aucun produit ne correspond à '{saisie_net}'."
# Préparation des données d'affichage
colonnes_prix_tableau = ['prix_iga', 'prix_super_c', 'prix_maxi', 'prix_metro']
colonnes_dispo = [c for c in ['code_upc', 'nom', 'entreprise_proprietaire', 'entreprise_province_etat', 'distribution'] if c in df_filtre.columns]
df_affichage = df_filtre[colonnes_dispo + [c for c in colonnes_prix_tableau if c in df_filtre.columns]].copy()

for c in df_affichage.columns:
    df_affichage[c] = df_affichage[c].astype(str).replace('nan', '')

config_colonnes = {
    "code_upc": st.column_config.TextColumn("code_upc", width="medium"),
    "nom": st.column_config.TextColumn("Nom du produit", width="large"),
    "siege_social": st.column_config.TextColumn("Entreprise"),
    "entreprise_province_etat": st.column_config.TextColumn("Province/État"),
    "distribution": st.column_config.TextColumn("Réseau d'épicerie")
}

st.markdown("---")
st.markdown(f"### 📋 Liste des produits ({len(df_affichage)} affichés) :")

selection_tableau = None 
if not saisie_net or (not df_filtre.empty and len(df_filtre) < len(df)):
    selection_tableau = st.dataframe(df_affichage, column_config=config_colonnes, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", key="tableau_consommateur")
else:
    if message_erreur_recherche and not saisie_net.strip().isdigit():
        st.warning(message_erreur_recherche)

    # Formulaire de contribution si code_upc numérique inconnu
    if saisie_net.strip().isdigit() and len(saisie_net.strip()) >= 10:
        st.info(f"📦 Le code_upc **{saisie_net}** est un nouveau produit.")
        
        with st.form(key="formulaire_nouveau_produit", clear_on_submit=True):
            # L'INFO-BULLE SOUHAITÉE EST APPLIQUÉE ICI
            nom_nouveau = st.text_input(
                "Nom exact du produit (ex: Fraises du Québec 1L)",
                help="Obligatoire. Précisez bien la marque, la variété et le format pour aider les prochains consommateurs (Ex: Biscuits Lu Véritable Petit Beurre 200g)."
            )
            cup_final = st.text_input("code_upc", value=saisie_net.strip(), disabled=True)
            entreprise = st.text_input("Entreprise propriétaire / Marque (ex: Unico)")
            province = st.text_input("Province / État (ex: Québec)")
            pays = st.text_input("Pays", value="Canada")
            distribution = st.text_input("Réseau d'épicerie (ex: IGA, Maxi, Metro, Super C)")
            
            st.write("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1: prix_iga = st.text_input("Prix IGA ($)")
            with col2: prix_superc = st.text_input("Prix Super C ($)")
            with col3: prix_maxi = st.text_input("Prix Maxi ($)")
            with col4: prix_metro = st.text_input("Prix Metro ($)")
        
            bouton_creer = st.form_submit_button("🚀 Enregistrer le nouveau produit dans le Nuage", type="primary", use_container_width=True)
            if bouton_creer and nom_nouveau:
                nouvelle_ligne = {'code_upc': cup_final, 'nom': nom_nouveau.strip(), 'siege_social': entreprise.strip(), 'entreprise_province_etat': province.strip(), 'entreprise_pays': pays.strip(), 'distribution': distribution.strip(), 'prix_iga': prix_iga.strip() or "Non inscrit", 'prix_super_c': prix_superc.strip() or "Non inscrit", 'prix_maxi': prix_maxi.strip() or "Non inscrit", 'prix_metro': prix_metro.strip() or "Non inscrit"}
                st.session_state['df_produits'] = pd.concat([st.session_state['df_produits'], pd.DataFrame([nouvelle_ligne])], ignore_index=True)
                if sauvegarder_donnees(st.session_state['df_produits']):
                    st.success("🎉 Produit ajouté avec succès.")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

# Récupération de la sélection utilisateur pour la fiche descriptive
if selection_tableau and selection_tableau["selection"]["rows"] and 'code_upc' in df_affichage.columns:
    index_ligne_cliquee = selection_tableau["selection"]["rows"][0]
    if index_ligne_cliquee < len(df_affichage):
        cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
        resultats = df[df['code_upc'] == cup_selectionne]

if resultats is not None and not resultats.empty:
    st.markdown("---")
    index_produit_reel = resultats.index[0]
    row = resultats.iloc[0]
    prov, pays = str(row.get('entreprise_province_etat', '')).strip(), str(row.get('entreprise_pays', '')).strip()
    
    couleur_boite, couleur_texte, verdict = ("#e1f5fe", "#0d47a1", "⚜️ PRODUIT QUÉBÉCOIS") if "québec" in prov.lower() else (("#e8f5e9", "#1b5e20", "🍁 PRODUIT CANADIEN") if "canada" in pays.lower() else ("#fafafa", "#424242", "🌍 PROPRIÉTÉ ÉTRANGÈRE"))

    st.html(f"""
    <div style="background-color: {couleur_boite}; padding: 22px; border-radius: 10px; border-left: 12px solid {couleur_texte}; margin-bottom: 15px;">
        <h3 style="color: {couleur_texte}; margin-top: 0;">{verdict}</h3>
        <p style="font-size: 22px; font-weight: bold;">📦 {row.get('nom', 'Produit sans nom')}</p>
        <p><b>🏭 Compagnie :</b> {row.get('entreprise_proprietaire', 'À déterminer')} | <b>📍 Origine :</b> {prov} ({pays})</p>
    </div>
    """)

    # Formulaire collaboratif de mise à jour des prix
    with st.form("formulaire_prix_epicerie"):
        col_p1, col_p2 = st.columns(2)
        nouveau_iga = col_p1.text_input("Prix IGA ($) :", value=str(row.get('prix_iga', '')))
        nouveau_maxi = col_p2.text_input("Prix Maxi ($) :", value=str(row.get('prix_maxi', '')))
        bouton_soumettre = st.form_submit_button("💾 Enregistrer la grille de prix", type="primary", use_container_width=True)
        
    if bouton_soumettre:
        st.session_state['df_produits'].at[index_produit_reel, 'prix_iga'] = nouveau_iga.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_maxi'] = nouveau_maxi.strip()
        if sauvegarder_donnees(st.session_state['df_produits']):
            st.success("Prix mis à jour !")
            time.sleep(1)
            st.rerun()

st.caption(f"Filtre d'affichage actif : Enseigne sélectionnée -> **{banniere.upper()}**")
