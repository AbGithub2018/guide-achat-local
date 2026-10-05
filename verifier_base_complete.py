import pandas as pd
import re
import requests

def detecter_provenance_texte(nom):
    """Analyse les mots-clés du nom du produit pour trouver l'origine."""
    if pd.isna(nom):
        return "Inconnu (Nom manquant)"
    nom_lower = str(nom).lower()
    
    # 1. Priorité Québec ⚜️
    keywords_quebec = [r"qu[ée]bec", r"qc", r"lac-saint-jean", r"charlevoix", r"estrie", r"st-valentin", r"orléans", r"miel pur"]
    if any(re.search(kw, nom_lower) for kw in keywords_quebec):
        return "Québec ⚜️"
    
    # 2. Canada 🇨🇦
    keywords_canada = [r"canada", r"canadien", r"ontario", r"vancouver", r"wonder"]
    if any(re.search(kw, nom_lower) for kw in keywords_canada):
        return "Canada 🇨🇦"
    
    # 3. États-Unis 🇺🇸
    keywords_usa = [r"usa", r"états-unis", r"californie", r"floride", r"key"]
    if any(re.search(kw, nom_lower) for kw in keywords_usa):
        return "États-Unis 🇺🇸"
        
    return None

def determiner_pays_upc(upc_str):
    """Détermine le pays selon le préfixe mondial de l'UPC (GS1)."""
    if not upc_str.isdigit() or len(upc_str) < 3:
        return "Code Invalide/Notation Excel"
    prefixe_2 = int(upc_str[:2])
    prefixe_3 = int(upc_str[:3])
    
    if 0 <= prefixe_2 <= 13: 
        return "Enregistré au Canada / USA (À valider par le nom)"
    elif 300 <= prefixe_3 <= 379:
        return "Enregistré en France 🇫🇷"
    elif 520 <= prefixe_3 <= 521:
        return "Enregistré en Grèce 🇬🇷"
    elif 690 <= prefixe_3 <= 699:
        return "Enregistré en Chine 🇨🇳"
    else:
        return "Autre origine internationale 🌍"

def analyser_base_complete():
    # URL configurée pour extraire directement le format tsv (tabulations) de votre onglet public
    url_sheet = "https://google.com"
    
    print("🌐 Connexion à la base de données Google Sheet (10 460 lignes)...")
    try:
        df = pd.read_csv(url_sheet, sep='\t')
    except Exception as e:
        print(f"❌ Erreur lors de l'accès au fichier : {e}")
        print("Vérifiez bien que le partage est ouvert.")
        return

    # Nettoyage des noms de colonnes
    df.columns = df.columns.str.strip()

    if 'code_upc' not in df.columns or 'nom' not in df.columns:
        print("❌ Erreur : Les colonnes 'code_upc' ou 'nom' sont introuvables.")
        print(f"Colonnes détectées dans votre fichier : {list(df.columns)}")
        return

    print(f"✅ Fichier chargé ! Analyse de {len(df)} lignes en cours...")

    # Nettoyage des erreurs de formatage provoquées par Excel (ex: 6,1346E+12)
    def nettoyer_upc(val):
        val_str = str(val).strip()
        if "E+" in val_str or "," in val_str:
            return "Erreur format scientifique"
        return re.sub(r'\D', '', val_str).zfill(12) if any(c.isdigit() for c in val_str) else "Invalide"

    df['upc_propre'] = df['code_upc'].apply(nettoyer_upc)

    # Double vérification sémantique + préfixes GS1
    resultats = []
    for _, row in df.iterrows():
        origine = detecter_provenance_texte(row['nom'])
        if not origine:
            origine = determiner_pays_upc(row['upc_propre'])
        resultats.append(origine)
        
    df['provenance_estimee'] = resultats

    # Compilation du rapport final
    print("\n" + "="*50)
    print("📊 RAPPORT D'ANALYSE DE LA BASE DE DONNÉES COMPLÈTE")
    print("="*50)
    print(df['provenance_estimee'].value_counts())
    print("="*50)
    
    erreurs_excel = (df['upc_propre'] == "Erreur format scientifique").sum()
    print(f"⚠️ Nombre de codes UPC brisés par une notation scientifique Excel : {erreurs_excel}")
    print("="*50)

if __name__ == "__main__":
    analyser_base_complete()
