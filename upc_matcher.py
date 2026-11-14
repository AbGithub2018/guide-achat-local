import os
import re
import unicodedata
from difflib import SequenceMatcher
import pandas as pd

FICHIER_SUPERC = 'superc_promos.csv'

MOTS_FAIBLES = {
    'rouge', 'vert', 'jaune', 'blanc', 'noir', 'rose', 'orange', 'bleu', 'dore', 'brun',
    'biscuit', 'fromage', 'biere', 'boisson', 'sauce', 'soupe', 'fruit', 'legume',
    'viande', 'poulet', 'boeuf', 'porc', 'poisson', 'crevette', 'filet', 'tranche',
    'fume', 'frais', 'fraiche', 'surgele', 'nature', 'original', 'classique',
    'doux', 'fort', 'leger', 'sans', 'lactose', 'bio', 'biologique', 'gros', 'petit',
    'mini', 'sac', 'boite', 'paquet', 'caisse', 'format', 'economique', 'familial',
    'chocolat', 'pomme', 'tomate', 'framboise', 'bleuet', 'fraise', 'raisin', 'banane',
    'citron', 'lime', 'peche', 'mangue', 'cerise', 'erable', 'vanille', 'caramel',
    'miel', 'ail', 'oignon', 'poivre', 'sel', 'sucre', 'eau', 'lait', 'jus', 'pain',
    'gateau', 'pate', 'riz', 'cafe', 'the', 'huile', 'beurre', 'creme', 'yogourt',
    'croustille', 'craquelin', 'barre', 'cereale', 'saucisse', 'jambon', 'bacon',
    'pizza', 'salade', 'vinaigrette', 'noix', 'amande', 'grille', 'rotie', 'roti',
    'cuit', 'cuite', 'cru', 'crue', 'entier', 'entiere', 'coupe', 'coupee', 'morceau',
    'moitie', 'prepare', 'preparee', 'assaisonne', 'assaisonnee', 'epice', 'epicee',
    'pelee', 'pele', 'lave', 'lavee', 'serre', 'jardin', 'maison', 'artisan'
}

def _normaliser(texte: str) -> str:
    if not texte:
        return ''
    texte = str(texte).lower()
    texte = ''.join(c for c in unicodedata.normalize('NFD', texte) if unicodedata.category(c) != 'Mn')
    texte = texte.replace("'", "").replace("’", "").replace(".", "")
    texte = re.sub(r'[^a-z0-9\s]', ' ', texte)
    return ' '.join(texte.split())

def _extraire_format_norm(texte: str) -> str:
    t = _normaliser(texte)
    match = re.search(r'(\d+(?:\s*\d+)?)\s*(kg|g|ml|l|un|rlx)\b', t)
    return f"{match.group(1).replace(' ', '')}{match.group(2)}" if match else ''

def _mots_significatifs(texte: str) -> set:
    mots_vides = {
        'de', 'du', 'des', 'la', 'le', 'les', 'et', 'ou', 'a', 'au', 'aux', 'en', 'avec',
        'pour', 'varietes', 'assorties', 'naturelle', 'naturel', 'choix', 'saveurs',
        'certains', 'produits', 'selection', 'type', 'style', 'facon', 'terre', 'pommes'
    }
    mots = set()
    for m in _normaliser(texte).split():
        if len(m) > 2 and m not in mots_vides and not m.isdigit():
            if len(m) > 4 and m.endswith(('s', 'x')):
                m = m[:-1]
            mots.add(m)
    return mots

def _mots_forts(texte: str) -> set:
    return _mots_significatifs(texte) - MOTS_FAIBLES
def _parser_prix(valeur: str) -> float:
    if not valeur:
        return 0.0
    match = re.search(r'(\d+)[,.](\d{2})', str(valeur))
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    match_entier = re.search(r'\b(\d{1,3})\s*\$', str(valeur))
    return float(match_entier.group(1)) if match_entier else 0.0

def _extraire_tous_prix_site(row) -> set:
    prix_possibles = set()
    p_main_str = str(row.get('price-update', '')).strip()
    p_sec_str = str(row.get('pricing__secondary-price', '')).strip()
    p_alt_str = str(row.get('pricing__main-price', '')).strip()

    for s in [p_main_str, p_sec_str, p_alt_str]:
        val = _parser_prix(s)
        if val > 0:
            prix_possibles.add(round(val, 2))

    match_mult = re.match(r'^(\d+)\s*/', p_main_str)
    if match_mult:
        multiplicateur = int(match_mult.group(1))
        val_sec = _parser_prix(p_sec_str)
        if val_sec > 0 and multiplicateur > 1:
            prix_possibles.add(round(val_sec * multiplicateur, 2))
    return prix_possibles

def _extraire_upc_url(url: str) -> str:
    match = re.search(r'/p/(\d{11,14})', str(url))
    if not match:
        return ''
    code = match.group(1)
    if len(code) == 11:
        return '0' + code
    if len(code) == 13 and code.startswith('0'):
        return code[1:]
    return code.zfill(12)

def _charger_referentiel_superc(chemin_csv: str) -> pd.DataFrame:
    df = pd.read_csv(chemin_csv, dtype=str).fillna('')
    df['code_upc'] = df['product-details-link href'].apply(_extraire_upc_url)
    df = df[df['code_upc'] != ''].drop_duplicates(subset=['code_upc']).copy()
    df['prix_possibles'] = df.apply(_extraire_tous_prix_site, axis=1)
    df['prix_promo_site'] = df.apply(
        lambda r: _parser_prix(r.get('price-update', '')) or _parser_prix(r.get('pricing__main-price', '')),
        axis=1
    )
    df['prix_reg_site'] = df['pricing__before-price'].apply(_parser_prix) if 'pricing__before-price' in df.columns else 0.0
    df['marque_norm'] = df.get('head__brand', '').apply(_normaliser)
    df['nom_complet'] = (df.get('head__brand', '') + ' ' + df.get('head__title', '')).str.strip()
    df['mots'] = df['nom_complet'].apply(_mots_significatifs)
    df['mots_forts'] = df['nom_complet'].apply(_mots_forts)
    df['format_norm'] = df['nom_complet'].apply(_extraire_format_norm)
    return df
def enrichir_avec_codes_upc(df_global: pd.DataFrame, inclure_variantes_superc: bool = True) -> pd.DataFrame:
    df_global = df_global.copy()
    if 'code_upc' not in df_global.columns:
        df_global['code_upc'] = ''

    if not os.path.exists(FICHIER_SUPERC):
        print(f"Fichier {FICHIER_SUPERC} introuvable : etape UPC ignoree.")
        return df_global

    df_superc = _charger_referentiel_superc(FICHIER_SUPERC)
    marques_connues = {m for m in df_superc['marque_norm'].unique() if m}
    upc_utilises = set()

    mask_sc = df_global['marchand'] == 'Super C'
    valide_du_sc = df_global.loc[mask_sc, 'valide_du'].iloc if mask_sc.any() and 'valide_du' in df_global.columns else ''
    valide_au_sc = df_global.loc[mask_sc, 'valide_au'].iloc if mask_sc.any() and 'valide_au' in df_global.columns else ''

    for idx, row_flipp in df_global[mask_sc].iterrows():
        p_promo = _parser_prix(row_flipp.get('prix_circulaire', ''))
        p_reg = _parser_prix(row_flipp.get('prix_regulier', ''))
        marque_brut = str(row_flipp.get('marque', '')).strip()
        produit_brut = str(row_flipp.get('produit', '')).strip()
        desc_brut = str(row_flipp.get('description', '')).strip()

        variantes = [produit_brut] + ([p.strip() for p in produit_brut.split(',') if p.strip()] if ',' in produit_brut else [])

        for var in variantes:
            marque_f = _normaliser(marque_brut)
            if not marque_f:
                titre_norm = _normaliser(var)
                for m in sorted(marques_connues, key=len, reverse=True):
                    if len(m) >= 3 and re.search(rf'\b{re.escape(m)}\b', titre_norm):
                        marque_f = m
                        break

            texte_f = f"{marque_brut} {var}".strip()
            mots_f = _mots_significatifs(texte_f)
            forts_f = _mots_forts(texte_f)
            format_f = _extraire_format_norm(f"{texte_f} {desc_brut}")
            mots_prod_sans_marque = mots_f - _mots_significatifs(marque_f)

            if not mots_f:
                continue

            match_trouve = None

            if p_promo > 0:
                meme_prix = df_superc[df_superc['prix_possibles'].apply(lambda s: any(abs(p - p_promo) <= 0.03 for p in s))]
                best_score = 0.0
                for _, r_sc in meme_prix.iterrows():
                    if marque_f and r_sc['marque_norm'] and not ('irresistible' in marque_f and 'irresistible' in r_sc['marque_norm']):
                        if (marque_f not in r_sc['marque_norm']) and (r_sc['marque_norm'] not in marque_f):
                            continue
                    mots_sc_sans_marque = r_sc['mots'] - _mots_significatifs(r_sc['marque_norm'])
                    communs_prod = mots_prod_sans_marque.intersection(mots_sc_sans_marque)
                    communs_forts = forts_f.intersection(r_sc['mots_forts'])
                    marque_ok = bool(marque_f and r_sc['marque_norm'] and (marque_f in r_sc['marque_norm'] or r_sc['marque_norm'] in marque_f))

                    if mots_prod_sans_marque and not communs_prod:
                        continue
                    if not communs_forts and not (marque_ok and communs_prod):
                        continue

                    score = len(communs_forts) * 20 + len(communs_prod) * 10
                    if p_reg > 0 and abs(r_sc['prix_reg_site'] - p_reg) <= 0.05:
                        score += 20
                    if marque_ok:
                        score += 25
                    if format_f and r_sc['format_norm'] == format_f:
                        score += 15
                    elif format_f and r_sc['format_norm'] and format_f != r_sc['format_norm']:
                        score -= 15

                    if score > best_score and score >= 40:
                        best_score = score
                        match_trouve = r_sc

            if match_trouve is None and p_promo > 0:
                meme_prix = df_superc[df_superc['prix_possibles'].apply(lambda s: any(abs(p - p_promo) <= 0.03 for p in s))]
                best_sim = 0.0
                for _, r_sc in meme_prix.iterrows():
                    if marque_f and r_sc['marque_norm'] and (marque_f not in r_sc['marque_norm']) and (r_sc['marque_norm'] not in marque_f):
                        continue
                    if not forts_f.intersection(r_sc['mots_forts']):
                        continue
                    sim = SequenceMatcher(None, _normaliser(texte_f), _normaliser(r_sc['nom_complet'])).ratio()
                    if sim > best_sim and sim >= 0.52:
                        best_sim = sim
                        match_trouve = r_sc

            if match_trouve is None and len(forts_f) >= 2:
                best_sim3 = 0.0
                for _, r_sc in df_superc.iterrows():
                    if marque_f and r_sc['marque_norm'] and (marque_f not in r_sc['marque_norm']) and (r_sc['marque_norm'] not in marque_f):
                        continue
                    if len(forts_f.intersection(r_sc['mots_forts'])) < 2:
                        continue
                    if format_f and r_sc['format_norm'] and format_f != r_sc['format_norm']:
                        continue
                    sim = SequenceMatcher(None, _normaliser(texte_f), _normaliser(r_sc['nom_complet'])).ratio()
                    if sim > best_sim3 and sim >= 0.62:
                        best_sim3 = sim
                        match_trouve = r_sc

            if match_trouve is not None:
                df_global.at[idx, 'code_upc'] = match_trouve['code_upc']
                if not marque_brut and match_trouve['head__brand']:
                    df_global.at[idx, 'marque'] = match_trouve['head__brand']
                if not df_global.at[idx, 'prix_regulier'] and match_trouve['prix_reg_site'] > 0:
                    df_global.at[idx, 'prix_regulier'] = f"{match_trouve['prix_reg_site']:.2f}"
                upc_utilises.add(match_trouve['code_upc'])
                break

    if inclure_variantes_superc:
        nouvelles_lignes = []
        for _, r_sc in df_superc.iterrows():
            if r_sc['code_upc'] not in upc_utilises:
                p_site = r_sc['prix_promo_site']
                p_reg_s = r_sc['prix_reg_site']
                nouvelles_lignes.append({
                    'marchand': 'Super C',
                    'marque': r_sc.get('head__brand', ''),
                    'produit': r_sc.get('head__title', ''),
                    'code_upc': r_sc['code_upc'],
                    'prix_circulaire': f"{p_site:.2f}" if p_site > 0 else '',
                    'prix_unitaire': p_site if p_site > 0 else 0.0,
                    'unite_prix': '',
                    'prix_regulier': f"{p_reg_s:.2f}" if p_reg_s > 0 else '',
                    'format': _extraire_format_norm(r_sc['nom_complet']),
                    'condition': '',
                    'description': '',
                    'valide_du': valide_du_sc,
                    'valide_au': valide_au_sc,
                    'flyer_id': 'superc_direct',
                })
        if nouvelles_lignes:
            df_global = pd.concat([df_global, pd.DataFrame(nouvelles_lignes)], ignore_index=True)

    return df_global
