import streamlit as st
import pandas as pd
import time
import requests
from streamlit_gsheets import GSheetsConnection

# 1. UNIQUE CONFIGURATION DE LA PAGE
st.set_page_config(
    page_title="Acheter Québécois & Canadien", 
    page_icon="📦", 
    layout="wide",
    initial_sidebar_state="expanded"
)

code_upc = "code_upc"

# Injection CSS de sécurité maximale
st.html("""
<style>
    #MainMenu, footer { visibility: hidden !important; display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="stHeaderActionElements"], .stAppDeployButton { 
        display: none !important; visibility: hidden !important; width: 0px !important; height: 0px !important;
    }
    .stViewerBadge, .stGitHubIcon, a[href*="github.com"], button[title*="GitHub"] { 
        display: none !important; visibility: hidden !important; opacity: 0 !important; width: 0px !important;
    }
    header div:nth-child(2) { display: none !important; }
    header { background-color: transparent !important; }
    [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] { display: flex !important; visibility: visible !important; }
    .stTextInput label p { font-size: 24px !important; font-weight: bold !important; color: #003366 !important; }
    .stTextInput input { font-size: 26px !important; padding: 15px !important; height: 65px !important; font-weight: bold !important; letter-spacing: 2px !important; }
    .stRadio label p { font-size: 26px !important; font-weight: bold !important; color: #111111 !important; }
    div[data-testid="stRadioHorizontal"] { gap: 40px !important; }
    div[data-testid="stColumns"] { display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 10px !important; }
    div[data-testid="column"] { flex: 1 1 calc(33.333% - 10px) !important; min-width: calc(33.333% - 10px) !important; max-width: calc(33.333% - 10px) !important; }
</style>
""")

def charger_donnees():
    """Se connecte automatiquement au Google Sheet."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_initial = conn.read(worksheet="Sheet1", ttl="2m")
        if df_initial is None or df_initial.empty:
            st.error("⚠️ Le fichier Google Sheet lu est vide. Vérifiez l'onglet 'Sheet1'.")
            return pd.DataFrame()

        df_initial = df_initial.astype(str)
        df_initial.columns = [c.strip().lower() for c in df_initial.columns]
        
        if 'code_upc' in df_initial.columns:
            df_initial['code_upc'] = df_initial['code_upc'].replace(r'\.0$', '', regex=True).str.strip()
        else:
            df_initial['code_upc'] = ""
        
        for col_prix in ['prix_iga', 'prix_super_c', 'prix_maxi', 'prix_metro', 'prix_walmart', 'prix_tigre_geant', 'prix_dollarama', 'prix_provigo']:
            if col_prix not in df_initial.columns:
                df_initial[col_prix] = ""
            df_initial[col_prix] = df_initial[col_prix].fillna("").astype(str).str.strip().replace("nan", "")
            
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
    """Enregistre les prix automatiquement."""
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
# Initialisation des variables d'état de session
if 'df_produits' not in st.session_state:
    st.session_state['df_produits'] = charger_donnees()
if 'banniere_active' not in st.session_state:
    st.session_state['banniere_active'] = "Tous"
if "admin_connecte" not in st.session_state:
    st.session_state["admin_connecte"] = False

df = st.session_state['df_produits']

# 2. BARRE LATERALE (Filtres Géopolitiques)
st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 22px;'>🌐 Filtrer les produits</h2>")

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

# Panneau Administration
st.sidebar.markdown("---") 
with st.sidebar.expander("🔑 Administration"):
    if not st.session_state["admin_connecte"]:
        mot_de_passe = st.text_input("Entrez le mot de passe de gestion", type="password", key="sidebar_mdp_secret")
        if mot_de_passe and mot_de_passe == st.secrets["admin"]["password"]:
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
# 3. ZONE PRINCIPALE : Entête
st.html("<h1 style='text-align: center; color: #003366; font-family: sans-serif;'>⚜️ MON GUIDE D'ACHAT LOCAL 🍁</h1>")
st.html("<p style='text-align: center; font-size: 16px; color: #666;'>Scannez un code-barres pour valider l'origine et gérer vos prix d'épicerie.</p>")

with st.expander("ℹ️ Comment utiliser l'application et économiser ?"):
    st.markdown("""
    ### 🛒 Protégeons notre portefeuille, encourageons l'achat local !
    Bienvenue sur **AchatQuébec**, votre outil citoyen pour dénicher les meilleurs prix à l'épicerie.
    1. **Recherchez un produit :** Tapez un mot-clé ou le code_upc.
    2. **Identifiez la provenance :** Repérez les drapeaux (Québec ⚜️, Canada 🍁).
    3. **Comparez les prix :** Voyez d'un coup d'œil quelle bannière est la moins chère.
    """)

# Boutons rapides de sélection de bannières
st.markdown("### 🏪 Choix rapide de votre bannière d'épicerie :")
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
# 4. ZONE DE RECHERCHE ET SCANNER
choix_mode = st.radio(
    "👉 MODE DE RECHERCHE :",
    ["⌨️ Recherche manuelle", "📸 Scanner un Code-Barres"],
    horizontal=True,
    label_visibility="collapsed"
)
saisie_net = ""

if "cup" in st.query_params:
    saisie_net = str(st.query_params["cup"]).strip()
    st.success(f"✅ code_upc détecté : {saisie_net}")

if choix_mode == "⌨️ Recherche manuelle":
    valeur_par_defaut = saisie_net if saisie_net else ""
    saisie = st.text_input("👉 TAPEZ UN NOM DE PRODUIT OU UN code_upc :", value=valeur_par_defaut, key="recherche_cup")    
    if saisie:
        saisie_net = saisie.strip()
    if "cup" in st.query_params:
        st.query_params.clear()
else:
    st.html("<h2 style='color: #003366; font-size: 28px; font-weight: bold;'>📷 Scanneur Local Haute Performance</h2>")
    from streamlit_qrcode_scanner import qrcode_scanner
    code_detecte = qrcode_scanner(key="scanner_officiel_live")
    if code_detecte:
        st.success(f"🎉 Code-barres détecté : {code_detecte}")
        saisie_net = str(code_detecte).strip()

# Logique de filtrage par recherche
resultats = None
message_erreur_recherche = None

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
                if len(recherche_texte) == 1:
                    resultats = recherche_texte
            else:
                message_erreur_recherche = f"⚠️ Aucun produit ne correspond à '{saisie_net}'."
# 5. CONFIGURATION ET RENDU DU TABLEAU
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

# Rendu sécurisé du Tableau interactif
selection_tableau = None
if not saisie_net or (not df_filtre.empty and len(df_filtre) < len(df)):
    selection_tableau = st.dataframe(
        df_affichage,
        column_config=config_colonnes,
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key="tableau_consommateur"
    )
else:
    if message_erreur_recherche and not saisie_net.strip().isdigit():
        st.warning(message_erreur_recherche)

# Détection sécurisée de la ligne cliquée
if selection_tableau and selection_tableau.get("selection") and selection_tableau["selection"]["rows"]:
    index_ligne_cliquee = selection_tableau["selection"]["rows"][0]
    if index_ligne_cliquee < len(df_affichage):
        cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
        resultats = df[df['code_upc'] == cup_selectionne]

# --- IMAGE DANS LA BARRE LATERALE APRES ACTION TABLEAU ---
st.sidebar.markdown("---") 
st.sidebar.subheader("Aperçu du produit")

if resultats is not None and not resultats.empty:
    raw_cup = resultats.iloc[0]['code_upc']
    try:
        cup_actuel = str(int(float(raw_cup))).strip()
        if cup_actuel:
            st.sidebar.success(f"📦 Image du CUP : {cup_actuel}")
            with st.sidebar.spinner("Recherche..."):
                try:
                    url_api = f"https://openfoodfacts.org{cup_actuel}.json"
                    reponse = requests.get(url_api, headers={"User-Agent": "AchatQuebecApp-Web"}, timeout=3)
                    if reponse.status_code == 200 and reponse.json().get("status") == 1:
                        lien_photo = reponse.json()["product"].get("image_url")
                        if lien_photo:
                            st.sidebar.image(lien_photo, use_container_width=True)
                        else:
                            st.sidebar.warning("⚠️ Aucune photo trouvée.")
                except:
                    st.sidebar.error("⚠️ Erreur Open Food Facts.")
    except:
        pass

# FORMULAIRE POUR NOUVEAU PRODUIT (CUP inconnu)
if saisie_net.strip().isdigit() and len(saisie_net.strip()) >= 10 and (resultats is None or resultats.empty):
    st.info(f"📦 Le code_upc **{saisie_net}** semble être un nouveau produit.")
    with st.form(key="formulaire_nouveau_produit", clear_on_submit=True):
        nom_nouveau = st.text_input("Nom exact du produit")
        entreprise = st.text_input("Entreprise propriétaire / Marque")
        province = st.text_input("Province / État", value="Québec")
        pays = st.text_input("Pays", value="Canada")
        distribution = st.text_input("Réseau d'épicerie")
        
        bouton_creer = st.form_submit_button("🚀 Enregistrer le nouveau produit", type="primary", use_container_width=True)
        if bouton_creer and nom_nouveau:
            nouvelle_ligne = {
                'code_upc': saisie_net.strip(), 'nom': nom_nouveau.strip(), 'siege_social': entreprise.strip(),
                'entreprise_province_etat': province.strip(), 'entreprise_pays': pays.strip(), 'distribution': distribution.strip(),
                'prix_iga': "", 'prix_super_c': "", 'prix_maxi': "", 'prix_metro': "", 'prix_walmart': "", 'prix_tigre_geant': "", 'prix_dollarama': "", 'prix_provigo': ""
            }
            st.session_state['df_produits'] = pd.concat([st.session_state['df_produits'], pd.DataFrame([nouvelle_ligne])], ignore_index=True)
            if sauvegarder_donnees(st.session_state['df_produits']):
                st.success("🎉 Produit ajouté !")
                time.sleep(1)
                st.rerun()

# 6. AFFICHAGE DE LA FICHE DÉTAILLÉE CONSOMMATEUR
if resultats is not None and not resultats.empty:
    row = resultats.iloc[0]
    index_produit_reel = resultats.index[0]
    
    prov = str(row.get('entreprise_province_etat', '')).strip()
    pays = str(row.get('entreprise_pays', '')).strip()
    
    if "québec" in prov.lower():
        couleur_boite, couleur_texte = "#e1f5fe", "#0d47a1"
        verdict = "⚜️ PRODUIT QUÉBÉCOIS"
    elif "canada" in pays.lower():
        couleur_boite, couleur_texte = "#e8f5e9", "#1b5e20"
        verdict = "🍁 PRODUIT CANADIEN"
    else:
        couleur_boite, couleur_texte = "#fafafa", "#424242"
        verdict = "🌍 PROPRIÉTÉ ÉTRANGÈRE"

    bloc_prix_html = f"""
    <div style="margin: 10px 0; display: flex; gap: 10px; flex-wrap: wrap;">
    <span style="font-size: 16px; font-weight: bold; background-color: #ffffff; padding: 6px 12px; border: 2px solid #d32f2f; border-radius: 5px;">🔴 IGA : {row.get('prix_iga', 'Non inscrit')}</span>
    <span style="font-size: 16px; font-weight: bold; background-color: #ffffff; padding: 6px 12px; border: 2px solid #0056b3; border-radius: 5px;">🔵 SUPER C : {row.get('prix_super_c', 'Non inscrit')}</span>
    <span style="font-size: 16px; font-weight: bold; background-color: #ffffff; padding: 6px 12px; border: 2px solid #f9d71c; border-radius: 5px;">🟡 MAXI : {row.get('prix_maxi', 'Non inscrit')}</span>
    <span style="font-size: 16px; font-weight: bold; background-color: #ffffff; padding: 6px 12px; border: 2px solid #28a745; border-radius: 5px;">🟢 METRO : {row.get('prix_metro', 'Non inscrit')}</span>
    </div>
    """

    st.html(f"""
    <div style="background-color: {couleur_boite}; padding: 22px; border-radius: 10px; border-left: 12px solid {couleur_texte}; margin-bottom: 15px;">
        <h3 style="color: {couleur_texte}; margin-top: 0;">{verdict}</h3>
        <p style="font-size: 22px; font-weight: bold;">📦 {row.get('nom', 'Sans nom')}</p>
        {bloc_prix_html}
    </div>
    """)

    # Formulaire de collaboration des prix
    with st.form("formulaire_prix_epicerie"):
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        nouveau_iga = col_p1.text_input("Prix IGA ($) :", value=row.get('prix_iga', ''))
        nouveau_super_c = col_p2.text_input("Prix Super C ($) :", value=row.get('prix_super_c', ''))
        nouveau_maxi = col_p3.text_input("Prix Maxi ($) :", value=row.get('prix_maxi', ''))
        nouveau_metro = col_p4.text_input("Prix Metro ($) :", value=row.get('prix_metro', ''))
        
        bouton_soumettre = st.form_submit_button("💾 Enregistrer la grille de prix", type="primary", use_container_width=True)

    if bouton_soumettre:
        st.session_state['df_produits'].at[index_produit_reel, 'prix_iga'] = nouveau_iga.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_super_c'] = nouveau_super_c.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_maxi'] = nouveau_maxi.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_metro'] = nouveau_metro.strip()

        if sauvegarder_donnees(st.session_state['df_produits']):
            st.success("Mise à jour réussie !")
            time.sleep(1)
            st.rerun()

st.caption(f"Filtre d'affichage actif : Enseigne sélectionnée -> **{banniere.upper()}**")
