import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURATION ET STYLE VISUEL DE LA PAGE
st.set_page_config(page_title="Acheter Québécois & Canadien", page_icon="📦", layout="wide")

# Injection CSS pour la barre de recherche géante
st.html("""
<style>
    .stTextInput label p { font-size: 24px !important; font-weight: bold !important; color: #003366 !important; }
    .stTextInput input { font-size: 26px !important; padding: 15px !important; height: 65px !important; font-weight: bold !important; letter-spacing: 2px !important; }
</style>
""")

def charger_donnees():
    """Se connecte automatiquement au Google Sheet grâce aux secrets de Streamlit Cloud."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
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
# 2. BARRE LATERALE (Statistiques et Filtres Géopolitiques)
st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 22px;'>🌐 Filtrer les produits par pays d'origine</h2>")

if 'entreprise_pays' in df.columns:
    pass
    # repartition_pays = df['entreprise_pays'].value_counts()
    # st.sidebar.write("**Origine financière de vos produits :**")
    # st.sidebar.bar_chart(repartition_pays)

st.sidebar.markdown("---")

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

# 3. ZONE PRINCIPALE : Entête
st.html("<h1 style='text-align: center; color: #003366; font-family: sans-serif;'>⚜️ MON GUIDE D'ACHAT LOCAL 🍁</h1>")
st.html("<p style='text-align: center; font-size: 16px; color: #666;'>Scannez un code-barres pour valider l'origine et gérer vos prix d'épicerie.</p>")

with st.expander("ℹ️ Comment utiliser l'application et économiser ? (Cliquez pour ouvrir)"):
    st.markdown("""
    ### 🛒 Protégeons notre portefeuille, encourageons l'achat local !
    Bienvenue sur **AchatQuébec**, votre outil citoyen et collaborative pour dénicher les meilleurs prix à l'épicerie tout en gardant notre argent ici. Ensemble, reprenons le contrôle de notre panier d'épicerie !
    
    #### 🕵️‍♂️ Comment ça fonctionne ?
    1. **Recherchez un produit :** Tapez un mot-clé (ex: *pomme*) ou le code CUP.
    2. **Identifiez la provenance :** Repérez les drapeaux et badges (Québec ⚜️, Canada 🍁).
    3. **Comparez les prix :** Voyez d'un coup d'œil quelle bannière est la moins chère.
    
    #### ✍️ Devenez un consommateur solidaire !
    Vous êtes à l'épicerie ? Cochez le produit, inscrivez le prix trouvé dans le formulaire gris au bas de l'écran, et cliquez sur **Enregistrer**. Chaque contribution aide la communauté !
    """)

# Boutons rapides de sélection de bannières
st.markdown("### 🏪 Choix rapide de votre bannière d'épicerie :")
col_iga, col_maxi, col_metro, col_super_c, col_walmart, col_tous = st.columns(6)

if col_iga.button("🔴 IGA", use_container_width=True):
    st.session_state['banniere_active'] = "IGA"
if col_maxi.button("🟡 Maxi", use_container_width=True):
    st.session_state['banniere_active'] = "Maxi"
if col_metro.button("🟢 Metro", use_container_width=True):
    st.session_state['banniere_active'] = "Metro"
if col_super_c.button("🔵 Super C", use_container_width=True):
    st.session_state['banniere_active'] = "Super_C"
if col_walmart.button("🔵 Walmart", use_container_width=True):
    st.session_state['banniere_active'] = "Walmart"
if col_tous.button("🔄 Toutes", use_container_width=True):
    st.session_state['banniere_active'] = "Tous"

banniere = st.session_state['banniere_active']

if banniere != "Tous" and 'distribution' in df_filtre.columns:
    nom_banniere_recherche = banniere.replace('_', ' ')
    condition_distribution = df_filtre['distribution'].str.lower().str.contains(nom_banniere_recherche.lower(), na=False)
    df_filtre = df_filtre[condition_distribution]

# 4. ZONE DE RECHERCHE ET SCANNER VIDÉO EN DIRECT (100% GRATUIT)
import streamlit.components.v1 as components

st.markdown("### 🔍 Rechercher ou Scanner un produit")
onglet_clavier, onglet_camera = st.tabs(["⌨️ Recherche manuelle", "📷 Scanner en direct"])

saisie_net = ""

with onglet_clavier:
    saisie = st.text_input("👉 TAPEZ UN NOM DE PRODUIT OU UN CODE CUP :", key="recherche_cup")
    if saisie:
        saisie_net = saisie.strip()

with onglet_camera:
    st.write("💡 Placez le code-barres devant la caméra. Le scan est automatique.")
    
    # Code du scanner vidéo en direct (Open-Source / Gratuit)
    scanner_html = """
    <div id="interactive" class="viewport" style="width: 100%; height: 300px; background-color: #000; border-radius: 10px; overflow: hidden;"></div>
    <script src="https://cloudflare.com"></script>
    <script>
        // On écoute le signal pour envoyer la valeur à Streamlit
        function envoyerCode(code) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: code
            }, '*');
        }

        Quagga.init({
            inputStream : {
                name : "Live",
                type : "LiveStream",
                target: document.querySelector('#interactive'),
                constraints: {
                    facingMode: "environment" // Force la caméra arrière du téléphone
                }
            },
            decoder : {
                readers : ["upc_reader", "upc_e_reader", "ean_reader"] // Formats d'épicerie standard
            }
        }, function(err) {
            if (err) { console.log(err); return }
            Quagga.start();
        });

        Quagga.onDetected(function(data) {
            var code = data.codeResult.code;
            envoyerCode(code);
        });
    </script>
    """
    # Affichage du composant caméra dans la page
    code_scanne = components.html(scanner_html, height=320)
    
    if code_scanne:
        saisie_net = str(code_scanne).strip()
        st.success(f"✅ Code CUP détecté en direct : {saisie_net}")

resultats = None
message_erreur_recherche = None

if saisie_net:


    try:
        cup_saisi = str(int(float(saisie_net))).strip()
    except ValueError:
        cup_saisi = saisie_net

    if 'code_upc' in df_filtre.columns:
        recherche_cup = df_filtre[df_filtre['code_upc'] == cup_saisi]
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
                    message_erreur_recherche = f"⚠️ Aucun produit ne correspond à '{saisie_net}' dans cette sélection."
# 5. CONFIGURATION ET RENDU DU TABLEAU INTERACTIF
colonnes_prix_tableau = ['prix_iga', 'prix_super_c', 'prix_maxi', 'prix_metro']
colonnes_dispo = [c for c in ['code_upc', 'nom', 'entreprise_proprietaire', 'entreprise_province_etat', 'distribution'] if c in df_filtre.columns]
df_affichage = df_filtre[colonnes_dispo + [c for c in colonnes_prix_tableau if c in df_filtre.columns]].copy()

for c in df_affichage.columns:
    df_affichage[c] = df_affichage[c].astype(str).replace('nan', '')

config_colonnes = {
    "code_upc": st.column_config.TextColumn("Code CUP", width="medium"),
    "nom": st.column_config.TextColumn("Nom du produit", width="large"),
    "entreprise_proprietaire": st.column_config.TextColumn("Entreprise"),
    "entreprise_province_etat": st.column_config.TextColumn("Province/État"),
    "distribution": st.column_config.TextColumn("Réseau d'épicerie"),
    "prix_iga": st.column_config.TextColumn("Prix IGA"),
    "prix_super_c": st.column_config.TextColumn("Prix Super C"),
    "prix_maxi": st.column_config.TextColumn("Prix Maxi"),
    "prix_metro": st.column_config.TextColumn("Prix Metro")
}

st.markdown("---")
st.markdown(f"### 📋 Liste des produits ({len(df_affichage)} affichés selon vos bannières et filtres) :")
st.write("💡 Cliquez n'importe où sur la ligne d'un produit pour voir sa fiche complète ci-dessous.")

if message_erreur_recherche:
    st.warning(message_erreur_recherche)

selection_tableau = st.dataframe(
    df_affichage,
    column_config=config_colonnes,
    use_container_width=True,
    hide_index=True,
    selection_mode="single-row",
    on_select="rerun",
    key="tableau_consommateur"
)

if selection_tableau and "rows" in selection_tableau["selection"] and selection_tableau["selection"]["rows"] and 'code_upc' in df_affichage.columns:
    index_ligne_cliquee = selection_tableau["selection"]["rows"][0]
    cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
    resultats = df[df['code_upc'] == cup_selectionne]

# 6. AFFICHAGE DE LA FICHE DÉTAILLÉE CONSOMMATEUR
if resultats is not None and not resultats.empty:
    st.markdown("---")
    index_produit_reel = resultats.index[0]
    row = resultats.iloc[0]  # Correction ici pour extraire proprement la ligne
    
    prov = str(row.get('entreprise_province_etat', '')).strip()
    pays = str(row.get('entreprise_pays', '')).strip()
    
    if "québec" in prov.lower():
        couleur_boite, couleur_texte = "#e1f5fe", "#0d47a1"
        verdict = "⚜️ PRODUIT QUÉBÉCOIS (Décisions et Siège au Québec)"
    elif "canada" in pays.lower():
        couleur_boite, couleur_texte = "#e8f5e9", "#1b5e20"
        verdict = "🍁 PRODUIT CANADIEN (Décisions au Canada)"
    else:
        couleur_boite, couleur_texte = "#fafafa", "#424242"
        verdict = "🌍 PROPRIÉTÉ ÉTRANGÈRE (L'argent quitte le pays)"

    p_iga = str(row.get('prix_iga', '')).strip()
    p_super_c = str(row.get('prix_super_c', '')).strip()
    p_maxi = str(row.get('prix_maxi', '')).strip()
    p_metro = str(row.get('prix_metro', '')).strip()
    
    affichage_iga = p_iga if p_iga and p_iga.lower() != "nan" else "Non inscrit"
    affichage_super_c = p_super_c if p_super_c and p_super_c.lower() != "nan" else "Non inscrit"
    affichage_maxi = p_maxi if p_maxi and p_maxi.lower() != "nan" else "Non inscrit"
    affichage_metro = p_metro if p_metro and p_metro.lower() != "nan" else "Non inscrit"
    
    usine_actuelle = row.get('lieu_usine', row.get('usine_principale', 'À déterminer'))

    bloc_prix_html = f"""
    <div style="margin: 10px 0; display: flex; gap: 10px; flex-wrap: wrap;">
        <span style="font-size: 16px; font-weight: bold; background-color: #ffffff; padding: 6px 12px; border: 2px solid #d32f2f; border-radius: 5px; color: #1a1a1a;">🔴 IGA : {affichage_iga}</span>
        <span style="font-size: 16px; font-weight: bold; background-color: #ffffff; padding: 6px 12px; border: 2px solid #0056b3; border-radius: 5px; color: #1a1a1a;">🔵 SUPER C : {affichage_super_c}</span>
        <span style="font-size: 16px; font-weight: bold; background-color: #ffffff; padding: 6px 12px; border: 2px solid #f9d71c; border-radius: 5px; color: #1a1a1a;">🟡 MAXI : {affichage_maxi}</span>
        <span style="font-size: 16px; font-weight: bold; background-color: #ffffff; padding: 6px 12px; border: 2px solid #28a745; border-radius: 5px; color: #1a1a1a;">🟢 METRO : {affichage_metro}</span>
    </div>
    """

    st.html(f"""
    <div style="background-color: {couleur_boite}; padding: 22px; border-radius: 10px; border-left: 12px solid {couleur_texte}; margin-bottom: 15px; font-family: Arial, sans-serif;">
        <h3 style="color: {couleur_texte}; margin-top: 0; font-size: 22px;">{verdict}</h3>
        <p style="font-size: 22px; font-weight: bold; margin-bottom: 5px; color: #1a1a1a;">📦 {row.get('nom', 'Produit sans nom')}</p>
        <p style="font-size: 24px; color: #d32f2f; font-weight: bold; background-color: #ffffff; display: inline-block; padding: 4px 12px; border-radius: 5px; border: 2px solid #d32f2f; margin: 5px 0;">🔢 CUP : {row.get('code_upc', 'Inconnu')}</p>
        {bloc_prix_html}
        <hr style="margin: 15px 0; border: 0; border-top: 1px solid #ccc;">
        <table style="width: 100%; font-size: 17px; color: #333; line-height: 1.8; border-collapse: collapse;">
            <tr><td style="width: 25%; padding: 4px 0;"><b>🏢 Compagnie :</b></td><td><b>{row.get('entreprise_proprietaire', 'À déterminer')}</b></td></tr>
            <tr><td style="padding: 4px 0;"><b>📍 Siège social :</b></td><td>{prov} ({pays})</td></tr>
            <tr><td style="padding: 4px 0;"><b>🏭 Usine principale :</b></td><td>{usine_actuelle}</td></tr>
            <tr><td style="padding: 4px 0;"><b>🏪 Réseau d'épicerie :</b></td><td>{row.get('distribution', 'Général')}</td></tr>
        </table>
    </div>
    """)

    st.markdown("#### 📝 Collaborer à la mise à jour des prix en direct au Québec :")
    with st.form("formulaire_prix_epicerie"):
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        
        nouveau_iga = col_p1.text_input("Prix IGA ($) :", value=p_iga if p_iga.lower() != "nan" else "", key="edit_iga")
        nouveau_super_c = col_p2.text_input("Prix Super C ($) :", value=p_super_c if p_super_c.lower() != "nan" else "", key="edit_super_c")
        nouveau_maxi = col_p3.text_input("Prix Maxi ($) :", value=p_maxi if p_maxi.lower() != "nan" else "", key="edit_maxi")
        nouveau_metro = col_p4.text_input("Prix Metro ($) :", value=p_metro if p_metro.lower() != "nan" else "", key="edit_metro")
        
        bouton_soumettre = st.form_submit_button("💾 Enregistrer la grille de prix en direct dans le Nuage", type="primary", use_container_width=True)

    if bouton_soumettre:
        st.session_state['df_produits'].at[index_produit_reel, 'prix_iga'] = nouveau_iga.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_super_c'] = nouveau_super_c.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_maxi'] = nouveau_maxi.strip()
        st.session_state['df_produits'].at[index_produit_reel, 'prix_metro'] = nouveau_metro.strip()
        
        if sauvegarder_donnees(st.session_state['df_produits']):
            st.success("Base de données collaborative mise à jour avec succès !")
            time.sleep(1)
            st.rerun()

st.caption(f"Filtre d'affichage actif : Enseigne sélectionnée -> **{banniere.upper()}**")
