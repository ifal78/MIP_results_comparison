import os
from typing import Dict, List

import pandas as pd
import altair as alt
from pathlib import Path

region_map = {
    "WECC": ["BASN", "CANO", "CASO", "NWPP", "SRSG", "RMRG"],
    "TRE": ["TRE", "TRE_WEST"],
    "SPP": ["SPPC", "SPPN", "SPPS"],
    "MISO": ["MISC", "MISE", "MISS", "MISW", "SRCE"],
    "PJM": ["PJMC", "PJMW", "PJME", "PJMD"],
    "SOU": ["SRSE", "SRCA", "FRCC"],
    "NE": ["ISNE", "NYUP", "NYCW"],
}

TECH_MAP = {
    "batteries": "Battery",
    "biomass_": "Other",
    "conventional_hydroelectric": "Hydro",
    "conventional_steam_coal": "Coal",
    "geothermal": "Geothermal",
    "natural_gas_fired_combined_cycle": "Natural Gas CC",
    "natural_gas_fired_combustion_turbine": "Natural Gas CT",
    "natural_gas_internal_combustion_engine": "Natural Gas Other",
    "natural_gas_steam_turbine": "Natural Gas Other",
    "onshore_wind_turbine": "Wind",
    "petroleum_liquids": "Other",
    "small_hydroelectric": "Hydro",
    "solar_photovoltaic": "Solar",
    "hydroelectric_pumped_storage": "Hydro",
    "nuclear": "Nuclear",
    "offshore_wind_turbine": "Wind",
    "distributed_generation": "Distributed Solar",
    "naturalgas_ccavgcf": "Natural Gas CC",
    "naturalgas_ctavgcf": "Natural Gas CT",
    "battery": "Battery",
    "landbasedwind": "Wind",
    "utilitypv": "Solar",
    "naturalgas_ccccsavgcf": "CCS",
    "ccs": "CCS",
    "offshorewind": "Wind",
    "hydrogen": "Hydrogen",
}


def tech_to_type(df: pd.DataFrame) -> pd.DataFrame:
    for tech, type in TECH_MAP.items():
        df.loc[df["resource_name"].str.contains(tech), "tech_type"] = type

    return df


def reverse_dict_of_lists(d: Dict[str, list]) -> Dict[str, List[str]]:
    """Reverse the mapping in a dictionary of lists so each list item maps to the key

    Parameters
    ----------
    d : Dict[str, List[str]]
        A dictionary with string keys and lists of strings.

    Returns
    -------
    Dict[str, str]
        A reverse mapped dictionary where the item of each list becomes a key and the
        original keys are mapped as values.
    """
    if isinstance(d, dict):
        rev = {v: k for k in d for v in d[k]}
    else:
        rev = dict()
    return rev


rev_region_map = reverse_dict_of_lists(region_map)


def load_data(data_path: Path, fn: str) -> pd.DataFrame:
    df_list = []
    for f in data_path.rglob(fn):
        if not ("output" in f.parts[-2] or "Results" in f.parts[-2]):
            # print(f.parts[-2])
            _df = pd.read_csv(f)
            df_list.append(_df)
    df = pd.concat(df_list, ignore_index=True)
    if "resource_name" in df.columns:
        df = tech_to_type(df)
        df = df.query("~tech_type.str.contains('Other')")
    if "line_name" in df.columns:
        df = fix_tx_line_names(df)
    if "zone" in df.columns:
        df["agg_zone"] = df["zone"].map(rev_region_map)

    return df


def load_genx_operations_data(data_path: Path, fn: str) -> pd.DataFrame:
    df_list = []
    for f in data_path.rglob(fn):
        _df = pd.read_csv(f)
        model = f.parts[-3].split("_")[0]
        _df["model"] = model
        df_list.append(_df)

    df = pd.concat(df_list, ignore_index=True)
    return df


def reverse_line_name(s: str) -> str:
    segments = s.split("_to_")
    return segments[-1] + "_to_" + segments[0]


def fix_tx_line_names(df: pd.DataFrame) -> pd.DataFrame:
    line_count = df.groupby("line_name", as_index=False)["model"].count()
    median_count = line_count["model"].median()
    reversed_lines = line_count.query("model < @median_count")

    for idx, row in reversed_lines.iterrows():
        df["line_name"] = df["line_name"].str.replace(
            row["line_name"], reverse_line_name(row["line_name"])
        )

    return df
