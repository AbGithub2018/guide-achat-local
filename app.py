import requests, json, random, re
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageEnhance
import numpy as np
import pandas as pd
from rapidocr_onnxruntime import RapidOCR

FLYERS = 'https://flyers-ng.flippback.com/api/flipp/data?locale=fr&postal_code={}&sid={}'
FLYER_ITEMS = 'https://flyers-ng.flippback.com/api/flipp/flyers/{}/flyer_items?locale=fr&sid={}'

# Test ciblé sur Super C (remettez toutes les bannières une fois validé)
GROCERY_STORES = {
    'Maxi', 'IGA', 'Super C', 'Metro', 'Provigo', 
    'Intermarché', 'Marché Tradition', 'Tradition', 'Bonichoix'
}
SESSION_HTTP = requests.Session()

def generate_sid():
    return ''.join(str(random.randint(0, 9)) for _ in range(16))

def get_flyers_by_postal_code(postal_code: str):
    sid = generate_sid()
    url = FLYERS.format(postal_code, sid)
    response = SESSION_HTTP.get(url)
    response.raise_for_status() 
    return response.json()

def get_grocery_flyer_id(postal_code: str):
    response_data = get_flyers_by_postal_code(postal_code)
    if 'flyers' not in response_data:
        return None
        
    grocery_flyers = []
    for flyer in response_data['flyers']:
        merchant = flyer.get('merchant')
        categories = flyer.get('categories', [])
        if isinstance(categories, str):
            categories = [cat.strip() for cat in categories.split(',')]
        
        if merchant in GROCERY_STORES:
            if any(cat in categories for cat in ['Groceries', 'Épicerie', 'Pharmacie', 'Pharmacy', 'Marchandise générale', 'General Merchandise']):
                grocery_flyers.append({
                    'id': flyer['id'],
                    'merchant': merchant
                })
    return grocery_flyers if grocery_flyers else None

def get_flyer_items(flyer_id: int):
    sid = generate_sid()
    url = FLYER_ITEMS.format(flyer_id, sid)
    response = SESSION_HTTP.get(url)
    response.raise_for_status()
    return response.json()

def formater_prix_match(dollars: str, cents: str) -> float:
    return float(f"{int(dollars)}.{cents}")

def extraire_texte_regulier(texte: str, prix_circulaire: float) -> str:
    """Détecte le prix régulier via 3 niveaux : mot-clé (reg.), Économisez, ou prix barré."""
    if not texte:
        return ''
    
    texte_propre = re.sub(r'\s+', ' ', texte)
    
    # NIVEAU 1 : Mots-clés explicites (reg., req., cour., ord., prix courant)
    mot_cle = r'(?:r[eéè€c][gq9][.,:;]?|cour\.?|ord\.?|valeur(?:\s*de)?|prix\s*(?:r[eéè]gulier|courant))'
    prix_sep = r'(\d{1,3})\s*[.,$]\s*(\d{2})'
    prix_colle = r'(\d{1,2})(\d{2})'
    prix_any = rf'(?:{prix_sep}|{prix_colle})'

    def lire_groupe_prix(match, idx_start):
        if match.group(idx_start) is not None:
            return formater_prix_match(match.group(idx_start), match.group(idx_start + 1))
        return formater_prix_match(match.group(idx_start + 2), match.group(idx_start + 3))

    # 1A. Fourchette explicite
    match_fourchette = re.search(
        rf'{mot_cle}\s*(?:de\s*)?{prix_any}\s*(?:[aà]|-|au)\s*{prix_any}',
        texte_propre,
        re.IGNORECASE
    )
    if match_fourchette:
        p1 = lire_groupe_prix(match_fourchette, 1)
        p2 = lire_groupe_prix(match_fourchette, 5)
        if 0 < p1 < 200 and 0 < p2 < 200 and p1 <= p2:
            return f"{p1:.2f} à {p2:.2f}"

    # 1B. Prix régulier unique explicite
    match_unique = re.search(
        rf'{mot_cle}\s*(?:de\s*|:)?\s*{prix_any}',
        texte_propre,
        re.IGNORECASE
    )
    if match_unique:
        p_val = lire_groupe_prix(match_unique, 1)
        fin_match = texte_propre[match_unique.end():match_unique.end() + 5].lower()
        if not re.match(r'^\s*(?:ml|g|kg|lb|un|oz)\b', fin_match) and 0 < p_val < 200:
            return f"{p_val:.2f}"

    # NIVEAU 2 : Calcul depuis "Économisez X,XX $" ou "Épargnez X $"
    if prix_circulaire > 0:
        match_eco = re.search(
            r'(?:[eé]conomisez|[eé]pargnez|rabais(?:\s*de)?)\s*(\d{1,2})(?:[.,$](\d{2}))?\s*\$?',
            texte_propre,
            re.IGNORECASE
        )
        if match_eco:
            dollars_eco = int(match_eco.group(1))
            cents_eco = int(match_eco.group(2)) if match_eco.group(2) else 0
            economie = dollars_eco + (cents_eco / 100.0)
            if 0 < economie < 100:
                return f"{(prix_circulaire + economie):.2f}"

    # NIVEAU 3 : Second prix sur l'affiche (prix barré sans le mot "reg.")
    if prix_circulaire > 0:
        tous_les_prix = re.finditer(
            r'(?<!\d)(\d{1,3})\s*[.,$]\s*(\d{2})(?!\s*(?:/\s*(?:lb|kg)|lb|kg|ml|g|oz))',
            texte_propre,
            re.IGNORECASE
        )
        candidats = []
        for m in tous_les_prix:
            val = formater_prix_match(m.group(1), m.group(2))
            if prix_circulaire < val < (prix_circulaire * 3.0) and val < 150:
                candidats.append(val)
        
        candidats_uniques = sorted(list(set(candidats)))
        if len(candidats_uniques) == 1:
            return f"{candidats_uniques[0]:.2f}"
        elif len(candidats_uniques) == 2 and (candidats_uniques[1] - candidats_uniques[0]) <= 3.0:
            return f"{candidats_uniques[0]:.2f} à {candidats_uniques[1]:.2f}"

    return ''

def lire_prix_regulier_image(image_url: str, prix_circulaire: float, lecteur_ocr) -> str:
    """Lecture rapide et haute précision avec RapidOCR."""
    if not image_url:
        return ''
    try:
        resp = SESSION_HTTP.get(image_url, timeout=6)
        img = Image.open(BytesIO(resp.content)).convert('RGB')
        
        # Zoom x2.0 + netteté (RapidOCR lit très vite et finement à cette taille)
        nouvelle_taille = (int(img.width * 2.0), int(img.height * 2.0))
        img_x2 = img.resize(nouvelle_taille, Image.Resampling.LANCZOS)
        img_x2 = ImageEnhance.Sharpness(img_x2).enhance(1.5)
        
        resultats, _ = lecteur_ocr(np.array(img_x2))
        texte_complet = ' '.join([ligne[1] for ligne in resultats]) if resultats else ''
        
        return extraire_texte_regulier(texte_complet, prix_circulaire)
    except Exception:
        return ''

def traiter_article(item, merchant, flyer_id, lecteur_ocr):
    nom_brut = str(item.get('name', '')).strip()
    nom_fr, _, _ = nom_brut.partition('|')
    nom = nom_fr.strip()
    
    prix = item.get('price', '')
    if not nom or prix in [None, '']:
        return None
    if nom.lower().startswith('banner -') or nom.lower() in ['cliquer ici', 'cliquez ici', 'voir la brochure']:
        return None
        
    try:
        prix_float = float(str(prix).replace(',', '.'))
    except ValueError:
        prix_float = 0.0

    description = str(item.get('description') or '').strip()
    image_url = str(item.get('cutout_image_url') or '').strip()
    
    champs_texte = ' '.join(
        str(item.get(k) or '') for k in ['description', 'sale_story', 'pre_price_text', 'post_price_text']
    )
    prix_regulier = extraire_texte_regulier(champs_texte, prix_float)
    
    if not prix_regulier and image_url:
        prix_regulier = lire_prix_regulier_image(image_url, prix_float, lecteur_ocr)
        if prix_regulier:
            print(f'  -> Trouvé ({merchant}) : {nom} | Circulaire: {prix} $ | Régulier: {prix_regulier} $')
            
    return {
        'marchand': merchant,
        'marque': str(item.get('brand') or '').strip(),
        'produit': nom,
        'prix_circulaire': prix,
        'prix_regulier': prix_regulier,
        'description': description,
        'valide_du': str(item.get('valid_from', ''))[:10],
        'valide_au': str(item.get('valid_to', ''))[:10],
        'image_url': image_url,
        'flyer_id': flyer_id
    }

def main():
    while True:
        postal_code = input('Entrez votre code postal (ex. G5Y4H3) : ').strip().replace(' ', '').upper()
        if len(postal_code) == 6:
            break
        print('Format invalide. Utilisez 6 caractères (ex. G5Y4H3).')
    
    print('\nInitialisation de RapidOCR...')
    lecteur_ocr = RapidOCR()
    
    print(f'Recherche des circulaires d\'épicerie pour : {postal_code}...')
    grocery_flyers = get_grocery_flyer_id(postal_code)
    
    if not grocery_flyers:
        print('Aucune circulaire trouvée.')
        return
    
    csv_data = []
    for flyer in grocery_flyers:
        flyer_id = flyer['id']
        merchant = flyer['merchant']
        print(f'\nAnalyse rapide en parallèle de {merchant} (ID: {flyer_id})...')
        items = get_flyer_items(flyer_id)
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(traiter_article, item, merchant, flyer_id, lecteur_ocr) for item in items]
            for future in futures:
                res = future.result()
                if res:
                    csv_data.append(res)
    
    if csv_data:
        df = pd.DataFrame(csv_data)
        df = df.drop_duplicates(subset=['marchand', 'produit', 'prix_circulaire'])
        compteur_reg = df['prix_regulier'].astype(bool).sum()
        filename = f'flyer_items_{postal_code}.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f'\nSuccès ! {len(df)} produits enregistrés ({compteur_reg} prix réguliers détectés) dans {filename}')
    else:
        print('Aucun article trouvé.')

if __name__ == '__main__':
    main()
