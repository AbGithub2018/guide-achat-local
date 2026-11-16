import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# Configuration de la page d'administration en mode LARGE
st.set_page_config(
    page_title="Espace Modérateur - Achat Québécois",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Espace d'Administration et Validation")
st.markdown("Bienvenue dans votre zone de quarantaine. Validez ou rejetez ici les propositions des utilisateurs avant leur mise en ligne dans le catalogue principal.")
st.markdown("---")

# Connexion unique à Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

if "admin_prive_connecte" not in st.session_state:
    st.session_state["admin_prive_connecte"] = False

if not st.session_state["admin_prive_connecte"]:
    st.subheader("🔑 Connexion sécurisée requise")
    mdp_saisi = st.text_input("Veuillez entrer votre mot de passe d'administrateur :", type="password", key="prive_mdp")
    
    if st.button("Se connecter", type="primary", use_container_width=True):
        if mdp_saisi == st.secrets["admin"]["password"]:
            st.session_state["admin_prive_connecte"] = True
            st.success("Connexion réussie !")
            time.sleep(1)
            st.rerun()
        else:
            st.error("⚠️ Mot de passe incorrect.")
    st.stop()

# --- CODE EXÉCUTÉ UNIQUEMENT SI CONNECTÉ ---
st.sidebar.success("🟢 Mode Administrateur Actif")
if st.sidebar.button("🔴 Se déconnecter", use_container_width=True):
    st.session_state["admin_prive_connecte"] = False
    st.rerun()

# 1. Chargement des onglets cloud indispensables et lissage des colonnes
try:
    df_sheet1 = conn.read(worksheet="Sheet1", ttl=0)
    df_sheet1.columns = [str(c).strip().lower() for c in df_sheet1.columns]
    
    df_historique = conn.read(worksheet="Historique_Prix", ttl=0)
    df_historique.columns = [str(c).strip().lower() for c in df_historique.columns]

    df_deals = conn.read(worksheet="Deals_Extra", ttl=0)
    df_deals.columns = [str(c).strip().lower() for c in df_deals.columns]
except Exception as e:
    st.error(f"❌ Erreur lors de la synchronisation avec Google Sheets : {e}")
    st.stop()

# 2. Séparation de la file d'attente en quatre onglets visuels larges
onglet_nouveaux, onglet_prix, onglet_photos, onglet_deals = st.tabs([
    "✨ Nouveaux produits à ajouter", 
    "💰 Prix suggérés à corriger",
    "📸 Photos à valider",
    "🔥 Deals Extra (Communauté)"
])
# =====================================================================
# GESTION DES NOUVEAUX PRODUITS (Onglet 1)
# =====================================================================
with onglet_nouveaux:
    if df_historique.empty:
        st.info("L'historique est complètement vide.")
    else:
        df_nouveaux_attente = df_historique[df_historique['source'].str.startswith("PROPOSITION_NOUVEAU:", na=False)]
        
        if df_nouveaux_attente.empty:
            st.success("🎉 Aucun nouveau produit en attente de validation.")
        else:
            st.warning(f"Il y a {len(df_nouveaux_attente)} proposition(s) de création de produit en attente.")
            
            for idx, ligne_h in df_nouveaux_attente.iterrows():
                texte_source = str(ligne_h['source'])
                cup_h = str(ligne_h['code_upc']).strip()
                dist_h = str(ligne_h['distribution']).strip()
                prix_h = str(ligne_h['prix']).strip()
                
                try:
                    infos_decoupees = texte_source.replace("PROPOSITION_NOUVEAU:", "").split("|")
                    v_nom = infos_decoupees[0].replace("Nom:", "").strip() if len(infos_decoupees) > 0 else "Inconnu"
                    v_marque = infos_decoupees[1].replace("Marque:", "").strip() if len(infos_decoupees) > 1 else ""
                    v_prov = infos_decoupees[2].replace("Province:", "").strip() if len(infos_decoupees) > 2 else ""
                    v_pays = infos_decoupees[3].replace("Pays:", "").strip() if len(infos_decoupees) > 3 else "Canada"
                except Exception:
                    v_nom, v_marque, v_prov, v_pays = texte_source, "", "", "Canada"
                
                with st.container(border=True):
                    st.markdown(f"### 📦 Proposition de fiche : **{v_nom}**")
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.markdown(f"**Code-barres (UPC) :** `{cup_h}`")
                        st.markdown(f"**Marque / Entreprise :** {v_marque}")
                    with col_info2:
                        st.markdown(f"**Provenance :** {v_prov} ({v_pays})")
                        st.markdown(f"**Prix initial constaté :** {prix_h}$ chez **{dist_h}**")
                    
                    c_valider, c_rejeter = st.columns(2)
                    
                    if c_valider.button("🟢 Accepter & Ajouter au catalogue", key=f"btn_val_prod_{idx}", use_container_width=True):
                        nouvelle_ligne_sheet1 = {col.strip().lower(): "" for col in df_sheet1.columns}
                        nouvelle_ligne_sheet1['code_upc'] = cup_h
                        nouvelle_ligne_sheet1['nom'] = v_nom
                        nouvelle_ligne_sheet1['entreprise_proprietaire'] = v_marque
                        nouvelle_ligne_sheet1['entreprise_province_etat'] = v_prov
                        nouvelle_ligne_sheet1['entreprise_pays'] = v_pays
                        nouvelle_ligne_sheet1['distribution'] = dist_h
                        
                        colonne_prix_cible = f"prix_{dist_h.lower().replace(' ', '_')}"
                        if colonne_prix_cible in nouvelle_ligne_sheet1:
                            nouvelle_ligne_sheet1[colonne_prix_cible] = prix_h
                        
                        df_sheet1_maj = pd.concat([df_sheet1, pd.DataFrame([nouvelle_ligne_sheet1])], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=df_sheet1_maj)
                        
                        df_historique.loc[idx, 'source'] = f"APPROUVE_OK: {texte_source}"
                        conn.update(worksheet="Historique_Prix", data=df_historique)
                        
                        st.success(f"🎉 Le produit '{v_nom}' a été ajouté avec succès !")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                        
                    if c_rejeter.button("❌ Rejeter la proposition", key=f"btn_rej_prod_{idx}", use_container_width=True):
                        df_historique.loc[idx, 'source'] = f"REFUSE_REJETE: {texte_source}"
                        conn.update(worksheet="Historique_Prix", data=df_historique)
                        st.error("Proposition écartée.")
                        time.sleep(1)
                        st.rerun()

# =====================================================================
# GESTION DES PRIX SUGGÉRÉS (Onglet 2)
# =====================================================================
with onglet_prix:
    if df_historique.empty:
        st.info("L'historique est complètement vide.")
    else:
        source_securisee = df_historique['source'].fillna("").astype(str)
        df_prix_attente = df_historique[
            (source_securisee == 'PROPOSITION_PRIX') & 
            (~source_securisee.str.startswith("APPROUVE_")) & 
            (~source_securisee.str.startswith("REFUSE_"))
        ]
        
        if df_prix_attente.empty:
            st.success("🎉 Aucun correctif de prix en attente de validation.")
        else:
            st.warning(f"Il y a {len(df_prix_attente)} proposition(s) de prix à réviser.")
            
            for idx, ligne_pr in df_prix_attente.iterrows():
                cup_pr = str(ligne_pr['code_upc']).strip()
                nouveau_prix = str(ligne_pr['prix']).strip()
                colonne_cible = str(ligne_pr['distribution']).strip()
                horodatage_pr = str(ligne_pr['horodatage'])
                
                with st.container(border=True):
                    st.markdown(f"### 💰 Proposition de nouveau prix")
                    st.markdown(f"**Produit / Clé Source (UPC ou Nom) :** `{cup_pr}`")
                    st.markdown(f"**Enseigne concernée (colonne) :** `{colonne_cible}`")
                    st.markdown(f"**Prix suggéré par l'utilisateur :** {nouveau_prix} $")
                    st.markdown(f"**Soumis le :** {horodatage_pr}")
                    
                    c_pr_valider, c_pr_rejeter = st.columns(2)
                    
                    if c_pr_valider.button("✅ Appliquer ce prix", key=f"btn_val_prix_unique_{idx}", use_container_width=True):
                        idx_produit = None
                        methode_trouvee = ""
                        
                        df_sheet1_prive = df_sheet1.copy()
                        df_sheet1_prive['code_upc_clean'] = df_sheet1_prive['code_upc'].fillna("").astype(str).str.strip()
                        df_sheet1_prive['nom_clean'] = df_sheet1_prive['nom'].fillna("").astype(str).str.strip().str.lower()
                        
                        match_upc = df_sheet1_prive[df_sheet1_prive['code_upc_clean'] == cup_pr].index
                        if not match_upc.empty:
                            idx_produit = match_upc
                            methode_trouvee = "le code UPC"
                        else:
                            match_nom = df_sheet1_prive[df_sheet1_prive['nom_clean'] == cup_pr.lower()].index
                            if not match_nom.empty:
                                idx_produit = match_nom
                                methode_trouvee = "le nom du produit"
                                
                        if idx_produit is not None:
                            try:
                                if colonne_cible in df_sheet1.columns:
                                    df_sheet1.loc[idx_produit, colonne_cible] = nouveau_prix
                                    conn.update(worksheet="Sheet1", data=df_sheet1)
                                    df_historique.loc[idx, 'source'] = "APPROUVE_PRIX"
                                    conn.update(worksheet="Historique_Prix", data=df_historique)
                                    
                                    st.cache_data.clear()
                                    st.success(f"🎉 Prix mis à jour avec succès via {methode_trouvee} !")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error(f"La colonne '{colonne_cible}' n'existe pas dans l'onglet Sheet1.")
                            except Exception as e:
                                st.error(f"⚠️ Erreur lors de la synchronisation Cloud : {e}")
                        else:
                            st.error("⚠️ Impossible de lier ce prix à un produit existant (Vérifiez l'UPC ou le Nom).")
                            
                    if c_pr_rejeter.button("❌ Rejeter", key=f"btn_rej_prix_unique_{idx}", use_container_width=True):
                        df_historique.loc[idx, 'source'] = "REFUSE_PRIX"
                        conn.update(worksheet="Historique_Prix", data=df_historique)
                        st.error("Proposition de prix rejetée.")
                        time.sleep(2)
                        st.rerun()
# =====================================================================
# GESTION DES PHOTOS UNIQUEMENT (Onglet 3)
# =====================================================================
with onglet_photos:
    if df_historique.empty:
        st.info("L'historique est complètement vide.")
    else:
        action_securisee = df_historique['source'].fillna("").astype(str)
        cup_historique_nettoye = df_historique['code_upc'].fillna("").astype(str).str.strip()
        
        df_photos_attente = df_historique[
            (action_securisee == 'modification_photo_cell') & 
            (cup_historique_nettoye != "") &
            (~action_securisee.str.startswith("APPROUVE_")) & 
            (~action_securisee.str.startswith("REFUSE_"))
        ]
        
        if df_photos_attente.empty:
            st.success("🎉 Aucune modification de photo en attente de validation.")
        else:
            st.warning(f"Il y a {len(df_photos_attente)} photo(s) soumise(s) à valider.")
            
            for idx, ligne_p in df_photos_attente.iterrows():
                cup_p = str(ligne_p['code_upc']).strip()
                url_photo = str(ligne_p['photo']).strip()
                horodatage_p = str(ligne_p['horodatage'])
                
                with st.container(border=True):
                    st.markdown(f"### 📸 Demande de mise à jour photo")
                    col_p_info, col_p_visuel = st.columns(2)
                    
                    with col_p_info:
                        st.markdown(f"**Recherche principale (UPC / Nom) :** `{cup_p}`")
                        st.markdown(f"**Soumis le :** {horodatage_p}")
                        st.write("")
                        
                        c_p_valider, c_p_rejeter = st.columns(2)
                        
                        if c_p_valider.button("✅ Valider & Appliquer", key=f"btn_val_photo_{idx}", use_container_width=True):
                            idx_produit = None
                            df_sheet1_prive = df_sheet1.copy()
                            if 'code_upc' in df_sheet1_prive.columns:
                                df_sheet1_prive['code_upc_clean'] = df_sheet1_prive['code_upc'].fillna("").astype(str).str.strip()
                            if 'nom' in df_sheet1_prive.columns:
                                df_sheet1_prive['nom_clean'] = df_sheet1_prive['nom'].fillna("").astype(str).str.strip().str.lower()
                            
                            if 'code_upc_clean' in df_sheet1_prive.columns:
                                match_upc = df_sheet1_prive[df_sheet1_prive['code_upc_clean'] == cup_p].index
                                if not match_upc.empty:
                                    idx_produit = match_upc
                            
                            if idx_produit is None and 'nom_clean' in df_sheet1_prive.columns:
                                match_nom = df_sheet1_prive[df_sheet1_prive['nom_clean'] == cup_p.lower()].index
                                if not match_nom.empty:
                                    idx_produit = match_nom
                            
                            if idx_produit is not None:
                                try:
                                    df_sheet1['photo'] = df_sheet1['photo'].astype(str)
                                    df_sheet1.loc[idx_produit, 'photo'] = url_photo
                                    conn.update(worksheet="Sheet1", data=df_sheet1)
                                    
                                    df_historique.loc[idx, 'source'] = "APPROUVE_PHOTO"
                                    conn.update(worksheet="Historique_Prix", data=df_historique)
                                    
                                    st.cache_data.clear()
                                    st.success(f"🎉 Image appliquée avec succès pour {cup_p} !")
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as error_sheets:
                                    st.error(f"⚠️ Erreur lors de la synchronisation Google Sheets : {error_sheets}")
                            else:
                                st.error(f"⚠️ Impossible de trouver '{cup_p}' dans le catalogue.")
                            
                        if c_p_rejeter.button("❌ Rejeter la photo", key=f"btn_rej_photo_{idx}", use_container_width=True):
                            df_historique.loc[idx, 'source'] = "REFUSE_PHOTO"
                            conn.update(worksheet="Historique_Prix", data=df_historique)
                            st.error("Changement de photo refusé.")
                            time.sleep(1)
                            st.rerun()
                                
                    with col_p_visuel:
                        if url_photo and url_photo.startswith("http"):
                            st.image(url_photo, caption=f"Aperçu pour : {cup_p}", use_container_width=True)
                        else:
                            st.error("⚠️ Aucun lien d'image valide pour ce scan.")

# =====================================================================
# GESTION DES DEALS EXTRA (Onglet 4)
# =====================================================================
with onglet_deals:
    if df_deals.empty or 'statut' not in df_deals.columns:
        st.info("Aucun Deal Extra soumis pour le moment.")
    else:
        statut_deal = df_deals['statut'].fillna("").astype(str).str.strip().str.upper()
        df_deals_attente = df_deals[statut_deal == "EN_ATTENTE"]
        
        if df_deals_attente.empty:
            st.success("🎉 Aucun Deal Extra en attente de validation.")
        else:
            st.warning(f"Il y a {len(df_deals_attente)} Deal(s) Extra soumis par la communauté à vérifier.")
            
            for idx, deal in df_deals_attente.iterrows():
                d_date = str(deal.get('date_soumission', '')).strip()
                d_pseudo = str(deal.get('pseudo', 'Anonyme')).strip()
                d_magasin = str(deal.get('magasin', '')).strip()
                d_ville = str(deal.get('ville', '')).strip()
                d_produit = str(deal.get('produit', '')).strip()
                d_prix = str(deal.get('prix', '')).strip()
                d_image = str(deal.get('lien_image', '')).strip()
                
                with st.container(border=True):
                    st.markdown(f"### 🔥 {d_produit} — **{d_prix} $** chez **{d_magasin}**")
                    col_d_info, col_d_visuel = st.columns([1.3, 1.0])
                    
                    with col_d_info:
                        st.markdown(f"**Ville / Succursale :** {d_ville}")
                        st.markdown(f"**Partagé par :** {d_pseudo}")
                        st.markdown(f"**Date :** {d_date}")
                        st.write("")
                        
                        c_d_valider, c_d_rejeter = st.columns(2)
                        if c_d_valider.button("✅ Publier le Deal", key=f"btn_val_deal_{idx}", use_container_width=True, type="primary"):
                            df_deals.loc[idx, 'statut'] = "APPROUVE"
                            conn.update(worksheet="Deals_Extra", data=df_deals)
                            st.cache_data.clear()
                            st.success("🎉 Deal Extra publié en direct sur l'application !")
                            time.sleep(1.5)
                            st.rerun()
                            
                        if c_d_rejeter.button("❌ Rejeter", key=f"btn_rej_deal_{idx}", use_container_width=True):
                            df_deals.loc[idx, 'statut'] = "REFUSE"
                            conn.update(worksheet="Deals_Extra", data=df_deals)
                            st.cache_data.clear()
                            st.error("Deal Extra rejeté.")
                            time.sleep(1.5)
                            st.rerun()
                            
                    with col_d_visuel:
                        if d_image and d_image.startswith("http"):
                            st.image(d_image, caption="Preuve photo soumise", use_container_width=True)
                        else:
                            st.caption("📷 Aucune photo jointe à cette trouvaille.")
