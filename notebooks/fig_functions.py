import os
from typing import Dict, List
import numpy as np

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
    if not df_list:
        return pd.DataFrame()
    df = pd.concat(df_list, ignore_index=True)
    if "resource_name" in df.columns:
        df = tech_to_type(df)
        df = df.query("~tech_type.str.contains('Other')")
    if "line_name" in df.columns:
        df = fix_tx_line_names(df)
    if "zone" in df.columns:
        df["agg_zone"] = df["zone"].map(rev_region_map)
    for col in ["value", "start_value", "end_value"]:
        if col in df.columns:
            df[col] = df[col].round(0)
    return df


def load_genx_operations_data(
    data_path: Path, fn: str, period_dict={"p1": 2030, "p2": 2040, "p3": 2050}
) -> pd.DataFrame:
    df_list = []
    for f in data_path.rglob(fn):
        model_part = -3
        _df = pd.read_csv(f)
        if "Results_p" in str(f):
            period = period_dict[f.parent.stem.split("_")[-1]]
            _df["planning_year"] = period
            model_part = -4
        model = f.parts[model_part].split("_")[0]
        _df["model"] = model
        df_list.append(_df)
    if not df_list:
        return pd.DataFrame()
    df = pd.concat(df_list, ignore_index=True)
    if fn == "costs.csv":
        df = add_genx_op_network_cost(df, data_path).pipe(calc_op_percent_total)
    return df


def calc_op_percent_total(op_costs: pd.DataFrame, group_by=["model"]) -> pd.DataFrame:
    if "planning_year" in op_costs.columns:
        group_by.append("planning_year")
    df_list = []
    for _, _df in op_costs.query("Costs != 'cTotal'").groupby(group_by):
        _df["percent_total"] = _df["Total"] / _df["Total"].sum()
        df_list.append(_df)
    return pd.concat(df_list)


def add_genx_op_network_cost(
    op_costs: pd.DataFrame,
    data_path: Path,
    original_network_fn: str = "original_network.csv",
    final_network_fn: str = "Network.csv",
    period_dict={"p1": 2030, "p2": 2040, "p3": 2050},
) -> pd.DataFrame:
    read_cols = [
        "Network_Lines",
        "Line_Max_Flow_MW",
        "Line_Reinforcement_Cost_per_MWyr",
    ]
    for f in data_path.rglob(original_network_fn):
        model_part = -2
        original_df = pd.read_csv(f, usecols=read_cols).set_index("Network_Lines")
        if "Inputs_p" in str(f):
            model_part = -4
            period = period_dict[f.parent.stem.split("_")[-1]]

        final_df = pd.read_csv(
            f.parent / final_network_fn, usecols=read_cols
        ).set_index("Network_Lines")
        model = f.parts[model_part].split("_")[0]
        new_tx_cost = (
            (final_df["Line_Max_Flow_MW"] - original_df["Line_Max_Flow_MW"])
            * original_df["Line_Reinforcement_Cost_per_MWyr"]
        ).sum()
        if "Inputs_p" in str(f):
            op_costs.loc[
                (op_costs["model"] == model)
                & (op_costs["Costs"] == "cNetworkExp")
                & (op_costs["planning_year"] == period),
                "Total",
            ] = new_tx_cost
        else:
            op_costs.loc[
                (op_costs["model"] == model) & (op_costs["Costs"] == "cNetworkExp"),
                "Total",
            ] = new_tx_cost

    return op_costs


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


def chart_total_cap(
    cap: pd.DataFrame,
    x_var="model",
    col_var=None,
) -> alt.Chart:
    group_by = ["tech_type", x_var, "planning_year"]
    _tooltips = [
        alt.Tooltip("tech_type", title="Technology"),
        alt.Tooltip("end_value", title="Capacity (MW)", format=",.0f"),
    ]
    if col_var is not None:
        group_by.append(col_var)
        _tooltips.append(alt.Tooltip(col_var))
    cap_data = cap.groupby(group_by, as_index=False)["end_value"].sum()

    chart = (
        alt.Chart(cap_data)
        .mark_bar()
        .encode(
            x=x_var,
            y=alt.Y("sum(end_value)").title("Capacity (MW)"),
            color=alt.Color("tech_type").scale(scheme="tableau20"),
            # column="zone",
            row="planning_year:O",
            tooltip=_tooltips,
        )
        .properties(width=350, height=250)
    )
    if col_var is not None:
        chart = chart.encode(column=col_var)
    return chart


def chart_regional_cap(
    cap: pd.DataFrame, group_by=["agg_zone", "tech_type", "model", "planning_year"]
) -> alt.Chart:
    data = cap.groupby(group_by, as_index=False)["end_value"].sum()
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x="model",
            y=alt.Y("end_value").title("Capacity (MW)"),
            color=alt.Color("tech_type").scale(scheme="tableau20"),
            column="agg_zone",
            row="planning_year:O",
            tooltip=[
                alt.Tooltip("tech_type", title="Technology"),
                alt.Tooltip("end_value", title="Capacity (MW)", format=",.0f"),
            ],
        )
        .properties(width=150, height=250)
    )
    return chart


def chart_total_gen(
    gen: pd.DataFrame,
    cap: pd.DataFrame = None,
    x_var="model",
    col_var=None,
) -> alt.Chart:
    merge_by = ["tech_type", "resource_name", x_var, "planning_year"]
    group_by = ["tech_type", x_var, "planning_year"]
    _tooltips = [
        alt.Tooltip("tech_type", title="Technology"),
        alt.Tooltip("value", title="Generation (MWh)", format=",.0f"),
    ]
    if col_var is not None:
        group_by.append(col_var)
        merge_by.append(col_var)
        _tooltips.append(alt.Tooltip(col_var))
    if cap is not None:
        _cap = (
            cap.query("unit=='MW'")
            .groupby(
                merge_by,
                # ["tech_type", "resource_name", "model", "planning_year"],
                as_index=False,
            )["end_value"]
            .sum()
        )
        _gen = pd.merge(
            gen,
            _cap,
            # on=["tech_type", "resource_name", "model", "planning_year"],
            on=merge_by,
            how="left",
        )
        _gen["end_value"].fillna(0, inplace=True)
        _gen["potential_gen"] = _gen["end_value"] * 8760

        data = _gen.groupby(group_by, as_index=False)[
            ["value", "potential_gen", "end_value"]
        ].sum()
        data["capacity_factor"] = (data["value"] / data["potential_gen"]).round(3)
        _tooltips.extend(
            [
                alt.Tooltip("capacity_factor", title="Capacity Factor"),
                alt.Tooltip("end_value", title="Capacity (MW)", format=",.0f"),
            ]
        )

    else:
        data = gen.groupby(group_by, as_index=False)["value"].sum()
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=x_var,
            y=alt.Y("value").title("Generation (MWh)"),
            color=alt.Color("tech_type").scale(scheme="tableau20"),
            # column="zone",
            row="planning_year:O",
            tooltip=_tooltips,
        )
        .properties(width=350, height=250)
    )
    if col_var is not None:
        chart = chart.encode(column=col_var)
    return chart


def chart_regional_gen(gen: pd.DataFrame, cap: pd.DataFrame = None) -> alt.Chart:
    if cap is not None:
        _cap = (
            cap.query("unit=='MW'")
            .groupby(
                ["tech_type", "resource_name", "model", "planning_year"], as_index=False
            )["end_value"]
            .sum()
        )
        _gen = pd.merge(
            gen,
            _cap,
            on=["tech_type", "resource_name", "model", "planning_year"],
            how="left",
        )
        _gen["end_value"].fillna(0, inplace=True)
        _gen["potential_gen"] = _gen["end_value"] * 8760
        data = _gen.groupby(
            ["agg_zone", "tech_type", "model", "planning_year"], as_index=False
        )[["value", "potential_gen"]].sum()
        data["capacity_factor"] = (data["value"] / data["potential_gen"]).round(3)
        _tooltips = [
            alt.Tooltip("tech_type", title="Technology"),
            alt.Tooltip("value", title="Generation (MWh)", format=",.0f"),
            alt.Tooltip("capacity_factor", title="Capacity Factor"),
        ]
    else:
        data = gen.groupby(
            ["agg_zone", "tech_type", "model", "planning_year"], as_index=False
        )["value"].sum()
        _tooltips = [
            alt.Tooltip("tech_type", title="Technology"),
            alt.Tooltip("value", title="Generation (MWh)", format=",.0f"),
        ]

    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x="model",
            y=alt.Y("value").title("Generation (MWh)"),
            color=alt.Color("tech_type").scale(scheme="tableau20"),
            column="agg_zone",
            row="planning_year:O",
            tooltip=_tooltips,
        )
        .properties(width=150, height=250)
    )
    return chart


def chart_tx_expansion(
    data: pd.DataFrame,
    x_var="model",
    facet_col="line_name",
    n_cols=10,
    col_var=None,
    row_var=None,
) -> alt.Chart:
    _tooltip = [
        alt.Tooltip("sum(value)", format=",.0f"),
    ]
    if x_var == "case":
        _tooltip.append(
            alt.Tooltip("case"),
        )
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            # xOffset="model:N",
            x=x_var,
            y=alt.Y("sum(value)").title("Total transmission expansion (MW)"),
            color="model:N",
            opacity=alt.Opacity("planning_year:O", sort="descending"),
            # facet=alt.Facet("line_name", columns=n_cols),
            order=alt.Order(
                # Sort the segments of the bars by this field
                "planning_year",
                sort="ascending",
            ),
            tooltip=_tooltip,
        )
        .properties(
            height=200,
            width=alt.Step(20),
        )
    )
    if facet_col is not None:
        chart = chart.encode(facet=alt.Facet(facet_col, columns=n_cols))
    elif col_var is None and row_var is None:
        text = (
            alt.Chart()
            .mark_text(dy=-5)
            .encode(
                x=x_var, y="sum(value):Q", text=alt.Text("sum(value):Q", format=".1e")
            )
        )
        chart = alt.layer(chart, text, data=data).properties(width=alt.Step(40))
    if col_var is not None:
        chart = chart.encode(column=col_var)
    if row_var is not None:
        chart = chart.encode(row=row_var)
    return chart


def chart_emissions(
    emiss: pd.DataFrame,
    x_var="model",
    col_var=None,
) -> alt.Chart:
    _tooltips = [alt.Tooltip("value", format=",.0f"), alt.Tooltip("zone")]
    if col_var is not None:
        _tooltips.append(alt.Tooltip(col_var))
    base = (
        alt.Chart()
        .mark_bar()
        .encode(
            x=x_var,
            y=alt.Y("value").title("CO2 emissions (tonnes)"),
            color=alt.Color("zone").scale(scheme="tableau20"),
            # column="agg_zone",
            # row="planning_year:O",
            tooltip=_tooltips,
        )
        # .properties(width=350, height=250)
        # .resolve_scale(y="independent")
    )
    text = (
        alt.Chart()
        .mark_text(dy=-5)
        .encode(x=x_var, y="sum(value):Q", text=alt.Text("sum(value):Q", format=".2e"))
    )  # .properties(width=350, height=250)

    if col_var is None:
        chart = (
            alt.layer(base, text, data=emiss)
            .properties(width=350, height=250)
            .facet(row="planning_year:O")
        )
    else:
        chart = (
            alt.layer(base, text, data=emiss)
            .properties(width=350, height=250)
            .facet(row="planning_year:O", column=col_var)
        )
    return chart


def chart_dispatch(data: pd.DataFrame) -> alt.Chart:
    selection = alt.selection_point(fields=["model"], bind="legend")
    chart = (
        alt.Chart(data)
        .mark_line()
        .encode(
            x="hour",
            y="value",
            color="model",
            row="tech_type",
            column="agg_zone",
            opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
        )
        .properties(width=250, height=150)
        .add_params(selection)
    ).resolve_scale(y="independent")
    return chart


def chart_wind_dispatch(data: pd.DataFrame) -> alt.Chart:
    selection = alt.selection_point(fields=["model"], bind="legend")
    if "cluster" in data.columns:
        chart = (
            alt.Chart(data)
            .mark_line()
            .encode(
                x="hour",
                y="value",
                color="model",
                strokeDash="cluster",
                facet=alt.Facet("zone", columns=5),
                opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
            )
            .properties(width=250, height=150)
            .add_params(selection)
        ).resolve_scale(y="independent")
    else:
        chart = (
            alt.Chart(data)
            .mark_line()
            .encode(
                x="hour",
                y="value",
                color="model",
                facet=alt.Facet("zone", columns=5),
                opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
            )
            .properties(width=250, height=150)
            .add_params(selection)
        ).resolve_scale(y="independent")
    return chart


def chart_op_cost(
    op_costs: pd.DataFrame,
    x_var="model",
    col_var=None,
) -> alt.Chart:
    if "planning_year" in op_costs.columns:
        col_var = "planning_year"
    _tooltip = [alt.Tooltip("Total", format=",.0f")]
    chart_cols = ["Costs", "Total", x_var]

    if "percent_total" in op_costs.columns:
        _tooltip.append(alt.Tooltip("percent_total:Q", format=".1%"))
        chart_cols.append("percent_total")
    if col_var is not None:
        _tooltip.append(alt.Tooltip(col_var))
        _tooltip.append(alt.Tooltip("Costs"))
        chart_cols.append(col_var)
    if op_costs.empty:
        return None
    base = (
        alt.Chart()
        .mark_bar()
        .encode(
            # xOffset="model:N",
            x=x_var,
            y=alt.Y("Total").title("Costs"),
            color="Costs:N",
            tooltip=_tooltip,
        )
    )

    text = (
        alt.Chart()
        .mark_text(dy=-5)
        .encode(x=x_var, y="sum(Total):Q", text=alt.Text("sum(Total):Q", format=".2e"))
    )

    chart = alt.layer(
        base,
        text,
        data=op_costs[chart_cols].query("Total>0 and Costs != 'cTotal'"),
    ).properties(width=250, height=250)

    if col_var is not None:
        chart = chart.facet(column=col_var)

    return chart


def chart_op_nse(
    op_nse: pd.DataFrame,
    x_var="model",
    col_var=None,
) -> alt.Chart:
    cols = ["Segment", "Total", "model"]
    if "planning_year" in op_nse:
        col_var = "planning_year"
    if col_var is not None:
        cols.append(col_var)
    if op_nse.empty:
        return None

    chart = (
        alt.Chart(op_nse[cols].query("Segment == 'AnnualSum'"))
        .mark_bar()
        .encode(
            # xOffset="model:N",
            x=x_var,
            y=alt.Y("Total").title("Annual non-served MWh"),
            color="model:N",
            tooltip=alt.Tooltip("Total", format=",.0f"),
        )
        .properties(width=250, height=250)
    )
    if col_var is not None:
        chart = chart.facet(column=col_var)

    return chart
