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

# 1. Chargement des deux onglets cloud indispensables et lissage des colonnes
try:
    df_sheet1 = conn.read(worksheet="Sheet1", ttl=0)
    df_sheet1.columns = [str(c).strip().lower() for c in df_sheet1.columns]
    
    df_historique = conn.read(worksheet="Historique_Prix", ttl=0)
    df_historique.columns = [str(c).strip().lower() for c in df_historique.columns]
except Exception as e:
    st.error(f"❌ Erreur lors de la synchronisation avec Google Sheets : {e}")
    st.stop()

# =====================================================================
# 2. Séparation de la file d'attente en trois onglets visuels larges
# =====================================================================
onglet_nouveaux, onglet_prix, onglet_photos = st.tabs([
    "✨ Nouveaux produits à ajouter", 
    "💰 Prix suggérés à corriger",
    "📸 Photos à valider"
])

# =====================================================================
# GESTION DES NOUVEAUX PRODUITS
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
# =====================================================================
# GESTION DES PHOTOS UNIQUEMENT (Onglet 3)
# =====================================================================
with onglet_photos:
    if df_historique.empty:
        st.info("L'historique est complètement vide.")
    else:
        # 1. Nettoyage et sécurisation des colonnes pivots pour le filtrage
        action_securisee = df_historique['source'].fillna("").astype(str)
        cup_historique_nettoye = df_historique['code_upc'].fillna("").astype(str).str.strip()
        
        # Filtre : modification_photo_cell et non traité
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
                # cup_p contient la valeur saisie (ex: "51500051962" ou "sundae syrup")
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
                        
                        # LOGIQUE BOUTON ACCEPTER
                        if c_p_valider.button("✅ Valider & Appliquer", key=f"btn_val_photo_{idx}", use_container_width=True):
                            idx_produit = None
                            methode_trouvee = ""
                            
                            # Préparation des colonnes de Sheet1 pour une comparaison propre
                            df_sheet1_prive = df_sheet1.copy()
                            if 'code_upc' in df_sheet1_prive.columns:
                                df_sheet1_prive['code_upc_clean'] = df_sheet1_prive['code_upc'].fillna("").astype(str).str.strip()
                            if 'nom' in df_sheet1_prive.columns:
                                df_sheet1_prive['nom_clean'] = df_sheet1_prive['nom'].fillna("").astype(str).str.strip().str.lower()
                            
                            # --- ÉTAPE 1 : Recherche principale par Code UPC ---
                            if 'code_upc_clean' in df_sheet1_prive.columns:
                                match_upc = df_sheet1_prive[df_sheet1_prive['code_upc_clean'] == cup_p].index
                                if not match_upc.empty:
                                    idx_produit = match_upc
                                    methode_trouvee = "le code UPC"
                            
                            # --- ÉTAPE 2 : Recherche secondaire par Nom (si UPC n'a rien donné) ---
                            if idx_produit is None and 'nom_clean' in df_sheet1_prive.columns:
                                match_nom = df_sheet1_prive[df_sheet1_prive['nom_clean'] == cup_p.lower()].index
                                if not match_nom.empty:
                                    idx_produit = match_nom
                                    methode_trouvee = "le nom du produit"
                            
                            # --- ÉTAPE 3 : Application de la modification si trouvé ---
                            if idx_produit is not None:
                                # SÉCURITÉ : On force la colonne 'photo' en type texte pour éviter l'erreur de type
                                if 'photo' in df_sheet1.columns:
                                    df_sheet1['photo'] = df_sheet1['photo'].astype(object)
                                
                                df_sheet1.loc[idx_produit, 'photo'] = url_photo
                                conn.update(worksheet="Sheet1", data=df_sheet1)
                                st.success(f"Image mise à jour avec succès via {methode_trouvee} !")
                                
                                # Enregistrement de la décision dans l'historique
                                df_historique.loc[idx, 'source'] = "APPROUVE_PHOTO"
                                conn.update(worksheet="Historique_Prix", data=df_historique)
                            else:
                                st.error(f"⚠️ Impossible de trouver '{cup_p}' dans le catalogue (ni dans code_upc, ni dans nom).")

                            
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                            
                        # LOGIQUE BOUTON REJETER
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
# GESTION DES MODIFICATIONS DE PRIX
# =====================================================================
with onglet_prix:
    if df_historique.empty:
        st.info("L'historique est complètement vide.")
    else:
        df_prix_attente = df_historique[df_historique['source'].str.startswith("PROPOSITION_PRIX", na=False)]
        
        if df_prix_attente.empty:
            st.success("🎉 Aucun correctif de prix en attente de validation.")
        else:
            st.warning(f"Il y a {len(df_prix_attente)} proposition(s) de modification de prix à réviser.")
            
            # Création sécurisée de la colonne temporaire de recherche
            df_sheet1['code_upc_clean'] = df_sheet1['code_upc'].astype(str).str.strip().replace(r'\.0$', '', regex=True).str.lstrip('0')
            
            for idx, ligne_h in df_prix_attente.iterrows():
                cup_h = str(ligne_h['code_upc']).strip()
                dist_h = str(ligne_h['distribution']).strip()
                prix_h = str(ligne_h['prix']).strip()
                
                cup_h_clean = str(cup_h).strip().lstrip('0')
                produit_correspondant = df_sheet1[df_sheet1['code_upc_clean'] == cup_h_clean]
                nom_catalogue = produit_correspondant.iloc[0]['nom'] if not produit_correspondant.empty else "⚠️ Code UPC inconnu"
                
                with st.container(border=True):
                    st.markdown(f"### 💰 Suggestion de prix pour : **{nom_catalogue}**")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.markdown(f"**Code-barres (UPC) :** `{cup_h}`")
                        st.markdown(f"**Enseigne / Supermarché :** {dist_h.upper().replace('_', ' ')}")
                    with col_p2:
                        st.markdown(f"**Nouveau prix proposé :** :green[{prix_h} $]")
                    
                    c_valider_prix, c_rejeter_prix = st.columns(2)
                    
                    if c_valider_prix.button("🟢 Approuver ce prix", key=f"btn_val_prix_{idx}", use_container_width=True):
                        if not produit_correspondant.empty:
                            idx_ligne_reelle = produit_correspondant.index[0]
                            colonne_prix_cible = str(dist_h).strip().lower().replace(' ', '_')
                            if not colonne_prix_cible.startswith("prix_"):
                                colonne_prix_cible = f"prix_{colonne_prix_cible}"
                            
                            if colonne_prix_cible in df_sheet1.columns:
                                df_sheet1.at[idx_ligne_reelle, colonne_prix_cible] = str(prix_h).replace(',', '.').strip()
                                # On nettoie la colonne temporaire avant l'envoi cloud
                                df_sheet1_clean = df_sheet1.drop(columns=['code_upc_clean'], errors='ignore')
                                conn.update(worksheet="Sheet1", data=df_sheet1_clean)
                            else:
                                st.error(f"La colonne {colonne_prix_cible} n'existe pas dans Sheet1.")
                        
                        df_historique.loc[idx, 'source'] = f"APPROUVE_OK: PROPOSITION_PRIX"
                        conn.update(worksheet="Historique_Prix", data=df_historique)
                        st.success("💰 Le prix a été mis à jour dans le catalogue public !")
                        st.cache_data.clear()
                        time.sleep(1.5)
                        st.rerun()
                        
                    if c_rejeter_prix.button("❌ Rejeter ce prix", key=f"btn_rej_prix_{idx}", use_container_width=True):
                        df_historique.loc[idx, 'source'] = f"REFUSE_REJETE: PROPOSITION_PRIX"
                        conn.update(worksheet="Historique_Prix", data=df_historique)
                        st.error("Suggestion de prix rejetée.")
                        time.sleep(1)
                        st.rerun()
