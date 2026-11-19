from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
import os
import re
import threading
import time
import numpy as np
import pandas as pd
from PIL import Image, ImageEnhance
from rapidocr_onnxruntime import RapidOCR

from app import (
    SESSION_HTTP,
    extraire_texte_regulier,
    get_flyer_items,
    get_grocery_flyer_id,
)
from upc_matcher import enrichir_avec_codes_upc

# Pôles régionaux pour couvrir toutes les circulaires du Québec
POLES_REGIONAUX_QC = [
    "G5Y4H3",  # Chaudière-Appalaches (Saint-Georges)
    "G1R4P5",  # Capitale-Nationale (Québec)
    "H2X1Y4",  # Montréal
    "J1H5H3",  # Estrie (Sherbrooke)
    "G7H5B1",  # Saguenay–Lac-Saint-Jean
    "G5L5J7",  # Bas-Saint-Laurent (Rimouski)
    "G9A5H3",  # Mauricie (Trois-Rivières)
    "J8X3X5",  # Outaouais (Gatineau)
]

NORMALISATION_MARCHANDS = {
    "Tradition": "Marché Tradition",
    "Marche Tradition": "Marché Tradition",
    "Tigre Géant": "Tigre Geant",
    "Giant Tiger": "Tigre Geant",
    "Adonis": "Marché Adonis",
    "Richelieu": "Marché Richelieu",
    "Ami": "Marché Ami",
    "Bonichoix": "Marché Bonichoix",
}


MOTEUR_OCR = RapidOCR()
VERROU_OCR = threading.Lock()


def telecharger_et_preparer_image(image_url: str):
    if not image_url:
        return None
    try:
        resp = SESSION_HTTP.get(image_url, timeout=6)
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        if img.width < 600:
            img = img.resize(
                (int(img.width * 1.8), int(img.height * 1.8)),
                Image.Resampling.LANCZOS,
            )
        img = ImageEnhance.Sharpness(img).enhance(1.4)
        return np.array(img)
    except Exception:
        return None


def lire_texte_ocr(img_array) -> str:
    if img_array is None:
        return ""
    try:
        with VERROU_OCR:
            resultats, _ = MOTEUR_OCR(img_array)
        return " ".join([ligne[1] for ligne in resultats]) if resultats else ""
    except Exception:
        return ""


def extraire_format(texte: str) -> str:
    if not isinstance(texte, str):
        return ""
    m = re.search(
        r"\b(?:\d+\s*[xX]\s*)?\d+(?:[.,/-]\d+)?\s*(?:ml|l|g|kg|lb|oz|un\.?|rouleaux?|btes?|boîtes?|paquets?)\b",
        texte,
        re.IGNORECASE,
    )
    return m.group(0).strip() if m else ""


def extraire_unite_prix(item, texte_global: str) -> str:
    """Identifie l'unité de vente du prix (/lb, /kg, ch., pq) pour éviter toute ambiguïté."""
    post = str(item.get("post_price_text") or "").strip().lower()
    if post:
        if "lb" in post or "livre" in post:
            return "/ lb"
        if "kg" in post:
            return "/ kg"
        if "ch" in post or "un" in post:
            return "ch."
        if len(post) <= 10:
            return post

    if re.search(
        r"(?:/|par)\s*lb\b|\bla\s+livre\b", texte_global, re.IGNORECASE
    ):
        return "/ lb"
    if re.search(r"(?:/|par)\s*kg\b|\ble\s+kg\b", texte_global, re.IGNORECASE):
        return "/ kg"
    if re.search(r"\bch\.?\b|\bchaque\b", texte_global, re.IGNORECASE):
        return "ch."
    return ""


def extraire_condition_et_multi(texte: str, prix_affiche: float):
    if not isinstance(texte, str):
        return "", 1
    conds = []
    quantite_multi = 1

    texte_sans_unites = re.sub(
        r"\b\d+(?:[.,/-]\d+)?\s*(?:ml|l|g|kg|lb|oz|un\.?|rouleaux?)\b",
        "",
        texte,
        flags=re.IGNORECASE,
    )

    m_multi = re.search(
        r"\b([2-9]|10)\s*(?:pour|/)\s*(\d+(?:[.,]\d{2})?)\s*\$?",
        texte_sans_unites,
        re.IGNORECASE,
    )
    if m_multi:
        qte = int(m_multi.group(1))
        total_multi = float(m_multi.group(2).replace(",", "."))
        if abs(total_multi - prix_affiche) < 0.05:
            quantite_multi = qte
            conds.append(f"{qte} pour {total_multi:.2f} $")

    m_fid = re.search(
        r"\b(?:Scene\+|Moi|PC Optimum|Prix membre)\b", texte, re.IGNORECASE
    )
    if m_fid:
        conds.append(m_fid.group(0).strip())

    return " | ".join(conds), quantite_multi


def extraire_prix_regulier_numerique(val: str) -> float:
    if not val or not isinstance(val, str):
        return 0.0
    m = re.search(r"(\d+\.\d{2})", val)
    return float(m.group(1)) if m else 0.0
def valider_prix_regulier(
    prix_special: float, prix_regulier_str: str
) -> str:
    """Élimine les faux prix réguliers OCR (ex: prix équivalent au kg/lb donnant >70% de rabais)."""
    if not prix_regulier_str or prix_special <= 0:
        return ""
    val_reg = extraire_prix_regulier_numerique(prix_regulier_str)
    if val_reg <= prix_special * 1.03 or val_reg > prix_special * 3.33:
        return ""
    return prix_regulier_str


def traiter_article_ameliore(item, merchant, flyer_id):
    nom_brut = str(item.get("name", "")).strip()
    nom_fr, _, _ = nom_brut.partition("|")
    nom = nom_fr.strip()

    prix = item.get("price", "")
    if not nom or prix in [None, ""]:
        return None
    if nom.lower().startswith("banner -") or nom.lower() in [
        "cliquer ici",
        "cliquez ici",
        "voir la brochure",
    ]:
        return None

    try:
        prix_float = float(str(prix).replace(",", "."))
    except ValueError:
        prix_float = 0.0

    description = str(item.get("description") or "").strip()
    image_url = str(item.get("cutout_image_url") or "").strip()

    champs_texte = " ".join(
        str(item.get(k) or "")
        for k in [
            "name",
            "description",
            "sale_story",
            "pre_price_text",
            "post_price_text",
        ]
    )

    if merchant in ["Walmart", "Tigre Geant"]:
        texte_ocr = ""
    else:
        img_array = telecharger_et_preparer_image(image_url) if image_url else None
        texte_ocr = lire_texte_ocr(img_array)
    texte_global = f"{champs_texte} {texte_ocr}".strip()

    condition, qte_multi = extraire_condition_et_multi(texte_global, prix_float)
    prix_unitaire = (
        round(prix_float / qte_multi, 2) if qte_multi > 1 else prix_float
    )

    prix_regulier = extraire_texte_regulier(champs_texte, prix_unitaire)
    if not prix_regulier and texte_ocr:
        prix_regulier = extraire_texte_regulier(texte_ocr, prix_unitaire)

    prix_regulier = valider_prix_regulier(prix_unitaire, prix_regulier)

    format_prod = extraire_format(texte_global)
    unite_prix = extraire_unite_prix(item, texte_global)

    return {
        "marchand": merchant,
        "marque": str(item.get("brand") or "").strip(),
        "produit": nom,
        "prix_circulaire": prix,
        "prix_unitaire": prix_unitaire,
        "unite_prix": unite_prix,
        "prix_regulier": prix_regulier,
        "format": format_prod,
        "condition": condition,
        "description": description,
        "valide_du": str(item.get("valid_from", ""))[:10],
        "valide_au": str(item.get("valid_to", ""))[:10],
        "flyer_id": flyer_id,
    }


def executer_mise_a_jour():
    debut = time.time()
    flyers_deja_traites = set()
    marchands_nationaux_faits = set()
    tous_les_articles = []

    for cp in POLES_REGIONAUX_QC:
        print(f"Vérification des circulaires pour {cp}...", flush=True)
        flyers = get_grocery_flyer_id(cp)
        if not flyers:
            continue

        for flyer in flyers:
            flyer_id = flyer["id"]
            merchant = NORMALISATION_MARCHANDS.get(
                flyer["merchant"], flyer["merchant"]
            )

            if flyer_id in flyers_deja_traites:
                continue
            if merchant in ["Walmart", "Tigre Geant"] and merchant in marchands_nationaux_faits:
                continue

            flyers_deja_traites.add(flyer_id)
            marchands_nationaux_faits.add(merchant)

            items = get_flyer_items(flyer_id)
            print(
                f"  -> Extraction {merchant} (ID: {flyer_id}) : {len(items)} articles..."
            )

            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(
                        traiter_article_ameliore, item, merchant, flyer_id
                    )
                    for item in items
                ]
                for f in futures:
                    res = f.result()
                    if res:
                        tous_les_articles.append(res)

    if not tous_les_articles:
        print("Aucun article extrait.")
        return

    df = pd.DataFrame(tous_les_articles)

    # Suppression intelligente des doublons insensible à la casse (en gardant distincts semaine actuelle et aperçu)
    df["produit_norm"] = df["produit"].astype(str).str.strip().str.lower()
    df = df.drop_duplicates(
        subset=["marchand", "produit_norm", "prix_circulaire", "valide_du"]
    ).drop(columns=["produit_norm"])

    df = enrichir_avec_codes_upc(df, inclure_variantes_superc=True)

    df["prix_circulaire_num"] = pd.to_numeric(
        df["prix_unitaire"], errors="coerce"
    ).fillna(0.0)
    df["prix_regulier_num"] = df["prix_regulier"].apply(
        extraire_prix_regulier_numerique
    )

    df["economie_dollar"] = (
        (df["prix_regulier_num"] - df["prix_circulaire_num"])
        .clip(lower=0.0)
        .round(2)
    )
    df["rabais_pourcent"] = (
        (
            (df["economie_dollar"] / df["prix_regulier_num"])
            .replace([float("inf"), -float("inf")], 0)
            .fillna(0)
            * 100
        )
        .round(0)
        .astype(int)
    )

    # --- FUSION AVEC LES CIRCULAIRES ENCORE VALIDES (CYCLE MERCREDI / JEUDI) ---
    fichier_csv = "circulaires_qc.csv"
    aujourd_hui = datetime.now(ZoneInfo("America/Montreal")).strftime("%Y-%m-%d")

    if os.path.exists(fichier_csv):
        df_ancien = pd.read_csv(fichier_csv, dtype=str).fillna("")
        # Conserve uniquement les offres non expirées (le jeudi, les offres du mercredi s'effacent automatiquement)
        df_valide = df_ancien[
            (df_ancien["valide_au"] == "") | (df_ancien["valide_au"] >= aujourd_hui)
        ].copy()
        df_final = pd.concat([df_valide, df], ignore_index=True)
    else:
        df_final = df.copy()

    # Déduplication en incluant 'valide_du' pour garder distincts la semaine courante et l'aperçu
    df_final["produit_norm"] = df_final["produit"].astype(str).str.strip().str.lower()
    df_final = df_final.drop_duplicates(
        subset=["marchand", "produit_norm", "prix_circulaire", "valide_du"],
        keep="last",
    ).drop(columns=["produit_norm"]).reset_index(drop=True)

    # Réassigner des IDs propres et uniques sur le fichier complet
    df_final["id_produit"] = df_final["marchand"].astype(str) + "_" + df_final.index.astype(str)

    compteur_reg = df_final["prix_regulier"].astype(bool).sum()
    df_final.to_csv(fichier_csv, index=False, encoding="utf-8-sig")

    duree = round(time.time() - debut, 1)
    print(
        f"Terminé en {duree}s : {len(df_final)} produits ({compteur_reg} prix réguliers) sauvegardés."
    )


if __name__ == "__main__":
    executer_mise_a_jour()
