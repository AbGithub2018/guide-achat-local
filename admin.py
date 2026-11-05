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
    st.stop()  # Bloque le reste du code tant qu'on n'est pas connecté
# --- CODE EXÉCUTÉ UNIQUEMENT SI CONNECTÉ ---
st.sidebar.success("🟢 Mode Administrateur en chef Actif")
if st.sidebar.button("🔴 Se déconnecter de l'administration", use_container_width=True):
    st.session_state["admin_prive_connecte"] = False
    st.rerun()

# 1. Chargement des deux onglets cloud indispensables
try:
    df_sheet1 = conn.read(worksheet="Sheet1", ttl=0)
    df_historique = conn.read(worksheet="Historique_Prix", ttl=0)
except Exception as e:
    st.error(f"❌ Erreur lors de la synchronisation avec Google Sheets : {e}")
    st.stop()

# 2. Séparation de la file d'attente en deux onglets visuels larges
onglet_nouveaux, onglet_prix = st.tabs(["✨ Nouveaux produits à ajouter", "💰 Prix suggérés à corriger"])

# =====================================================================
# GESTION DES NOUVEAUX PRODUITS
# =====================================================================
with onglet_nouveaux:
    if df_historique.empty:
        st.info("L'historique est complètement vide.")
    else:
        # On cherche les lignes contenant PROPOSITION_NOUVEAU dans la colonne source
        df_nouveaux_attente = df_historique[df_historique['source'].str.contains("PROPOSITION_NOUVEAU:", na=False)]
        
        if df_nouveaux_attente.empty:
            st.success("🎉 Aucun nouveau produit en attente de validation.")
        else:
            st.warning(f"Il y a {len(df_nouveaux_attente)} proposition(s) de création de produit en attente.")
            
            for idx, ligne_h in df_nouveaux_attente.iterrows():
                texte_source = str(ligne_h['source'])
                cup_h = str(ligne_h['code_upc']).strip()
                dist_h = str(ligne_h['distribution']).strip()
                prix_h = str(ligne_h['prix']).strip()
                
                # Dépaquetage sécurisé des variables textuelles compactées
                try:
                    infos_decoupees = texte_source.replace("PROPOSITION_NOUVEAU:", "").split("|")
                    v_nom = infos_decoupees[0].replace("Nom:", "").strip() if len(infos_decoupees) > 0 else "Inconnu"
                    v_marque = infos_decoupees[1].replace("Marque:", "").strip() if len(infos_decoupees) > 1 else ""
                    v_prov = infos_decoupees[2].replace("Province:", "").strip() if len(infos_decoupees) > 2 else ""
                    v_pays = infos_decoupees[3].replace("Pays:", "").strip() if len(infos_decoupees) > 3 else "Canada"
                except Exception:
                    v_nom, v_marque, v_prov, v_pays = texte_source, "", "", "Canada"
                
                # Interface visuelle spacieuse sous forme de carte descriptive
                with st.container(border=True):
                    st.markdown(f"### 📦 Proposition de fiche : **{v_nom}**")
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.markdown(f"**Code-barres (UPC) :** `{cup_h}`")
                        st.markdown(f"**Marque / Entreprise :** {v_marque}")
                    with col_info2:
                        st.markdown(f"**Provenance :** {v_prov} ({v_pays})")
                        st.markdown(f"**Prix initial constaté :** {prix_h}$ chez **{dist_h}**")
                    
                    # Boutons d'action pour la création
                    c_valider, c_rejeter = st.columns(2)
                    
                    if c_valider.button("🟢 Accepter & Ajouter au catalogue public", key=f"btn_val_prod_{idx}", use_container_width=True):
                        # Création de la ligne complète formatée pour Sheet1
                        nouvelle_ligne_sheet1 = {col.strip().lower(): "" for col in df_sheet1.columns}
                        nouvelle_ligne_sheet1['code_upc'] = cup_h
                        nouvelle_ligne_sheet1['nom'] = v_nom
                        nouvelle_ligne_sheet1['entreprise_proprietaire'] = v_marque
                        nouvelle_ligne_sheet1['entreprise_province_etat'] = v_prov
                        nouvelle_ligne_sheet1['entreprise_pays'] = v_pays
                        nouvelle_ligne_sheet1['distribution'] = dist_h
                        
                        # Correspondance dynamique de l'étiquette de prix
                        colonne_prix_cible = f"prix_{dist_h.lower().replace(' ', '_')}"
                        if colonne_prix_cible in nouvelle_ligne_sheet1:
                            nouvelle_ligne_sheet1[colonne_prix_cible] = prix_h
                        
                        # Push définitif vers Sheet1 et archivage dans l'historique
                        df_sheet1_maj = pd.concat([df_sheet1, pd.DataFrame([nouvelle_ligne_sheet1])], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=df_sheet1_maj)
                        
                        df_historique.loc[idx, 'source'] = f"APPROUVE_OK: {texte_source}"
                        conn.update(worksheet="Historique_Prix", data=df_historique)
                        
                        st.success(f"🎉 Le produit '{v_nom}' a été ajouté avec succès à la base principale !")
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
# GESTION DES MODIFICATIONS DE PRIX
# =====================================================================
with onglet_prix:
    if df_historique.empty:
        st.info("L'historique est complètement vide.")
    else:
        # On cherche les lignes contenant PROPOSITION_PRIX dans la colonne source
        df_prix_attente = df_historique[df_historique['source'].astype(str) == "PROPOSITION_PRIX"]
        
        if df_prix_attente.empty:
            st.success("🎉 Aucun correctif de prix en attente de validation.")
        else:
            st.warning(f"Il y a {len(df_prix_attente)} proposition(s) de modification de prix à réviser.")
            
            for idx, ligne_h in df_prix_attente.iterrows():
                cup_h = str(ligne_h['code_upc']).strip()
                dist_h = str(ligne_h['distribution']).strip()
                prix_h = str(ligne_h['prix']).strip()
                
                # Aller chercher le vrai nom actuel dans Sheet1 pour vous donner du contexte
                produit_correspondant = df_sheet1[df_sheet1['code_upc'].astype(str).str.strip() == cup_h]
                nom_catalogue = produit_correspondant.iloc[0]['nom'] if not produit_correspondant.empty else "⚠️ Code UPC inconnu dans le catalogue principal"
                
                with st.container(border=True):
                    st.markdown(f"### 💰 Suggestion de prix pour : **{nom_catalogue}**")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.markdown(f"**Code-barres (UPC) :** `{cup_h}`")
                        st.markdown(f"**Enseigne / Supermarché :** {dist_h.upper().replace('_', ' ')}")
                    with col_p2:
                        st.markdown(f"**Nouveau prix proposé :** :green[{prix_h} $]")
                    
                    # Boutons d'action pour le prix
                    c_valider_prix, c_rejeter_prix = st.columns(2)
                    
                    if c_valider_prix.button("🟢 Approuver ce prix", key=f"btn_val_prix_{idx}", use_container_width=True):
                        if not produit_correspondant.empty:
                            index_catalogue = produit_correspondant.index[0]
                            colonne_prix_cible = f"prix_{dist_h.lower().replace(' ', '_')}"
                            
                            if colonne_prix_cible in df_sheet1.columns:
                                df_sheet1.loc[index_catalogue, colonne_prix_cible] = prix_h
                                conn.update(worksheet="Sheet1", data=df_sheet1)
                        
                        df_historique.loc[idx, 'source'] = f"APPROUVE_OK: PROPOSITION_PRIX"
                        conn.update(worksheet="Historique_Prix", data=df_historique)
                        
                        st.success("💰 Le prix a été mis à jour dans le catalogue public !")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                        
                    if c_rejeter_prix.button("❌ Rejeter ce prix", key=f"btn_rej_prix_{idx}", use_container_width=True):
                        df_historique.loc[idx, 'source'] = f"REFUSE_REJETE: PROPOSITION_PRIX"
                        conn.update(worksheet="Historique_Prix", data=df_historique)
                        st.error("Suggestion de prix rejetée.")
                        time.sleep(1)
                        st.rerun()
