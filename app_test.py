import os
from datetime import datetime
import urllib.parse
import pandas as pd
import streamlit as st
from io import BytesIO
import barcode
from barcode.writer import ImageWriter

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


import re


def calculer_prix_unitaire(prix_str, format_str):
    """Calcule le prix par 100g ou 100ml pour déjouer la réduflation."""
    try:
        prix = float(prix_str)
        txt = str(format_str).lower().replace(",", ".")
        if prix <= 0 or not txt:
            return ""

        multi = 1.0
        match_multi = re.search(r"(\d+)\s*[x*]\s*(\d+(?:\.\d+)?)", txt)
        if match_multi:
            multi = float(match_multi.group(1))
            val = float(match_multi.group(2))
        else:
            match_val = re.search(r"(\d+(?:\.\d+)?)", txt)
            if not match_val:
                return ""
            val = float(match_val.group(1))

        quantite_totale = multi * val
        if quantite_totale <= 0:
            return ""

        if "kg" in txt:
            return f"{(prix / (quantite_totale * 1000)) * 100:.2f} $ / 100g"
        elif "g" in txt and "mg" not in txt:
            return f"{(prix / quantite_totale) * 100:.2f} $ / 100g"
        elif "ml" in txt:
            return f"{(prix / quantite_totale) * 100:.2f} $ / 100ml"
        elif "l" in txt:
            return f"{(prix / (quantite_totale * 1000)) * 100:.2f} $ / 100ml"
        return ""
    except Exception:
        return ""


import unicodedata


def normaliser_texte(texte: str) -> str:
    """Enlève les accents et met en minuscules pour faciliter la recherche."""
    txt = str(texte).lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", txt)
        if unicodedata.category(c) != "Mn"
    )


@st.cache_data(ttl=3600)
def charger_circulaires_qc():
    fichier = "circulaires_qc.csv"
    if not os.path.exists(fichier):
        return None
    df = pd.read_csv(fichier, dtype=str).fillna("")
    if "unite_prix" not in df.columns:
        df["unite_prix"] = ""
    if "code_upc" not in df.columns:
        df["code_upc"] = ""
    df["code_upc"] = (
        df["code_upc"]
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .apply(lambda x: x.zfill(12) if x.isdigit() else x)
    )
    df["marchand_norm"] = df["marchand"].astype(str).str.strip().str.upper()
    df["marchand_norm"] = df["marchand_norm"].replace({
        "TIGRE GEANT": "TIGRE GÉANT",
        "GIANT TIGER": "TIGRE GÉANT",
        "MARCHE TRADITION": "MARCHÉ TRADITION",
        "MARCHE AMI": "MARCHÉ AMI",
    })

    df["rayon_auto"] = df["produit"].apply(classer_rayon)
    df["prix_unitaire_calc"] = df.apply(
        lambda r: calculer_prix_unitaire(r.get("prix_circulaire_num", 0), r.get("format", "")),
        axis=1,
    )
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
    "https://achatquebec.streamlit.app",
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

        if nom_article and len(nom_article.strip()) >= 3 and df_circulaires is not None:
            correspondances = df_circulaires[
                df_circulaires["produit"].str.contains(nom_article.strip(), case=False, na=False)
            ].copy()
            if not correspondances.empty:
                correspondances["prix_num_temp"] = pd.to_numeric(
                    correspondances["prix_circulaire_num"], errors="coerce"
                )
                correspondances = correspondances.dropna(subset=["prix_num_temp"]).sort_values(by="prix_num_temp")
                if not correspondances.empty:
                    meilleur = correspondances.head(1).squeeze()
                    st.info(
                        f"💡 **Meilleur prix repéré :** {meilleur['produit']} à **{meilleur['prix_num_temp']:.2f} $** chez **{meilleur['marchand_norm']}** !"
                    )

        col_p, col_q = st.columns([1.5, 1.0])
        with col_p:
            prix_article = st.number_input(
                "Prix unitaire ($) :", value=0.00, step=0.01, key="input_prix"
            )
        with col_q:
            qte_article = st.number_input(
                "Quantité :", min_value=1, value=1, step=1, key="input_qte"
            )

        if st.button("✨ Enregistrer l'article", use_container_width=True):
            if nom_article:
                st.session_state["panier_achats"].append({
                    "magasin": banniere_active,
                    "catégorie": categorie,
                    "produit": nom_article,
                    "upc": "",
                    "quantite": int(qte_article),
                    "prix": float(prix_article),
                    "economie": 0.0,
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
            aujourd_hui = datetime.now().strftime("%Y-%m-%d")
            panier_valide = []
            nb_expires = 0

            for item_p in st.session_state["panier_achats"]:
                item_p.setdefault("upc", "")
                item_p.setdefault("quantite", 1)
                item_p.setdefault("economie", 0.0)
                item_p.setdefault("valide_au", "")
                item_p.setdefault("achete", False)

                date_exp = str(item_p["valide_au"]).strip()
                if date_exp and len(date_exp) >= 10 and date_exp[:10] < aujourd_hui:
                    nb_expires += 1
                else:
                    panier_valide.append(item_p)

            if nb_expires > 0:
                st.session_state["panier_achats"] = panier_valide
                st.warning(f"⏰ {nb_expires} article(s) expiré(s) ont été retirés automatiquement de votre liste.")
                st.rerun()

            vue_panier = st.radio(
                "Mode d'affichage :",
                ["📊 Facture & Quantités", "🛒 Checklist en magasin (par épicerie)"],
                horizontal=True,
                label_visibility="collapsed",
            )

            df_panier = pd.DataFrame(st.session_state["panier_achats"])
            df_panier["Sous-total"] = df_panier["prix"] * df_panier["quantite"]

            if vue_panier == "📊 Facture & Quantités":
                df_panier["Supprimer"] = False
                df_editeur = df_panier[
                    ["Supprimer", "quantite", "produit", "magasin", "catégorie", "prix", "Sous-total"]
                ].rename(
                    columns={
                        "quantite": "Qté",
                        "produit": "Article",
                        "magasin": "Magasin",
                        "catégorie": "Rayon",
                        "prix": "Prix unit.",
                    }
                )

                st.caption("💡 Modifiez une quantité ou cochez 🗑️ pour retirer un article.")
                df_modifie = st.data_editor(
                    df_editeur,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Supprimer": st.column_config.CheckboxColumn("🗑️", default=False, width="small"),
                        "Qté": st.column_config.NumberColumn("Qté", min_value=1, max_value=99, step=1, width="small"),
                        "Article": st.column_config.TextColumn("Article", disabled=True),
                        "Magasin": st.column_config.TextColumn("Magasin", disabled=True),
                        "Rayon": st.column_config.TextColumn("Rayon", disabled=True),
                        "Prix unit.": st.column_config.NumberColumn("Prix unit.", format="%.2f $", disabled=True),
                        "Sous-total": st.column_config.NumberColumn("Total", format="%.2f $", disabled=True),
                    },
                    key="editeur_panier",
                )

                if df_modifie["Supprimer"].any() or not df_modifie["Qté"].equals(df_editeur["Qté"]):
                    nouveau_panier = []
                    for idx in range(len(df_modifie)):
                        if not df_modifie["Supprimer"].iloc[idx]:
                            ligne = st.session_state["panier_achats"][idx].copy()
                            ligne["quantite"] = int(df_modifie["Qté"].iloc[idx])
                            nouveau_panier.append(ligne)
                    st.session_state["panier_achats"] = nouveau_panier
                    st.rerun()

            else:
                st.caption("✅ Cochez les articles au fur et à mesure que vous les mettez dans votre panier :")
                magasins_uniques = sorted(df_panier["magasin"].unique())

                for mag in magasins_uniques:
                    st.markdown(f"#### 🏪 {mag}")
                    indices_mag = [
                        i for i, a in enumerate(st.session_state["panier_achats"]) if a["magasin"] == mag
                    ]
                    indices_mag.sort(key=lambda idx: st.session_state["panier_achats"][idx]["catégorie"])

                    rayon_courant = ""
                    for idx in indices_mag:
                        art = st.session_state["panier_achats"][idx]
                        if art["catégorie"] != rayon_courant:
                            rayon_courant = art["catégorie"]
                            st.markdown(f"<small style='color:#4B5563; font-weight:bold;'>{rayon_courant}</small>", unsafe_allow_html=True)

                        libelle = f"{art['quantite']}x {art['produit']} — **{art['prix'] * art['quantite']:.2f} $**"
                        if art["achete"]:
                            libelle = f"~~{libelle}~~"

                        coche = st.checkbox(
                            libelle,
                            value=art["achete"],
                            key=f"chk_magasin_{idx}",
                        )
                        if coche != art["achete"]:
                            st.session_state["panier_achats"][idx]["achete"] = coche
                            st.rerun()

                if any(a["achete"] for a in st.session_state["panier_achats"]):
                    if st.button("🧹 Effacer les articles achetés (cochés)", use_container_width=True):
                        st.session_state["panier_achats"] = [
                            a for a in st.session_state["panier_achats"] if not a["achete"]
                        ]
                        st.rerun()


            articles_avec_upc = [
                a for a in st.session_state["panier_achats"]
                if str(a.get("upc", "")).strip().isdigit() and len(str(a.get("upc", "")).strip()) == 12
            ]
            if articles_avec_upc:
                with st.expander(f"📷 Codes-barres scannables ({len(articles_avec_upc)})", expanded=True):
                    for art in articles_avec_upc:
                        tampon_img = BytesIO()
                        code_barre = barcode.get("upca", str(art["upc"]).strip(), writer=ImageWriter())
                        code_barre.write(tampon_img, options={"module_height": 8.0, "font_size": 8, "text_distance": 3.0, "quiet_zone": 2.0})
                        st.markdown(f"**{art['produit']}** (Qté : {art['quantite']})")
                        st.image(tampon_img.getvalue(), width=210)

            st.markdown(
                "<h4 style='font-size: 16px; color: #4B5563; font-weight: bold; margin-top: 15px;'>📊 Répartition de mes dépenses par enseigne :</h4>",
                unsafe_allow_html=True,
            )
            df_comparatif = (
                df_panier.groupby("magasin")["Sous-total"].sum().reset_index()
            )

            for _, rangee in df_comparatif.iterrows():
                magasin_nom = rangee["magasin"]
                total_magasin = rangee["Sous-total"]
                st.markdown(
                    f"🔹 Total estimé chez **{magasin_nom}** : `{total_magasin:.2f} $`"
                )

            inclure_taxes = st.checkbox(
                "🧾 Inclure l'estimation des taxes (TPS/TVQ 14,975 %) sur les articles non alimentaires (« Entretien / Autre »)",
                value=True,
            )

            sous_total_general = float(df_panier["Sous-total"].sum())
            montant_taxable = float(
                df_panier[df_panier["catégorie"].str.contains("Entretien|Autre", case=False, na=False)]["Sous-total"].sum()
            )
            taxes_estimees = round(montant_taxable * 0.14975, 2) if inclure_taxes else 0.0
            total_final = sous_total_general + taxes_estimees

            if inclure_taxes and taxes_estimees > 0:
                st.caption(f"Sous-total avant taxes : **{sous_total_general:.2f} $** | Taxes estimées (TPS/TVQ) : **{taxes_estimees:.2f} $**")

            st.markdown(
                f"""
                <div style="background-color: #FEF2F2; border: 2px dashed #EF4444; padding: 15px; border-radius: 8px; text-align: center; margin-top: 15px; margin-bottom: 12px;">
                    <span style="color: #991B1B; font-size: 16px; font-weight: bold; display: block; text-transform: uppercase; letter-spacing: 1px;">Estimation totale cumulée</span>
                    <span style="color: #DC2626; font-size: 36px; font-weight: 900; font-family: monospace;">{total_final:.2f} $</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            total_economies = float((df_panier["economie"] * df_panier["quantite"]).sum())
            if total_economies > 0:
                st.markdown(
                    f"""
                    <div style="background-color: #ECFDF5; border: 2px solid #10B981; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
                        <span style="color: #065F46; font-size: 14px; font-weight: bold; display: block;">🎉 Économies réalisées grâce aux circulaires</span>
                        <span style="color: #059669; font-size: 24px; font-weight: 900; font-family: monospace;">{total_economies:.2f} $</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            lignes_export = [f"MA LISTE D'ÉPICERIE ({datetime.now().strftime('%Y-%m-%d')})", "=" * 42]
            for mag in sorted(df_panier["magasin"].unique()):
                sous_df_mag = df_panier[df_panier["magasin"] == mag].sort_values(by=["catégorie", "produit"])
                lignes_export.append(f"\n🏪 {mag.upper()} (Total : {sous_df_mag['Sous-total'].sum():.2f} $)")
                lignes_export.append("-" * 35)
                rayon_actuel = ""
                for _, row_exp in sous_df_mag.iterrows():
                    if row_exp["catégorie"] != rayon_actuel:
                        rayon_actuel = row_exp["catégorie"]
                        lignes_export.append(f"  [{rayon_actuel}]")
                    etat = "☑" if row_exp["achete"] else "☐"
                    lignes_export.append(
                        f"   {etat} {row_exp['quantite']}x {row_exp['produit']} - {row_exp['Sous-total']:.2f} $"
                    )
            lignes_export.append("\n" + "=" * 42)
            lignes_export.append(f"TOTAL ESTIMÉ (taxes incl.) : {total_final:.2f} $")
            if total_economies > 0:
                lignes_export.append(f"ÉCONOMIES CIRCULAIRES : {total_economies:.2f} $")

            texte_export = "\n".join(lignes_export)

            col_dl, col_raz = st.columns(2)
            with col_dl:
                st.download_button(
                    "📲 Télécharger (.txt)",
                    data=texte_export,
                    file_name=f"liste_epicerie_{datetime.now().strftime('%Y-%m-%d')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            with col_raz:
                if st.button("🗑️ Tout effacer", use_container_width=True):
                    st.session_state["panier_achats"] = []
                    st.rerun()

            with st.expander("📋 Copier la liste en 1 clic (Notes / SMS)", expanded=False):
                st.code(texte_export, language=None)

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

        if "superc" in url_base_site or "metro" in url_base_site:
            url_final_site = f"{url_base_site}/trouver-une-epicerie"
        elif "maxi" in url_base_site or "provigo" in url_base_site:
            url_final_site = f"{url_base_site}/store-locator"
        elif "iga" in url_base_site:
            url_final_site = f"{url_base_site}/fr/trouver_un_magasin"
        elif "walmart" in url_base_site or "gianttiger" in url_base_site:
            url_final_site = f"{url_base_site}/fr/magasins"
        elif "dollarama" in url_base_site:
            url_final_site = f"{url_base_site}/fr-CA/trouver-un-magasin"
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
        mode_global = st.toggle(
            "🌎 Comparer dans toutes les bannières simultanément",
            value=False,
            help="Activez cette option pour trouver le meilleur prix parmi toutes les épiceries.",
        )

        if mode_global:
            df_offres = df_circulaires.copy()
            titre_section = "toutes les bannières"
        else:
            df_offres = df_circulaires[
                df_circulaires["marchand_norm"] == cle_recherche
            ].copy()
            titre_section = banniere_active

        if not df_offres.empty:
            with st.container(border=True):
                date_fin = df_offres["valide_au"].head(1).squeeze()
                st.caption(
                    f"📅 {len(df_offres)} articles en spécial dans **{titre_section}** (valide jusqu'au {date_fin})"
                )

                rayon_filtre = st.selectbox(
                    "📂 Filtrer par rayon :",
                    ["Tous les rayons"]
                    + sorted(df_offres["rayon_auto"].unique().tolist()),
                )

                c_rech, c_tri = st.columns([1.4, 1.0])
                with c_rech:
                    recherche_article = st.text_input(
                        f"🔍 Mot-clé ({titre_section}) :",
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
                    requete_norm = normaliser_texte(recherche_article)
                    requete_norm = requete_norm.replace("coke", "coca")
                    mots_cles = requete_norm.split()

                    texte_complet = (
                        df_offres["produit"].apply(normaliser_texte)
                        + " "
                        + df_offres["marque"].apply(normaliser_texte)
                    )

                    masque = pd.Series(True, index=df_offres.index)
                    for mot in mots_cles:
                        masque = masque & texte_complet.str.contains(mot, regex=False, na=False)

                    df_offres = df_offres[masque]


                df_offres["prix_circulaire_num"] = pd.to_numeric(df_offres["prix_circulaire_num"], errors="coerce").fillna(0.0)
                df_offres["rabais_pourcent"] = pd.to_numeric(df_offres["rabais_pourcent"], errors="coerce").fillna(0)
                df_offres["economie_dollar"] = pd.to_numeric(df_offres["economie_dollar"], errors="coerce").fillna(0.0)

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

                df_offres["produit_norm"] = (
                    df_offres["produit"].astype(str).str.strip().str.lower()
                )
                df_offres = df_offres.drop_duplicates(
                    subset=["marchand_norm", "produit_norm", "prix_circulaire_num"]
                )

                for _, item in df_offres.iterrows():
                    with st.container(border=True):
                        col_info, col_prix, col_btn = st.columns(
                            [2.2, 1.1, 1.0]
                        )

                        with col_info:
                            icone_rayon = item["rayon_auto"].split(" ").pop(0)
                            magasin_item = item["marchand_norm"]
                            titre = f"{icone_rayon} **{item['produit']}**"
                            if item["marque"]:
                                titre += f" ({item['marque']})"
                            if mode_global:
                                titre += f" — 🏪 `{magasin_item}`"
                            st.markdown(titre)

                            sous_infos = [item["rayon_auto"]]
                            if item["format"]:
                                sous_infos.append(f"📦 {item['format']}")
                            if item.get("prix_unitaire_calc"):
                                sous_infos.append(f"⚖️ **{item['prix_unitaire_calc']}**")
                            if item["condition"]:
                                sous_infos.append(f"🏷️ {item['condition']}")
                            if str(item.get("code_upc", "")).strip():
                                sous_infos.append(f"🔢 UPC:\u00A0{item['code_upc']}")

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
                                st.markdown(
                                    f"<small style='color: #6B7280;'><span style='text-decoration: line-through;'>{item['prix_regulier']} $ {unite}</span> <b style='color: #16A34A;'>(-{int(item['rabais_pourcent'])}%)</b></small>",
                                    unsafe_allow_html=True,
                                )
                            elif item["prix_regulier"]:
                                st.markdown(
                                    f"<small style='color: #6B7280; text-decoration: line-through;'>{item['prix_regulier']} $ {unite}</small>",
                                    unsafe_allow_html=True,
                                )

                        with col_btn:
                            if st.button(
                                "➕ Ajouter",
                                key=f"add_spec_{item['id_produit']}_{magasin_item}",
                                use_container_width=True,
                                type="primary",
                            ):
                                nom_final = item["produit"]
                                if item["format"]:
                                    nom_final += f" ({item['format']})"
                                if unite:
                                    nom_final += f" [{unite}]"

                                st.session_state["panier_achats"].append({
                                    "magasin": magasin_item,
                                    "catégorie": item["rayon_auto"],
                                    "produit": nom_final,
                                    "upc": str(item.get("code_upc", "")).strip(),
                                    "prix": prix_num,
                                })

                                st.toast(
                                    f"✅ {nom_final} ({magasin_item}) ajouté à votre facture !",
                                    icon="🛒",
                                )
                                st.rerun()
        else:
            with st.container(border=True):
                st.info(
                    f"Aucun spécial extrait automatiquement pour **{titre_section}** cette semaine. Utilisez le bouton ci-dessus pour consulter la circulaire sur le site officiel !"
                )
    else:
        with st.container(border=True):
            st.warning(
                "⏳ Le fichier des spéciaux de la semaine (`circulaires_qc.csv`) n'est pas encore disponible dans le dossier."
            )
