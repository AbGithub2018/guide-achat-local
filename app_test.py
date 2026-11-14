import os
import urllib.parse
import pandas as pd
import streamlit as st

from fonctions_geo import calculer_distance, charger_donnees

st.set_page_config(
    page_title="Planificateur Budget Épicerie",
    page_icon="🍎",
    layout="wide",
)

if "panier_achats" not in st.session_state:
    st.session_state["panier_achats"] = []

if "banniere_manuelle" not in st.session_state:
    st.session_state["banniere_manuelle"] = "SUPER C"

LIENS_OFFICIELS = {
    "SUPER C": "https://superc.ca",
    "MAXI": "https://maxi.ca",
    "IGA": "https://iga.net",
    "PROVIGO": "https://provigo.ca",
    "METRO": "https://metro.ca",
    "MARCHÉ ADONIS": "https://groupeadonis.ca",
    "MARCHÉ AMI": "https://marcheami.ca",
    "MARCHÉ BONICHOIX": "https://bonichoix.com",
    "MARCHÉ RICHELIEU": "https://marcherichelieu.ca",
    "MARCHÉ TRADITION": "https://marchetradition.com",
    "WALMART": "https://walmart.ca",
    "COSTCO": "https://costco.ca",
    "TIGRE GÉANT": "https://gianttiger.com",
    "DOLLARAMA": "https://dollarama.com",
}


def classer_rayon(nom_produit: str) -> str:
    """Attribue automatiquement un rayon et une icône visuelle sans image protégée."""
    txt = str(nom_produit).lower()
    if any(
        m in txt
        for m in [
            "porc",
            "boeuf",
            "bœuf",
            "poulet",
            "dinde",
            "veau",
            "saumon",
            "crevette",
            "poisson",
            "jambon",
            "bacon",
            "saucisse",
            "steak",
            "rôti",
            "filet",
            "bifteck",
            "côtelette",
            "viande",
        ]
    ):
        return "🥩 Viandes et Poissons"
    if any(
        m in txt
        for m in [
            "pomme",
            "banane",
            "fraise",
            "framboise",
            "bleuet",
            "orange",
            "raisin",
            "melon",
            "tomate",
            "laitue",
            "carotte",
            "oignon",
            "poivron",
            "brocoli",
            "concombre",
            "patate",
            "pomme de terre",
            "salade",
            "avocat",
            "champignon",
            "céleri",
            "citron",
        ]
    ):
        return "🍎 Fruits et Légumes"
    if any(
        m in txt
        for m in [
            "lait",
            "fromage",
            "beurre",
            "yogourt",
            "crème",
            "oeuf",
            "œuf",
            "margarine",
            "cheddar",
            "mozzarella",
        ]
    ):
        return "🧀 Produits laitiers"
    if any(
        m in txt
        for m in [
            "pain",
            "bagel",
            "muffin",
            "croissant",
            "tortilla",
            "brioche",
            "gâteau",
            "tarte",
            "biscuit",
        ]
    ):
        return "🍞 Boulangerie"
    if any(
        m in txt
        for m in [
            "papier",
            "savon",
            "détergent",
            "essuie-tout",
            "mouchoir",
            "sac",
            "nettoyant",
            "shampooing",
            "dentifrice",
        ]
    ):
        return "🧼 Entretien / Autre"
    return "📦 Épicerie / Boîtes"


@st.cache_data(ttl=3600)
def charger_circulaires_qc():
    fichier = "circulaires_qc.csv"
    if not os.path.exists(fichier):
        return None
    df = pd.read_csv(fichier).fillna("")
    if "unite_prix" not in df.columns:
        df["unite_prix"] = ""
    df["marchand_norm"] = df["marchand"].astype(str).str.strip().str.upper()
    df["marchand_norm"] = df["marchand_norm"].replace({
        "TIGRE GEANT": "TIGRE GÉANT",
        "MARCHE TRADITION": "MARCHÉ TRADITION",
        "MARCHE AMI": "MARCHÉ AMI",
    })
    df["rayon_auto"] = df["produit"].apply(classer_rayon)
    return df


df_coords, df_magasins = charger_donnees()
if df_coords is None or df_magasins is None:
    st.stop()

df_circulaires = charger_circulaires_qc()
st.sidebar.markdown(
    "<h2 style='font-size: 22px; color: #1E3A8A; margin-bottom: 10px;'>⚙️ Critères de recherche</h2>",
    unsafe_allow_html=True,
)
saisie_utilisateur = st.sidebar.text_input(
    "Entrez votre code postal (ex: G5Y 4H3)", "G5Y4H3"
)
code_recherche = saisie_utilisateur.replace(" ", "").upper()
rayon_max = st.sidebar.slider(
    "Rayon maximum de recherche (km)", 5, 100, 25, 5
)

bannieres_disponibles = ["Toutes les bannières"] + sorted(
    list(df_magasins["Nom_Commerce"].dropna().unique())
)
banniere_selectionnee = st.sidebar.selectbox(
    "Filtrer par bannière :", bannieres_disponibles
)

if banniere_selectionnee != "Toutes les bannières":
    st.session_state["banniere_manuelle"] = banniere_selectionnee

banniere_active = st.session_state["banniere_manuelle"]

st.sidebar.write("---")
st.sidebar.markdown(
    "<h3 style='font-size: 18px; color: #1E3A8A;'>📍 Commerces à proximité</h3>",
    unsafe_allow_html=True,
)

if code_recherche:
    point_origine = df_coords[df_coords["Code postal"] == code_recherche]

    if not point_origine.empty:
        lat_centre = float(point_origine["Latitude"].iloc[0])
        lon_centre = float(point_origine["Longitude"].iloc[0])
        st.sidebar.caption(
            f"Position détectée : {point_origine['Ville'].iloc[0]}"
        )

        df_magasins_gps = pd.merge(
            df_magasins,
            df_coords,
            on="Code postal",
            how="inner",
            suffixes=("", "_Ref"),
        )
        df_magasins_gps["Distance_KM"] = calculer_distance(
            lat_centre,
            lon_centre,
            df_magasins_gps["Latitude"],
            df_magasins_gps["Longitude"],
        )

        resultats_filtres = df_magasins_gps[
            df_magasins_gps["Distance_KM"] <= rayon_max
        ].sort_values(by="Distance_KM")
        if banniere_selectionnee != "Toutes les bannières":
            resultats_filtres = resultats_filtres[
                resultats_filtres["Nom_Commerce"] == banniere_selectionnee
            ]

        if not resultats_filtres.empty:
            for index, rangee in resultats_filtres.iterrows():
                nom_magasin = rangee["Nom_Commerce"]
                distance = rangee["Distance_KM"]

                st.sidebar.markdown(
                    f"**{nom_magasin}** ({distance:.1f} km)<br/><small style='color: #6B7280;'>{rangee.get('Adresse_Rue', '')}</small>",
                    unsafe_allow_html=True,
                )
                if st.sidebar.button(
                    "📖 Consulter",
                    key=f"voir_magasin_{index}",
                    use_container_width=True,
                ):
                    st.session_state["banniere_manuelle"] = nom_magasin
                    st.rerun()
                st.sidebar.write("")
        else:
            st.sidebar.warning("Aucun commerce trouvé dans ce rayon.")
st.markdown(
    """
    <div style="background-color: #1E3A8A; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 36px; font-weight: bold;">🍎 Mon Planificateur Anti-Inflation</h1>
        <p style="color: #E0E7FF; margin: 5px 0 0 0; font-size: 16px;">Comparez vos bannières et optimisez votre facture d'épicerie gratuitement</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.link_button(
    "⚙️ Ouvrir l'application Mon Guide d'Achat Local (Scanner un Code-Barres / Pays d'Origine)",
    "https://streamlit.app",
    type="primary",
    use_container_width=True,
)
st.write("---")

col_gauche, col_droite = st.columns([1.0, 1.0])

with col_gauche:
    with st.container(border=True):
        st.markdown(
            "<h2 style='font-size: 24px; color: #1E3A8A; font-weight: 600; margin-top: 0px;'>🔍 Étape 1 : Saisie manuelle</h2>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div style="background-color: #EFF6FF; padding: 10px; border-left: 5px solid #3B82F6; border-radius: 4px; margin-bottom: 15px;">
                <span style="color: #1E40AF; font-weight: bold; font-size: 16px;">🛒 Magasin actif : {banniere_active}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        categorie = st.selectbox(
            "Sélectionner le rayon :",
            [
                "🍎 Fruits et Légumes",
                "🥩 Viandes et Poissons",
                "🧀 Produits laitiers",
                "🍞 Boulangerie",
                "📦 Épicerie / Boîtes",
                "🧼 Entretien / Autre",
            ],
        )

        nom_article = st.text_input(
            "Nom de l'article :",
            placeholder="Ex: Banane, Beurre...",
            key="input_nom",
        )
        prix_article = st.number_input(
            "Prix en spécial ($) :", value=0.00, step=0.01, key="input_prix"
        )

        if st.button("✨ Enregistrer l'article", use_container_width=True):
            if nom_article:
                st.session_state["panier_achats"].append({
                    "magasin": banniere_active,
                    "catégorie": categorie,
                    "produit": nom_article,
                    "prix": prix_article,
                })
                st.toast("Article enregistré !", icon="✅")
                st.rerun()
            else:
                st.warning("Veuillez entrer un nom d'article.")
    st.write("")

    with st.container(border=True):
        st.markdown(
            "<h2 style='font-size: 24px; color: #1E3A8A; font-weight: 600; margin-top: 0px;'>🛍️ Ma facture d'épicerie simulée</h2>",
            unsafe_allow_html=True,
        )

        if st.session_state["panier_achats"]:
            df_panier = pd.DataFrame(st.session_state["panier_achats"])

            df_affichage = df_panier.rename(
                columns={
                    "magasin": "Magasin",
                    "catégorie": "Rayon",
                    "produit": "Article",
                    "prix": "Prix",
                }
            )
            df_affichage["Prix"] = df_affichage["Prix"].map("{:.2f} $".format)
            st.dataframe(df_affichage, use_container_width=True, hide_index=True)

            st.markdown(
                "<h4 style='font-size: 16px; color: #4B5563; font-weight: bold; margin-top: 15px;'>📊 Répartition de mes dépenses par enseigne :</h4>",
                unsafe_allow_html=True,
            )
            df_comparatif = (
                df_panier.groupby("magasin")["prix"].sum().reset_index()
            )

            for _, rangee in df_comparatif.iterrows():
                magasin_nom = rangee["magasin"]
                total_magasin = rangee["prix"]
                st.markdown(
                    f"🔹 Total estimé chez **{magasin_nom}** : `{total_magasin:.2f} $`"
                )

            st.markdown(
                f"""
                <div style="background-color: #FEF2F2; border: 2px dashed #EF4444; padding: 15px; border-radius: 8px; text-align: center; margin-top: 20px; margin-bottom: 15px;">
                    <span style="color: #991B1B; font-size: 16px; font-weight: bold; display: block; text-transform: uppercase; letter-spacing: 1px;">Estimation totale cumulée</span>
                    <span style="color: #DC2626; font-size: 36px; font-weight: 900; font-family: monospace;">{df_panier['prix'].sum():.2f} $</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("🗑️ Réinitialiser ma liste", use_container_width=True):
                st.session_state["panier_achats"] = []
                st.rerun()
        else:
            st.info(
                "Votre liste d'épicerie est vide pour le moment. Trouvez des rabais à droite et ajoutez-les ici !"
            )
with col_droite:
    with st.container(border=True):
        st.markdown(
            f"<h2 style='font-size: 24px; color: #1E3A8A; font-weight: 600; margin-top: 0px;'>🏷️ Spéciaux et Liens : {banniere_active}</h2>",
            unsafe_allow_html=True,
        )

        cle_recherche = str(banniere_active).upper().strip()
        url_base_site = LIENS_OFFICIELS.get(
            cle_recherche, "https://google.com"
        )
        code_postal_url = urllib.parse.quote(code_recherche)

        if cle_recherche in [
            "MARCHÉ AMI",
            "MARCHÉ BONICHOIX",
            "MARCHÉ RICHELIEU",
            "MARCHÉ TRADITION",
            "COSTCO",
        ]:
            url_final_site = f"https://google.com{urllib.parse.quote(f'{banniere_active} {code_recherche}')}"
        elif "superc" in url_base_site or "metro" in url_base_site:
            url_final_site = f"{url_base_site}?search={code_postal_url}"
        elif "maxi" in url_base_site or "provigo" in url_base_site:
            url_final_site = f"{url_base_site}?searchQuery={code_postal_url}"
        elif "walmart" in url_base_site or "gianttiger" in url_base_site:
            url_final_site = f"{url_base_site}?q={code_postal_url}"
        elif "dollarama" in url_base_site:
            url_final_site = f"{url_base_site}?localisation={code_postal_url}"
        else:
            url_final_site = url_base_site

        col_l1, col_l2 = st.columns(2)
        with col_l1:
            st.link_button(
                "🌐 Circulaire illustrée (Site officiel)",
                url_base_site,
                use_container_width=True,
            )
        with col_l2:
            st.link_button(
                "📍 Ma succursale locale",
                url_final_site,
                type="primary",
                use_container_width=True,
            )

    st.write("")

    if df_circulaires is not None:
        df_offres = df_circulaires[
            df_circulaires["marchand_norm"] == cle_recherche
        ].copy()

        if not df_offres.empty:
            with st.container(border=True):
                date_fin = df_offres["valide_au"].iloc[0]
                st.caption(
                    f"📅 {len(df_offres)} articles en spécial chez **{banniere_active}** (valide jusqu'au {date_fin})"
                )

                rayon_filtre = st.selectbox(
                    "📂 Filtrer par rayon :",
                    ["Tous les rayons"]
                    + sorted(df_offres["rayon_auto"].unique().tolist()),
                )

                c_rech, c_tri = st.columns([1.4, 1.0])
                with c_rech:
                    recherche_article = st.text_input(
                        f"🔍 Mot-clé ({banniere_active}) :",
                        placeholder="Ex: poulet, beurre, café...",
                    )
                with c_tri:
                    tri_option = st.selectbox(
                        "Trier par :",
                        [
                            "Meilleur % de rabais",
                            "Prix le plus bas",
                            "Économie en $",
                            "Ordre alphabétique",
                        ],
                    )

                if rayon_filtre != "Tous les rayons":
                    df_offres = df_offres[
                        df_offres["rayon_auto"] == rayon_filtre
                    ]

                if recherche_article:
                    df_offres = df_offres[
                        df_offres["produit"].str.contains(
                            recherche_article, case=False, na=False
                        )
                        | df_offres["marque"].str.contains(
                            recherche_article, case=False, na=False
                        )
                    ]

                if tri_option == "Meilleur % de rabais":
                    df_offres = df_offres.sort_values(
                        by=["rabais_pourcent", "prix_circulaire_num"],
                        ascending=[False, True],
                    )
                elif tri_option == "Prix le plus bas":
                    df_offres = df_offres.sort_values(
                        by="prix_circulaire_num", ascending=True
                    )
                elif tri_option == "Économie en $":
                    df_offres = df_offres.sort_values(
                        by="economie_dollar", ascending=False
                    )
                else:
                    df_offres = df_offres.sort_values(
                        by="produit", ascending=True
                    )
                for _, item in df_offres.iterrows():
                    with st.container(border=True):
                        col_info, col_prix, col_btn = st.columns(
                            [2.2, 1.1, 1.0]
                        )

                        with col_info:
                            icone_rayon = item["rayon_auto"].split(" ")[0]
                            titre = f"{icone_rayon} **{item['produit']}**"
                            if item["marque"]:
                                titre += f" ({item['marque']})"
                            st.markdown(titre)

                            sous_infos = [item["rayon_auto"]]
                            if item["format"]:
                                sous_infos.append(f"📦 {item['format']}")
                            if item["condition"]:
                                sous_infos.append(f"🏷️ {item['condition']}")
                            st.caption("  |  ".join(sous_infos))

                        with col_prix:
                            prix_num = float(item["prix_circulaire_num"])
                            unite = str(item.get("unite_prix") or "").strip()
                            st.markdown(
                                f"**{prix_num:.2f} $** <small>{unite}</small>",
                                unsafe_allow_html=True,
                            )
                            if (
                                item["prix_regulier"]
                                and int(item["rabais_pourcent"]) > 0
                            ):
                                st.caption(
                                    f"~~{item['prix_regulier']} $ {unite}~~ (-{item['rabais_pourcent']}%)"
                                )
                            elif item["prix_regulier"]:
                                st.caption(
                                    f"~~{item['prix_regulier']} $ {unite}~~"
                                )

                        with col_btn:
                            if st.button(
                                "➕ Ajouter",
                                key=f"add_spec_{item['id_produit']}",
                                use_container_width=True,
                                type="primary",
                            ):
                                nom_final = item["produit"]
                                if item["format"]:
                                    nom_final += f" ({item['format']})"
                                if unite:
                                    nom_final += f" [{unite}]"

                                st.session_state["panier_achats"].append({
                                    "magasin": banniere_active,
                                    "catégorie": item["rayon_auto"],
                                    "produit": nom_final,
                                    "prix": prix_num,
                                })
                                st.toast(
                                    f"✅ {nom_final} ajouté à votre facture !",
                                    icon="🛒",
                                )
                                st.rerun()
        else:
            with st.container(border=True):
                st.info(
                    f"Aucun spécial extrait automatiquement pour **{banniere_active}** cette semaine. Utilisez le bouton ci-dessus pour consulter la circulaire sur le site officiel !"
                )
    else:
        with st.container(border=True):
            st.warning(
                "⏳ Le fichier des spéciaux de la semaine (`circulaires_qc.csv`) n'est pas encore disponible dans le dossier."
            )
