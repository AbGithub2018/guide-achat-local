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
    2. **Identifiez la provenance :** Repérez les drapes et badges (Québec ⚜️, Canada 🍁).
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

input("👉 TAPEZ UN NOM DE PRODUIT OU UN CODE CUP :", key="recherche_cup")
    if saisie:
        saisie_net = saisie.strip()

# 4. ZONE DE RECHERCHE ET SCANNER PHOTO
onglet_clavier, onglet_camera = st.tabs(["⌨️ Recherche manuelle", "📷 Scanner un Code-Barres"])

saisie_net = ""

with onglet_clavier:
    saisie = st.text_input("👉 TAPEZ UN NOM DE PRODUIT OU UN CODE CUP :", key="recherche_cup")
    if saisie:
        saisie_net = saisie.strip()

with onglet_camera:
    st.write("📷 **Alignez le code-barres** au centre de la caméra de votre téléphone pour le numériser en temps réel :")
    try:
        from streamlit_qrcode_scanner import qr_scanner
        # Déclenche un scan vidéo continu en utilisant la caméra arrière du mobile
        code_scanne = qr_scanner(key="scanner_live_achat_quebec")
        
        if code_scanne:
            saisie_net = str(code_scanne).strip()
            st.success(f"✅ Code CUP détecté au vol : {saisie_net}")
            time.sleep(0.5)
            st.rerun()
    except Exception as e:
        st.error(f"❌ Impossible de démarrer le lecteur vidéo en direct : {e}")

resultats = None
message_erreur_recherche = None

# --- CETTE LOGIQUE DE RECHERCHE DOIT RESTER ICI POUR LE CLAVIER ---
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

# --- SECTION LOGIQUE : AFFICHAGE DU TABLEAU OU DU MESSAGE D'ERREUR ---
selection_tableau = None 

# CAS A : L'utilisateur n'a rien écrit dans la case -> On montre la liste complète par défaut
if not saisie_net:
    selection_tableau = st.dataframe(
        df_affichage,
        column_config=config_colonnes,
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key="tableau_consommateur"
    )

# CAS B : L'utilisateur a fait une recherche et on a des résultats -> On montre la liste filtrée
elif not df_filtre.empty and len(df_filtre) < len(df):
    selection_tableau = st.dataframe(
        df_affichage,
        column_config=config_colonnes,
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key="tableau_consommateur"
    )

# CAS C : La recherche ne donne RIEN -> On masque complètement le tableau de 10 440 lignes
else:
    if message_erreur_recherche and not saisie_net.strip().isdigit():
        st.warning(message_erreur_recherche)

    # Le formulaire collaboratif s'ouvre UNIQUE et SEULEMENT si c'est un code CUP numérique inconnu
    if saisie_net.strip().isdigit() and len(saisie_net.strip()) >= 10:
        st.info(f"📦 Le code CUP **{saisie_net}** semble être un nouveau produit pas encore répertorié.")
        st.write("Devenez le premier à l'ajouter pour la communauté Achat Québec ! 🇨🇦")
        
        with st.form(key="formulaire_nouveau_produit", clear_on_submit=True):
            nom_nouveau = st.text_input("Nom exact du produit (ex: Fraises du Québec 1L)")
            cup_final = st.text_input("Code CUP", value=saisie_net.strip(), disabled=True)
            entreprise = st.text_input("Entreprise propriétaire / Marque (ex: Unico)")
            province = st.text_input("Province / État (ex: Québec)")
            pays = st.text_input("Pays", value="Canada")
            distribution = st.text_input("Réseau d'épicerie (ex: IGA, Maxi, Metro, Super C)")
            
            st.write("---")
            st.write("**Entrez les prix constatés en magasin (optionnel) :**")
            col1, col2, col3, col4 = st.columns(4)
            with col1: prix_iga = st.text_input("Prix IGA ($)", value="")
            with col2: prix_superc = st.text_input("Prix Super C ($)", value="")
            with col3: prix_maxi = st.text_input("Prix Maxi ($)", value="")
            with col4: prix_metro = st.text_input("Prix Metro ($)", value="")
            
            bouton_creer = st.form_submit_button("🚀 Enregistrer le nouveau produit dans le Nuage", type="primary", use_container_width=True)
            
            if bouton_creer:
                if nom_nouveau:
                    with st.spinner("Enregistrement de la nouvelle fiche produit..."):
                        try:
                            p_iga_val = prix_iga.strip() if prix_iga.strip() else "Non inscrit"
                            p_super_c_val = prix_superc.strip() if prix_superc.strip() else "Non inscrit"
                            p_maxi_val = prix_maxi.strip() if prix_maxi.strip() else "Non inscrit"
                            p_metro_val = prix_metro.strip() if prix_metro.strip() else "Non inscrit"
                            
                            nouvelle_ligne = {
                                'code_upc': cup_final,
                                'nom': nom_nouveau.strip(),
                                'entreprise_proprietaire': entreprise.strip(),
                                'entreprise_province_etat': province.strip(),
                                'entreprise_pays': pays.strip(),
                                'distribution': distribution.strip(),
                                'prix_iga': p_iga_val,
                                'prix_super_c': p_super_c_val,
                                'prix_maxi': p_maxi_val,
                                'prix_metro': p_metro_val
                            }
                            
                            import pandas as pd
                            st.session_state['df_produits'] = pd.concat([st.session_state['df_produits'], pd.DataFrame([nouvelle_ligne])], ignore_index=True)
                            
                            if sauvegarder_donnees(st.session_state['df_produits']):
                                st.success(f"🎉 Un grand merci ! Le produit '{nom_nouveau}' a été ajouté avec succès.")
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erreur lors de l'enregistrement : {e}")
                else:
                    st.error("⚠️ Le Nom du produit est obligatoire pour valider la fiche.")

# Détection de la ligne cliquée dans le tableau interactif
if selection_tableau and "rows" in selection_tableau["selection"] and selection_tableau["selection"]["rows"] and 'code_upc' in df_affichage.columns:
    index_ligne_cliquee = selection_tableau["selection"]["rows"][0]
    cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
    resultats = df[df['code_upc'] == cup_selectionne]

# 6. AFFICHAGE DE LA FICHE DÉTAILLÉE CONSOMMATEUR
if resultats is not None and not resultats.empty:
    st.markdown("---")
    index_produit_reel = resultats.index[0]
    row = resultats.iloc[0]
    
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
