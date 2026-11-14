import os
import re
import unicodedata
from difflib import SequenceMatcher
import pandas as pd

FICHIER_BASE_QC = "base_upc_qc.csv"

MOTS_FAIBLES = {
    "rouge", "vert", "jaune", "blanc", "noir", "rose", "orange", "bleu", "dore",
    "biscuit", "fromage", "biere", "boisson", "sauce", "soupe", "fruit", "legume",
    "viande", "poulet", "boeuf", "porc", "poisson", "crevette", "filet", "tranche",
    "fume", "frais", "fraiche", "surgele", "nature", "original", "classique",
    "doux", "fort", "leger", "sans", "lactose", "bio", "biologique", "gros", "petit",
    "mini", "sac", "boite", "paquet", "caisse", "format", "economique", "familial",
    "chocolat", "pomme", "tomate", "framboise", "bleuet", "fraise", "raisin", "banane",
    "citron", "lime", "peche", "mangue", "cerise", "erable", "vanille", "caramel",
    "miel", "ail", "oignon", "poivre", "sel", "sucre", "eau", "lait", "jus", "pain",
    "gateau", "pate", "riz", "cafe", "the", "huile", "beurre", "creme", "yogourt",
    "croustille", "craquelin", "barre", "cereale", "saucisse", "jambon", "bacon",
    "pizza", "salade", "vinaigrette", "noix", "amande", "serre", "jardin", "maison"
}

def _normaliser(texte: str) -> str:
    if not texte:
        return ""
    texte = str(texte).lower()
    texte = "".join(
        c for c in unicodedata.normalize("NFD", texte)
        if unicodedata.category(c) != "Mn"
    )
    texte = texte.replace("'", "").replace("’", "").replace(".", "")
    texte = re.sub(r"[^a-z0-9\s]", " ", texte)
    return " ".join(texte.split())

def _mots_significatifs(texte: str) -> set:
    mots_vides = {
        "de", "du", "des", "la", "le", "les", "et", "ou", "a", "au", "aux",
        "en", "avec", "pour", "varietes", "assorties", "choix", "saveurs",
        "certains", "produits", "selection", "type", "style", "facon", "terre", "pommes"
    }
    mots = set()
    for m in _normaliser(texte).split():
        if len(m) > 2 and m not in mots_vides and not m.isdigit():
            if len(m) > 4 and m.endswith(("s", "x")):
                m = m[:-1]
            mots.add(m)
    return mots

def _extraire_upc_url(url: str) -> str:
    match = re.search(r"/p/(\d{11,14})", str(url))
    if not match:
        return ""
    code = match.group(1)
    if len(code) == 11:
        return "0" + code
    if len(code) == 13 and code.startswith("0"):
        return code[1:]
    return code.zfill(12)
def _charger_base_permanente_qc() -> list:
    """Charge instantanément le dictionnaire permanent des produits québécois."""
    if not os.path.exists(FICHIER_BASE_QC):
        return []
    df = pd.read_csv(FICHIER_BASE_QC, dtype=str).fillna("")
    if "product-details-link href" not in df.columns:
        return []

    df["code_upc"] = df["product-details-link href"].apply(_extraire_upc_url)
    df = df[df["code_upc"] != ""].drop_duplicates(subset=["code_upc"])

    catalogue = []
    for _, r in df.iterrows():
        marque = str(r.get("head__brand", "")).strip()
        titre = str(r.get("head__title", "")).strip()
        nom_complet = f"{marque} {titre}".strip()
        mots = _mots_significatifs(nom_complet)
        forts = mots - MOTS_FAIBLES
        if forts:
            catalogue.append({
                "upc": r["code_upc"],
                "marque_norm": _normaliser(marque),
                "nom_norm": _normaliser(nom_complet),
                "mots": mots,
                "forts": forts,
            })
    return catalogue


def _chercher_dans_base_qc(marque: str, produit: str, catalogue: list) -> str:
    premier_produit = produit.split(",")[0].strip()
    texte_f = f"{marque} {premier_produit}".strip()
    mots_f = _mots_significatifs(texte_f)
    forts_f = mots_f - MOTS_FAIBLES
    if not forts_f:
        return ""

    marque_f = _normaliser(marque)
    mots_sans_marque = mots_f - _mots_significatifs(marque_f)

    meilleur_upc = ""
    meilleur_score = 0.0

    for item in catalogue:
        if marque_f and item["marque_norm"]:
            if not ("irresistible" in marque_f and "irresistible" in item["marque_norm"]):
                if (marque_f not in item["marque_norm"]) and (item["marque_norm"] not in marque_f):
                    continue

        communs_forts = forts_f.intersection(item["forts"])
        if not communs_forts:
            continue

        communs_totaux = mots_sans_marque.intersection(item["mots"])
        if mots_sans_marque and not communs_totaux:
            continue

        sim = SequenceMatcher(None, _normaliser(texte_f), item["nom_norm"]).ratio()
        score = len(communs_forts) * 20 + len(communs_totaux) * 10 + (sim * 25)
        if marque_f and item["marque_norm"]:
            score += 20

        if score > meilleur_score and score >= 45:
            meilleur_score = score
            meilleur_upc = item["upc"]

    return meilleur_upc


def enrichir_avec_codes_upc(df_global: pd.DataFrame, inclure_variantes_superc: bool = True) -> pd.DataFrame:
    """Enrichit toutes les bannières en moins d'une seconde sans appel réseau externe."""
    df_global = df_global.copy()
    if "code_upc" not in df_global.columns:
        df_global["code_upc"] = ""

    catalogue_qc = _charger_base_permanente_qc()
    memoire_locale = {}

    for idx, row in df_global.iterrows():
        marque = str(row.get("marque") or "").strip()
        produit = str(row.get("produit") or "").strip()
        cle = _normaliser(f"{marque} {produit}")
        if not cle:
            continue

        if cle in memoire_locale:
            df_global.at[idx, "code_upc"] = memoire_locale[cle]
            continue

        code = _chercher_dans_base_qc(marque, produit, catalogue_qc)
        memoire_locale[cle] = code
        df_global.at[idx, "code_upc"] = code

    nb_upc = df_global["code_upc"].astype(bool).sum()
    print(f"Codes UPC associés instantanément : {nb_upc} / {len(df_global)} produits.")
    return df_global
