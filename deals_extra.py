from datetime import datetime
from io import BytesIO
import base64
import uuid
import requests
from PIL import Image
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection


def compresser_photo_50ko(fichier_photo) -> bytes:
    """Redimensionne et compresse la photo pour qu'elle pèse <= 50 Ko."""
    fichier_photo.seek(0)
    img = Image.open(fichier_photo)
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
    """Envoie la photo compressée (< 50 Ko) dans image_circulaire/ sur GitHub."""
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        if not token:
            st.warning("⚠️ Secret GITHUB_TOKEN manquant.")
            return ""

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        res_user = requests.get("https://github.com", headers=headers, timeout=10)
        if res_user.status_code != 200:
            st.warning("⚠️ Impossible de vérifier le compte GitHub.")
            return ""
        pseudo_github = res_user.json().get("login", "")
        repo = f"{pseudo_github}/guide-achat-local"
        branch = "main"

        octets_image = compresser_photo_50ko(fichier_photo)
        contenu_b64 = base64.b64encode(octets_image).decode("utf-8")

        horodatage_nom = datetime.now().strftime("%Y%m%d_%H%M%S")
        id_court = uuid.uuid4().hex[:6]
        chemin_fichier = f"image_circulaire/deal_{horodatage_nom}_{id_court}.jpg"

        url_api = f"https://github.com{repo}/contents/{chemin_fichier}"
        payload = {
            "message": f"Ajout photo Deal Extra ({chemin_fichier})",
            "content": contenu_b64,
            "branch": branch,
        }

        reponse = requests.put(url_api, headers=headers, json=payload, timeout=15)
        if reponse.status_code in (200, 201):
            return f"https://githubusercontent.com{repo}/{branch}/{chemin_fichier}"
        else:
            st.warning(f"⚠️ GitHub a refusé l'envoi ({reponse.status_code}).")
            return ""
    except Exception as e:
        st.warning(f"⚠️ Erreur photo : {e}")
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


def afficher_section_deals_extra(banniere_active: str, ville_detectee: str, liens_officiels: dict, classer_rayon_fn):
    """Affiche le module communautaire Le Deal Extra."""
    conn_gsheets = st.connection("gsheets", type=GSheetsConnection)
    df_deals_extra = charger_deals_extra(conn_gsheets)
    nb_deals = len(df_deals_extra)

    titre_expander = (
        f"📸 Le Deal Extra — {nb_deals} trouvaille(s) en magasin partagée(s) par la communauté !"
        if nb_deals > 0
        else "📸 Le Deal Extra — Partagez ou découvrez les rabais cachés en magasin !"
    )

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

                            if d_img and d_img.startswith("http"):
                                st.image(d_img, use_container_width=True)

                            st.markdown(f"**{d_prod}**")
                            st.markdown(
                                f"<span style='color:#DC2626; font-size:22px; font-weight:900;'>{d_prix:.2f} $</span> — 🏪 **{d_mag}**",
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
