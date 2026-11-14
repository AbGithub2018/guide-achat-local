import numpy as np
import pandas as pd
import streamlit as st


def calculer_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance en kilomètres entre deux coordonnées GPS."""
    R = 6371.0
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


def _trouver_colonne_cp(df):
    for col in df.columns:
        nom_propre = col.strip().lower().replace("_", " ")
        if "code postal" in nom_propre or nom_propre in [
            "cp",
            "postal code",
            "codepostal",
        ]:
            return col
    return df.columns[0]


@st.cache_data
def charger_donnees():
    """Charge et nettoie les fichiers de codes postaux et de magasins."""
    try:
        df_coords = pd.read_csv(
            "codes_qc.csv", sep=None, engine="python", encoding="utf-8-sig"
        )
        df_magasins = pd.read_csv(
            "disponibilite_magasins.csv",
            sep=None,
            engine="python",
            encoding="utf-8-sig",
        )

        df_coords.columns = df_coords.columns.str.strip()
        df_magasins.columns = df_magasins.columns.str.strip()

        col_cp_coords = _trouver_colonne_cp(df_coords)
        col_cp_mag = _trouver_colonne_cp(df_magasins)

        df_coords["Code postal"] = (
            df_coords[col_cp_coords]
            .astype(str)
            .str.replace(" ", "")
            .str.upper()
        )
        df_magasins["Code postal"] = (
            df_magasins[col_cp_mag]
            .astype(str)
            .str.replace(" ", "")
            .str.upper()
        )

        df_coords["Latitude"] = pd.to_numeric(
            df_coords["Latitude"], errors="coerce"
        )
        df_coords["Longitude"] = pd.to_numeric(
            df_coords["Longitude"], errors="coerce"
        )

        return df_coords, df_magasins
    except Exception as e:
        st.error(f"Erreur lors de la lecture des fichiers CSV : {e}")
        return None, None
