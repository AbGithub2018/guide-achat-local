import glob
import os
import pandas as pd

print("⏳ Début de la fusion de vos fichiers de bannières propres...")

# Recherche tous vos fichiers individuels propres
fichiers_bannieres = glob.glob("tous_les_*_quebec.csv")

if not fichiers_bannieres:
    print("❌ Aucun fichier trouvé. Assurez-vous d'être dans le bon dossier.")
else:
    liste_df = []
    for fichier in fichiers_bannieres:
        try:
            # Lecture en UTF-8 natif séparé par des virgules
            df = pd.read_csv(fichier, sep=",", encoding="utf-8")
            print(f"✅ Combiné avec succès : '{fichier}' ({len(df)} lignes)")
            liste_df.append(df)
        except Exception as e:
            print(f"⚠️ Erreur sur '{fichier}' : {e}")

    # Fusion globale en un tableau maître
    df_maitre = pd.concat(liste_df, ignore_index=True)
    
    # Nettoyage des doublons physiques exacts
    df_maitre = df_maitre.drop_duplicates(subset=["Adresse_Rue", "Nom_Commerce"])

    # Sauvegarde finale en écrasant l'ancien fichier défectueux
    df_maitre.to_csv("disponibilite_magasins.csv", index=False, sep=",")
    print(f"\n🚀 SUCCESS ! Le fichier unique 'disponibilite_magasins.csv' a été créé avec {len(df_maitre)} commerces réels.")
