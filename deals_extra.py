from datetime import datetime
from io import BytesIO
import base64
import uuid
import requests
from PIL import Image, ImageOps
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection


def compresser_photo_50ko(fichier_photo) -> bytes:
    """Redimensionne, redresse et compresse la photo pour qu'elle pèse <= 50 Ko."""
    fichier_photo.seek(0)
    img = Image.open(fichier_photo)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    for dimension in [(800, 800), (640, 640), (480, 480)]:
        img_copie = img.copy()
        img_copie.thumbnail(dimension)
        for qualite in (80, 65, 50, 35):
            tampon = BytesIO()
            img_copie.save(tampon, format="JPEG", quality=qualite, optimize=True)
            donnees = tampon.getvalue()
            if len(donnees) <= 51200:
                return donnees

    tampon = BytesIO()
    img_copie.save(tampon, format="JPEG", quality=25, optimize=True)
    return tampon.getvalue()


def televerser_vers_github(fichier_photo) -> str:
    """Envoie la photo compressée (< 50 Ko) dans image_circulaire/ sur GitHub (modèle app_web.py)."""
    try:
        UTILISATEUR_GH = "abgithub2018"
        DEPOT_GH = "guide-achat-local"
        TOKEN_GH = st.secrets["GITHUB_TOKEN"]

        octets_image = compresser_photo_50ko(fichier_photo)
        image_base64 = base64.b64encode(octets_image).decode("utf-8")

        horodatage_nom = pd.Timestamp.now(tz="America/Toronto").strftime("%Y%m%d_%H%M%S")
        id_court = uuid.uuid4().hex[:6]
        nom_fichier_image = f"deal_{horodatage_nom}_{id_court}.jpg"

        url_api_github = f"https://github.com{UTILISATEUR_GH}/{DEPOT_GH}/contents/image_circulaire/{nom_fichier_image}"
        headers_gh = {
            "Authorization": f"token {TOKEN_GH}",
            "Accept": "application/vnd.github.v3+json",
        }

        reponse_get = requests.get(url_api_github, headers=headers_gh)
        sha_fichier = None
        if reponse_get.status_code == 200:
            sha_fichier = reponse_get.json().get("sha")

        donnees_envoi = {
            "message": f"📸 Ajout photo Deal Extra ({nom_fichier_image}) via mobile",
            "content": image_base64,
        }
        if sha_fichier:
            donnees_envoi["sha"] = sha_fichier

        envoi_gh = requests.put(url_api_github, headers=headers_gh, json=donnees_envoi)
        if envoi_gh.status_code not in (200, 201):
            raise Exception(f"GitHub a répondu avec le code {envoi_gh.status_code}")

        lien_public_github = f"https://githubusercontent.com{UTILISATEUR_GH}/{DEPOT_GH}/main/image_circulaire/{nom_fichier_image}"
        return lien_public_github

    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde sur GitHub : {e}")
        return ""


@st.cache_data(ttl=300)
def charger_deals_extra(_conn):
    """Charge les Deals Extra approuvés depuis Google Sheets."""
    try:
        df = _conn.read(worksheet="Deals_Extra", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame()
        df.columns = [str(c).strip().lower() for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated()]
        if "statut" not in df.columns:
            return pd.DataFrame()
        df_approuves = df[df["statut"].fillna("").astype(str).str.strip().str.upper() == "APPROUVE"].copy()
        return df_approuves.iloc[::-1]
    except Exception:
        return pd.DataFrame()


@st.dialog("🔍 Aperçu de la trouvaille")
def agrandir_photo_deal(url_img: str, produit: str, prix: float, magasin: str, ville: str):
    st.image(url_img, use_container_width=True)
    st.markdown(f"### {produit} — :red[{prix:.2f} $]")
    st.caption(f"🏪 {magasin}" + (f" | 📍 {ville}" if ville else ""))
def afficher_section_deals_extra(banniere_active: str, ville_detectee: str, liens_officiels: dict, classer_rayon_fn):
    """Affiche le module communautaire Le Deal Extra (avec bascule automatique en mode démo si secrets absents)."""
    try:
        conn_gsheets = st.connection("gsheets", type=GSheetsConnection)
        _ = st.secrets["connections"]["gsheets"]
        df_deals_extra = charger_deals_extra(conn_gsheets)
        mode_demo = False
    except Exception:
        conn_gsheets = None
        mode_demo = True
        if "deals_demo_presse" not in st.session_state:
            st.session_state["deals_demo_presse"] = []
        df_deals_extra = pd.DataFrame(st.session_state["deals_demo_presse"])

    nb_deals = len(df_deals_extra)

    st.markdown("""
    <style>
    .st-key-bloc_deal_extra div[data-testid="stExpander"] {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%) !important;
        border: 2px solid #f59e0b !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2) !important;
        margin: 15px 0 !important;
    }
    .st-key-bloc_deal_extra div[data-testid="stExpander"] details summary {
        padding: 18px 22px !important;
    }
    .st-key-bloc_deal_extra div[data-testid="stExpander"] details summary p {
        font-size: 1.25rem !important;
        font-weight: 800 !important;
        color: #173782 !important;
    }
    .st-key-bloc_deal_extra div[data-testid="stExpander"]:hover {
        border-color: #d97706 !important;
        box-shadow: 0 6px 16px rgba(245, 158, 11, 0.3) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    titre_expander = (
        f"📸 LE DEAL EXTRA — {nb_deals} trouvaille(s) en magasin partagée(s) ! (Cliquez pour voir ou ajouter)"
        if nb_deals > 0
        else "📸 LE DEAL EXTRA — Vous voyez un rabais en épicerie ? Cliquez ici pour le partager !"
    )

    with st.container(key="bloc_deal_extra"):
        with st.expander(titre_expander, expanded=(nb_deals > 0)):
            tab_voir, tab_ajouter = st.tabs([
                f"🔥 Trouvailles en cours ({nb_deals})",
                "📢 Partager un Deal vu en magasin"
            ])

            with tab_voir:
                if df_deals_extra.empty:
                    st.info("Aucune trouvaille en cours pour le moment. Soyez le premier à partager un rabais repéré en rayon !")
                else:
                    cols_deals = st.columns(3)
                    for i, (_, deal) in enumerate(df_deals_extra.iterrows()):
                        with cols_deals[i % 3]:
                            with st.container(border=True):
                                d_prod = str(deal.get("produit", "")).strip()
                                d_mag = str(deal.get("magasin", "")).strip().upper()
                                d_ville = str(deal.get("ville", "")).strip()
                                d_pseudo = str(deal.get("pseudo", "Anonyme")).strip() or "Anonyme"
                                d_date = str(deal.get("date_soumission", "")).strip()
                                d_img = str(deal.get("lien_image", "")).strip()
                                try:
                                    d_prix = float(str(deal.get("prix", "0")).replace(",", "."))
                                except ValueError:
                                    d_prix = 0.0

                                c_img, c_txt = st.columns([1, 1.6])

                                with c_img:
                                    if d_img and (d_img.startswith("http") or d_img.startswith("data:image")):
                                        st.markdown(
                                            f"""
                                            <div style="width:100%; height:130px; border-radius:8px; background-color:#f8fafc; display:flex; align-items:center; justify-content:center; padding:4px;">
                                                <img src="{d_img}" style="max-width:100%; max-height:100%; object-fit:contain; border-radius:6px;" alt="{d_prod}" />
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )
                                        if st.button("🔍 Agrandir", key=f"zoom_deal_{i}", use_container_width=True):
                                            agrandir_photo_deal(d_img, d_prod, d_prix, d_mag, d_ville)

                                with c_txt:
                                    st.markdown(f"**{d_prod}**")
                                    st.markdown(
                                        f"<span style='color:#DC2626; font-size:20px; font-weight:900;'>{d_prix:.2f} $</span> — 🏪 **{d_mag}**",
                                        unsafe_allow_html=True,
                                    )
                                    infos_sub = [f"📍 {d_ville}"] if d_ville else []
                                    infos_sub.append(f"👤 {d_pseudo}")
                                    if d_date:
                                        infos_sub.append(f"📅 {d_date[:10]}")
                                    st.caption(" | ".join(infos_sub))

                                if st.button("➕ Ajouter à ma liste", key=f"btn_add_deal_{i}", use_container_width=True):
                                    st.session_state["panier_achats"].append({
                                        "magasin": d_mag if d_mag else banniere_active,
                                        "magasin_source": d_mag if d_mag else banniere_active,
                                        "catégorie": classer_rayon_fn(d_prod),
                                        "produit": f"📸 {d_prod}",
                                        "upc": "",
                                        "quantite": 1,
                                        "prix": d_prix,
                                        "economie": 0.0,
                                        "valide_au": "",
                                        "achete": False,
                                    })
                                    st.toast(f"✅ Deal Extra '{d_prod}' ajouté à votre facture !", icon="📸")
                                    st.rerun()
            with tab_ajouter:
                st.caption("Prenez l'étiquette ou le produit en photo avec votre cellulaire et partagez le rabais avec la communauté !")
                with st.form("form_soumission_deal_extra", clear_on_submit=True):
                    c_f1, c_f2 = st.columns(2)
                    liste_magasins = sorted(list(liens_officiels.keys())) + ["AUTRE"]
                    idx_defaut = liste_magasins.index(banniere_active) if banniere_active in liste_magasins else 0

                    with c_f1:
                        deal_produit = st.text_input("Nom du produit et format *", placeholder="Ex: Poitrines de poulet désossées")
                        deal_magasin = st.selectbox("Épicerie *", liste_magasins, index=idx_defaut)
                        deal_prix = st.number_input("Prix repéré ($) *", min_value=0.01, step=0.01, format="%.2f")
                    with c_f2:
                        deal_ville = st.text_input("Ville / Succursale *", value=ville_detectee, placeholder="Ex: Saint-Georges")
                        deal_pseudo = st.text_input("Votre prénom ou pseudo (optionnel)", placeholder="Ex: Marc Q.")
                        photo_cell = st.file_uploader(
                            "📸 Prendre une photo ou choisir dans la galerie",
                            type=["jpg", "jpeg", "png", "webp"],
                            help="Sur téléphone, appuyez ici pour ouvrir l'appareil photo (max 50 Ko).",
                        )

                    if st.form_submit_button("🚀 Envoyer mon Deal Extra", type="primary", use_container_width=True):
                        if not deal_produit.strip() or not deal_ville.strip() or deal_prix <= 0:
                            st.error("⚠️ Veuillez remplir le produit, le prix et la ville.")
                        elif mode_demo:
                            img_data_url = ""
                            if photo_cell is not None:
                                octets = compresser_photo_50ko(photo_cell)
                                b64 = base64.b64encode(octets).decode("utf-8")
                                img_data_url = f"data:image/jpeg;base64,{b64}"

                            st.session_state["deals_demo_presse"].insert(0, {
                                "statut": "APPROUVE",
                                "date_soumission": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "pseudo": deal_pseudo.strip() if deal_pseudo.strip() else "Anonyme",
                                "magasin": deal_magasin.strip(),
                                "ville": deal_ville.strip(),
                                "produit": deal_produit.strip(),
                                "prix": f"{deal_prix:.2f}",
                                "lien_image": img_data_url,
                            })
                            st.success("🎉 [Mode Démo Presse] En production, cette soumission envoie une alerte courriel pour modération avant publication. Ici, elle est affichée directement pour votre test !")
                            st.rerun()
                        else:
                            lien_github = ""
                            if photo_cell is not None:
                                with st.spinner("📤 Compression (max 50 Ko) et sauvegarde dans GitHub..."):
                                    lien_github = televerser_vers_github(photo_cell)

                            try:
                                colonnes_propres = [
                                    "statut", "date_soumission", "pseudo", "magasin", "ville", "produit", "prix", "lien_image"
                                ]
                                df_existant = conn_gsheets.read(worksheet="Deals_Extra", ttl=0)
                                if df_existant is None or df_existant.empty:
                                    df_existant = pd.DataFrame(columns=colonnes_propres)
                                else:
                                    df_existant.columns = [str(c).strip().lower() for c in df_existant.columns]
                                    df_existant = df_existant.loc[:, ~df_existant.columns.duplicated()]
                                    for col in colonnes_propres:
                                        if col not in df_existant.columns:
                                            df_existant[col] = ""
                                    df_existant = df_existant[colonnes_propres]

                                nouvelle_entree = pd.DataFrame([{
                                    "statut": "EN_ATTENTE",
                                    "date_soumission": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "pseudo": deal_pseudo.strip() if deal_pseudo.strip() else "Anonyme",
                                    "magasin": deal_magasin.strip(),
                                    "ville": deal_ville.strip(),
                                    "produit": deal_produit.strip(),
                                    "prix": f"{deal_prix:.2f}",
                                    "lien_image": lien_github,
                                }])
                                df_maj = pd.concat([df_existant, nouvelle_entree], ignore_index=True)
                                conn_gsheets.update(worksheet="Deals_Extra", data=df_maj)
                                st.success("🎉 Merci ! Votre Deal Extra a été envoyé et sera publié dès sa validation.")
                            except Exception as err_gs:
                                st.error(f"❌ Erreur lors de l'envoi vers Google Sheets : {err_gs}")
