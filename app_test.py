# =========================================================================
# COLONNE DE DROITE : AFFICHAGE DU TEXTE EN VERSION STYLISÉE (MARKDOWN)
# =========================================================================
with col_droite:
    st.subheader(f"📋 Les Rabais Vedettes : {banniere_active}")

    # Gestion automatique des noms de sous-dossiers (sans accents)
    nom_sous_dossier = str(banniere_active).lower().replace(" ", "_").replace("é", "e").replace("è", "e").replace("à", "a")
    chemin_dossier_txt = os.path.join(DOSSIER_BANNIERES, nom_sous_dossier)

    if os.path.exists(chemin_dossier_txt):
        fichiers_texte = [
            f
            for f in os.listdir(chemin_dossier_txt)
            if f.lower().endswith(".txt")
        ]

        if fichiers_texte:
            fichier_cible = os.path.join(chemin_dossier_txt, fichiers_texte[0])
            
            try:
                with open(fichier_cible, "r", encoding="utf-8") as f:
                    contenu_notes = f.read()
                
                # Encadré visuel élégant pour mettre en valeur vos promotions rédigées
                st.info("💡 **Astuce budget :** Comparez ces rabais vedettes avec votre liste à gauche avant d'ouvrir la circulaire complète.")
                
                # Affichage sous forme de page stylisée plutôt qu'une boîte grise de saisie
                st.markdown(
                    f'<div style="background-color: #F8F9FA; padding: 20px; border-radius: 10px; '
                    f'border-left: 5px solid #FF4B4B; line-height: 1.6; color: #212529;">'
                    f'{contenu_notes.replace("\n", "<br>")}'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
            except Exception as e:
                st.error("Impossible de lire le fichier de description.")
        else:
            st.info("Aucun fichier de rabais textuel (.txt) dans ce dossier.")
    else:
        st.warning(f"Dossier introuvable : bannieres/{nom_sous_dossier}")
