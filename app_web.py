import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
from PIL import Image

# Tentative d'importation de la bibliothèque de décodage d'image au CPU
try:
    from pyzbar.pyzbar import decode
except ImportError:
    decode = None

code_upc = "code_upc"

# 1. CONFIGURATION ET STYLE VISUEL DE LA PAGE
st.set_page_config(page_title="Acheter Québécois & Canadien", page_icon="📦", layout="wide")

st.html("""
<style>
    /* Grossir la barre de recherche géante */
    .stTextInput label p { font-size: 24px !important; font-weight: bold !important; color: #003366 !important; }
    .stTextInput input { font-size: 26px !important; padding: 15px !important; height: 65px !important; font-weight: bold !important; letter-spacing: 2px !important; }
    
    /* Grossir de façon spectaculaire les textes des boutons de sélection (Radio) */
    .stRadio label p { font-size: 26px !important; font-weight: bold !important; color: #111111 !important; }
    div[data-testid="stRadioHorizontal"] { gap: 40px !important; }
</style>
""")

def charger_donnees():
    """Se connecte automatiquement au Google Sheet grâce aux secrets de Streamlit Cloud."""
    try:
        conn = st.connection("gsheets", type="streamlit_gsheets.GSheetsConnection")
        df_initial = conn.read(worksheet="Sheet1")
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
        
        for col_prix in ['prix_iga', 'prix_super_c', 'prix_maxi', 'prix_metro']:
            if col_prix not in df_initial.columns:
                df_initial[col_prix] = ""
            df_initial[col_prix] = df_initial[col_prix].replace('nan', '').str.strip()
            
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

df = st.session_state['df_produits']

if 'banniere_active' not in st.session_state:
    st.session_state['banniere_active'] = "Tous"
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

# ZONE ADMINISTRATEUR
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

# 3. ZONE PRINCIPALE : Entête
st.html("<h1 style='text-align: center; color: #003366; font-family: sans-serif;'>⚜️ MON GUIDE D'ACHAT LOCAL 🍁</h1>")

# Boutons rapides de sélection de bannières
st.markdown("### 🏪 Choix rapide de votre bannière d'épicerie :")
col_iga, col_maxi, col_metro, col_super_c, col_walmart, col_tous = st.columns(6)
if col_iga.button("🔴 IGA", use_container_width=True): st.session_state['banniere_active'] = "IGA"
if col_maxi.button("🟡 Maxi", use_container_width=True): st.session_state['banniere_active'] = "Maxi"
if col_metro.button("🟢 Metro", use_container_width=True): st.session_state['banniere_active'] = "Metro"
if col_super_c.button("🔵 Super C", use_container_width=True): st.session_state['banniere_active'] = "Super_C"
if col_walmart.button("🔵 Walmart", use_container_width=True): st.session_state['banniere_active'] = "Walmart"
if col_tous.button("🔄 Toutes", use_container_width=True): st.session_state['banniere_active'] = "Tous"

banniere = st.session_state['banniere_active']

if banniere != "Tous" and 'distribution' in df_filtre.columns:
    nom_banniere_recherche = banniere.replace('_', ' ')
    df_filtre = df_filtre[df_filtre['distribution'].str.lower().str.contains(nom_banniere_recherche.lower(), na=False)]
# 4. MODE DE RECHERCHE
choix_mode = st.radio(
    "👉 MODE DE RECHERCHE :",
    ["⌨️ Recherche manuelle", "📸 Utiliser l'appareil photo du téléphone"],
    horizontal=True,
    label_visibility="collapsed"
)

saisie_net = ""

if choix_mode == "📸 Utiliser l'appareil photo du téléphone":
    st.html("<h3 style='color: #003366;'>📸 Scanner de code-barres intégré</h3>")
    photo_cam = st.camera_input("Prendre une photo du code-barres", label_visibility="collapsed")
    
    if photo_cam and decode is not None:
        try:
            img = Image.open(photo_cam)
            codes_detectes = decode(img)
            if codes_detectes:
                saisie_net = str(codes_detectes.data.decode("utf-8")).strip()
                st.success(f"🎯 Code détecté avec succès : {saisie_net}")
            else:
                st.warning("🔎 Aucun code-barres net n'a été détecté. Rapprochez-vous ou améliorez l'éclairage.")
        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")

valeur_par_defaut = saisie_net if saisie_net else ""
saisie = st.text_input("👉 TAPEZ UN NOM DE PRODUIT OU UN CODE-BARRES :", value=valeur_par_defaut, key="recherche_cup")    

if saisie:
    saisie_net = saisie.strip()

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
            recherche_texte = df_filtre[conditions]
            if not recherche_texte.empty:
                df_filtre = recherche_texte
                if len(recherche_texte) == 1:
                    resultats = recherche_texte
            else:
                message_erreur_recherche = f"⚠️ Aucun produit ne correspond à '{saisie_net}'."

# 5. CONFIGURATION ET RENDU DU TABLEAU INTERACTIF
colonnes_prix_tableau = ['prix_iga', 'prix_super_c', 'prix_maxi', 'prix_metro']
colonnes_dispo = [c for c in ['code_upc', 'nom', 'entreprise_proprietaire', 'entreprise_province_etat', 'distribution'] if c in df_filtre.columns]
df_affichage = df_filtre[colonnes_dispo + [c for c in colonnes_prix_tableau if c in df_filtre.columns]].copy()

for c in df_affichage.columns:
    df_affichage[c] = df_affichage[c].astype(str).replace('nan', '')

config_colonnes = {"code_upc": st.column_config.TextColumn("code_upc"), "nom": st.column_config.TextColumn("Nom du produit")}

st.markdown("---")
selection_tableau = st.dataframe(
    df_affichage, column_config=config_colonnes, use_container_width=True, hide_index=True,
    selection_mode="single-row", on_select="rerun", key="tableau_consommateur"
)

# Gestion de l'ajout collaboratif si code inconnu
if saisie_net.strip().isdigit() and len(saisie_net.strip()) >= 10 and (resultats is None or resultats.empty):
    st.info(f"📦 Le code_upc **{saisie_net}** semble être un nouveau produit pas encore répertorié.")
    with st.form(key="formulaire_nouveau_produit", clear_on_submit=True):
        nom_nouveau = st.text_input("Nom exact du produit")
        entreprise = st.text_input("Entreprise propriétaire / Marque")
        province = st.text_input("Province / État (ex: Québec)")
        pays = st.text_input("Pays", value="Canada")
        distribution = st.text_input("Réseau d'épicerie")
        
        if st.form_submit_button("🚀 Enregistrer dans le Nuage", type="primary", use_container_width=True):
            if nom_nouveau:
                nouvelle_ligne = {
                    'code_upc': saisie_net.strip(), 'nom': nom_nouveau.strip(), 'siege_social': entreprise.strip(),
                    'entreprise_province_etat': province.strip(), 'entreprise_pays': pays.strip(), 'distribution': distribution.strip(),
                    'prix_iga': "Non inscrit", 'prix_super_c': "Non inscrit", 'prix_maxi': "Non inscrit", 'prix_metro': "Non inscrit"
                }
                st.session_state['df_produits'] = pd.concat([st.session_state['df_produits'], pd.DataFrame([nouvelle_ligne])], ignore_index=True)
                if sauvegarder_donnees(st.session_state['df_produits']):
                    st.success("🎉 Produit ajouté !")
                    time.sleep(1)
                    st.rerun()

if selection_tableau and "rows" in selection_tableau["selection"] and selection_tableau["selection"]["rows"]:
    index_ligne_cliquee = selection_tableau["selection"]["rows"]
    if index_ligne_cliquee < len(df_affichage):
        cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
        resultats = df[df['code_upc'] == cup_selectionne]

# 6. AFFICHAGE DE LA FICHE SIGNALÉTIQUE DÉTAILLÉE
if resultats is not None and not resultats.empty:
    st.markdown("---")
    index_produit_reel = resultats.index
    row = resultats.iloc[0]
    prov = str(row.get('entreprise_province_etat', '')).strip()
    pays = str(row.get('entreprise_pays', '')).strip()

    if "québec" in prov.lower():
        c_boite, c_texte, verdict = "#e1f5fe", "#0d47a1", "⚜️ PRODUIT QUÉBÉCOIS (Décisions et Siège au Québec)"
    elif "canada" in pays.lower():
        c_boite, c_texte, verdict = "#e8f5e9", "#1b5e20", "🍁 PRODUIT CANADIEN (Décisions au Canada)"
    else:
        c_boite, c_texte, verdict = "#fafafa", "#424242", "🌍 PROPRIÉTÉ ÉTRANGÈRE (L'argent quitte le pays)"

    st.html(f"""
    <div style="background-color: {c_boite}; padding: 22px; border-radius: 10px; border-left: 12px solid {c_texte}; margin-bottom: 15px;">
        <h3 style="color: {c_texte}; margin-top: 0; font-size: 22px;">{verdict}</h3>
        <p style="font-size: 22px; font-weight: bold; color: #1a1a1a;">📦 {row.get('nom', 'Produit sans nom')}</p>
        <p style="font-size: 18px; color: #333;"><b>🏢 Compagnie :</b> {row.get('entreprise_proprietaire', 'À déterminer')}</p>
        <p style="font-size: 18px; color: #333;"><b>📍 Siège social :</b> {prov} ({pays})</p>
        <p style="font-size: 18px; color: #333;"><b>🏭 Usine :</b> {row.get('lieu_usine', 'À déterminer')}</p>
    </div>
    """)

    with st.form("formulaire_prix_epicerie"):
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        n_iga = col_p1.text_input("Prix IGA ($) :", value=str(row.get('prix_iga', '')))
        n_sc = col_p2.text_input("Prix Super C ($) :", value=str(row.get('prix_super_c', '')))
        n_mx = col_p3.text_input("Prix Maxi ($) :", value=str(row.get('prix_maxi', '')))
        n_mt = col_p4.text_input("Prix Metro ($) :", value=str(row.get('prix_metro', '')))
        
        if st.form_submit_button("💾 Enregistrer les prix", type="primary", use_container_width=True):
            st.session_state['df_produits'].at[index_produit_reel, 'prix_iga'] = n_iga.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_super_c'] = n_sc.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_maxi'] = n_mx.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_metro'] = n_mt.strip()
            if sauvegarder_donnees(st.session_state['df_produits']):
                st.success("Prix mis à jour !")
                time.sleep(1)
                st.rerun()

st.caption(f"Filtre d'affichage actif : Enseigne sélectionnée -> **{banniere.upper()}**")

