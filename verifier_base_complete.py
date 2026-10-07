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
def classifier_produit_exact(nom_produit):
    """Analyse le nom du produit et retourne (Categorie, Sous_Categorie)."""
    nom = str(nom_produit).lower().strip()
    
    # =========================================================================
    # 1. PRODUITS FRAIS ET PÉRISSABLES
    # =========================================================================
    if any(m in nom for m in ["lait de", "lait homogénéisé", "lait 1%", "lait 2%", "lait 0%", "crème à cuisson", "crème à café", "creme 15%", "creme 35%", "ultra'crème", "québon", "sealtest", "lactantia", "nutrilait"]):
        if not any(x in nom for x in ["chocolat", "chocolate", "amande", "soya", "avoine", "coco", "bacon"]):
            return "1. Produits frais et périssables", "Produits laitiers et Œufs"
    if any(m in nom for m in ["fromage", "cheddar", "mozzarella", "mozzarellissima", "parmesan", "feta", "ricotta", "mascarpone", "gouda", "swiss", "suisse", "havarti", "bocconcini", "cheestrings", "ficello", "la vache qui rit", "philadelphia", "cottage", "le cendrillion", "oka", "mizithra", "paneer", "st agur", "grana padano"]):
        return "1. Produits frais et périssables", "Produits laitiers et Œufs"
    if any(m in nom for m in ["yogourt", "yogurt", "yaourt", "skyr", "oikos", "activia", "iogo", "yop", "danone", "danino", "pouding", "pudding", "kefir", "kéfir", "danette"]):
        return "1. Produits frais et périssables", "Yogourts et desserts laitiers"
    if any(m in nom for m in ["œuf", "oeuf", "oeufs", "blancs d'oeuf", "créations oeufs", "naturoeuf", "nutri"]):
        return "1. Produits frais et périssables", "Œufs et succédanés"
    if any(m in nom for m in ["beurre", "butter", "margarine", "becel", "crystal margarine", "imperial"]):
        return "1. Produits frais et périssables", "Beurre et margarines"
    if any(m in nom for m in ["poulet", "chicken", "dinde", "turkey", "dindon", "volaille", "poitrine", "cuisse", "ailes", "nuggets", "souvlakis", "bovril aux poulet"]):
        return "1. Produits frais et périssables", "Viandes et Volailles"
    if any(m in nom for m in ["bœuf", "boeuf", "porc", "veau", "agneau", "haché", "steak", "rôti", "roti", "bifteck", "grillade", "meatballs", "bovril boeuf", "longe de porc"]):
        return "1. Produits frais et périssables", "Viandes et Volailles"
    if any(m in nom for m in ["jambon", "bacon", "saucisse", "saucisson", "charcuterie", "pepperoni", "salami", "bologne", "baloney", "cretons", "pancetta", "rosette de lyon"]):
        return "1. Produits frais et périssables", "Viandes et Volailles"
    if any(m in nom for m in ["crevette", "shrimp", "pétoncle", "moule", "homard", "lobster", "calmar", "calamari", "fruits de mer", "palourdes"]):
        return "1. Produits frais et périssables", "Poissons et Fruits de mer"
    if any(m in nom for m in ["saumon", "salmon", "truite", "morue", "cod ", "aiglefin", "hadock", "sole ", "thon", "tuna", "sardine", "maquereau", "anchois", "poisson", "flétan"]):
        return "1. Produits frais et périssables", "Poissons et Fruits de mer"
    if any(m in nom for m in ["fraise", "strawberry", "bleuet", "blueberry", "framboise", "raspberry", "mûre", "blackberry", "pomme", "apple", "poire", "pear", "orange", "citron", "lemon", "lime", "banane", "banana", "ananas", "pineapple", "mangue", "mango", "pamplemousse", "grapefruit", "kiwi", "cantaloup", "clémentine", "clementine"]):
        return "1. Produits frais et périssables", "Fruits et Légumes"
    if any(m in nom for m in ["carotte", "carrot", "céleri", "celery", "laitue", "lettuce", "salade", "salad", "épinard", "spinach", "chou ", "cabbage", "tomate", "tomato", "oignon", "onion", "ail ", "garlic", "avocat", "avocado", "poivron", "pepper", "jalapeño", "jalapeno", "champignon", "mushroom", "patate", "potato", "frite", "poireau", "leek", "brocoli", "broccoli", "fine herbe", "radis", "thyme", "persil", "échalotes"]):
        return "1. Produits frais et périssables", "Fruits et Légumes"
        # =========================================================================
    # 2. ÉPICERIE SÈCHE (LES ALLÉES CENTRALES)
    # =========================================================================
    if any(m in nom for m in ["pain", "bread", "loaf", "superclub pom", "miche"]):
        return "2. Épicerie sèche (Les allées centrales)", "Boulangerie et Pâtisserie"
    if any(m in nom for m in ["tortilla", "pita", "naan", "wraps", "wrap ", "flatbread"]):
        return "2. Épicerie sèche (Les allées centrales)", "Boulangerie et Pâtisserie"
    if any(m in nom for m in ["bagel", "muffin", "croissant", "brioche", "briochettes", "chocolatine", "english muffins", "crumpets"]):
        return "2. Épicerie sèche (Les allées centrales)", "Boulangerie et Pâtisserie"
    if any(m in nom for m in ["gâteau", "gateau", "cake", "tarte", "pie ", "pâtisserie", "patisserie", "vol au vent", "chausson", "madeleines", "strudel"]):
        return "2. Épicerie sèche (Les allées centrales)", "Boulangerie et Pâtisserie"
    if any(m in nom for m in ["riz ", "rice", "pâtes", "pates", "pasta", "spaghetti", "macaroni", "fusilli", "penne", "linguine", "nouille", "noodle", "ramen", "vermicelle", "quinoa", "couscous", "orzo"]):
        return "2. Épicerie sèche (Les allées centrales)", "Épicerie salée et Garde-manger"
    if any(m in nom for m in ["huile", "oil ", "vinaigre", "vinegar", "moutarde", "mustard", "ketchup", "mayonnaise", "mayo ", "relish", "pesto", "salsa", "sauce", "vinaigrette", "dressing", "tahini"]):
        return "2. Épicerie sèche (Les allées centrales)", "Épicerie salée et Garde-manger"
    if any(m in nom for m in ["conserve", "soupe", "soup", "bouillon", "broth", "bovril", "fèves", "feves", "beans", "lentille", "lentil", "pois ", "peas", "pois chiche", "chickpeas", "haricot", "artichaut", "olives", "clark", "aylmer", "unico", "bush's", "campbell", "habitant"]):
        return "2. Épicerie sèche (Les allées centrales)", "Épicerie salée et Garde-manger"
    if any(m in nom for m in ["farine", "flour", "sucre", "sugar", "cassonade", "poudre à pâte", "poudre a pate", "bicarbonate", "levure", "fecule", "fécule", "cocoa", "cacao", "baking", "maizena", "truvia", "splenda", "gelatine", "gélatine", "glaçage", "frosting"]):
        return "2. Épicerie sèche (Les allées centrales)", "Épicerie salée et Garde-manger"
    if any(m in nom for m in ["céréale", "cereal", "cheerios", "flakes", "krispies", "shreddies", "oatmeal", "gruau", "granola", "froot loops", "corn pops", "frosted flakes"]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"
    if any(m in nom for m in ["miel", "honey", "sirop", "syrup", "érable", "maple", "tartinade", "nutella", "spread", "confiture", "jam "]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"
    if any(m in nom for m in ["chips", "croustille", "crisps", "pringles", "ruffles", "doritos", "cheetos", "takis", "popcorn", "maïs soufflé", "bretzel", "pretzel", "craquelin", "cracker", "crispers", "hickory sticks", "vinta"]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"
    if any(m in nom for m in ["barre tendre", "barre granola", "granola bar", "clif", "kind bar", "chewy", "m&m", "mars", "snickers", "kitkat", "twix", "skittles", "turtles", "smarties", "lindor", "lindt", "bonbon", "candy", "friandise", "oreo", "pattes d'ours", "bear paws", "célébration", "kinder"]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"
    if any(m in nom for m in ["noix", "nuts", "amande", "almond", "cacahuète", "peanut", "arachide", "cashew", "cajou", "pistache", "pistachios", "walnuts", "graine", "seeds"]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"

    # =========================================================================
    # 3. SURGELÉS ET BOISSONS
    # =========================================================================
    if any(m in nom for m in ["surgelé", "congelé", "frozen", "pizza", "lasagne", "lasaña", "wonton", "dumpling", "gyoza", "egg roll", "pâté impérial", "pogo", "perogies", "ravioli", "tortellini", "gnocchi", "delissio", "giuseppe"]):
        return "3. Surgelés et Boissons", "Aliments surgelés"
    if any(m in nom for m in ["pané", "panes", "janes", "pépites", "nuggets", "strips", "burgers", "wings", "ailes de poulet", "flamingo", "mères michel", "pinty's"]):
        return "3. Surgelés et Boissons", "Aliments surgelés"
    if any(m in nom for m in ["frites", "fries", "mélange de légumes", "mélange de petits fruits", "bleuets sauvages boréals", "mccain", "lamb weston"]):
        return "3. Surgelés et Boissons", "Aliments surgelés"
    if any(m in nom for m in ["glace", "sorbet", "creme glacee", "crème glacée", "ice cream", "magnum", "drumstick", "haagen", "chapman", "coolway", "parlour", "melona", "revello"]):
        return "3. Surgelés et Boissons", "Aliments surgelés"
    if any(m in nom for m in ["coke", "pepsi", "7up", "soda", "gazeuse", "eaux pétillantes", "pétillante", "bubly", "perrier", "fresca", "crush orange", "dr pepper", "sprite", "eska", "dasani", "montellier", "aquafina", "zevia"]):
        return "3. Surgelés et Boissons", "Boissons (non alcoolisées)"
    if any(m in nom for m in ["jus ", "jus de", "nectar", "limonade", "tropicana", "fruit punch", "punch aux fruits", "snapple", "oasis", "fruitsations", "pure leaf", "nestea", "apple juice", "orange juice", "ocean spray", "sunrype", "v8"]):
        return "3. Surgelés et Boissons", "Boissons (non alcoolisées)"
    if any(m in nom for m in ["café", "cafe ", "cappuccino", "thé ", "the ", "tisane", "infusion", "van houtte", "tim hortons", "maxwell house", "starbucks", "twinings", "mccafé", "nabob", "tassimo"]):
        return "3. Surgelés et Boissons", "Boissons (non alcoolisées)"
    if any(m in nom for m in ["lait d'amande", "lait de soya", "lait d'avoine", "boisson végétale", "silk", "so nice", "sofresh", "milked oats"]):
        return "3. Surgelés et Boissons", "Boissons (non alcoolisées)"
    if any(m in nom for m in ["beer", "bière", "biere", "microbrasserie", "st-ambroise", "coors", "lager", "sleeman", "bud light", "budweiser", "heineken", "madjack", "vin ", "vins", "bordeaux", "sauvignon", "shiraz", "barefoot", "cidre"]):
        return "3. Surgelés et Boissons", "Bières et Vins (Alcools)"

    # =========================================================================
    # 4. CATÉGORIES SPÉCIALISÉES
    # =========================================================================
    if "sushi" in nom or "california roll" in nom:
        return "4. Catégories spécialisées", "Prêt-à-manger / Traiteur"
    if any(m in nom for m in ["sandwich", "wrap ", "salade préparée", "salade de poulet", "salade de jambon", "salade de chou", "coleslaw", "poulet rôti chaud", "poulet cuit et chaud"]):
        return "4. Catégories spécialisées", "Prêt-à-manger / Traiteur"
    if "biologique" in nom or "bio " in nom or "organic" in nom:
        return "4. Catégories spécialisées", "Alimentation saine et produits naturels"

    return "Épicerie générale", "Non classifié"


    # Compilation du rapport final

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
        # 2. Remplissage automatique des nouvelles catégories (Colonne V et W)
    cats = []
    sous_cats = []
    for _, row in df.iterrows():
        c, sc = classifier_produit_exact(row['nom'])
        cats.append(c)
        sous_cats.append(sc)
        
    df['categorie'] = cats         # Écrit le niveau 1 dans la Colonne V
    df['sous_categorie'] = sous_cats   # Écrit le niveau 2 dans la Colonne W


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
