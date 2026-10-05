import streamlit as st
import pandas as pd
import re

# Configuration de la page
st.set_page_config(page_title="Comparateur Épicerie Québec", page_icon="⚜️", layout="wide")

st.title("⚜️ Outil de Provenance Alimentaire & Comparateur (Québec)")
st.write("Analysez notre base de données de plus de 10 000 produits pour savoir où va votre argent.")

# Chargement intelligent des 10 460 lignes (avec mise en cache Streamlit)
@st.cache_data
def charger_et_analyser_base():
    url_sheet = "https://google.com"
    try:
        df = pd.read_csv(url_sheet, sep='\t')
        df.columns = df.columns.str.strip()
        
        # Nettoyage des codes UPC brisés par Excel (ex: notation scientifique)
        def nettoyer_upc(val):
            val_str = str(val).strip()
            if "E+" in val_str or "," in val_str:
                return "Erreur format Excel"
            return re.sub(r'\D', '', val_str).zfill(12) if any(c.isdigit() for c in val_str) else "Invalide"
            
        df['upc_propre'] = df['code_upc'].apply(nettoyer_upc)
        
        # Fonction interne de catégorisation rapide pour les statistiques
        def detecter_origine_rapide(row):
            nom_lower = str(row['nom']).lower() if pd.notna(row['nom']) else ""
            if any(re.search(kw, nom_lower) for kw in [r"qu[ée]bec", r"qc", r"lac-saint-jean", r"charlevoix", r"estrie", r"st-valentin", r"orléans", r"miel pur"]):
                return "Québec ⚜️"
            if any(re.search(kw, nom_lower) for kw in [r"canada", r"canadien", r"ontario", r"vancouver", r"wonder"]):
                return "Canada 🇨🇦"
            if any(re.search(kw, nom_lower) for kw in [r"usa", r"états-unis", r"californie", r"floride", r"key"]):
                return "États-Unis 🇺🇸"
            
            # Vérification des préfixes de codes-barres mondiaux (GS1)
            upc = row['upc_propre']
            if upc.isdigit() and len(upc) >= 3:
                if 0 <= int(upc[:2]) <= 13:
                    return "Enregistré au Canada/USA (À valider)"
                elif 300 <= int(upc[:3]) <= 379:
                    return "France 🇫🇷"
                elif 690 <= int(upc[:3]) <= 699:
                    return "Chine 🇨🇳"
            return "Autre / À valider 🌍"
            
        df['provenance_estimee'] = df.apply(detecter_origine_rapide, axis=1)
        return df
    except Exception as e:
        st.error(f"Impossible de se connecter au Google Sheet : {e}")
        return None

# Lancement du chargement
df_complet = charger_et_analyser_base()

if df_complet is not None:
    # ---------------------------------------------------------
    # SECTION 1 : TABLEAU DE BORD & STATISTIQUES GLOBALES
    # ---------------------------------------------------------
    st.header("📊 Statistiques de la base de données en direct")
    
    # Calcul des compteurs
    total_produits = len(df_complet)
    total_quebec = len(df_complet[df_complet['provenance_estimee'] == "Québec ⚜️"])
    erreurs_upc = len(df_complet[df_complet['upc_propre'] == "Erreur format Excel"])
    
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(label="Total des produits référencés", value=f"{total_produits:,}")
    with col_m2:
        st.metric(label="Produits identifiés d'ici ⚜️", value=f"{total_quebec:,}", delta=f"{(total_quebec/total_produits)*100:.1f}% de la base")
    with col_m3:
        st.metric(label="Codes UPC à corriger (Erreur Excel)", value=erreurs_upc, delta="- Action requise" if erreurs_upc > 0 else "Parfait", delta_color="inverse")
        
    # Graphique de répartition de la provenance
    st.subheader("🌍 Répartition estimée des produits")
    stats_provenance = df_complet['provenance_estimee'].value_counts()
    st.bar_chart(stats_provenance)
    
    st.divider()

    # ---------------------------------------------------------
    # SECTION 2 : RECHERCHE POUR LES CONSOMMATEURS
    # ---------------------------------------------------------
    st.header("🔍 Rechercher un produit alimentaire")
    recherche = st.text_input("Entrez un nom de produit ou un code UPC (ex: Sirop d'érable, 058496...) :", "")
    
    if recherche:
        recherche_clean = recherche.strip().lower()
        
        # Filtrer la base selon le nom ou l'UPC parmi vos 19 colonnes
        resultats = df_complet[
            df_complet['nom'].astype(str).str.lower().str.contains(recherche_clean) |
            df_complet['code_upc'].astype(str).str.contains(recherche_clean)
        ]
        
        if not resultats.empty:
            st.success(f"💡 {len(resultats)} produit(s) trouvé(s) ! Affichage des 10 premiers résultats :")
            
            for idx, row in resultats.head(10).iterrows():
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.subheader(row['nom'])
                        st.caption(f"Code UPC brut : {row['code_upc']} | Index de la ligne : {idx + 2}")
                    with c2:
                        st.info(f"**Provenance :** \n\n{row['provenance_estimee']}")
                    st.divider()
        else:
            st.warning("Aucun produit ne correspond à ce nom ou ce code-barres dans la base actuelle.")
else:
    st.warning("En attente des données...")
