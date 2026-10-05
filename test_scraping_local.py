import pandas as pd
import re
import os

def detecter_origine_nom(nom):
    """
    Analyse le nom ou la description du produit scrappé pour détecter
    l'origine (Québec, Canada, USA, ou Ailleurs).
    """
    if pd.isna(nom):
        return "Inconnu (Nom manquant)"
    
    nom_lower = str(nom).lower()
    
    # Mots-clés pour le Québec (Priorité 1)
    keywords_quebec = [
        r"qu[ée]bec", r"qc", r"lac-saint-jean", r"charlevoix", r"estrie", 
        r"beauce", r"érablière", r"orléans", r"local", r"d'ici"
    ]
    # Mots-clés pour le Canada (Priorité 2)
    keywords_canada = [
        r"canada", r"canadien", r"ontario", r"maritimes", r"alberta", r"bc"
    ]
    # Mots-clés pour les USA (Priorité 3)
    keywords_usa = [
        r"usa", r"états-unis", r"californie", r"floride", r"american", r"us"
    ]

    # Vérification par expressions régulières
    if any(re.search(kw, nom_lower) for kw in keywords_quebec):
        return "Fabriqué au Québec ⚜️"
    elif any(re.search(kw, nom_lower) for kw in keywords_canada):
        return "Canada 🇨🇦"
    elif any(re.search(kw, nom_lower) for kw in keywords_usa):
        return "États-Unis 🇺🇸"
    else:
        return "Ailleurs / À valider par l'UPC 🌍"

def tester_et_enrichir_csv(fichier_entrée, fichier_sortie="resultat_test_provenance.csv"):
    if not os.path.exists(fichier_entrée):
        print(f"Erreur : Le fichier de test '{fichier_entrée}' est introuvable.")
        return

    # Chargement des données
    df = pd.read_csv(fichier_entrée)
    df.columns = df.columns.str.strip() # Nettoyer les espaces dans les titres de colonnes

    print(f"🔬 Analyse de {len(df)} lignes de test...")

    # 1. Validation du format du code UPC (doit être numérique et faire idéalement 12 chiffres)
    df['upc_propre'] = df['code_upc'].astype(str).str.strip().str.zfill(12)
    df['upc_valide'] = df['upc_propre'].str.isdigit() & (df['upc_propre'].str.len() <= 13)

    # 2. Extraction et classification de l'origine basée sur le texte scrappé
    df['origine_detectee'] = df['nom'].apply(detecter_origine_nom)

    # Sauvegarde du fichier enrichi
    df.to_csv(fichier_sortie, index=False)
    
    # Affichage du bilan textuel dans le terminal
    print("\n=========================================")
    print("📊 BILAN DU TEST DE PROVENANCE (TEXTE)")
    print("=========================================")
    print(df['origine_detectee'].value_counts())
    print("=========================================")
    print(f"Anomalies de codes UPC détectées : {len(df[df['upc_valide'] == False])}")
    print(f"Fichier de test enrichi sauvegardé sous : {fichier_sortie}")

if __name__ == "__main__":
    # Exécution sur notre fichier de test
    tester_et_enrichir_csv("data_test.csv")
