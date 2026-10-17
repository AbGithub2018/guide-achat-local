import pandas as pd
import sys

print("⏳ Étape 1 : Lecture directe de Etablissements.csv...")
try:
    df_etab = pd.read_csv("Etablissements.csv", low_memory=False)
except Exception as e:
    print(f"❌ Erreur : {e}")
    sys.exit()

# On passe les colonnes en majuscules pour correspondre au fichier officiel
df_etab.columns = [c.upper() for c in df_etab.columns]

print("🔍 Étape 2 : Filtrage automatique selon votre liste de bannières d'alimentation...")
# Votre liste officielle de mots-clés mise en majuscules
bannieres = [
    'IGA', 'SUPER C', 'SUPER-C', 'METRO', 'MAXI', 'PROVIGO', 
    'MARCHÉ TRADITION', 'MARCHE TRADITION', 'TIGRE GÉANT', 'TIGRE GEANT', 
    'MARCHÉ BONICHOIX', 'MARCHE BONICHOIX', 'DOLLARAMA', 'MARCHÉ AMI', 'MARCHE AMI', 
    'IGA EXPRESS', 'MARCHÉ RICHELIEU', 'MARCHE RICHELIEU', 'WALMART', 'MARCHÉ ADONIS', 'MARCHE ADONIS', 'COSTCO'
]

df_etab['NOM_ETAB_MAJ'] = df_etab['NOM_ETAB'].astype(str).str.upper()
df_vrais = df_etab[df_etab['NOM_ETAB_MAJ'].str.contains('|'.join(bannieres), na=False)].copy()

print(f"✅ {len(df_vrais)} établissements physiques trouvés au Québec avec vos critères.")

print("🛠️ Étape 3 : Reconstruction et formatage des codes postaux avec espace...")
df_final = pd.DataFrame()
df_final['Nom_Commerce'] = df_vrais['NOM_ETAB'].astype(str).str.strip()
df_final['Adresse_Rue'] = df_vrais['LIGN1_ADR'].astype(str).str.strip()
df_final['Municipalite'] = df_vrais['LIGN2_ADR'].astype(str).str.strip()

# Cette ligne prend le code collé de LIGN4_ADR (ex: H1J1Z1) et insère l'espace officiel (ex: H1J 1Z1)
def formater_code_postal(code):
    c = str(code).replace(" ", "").upper().strip()
    if len(c) == 6:
        return f"{c[:3]} {c[3:]}"
    return c

df_final['Code_Postal'] = df_vrais['LIGN4_ADR'].apply(formater_code_postal)

# Élimination des lignes vides ou invalides
df_final = df_final.dropna(subset=['Code_Postal'])
df_final = df_final[~df_final['Code_Postal'].isin(['NAN', 'INCONNU', ''])]
df_final = df_final.drop_duplicates(subset=['Adresse_Rue', 'Nom_Commerce'])

# Étape 4 : Sauvegarde forcée avec de VRAIES virgules et encodage universel UTF-8
df_final.to_csv("disponibilite_magasins.csv", index=False, sep=",", encoding="utf-8")

print("\n🚀 OPÉRATION TERMINÉE AVEC SUCCÈS !")
print(f"Le fichier 'disponibilite_magasins.csv' a été mis à jour et contient {len(df_final)} lignes parfaites.")
