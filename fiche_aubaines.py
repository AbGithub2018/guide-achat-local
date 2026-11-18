import re
import unicodedata
import streamlit as st
import pandas as pd

COULEURS_BANNIERES = {
    "MAXI": "#E31837",
    "SUPER C": "#E31837",
    "IGA": "#D71920",
    "METRO": "#D71920",
    "PROVIGO": "#E31837",
    "WALMART": "#0071CE",
    "TIGRE GÉANT": "#F59E0B",
    "COSTCO": "#005DAA",
    "MARCHÉ ADONIS": "#16A34A",
}

SYNONYMES_EPICERIE = {
    "poulet": ["poulet", "poitrine", "cuisse", "pilon", "aile", "chicken"],
    "boeuf": ["boeuf", "bœuf", "hache", "bifteck", "steak", "roti", "beef"],
    "porc": ["porc", "cotelette", "filet", "bacon", "jambon", "saucisse", "pork"],
    "patate": ["patate", "pomme de terre", "pommes de terre", "potato"],
    "fromage": ["fromage", "cheddar", "mozzarella", "brie", "feta", "gouda", "cheese"],
    "beurre": ["beurre", "butter"],
    "lait": ["lait", "milk"],
    "oeuf": ["oeuf", "œuf", "egg"],
    "coke": ["coke", "coca", "pepsi", "boisson gazeuse", "soft drink"],
    "jus": ["jus", "juice", "oasis", "tropicana", "simply"],
    "cafe": ["cafe", "café", "coffee", "nespresso", "k-cup", "tassimo"],
    "pain": ["pain", "bagel", "muffin", "baguette", "bread", "tortilla"],
    "papier": ["papier", "hygienique", "essuie-tout", "mouchoir", "cashmere", "royale", "bounty"],
    "savon": ["savon", "detergent", "lessive", "tide", "gain", "palmolive"],
}


def normaliser_texte(texte: str) -> str:
    """Enlève les accents et met en minuscules pour faciliter la recherche."""
    txt = str(texte).lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", txt)
        if unicodedata.category(c) != "Mn"
    )


def obtenir_variantes_recherche(mot_cle: str) -> list:
    """Retourne les synonymes associés à un mot-clé d'épicerie."""
    mot_norm = normaliser_texte(mot_cle)
    variantes = {mot_norm}
    for cle, liste_syn in SYNONYMES_EPICERIE.items():
        if mot_norm == cle or mot_norm in liste_syn:
            variantes.update(liste_syn)
    return list(variantes)


def calculer_equivalence_prix(prix: float, format_str: str, unite_str: str) -> str:
    """Convertit /lb <-> /kg et calcule le prix au 100g/100ml avec garde-fou."""
    unite_clean = str(unite_str).replace("/", "").strip().lower()
    if unite_clean in ["kg", "le kg", "kilo", "kilos", "kilogramme"]:
        return f"({prix / 2.20462:.2f}$/lb)"
    if unite_clean in ["lb", "la lb", "livre", "livres"]:
        return f"({prix * 2.20462:.2f}$/kg)"

    txt = str(format_str).lower().replace(",", ".").strip()
    if prix <= 0 or not txt:
        return ""

    if "-" in txt or ("/" in txt and not re.search(r"^\d+/\d+", txt)):
        return ""

    match = re.search(r"^(?:(\d+)\s*[x*/]\s*)?(\d+(?:\.\d+)?)\s*(kg|g|ml|l)$", txt)
    if not match:
        return ""

    multi = float(match.group(1)) if match.group(1) else 1.0
    val = float(match.group(2))
    unite = match.group(3)

    qte = multi * val
    if qte <= 0:
        return ""

    if unite == "kg":
        res = (prix / (qte * 1000)) * 100
        label = "100g"
    elif unite == "g":
        res = (prix / qte) * 100
        label = "100g"
    elif unite == "ml":
        res = (prix / qte) * 100
        label = "100ml"
    else:
        res = (prix / (qte * 1000)) * 100
        label = "100ml"

    if res < 0.05 or res > 15.0:
        return ""

    return f"({res:.2f}$/{label})"
def generer_html_fiche(df_selection: pd.DataFrame, date_fin: str, filtre_recherche: str = "") -> str:
    """Génère une fiche HTML multi-colonnes prête à imprimer ou enregistrer en PDF."""
    sous_titre = f"Offres valides jusqu'au {date_fin} • Généré via Mon Planificateur Anti-Inflation"
    if filtre_recherche:
        sous_titre += f" • Recherche : « {filtre_recherche} »"

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            margin: 15px;
            background-color: #ffffff;
            color: #111827;
        }}
        .banniere-entete {{
            background-color: #1E3A8A;
            color: white;
            padding: 16px 20px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
        }}
        .banniere-entete h1 {{
            margin: 0;
            font-size: 22px;
        }}
        .banniere-entete p {{
            margin: 4px 0 0 0;
            font-size: 13px;
            color: #E0E7FF;
        }}
        .grille {{
            column-count: 3;
            column-gap: 14px;
        }}
        .carte-magasin {{
            break-inside: avoid;
            border: 1px solid #D1D5DB;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 14px;
            background-color: #FAFAFA;
        }}
        .titre-magasin {{
            font-size: 15px;
            font-weight: bold;
            padding-bottom: 6px;
            margin-bottom: 8px;
            border-bottom: 3px solid #1E3A8A;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .badge-nb {{
            font-size: 11px;
            font-weight: normal;
            color: #4B5563;
        }}
        .ligne-produit {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            font-size: 11px;
            padding: 4px 0;
            border-bottom: 1px dotted #E5E7EB;
        }}
        .nom-prod {{
            padding-right: 6px;
            line-height: 1.25;
        }}
        .prix-prod {{
            font-weight: bold;
            white-space: nowrap;
            text-align: right;
        }}
        .prix-equiv {{
            display: block;
            font-size: 9.5px;
            font-weight: normal;
            color: #059669;
        }}
        @media print {{
            body {{ margin: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
    </head>
    <body>
        <div class="banniere-entete">
            <div>
                <h1>🍎 Liste des meilleures aubaines de la semaine</h1>
                <p>{sous_titre}</p>
            </div>
            <button class="no-print" onclick="window.print()" style="background:#10B981; color:white; border:none; padding:10px 16px; border-radius:6px; font-weight:bold; cursor:pointer; font-size:14px;">
                🖨️ Imprimer / Sauver en PDF
            </button>
        </div>
        <div class="grille">
    """

    for magasin in sorted(df_selection["marchand_norm"].unique()):
        groupe = df_selection[df_selection["marchand_norm"] == magasin].sort_values(by="prix_circulaire_num")
        couleur = COULEURS_BANNIERES.get(magasin, "#1E3A8A")
        
        html += f"""
        <div class="carte-magasin">
            <div class="titre-magasin" style="border-bottom-color: {couleur}; color: {couleur};">
                <span>{magasin}</span>
                <span class="badge-nb">{len(groupe)} aubaines</span>
            </div>
        """
        for _, row in groupe.iterrows():
            nom = str(row["produit"]).strip()
            nom = re.sub(r"\(\d{8,}\s*[a-zA-Z]*\)", "", nom).strip()
            
            fmt = str(row.get("format", "")).strip()
            if fmt and not re.search(r"\d{8,}", fmt) and fmt.lower() not in nom.lower():
                nom += f" <span style='color:#6B7280;'>({fmt})</span>"
            
            prix = float(row["prix_circulaire_num"])
            unite = str(row.get("unite_prix", "")).strip()
            prix_txt = f"{prix:.2f}$"
            if unite:
                prix_txt += f" <small style='font-weight:normal;'>{unite}</small>"

            equiv = calculer_equivalence_prix(prix, fmt, unite)
            equiv_html = f"<span class='prix-equiv'>{equiv}</span>" if equiv else ""

            html += f"""
            <div class="ligne-produit">
                <span class="nom-prod">☐ {nom}</span>
                <span class="prix-prod">{prix_txt}{equiv_html}</span>
            </div>
            """
        html += "</div>"

    html += """
        </div>
    </body>
    </html>
    """
    return html


def afficher_generateur_fiche(df_circulaires: pd.DataFrame):
    """Affiche l'interface de configuration et l'aperçu de la fiche dans Streamlit."""
    if df_circulaires is None or df_circulaires.empty:
        st.warning("Aucune donnée de circulaire disponible pour générer la fiche.")
        return

    df_clean = df_circulaires.copy()
    df_clean["prix_circulaire_num"] = pd.to_numeric(df_clean["prix_circulaire_num"], errors="coerce").fillna(0.0)
    df_clean["rabais_pourcent"] = pd.to_numeric(df_clean["rabais_pourcent"], errors="coerce").fillna(0)
    df_clean = df_clean[df_clean["prix_circulaire_num"] > 0]

    if "valide_au" in df_clean.columns:
        df_clean["valide_au_clean"] = df_clean["valide_au"].astype(str).str.strip().str.slice(0, 10)
        dates_max = df_clean.groupby("marchand_norm")["valide_au_clean"].transform("max")
        df_clean = df_clean[df_clean["valide_au_clean"] == dates_max]

    col1, col2, col3 = st.columns([1.5, 1.0, 1.0])
    with col1:
        magasins_dispos = sorted(df_clean["marchand_norm"].unique())
        magasins_choisis = st.multiselect(
            "🏪 Bannières à inclure :",
            magasins_dispos,
            default=magasins_dispos[:6],
        )
    with col2:
        nb_max_par_magasin = st.slider(
            "📊 Aubaines max par magasin :",
            min_value=5,
            max_value=100,
            value=25,
            step=5,
        )
    with col3:
        critere_tri = st.selectbox(
            "🎯 Sélectionner les :",
            ["Meilleurs % de rabais", "Prix les plus bas"],
        )

    activer_recherche = st.checkbox(
        "🔍 Filtrer et comparer des produits précis (avec synonymes et prix au 100g / lb)",
        value=False,
        key="chk_activer_recherche_fiche",
    )

    recherche_fiche = ""
    if activer_recherche:
        recherche_fiche = st.text_input(
            "Entrez vos produits (séparez par une virgule pour plusieurs articles) :",
            placeholder="Ex: poulet, beurre, fromage, patate, coke...",
            key="recherche_fiche_aubaines",
        )

    if not magasins_choisis:
        st.info("Sélectionnez au moins une bannière pour afficher la fiche.")
        return

    df_filtre = df_clean[df_clean["marchand_norm"].isin(magasins_choisis)].copy()

    if "flyer_id" in df_filtre.columns:
        df_filtre["nb_items_flyer"] = df_filtre.groupby(["marchand_norm", "flyer_id"])["produit"].transform("count")
    else:
        df_filtre["nb_items_flyer"] = 0

    df_filtre["cle_dedup"] = df_filtre["produit"].apply(lambda t: normaliser_texte(t)[:35])
    df_filtre = df_filtre.sort_values(by=["nb_items_flyer", "prix_circulaire_num"], ascending=[False, True])
    df_filtre = df_filtre.drop_duplicates(subset=["marchand_norm", "cle_dedup"])

    termes_saisis = [t.strip() for t in recherche_fiche.split(",") if t.strip()]
    if termes_saisis:
        texte_searchable = (
            df_filtre["produit"].apply(normaliser_texte)
            + " "
            + df_filtre["marque"].apply(normaliser_texte)
        )
        masque = pd.Series(False, index=df_filtre.index)
        for terme in termes_saisis:
            for variante in obtenir_variantes_recherche(terme):
                masque = masque | texte_searchable.str.contains(variante, regex=False, na=False)
        df_filtre = df_filtre[masque]

        if df_filtre.empty:
            st.warning(f"Aucun rabais trouvé pour « {recherche_fiche} » dans les bannières sélectionnées.")
            return

    if critere_tri == "Meilleurs % de rabais":
        df_filtre = df_filtre.sort_values(
            by=["rabais_pourcent", "nb_items_flyer", "prix_circulaire_num"],
            ascending=[False, False, True],
        )
    else:
        df_filtre = df_filtre.sort_values(
            by=["nb_items_flyer", "prix_circulaire_num"],
            ascending=[False, True],
        )

    df_top = df_filtre if termes_saisis else df_filtre.groupby("marchand_norm").head(nb_max_par_magasin)

    date_fin = (
        str(df_top["valide_au"].dropna().iloc[0])
        if "valide_au" in df_top.columns and not df_top["valide_au"].dropna().empty
        else "cette semaine"
    )

    html_rendu = generer_html_fiche(df_top, date_fin, recherche_fiche.strip())

    st.download_button(
        "📥 Télécharger la fiche interactive (.html) pour impression ou capture d'écran",
        data=html_rendu,
        file_name=f"aubaines_semaine_{date_fin}.html",
        mime="text/html",
        use_container_width=True,
        type="primary",
    )

    with st.container(border=True):
        st.components.v1.html(html_rendu, height=750, scrolling=True)
