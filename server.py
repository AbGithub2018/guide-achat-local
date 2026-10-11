from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List

app = FastAPI()

# Autorise la communication entre le fichier HTML du téléphone et l'API Python Cloud
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def obtenir_connexion_sheets():
    scope = ["https://google.com", "https://googleapis.com"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("secrets_google.json", scope)
    client = gspread.authorize(creds)
    # Remplacer par le NOM EXACT de votre fichier Google Sheets si nécessaire
    return client.open("Acheter Québécois & Canadien")

class ScanItem(BaseModel):
    code_upc: str
    horodatage: str

@app.post("/api/synchroniser")
def synchroniser_codes(scans: List[ScanItem]):
    try:
        classeur = obtenir_connexion_sheets()
        onglet_principal = classeur.worksheet("Sheet1")
        onglet_historique = classeur.worksheet("Historique_Prix")
        
        donnees_principales = onglet_principal.get_all_records()
        df_principal = pd.DataFrame(donnees_principales)
        df_principal.columns = [c.strip().lower() for c in df_principal.columns]
        
        nouvelles_lignes_historique = []

        for scan in scans:
            cup_nettoye = scan.code_upc.strip().lstrip('0')
            
            existe = False
            if 'code_upc' in df_principal.columns:
                df_principal['code_upc_str'] = df_principal['code_upc'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True).str.lstrip('0')
                match = df_principal[df_principal['code_upc_str'] == cup_nettoye]
                if not match.empty:
                    existe = True
            
            # Si le produit scanné n'existe pas encore dans votre base, on l'initialise dans Sheet1
            if not existe:
                nouvelle_fiche = [
                    scan.code_upc,
                    f"Nouveau produit ({scan.code_upc})",
                    "", "", "", "", "", "Canada", "", "", "", "", "", "", "", "", "", "", "", "", ""
                ]
                onglet_principal.append_row(nouvelle_fiche)
            
            # Préparation de l'entrée automatique pour l'onglet Historique_Prix
            nouvelles_lignes_historique.append([
                scan.horodatage, 
                scan.code_upc, 
                "Scan Magasin", 
                "", 
                "collaboratif"
            ])
            
        if nouvelles_lignes_historique:
            onglet_historique.append_rows(nouvelles_lignes_historique)
            
        return {"status": "success", "message": f"{len(scans)} scans synchronisés avec succès."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
