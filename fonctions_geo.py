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


@st.cache_data
def charger_donnees():
    """Charge et nettoie les fichiers de codes postaux et de magasins."""
    try:
        df_coords = pd.read_csv("codes_qc.csv", sep=";")
        df_magasins = pd.read_csv("disponibilite_magasins.csv")

        df_coords["Code postal"] = (
            df_coords["Code postal"].astype(str).str.replace(" ", "").str.upper()
        )
        df_magasins["Code postal"] = (
            df_magasins["Code postal"].astype(str).str.replace(" ", "").str.upper()
        )
        return df_coords, df_magasins
    except Exception as e:
        st.error(f"Erreur lors de la lecture des fichiers CSV : {e}")
        return None, None
