import os
from typing import Dict, List
import numpy as np

import pandas as pd
import geopandas as gpd
import altair as alt
from pathlib import Path
from joblib import Parallel, delayed

# alt.data_transformers.enable("vegafusion")

try:
    pd.options.mode.copy_on_write = True
except:
    pass

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

EXISTING_TECH_MAP = {
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
    "nuclear_1": "Nuclear",
    "offshore_wind_turbine": "Wind",
    "distributed_generation": "Distributed Solar",
}

_TECH_MAP = {}
for k, v in TECH_MAP.items():
    if k in EXISTING_TECH_MAP.keys():
        _TECH_MAP[k] = (v, True)
    else:
        _TECH_MAP[k] = (v, False)


def tech_to_type(df: pd.DataFrame) -> pd.DataFrame:
    df.loc[:, "existing"] = False
    df.loc[:, "tech_type"] = "Not Specified"
    for tech, (t, ex) in _TECH_MAP.items():
        df.loc[df["resource_name"].str.contains(tech), ["tech_type", "existing"]] = [
            t,
            ex,
        ]
    df.loc[df["resource_name"] == "unserved_load", "tech_type"] = "Other"

    # for tech, type in TECH_MAP.items():
    #     df.loc[df["resource_name"].str.contains(tech), "tech_type"] = type
    # for tech in EXISTING_TECH_MAP.keys():
    #     df.loc[df["resource_name"].str.contains(tech), "existing"] = True

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
    fn = f"{fn.split('.')[0]}.*"
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
        df.loc[:, "agg_zone"] = df.loc[:, "zone"].map(rev_region_map)
    for col in ["value", "start_value", "end_value"]:
        if col in df.columns:
            df.loc[:, col] = df[col].round(0)
    return df


def load_genx_operations_data(
    data_path: Path,
    fn: str,
    period_dict={"p1": 2030, "p2": 2040, "p3": 2050},
    hourly_data: bool = False,
) -> pd.DataFrame:
    df_list = []
    nrows = None
    if hourly_data:
        nrows = 5
    files = list(data_path.rglob(fn))
    if not files:
        return pd.DataFrame()
    df_list = Parallel(n_jobs=1)(
        delayed(_load_op_data)(f, hourly_data, nrows, period_dict) for f in files
    )
    # model_part = -3
    # _df = pd.read_csv(f, nrows=nrows)  # , dtype_backend="pyarrow")
    # if hourly_data:
    #     if fn == "nse.csv":
    #         _df = total_from_nse_hourly_data(_df)
    #     elif "Resource" in _df.columns:
    #         _df = total_from_resource_op_hourly_data(_df)
    #     else:
    #         raise ValueError(f"There is no hourly data function for file {fn}")
    # if "Results_p" in str(f):
    #     period = period_dict[f.parent.stem.split("_")[-1]]
    #     _df.loc[:, "planning_year"] = period
    #     model_part = -4
    # elif "Inputs_p" in str(f):
    #     period = period_dict[f.parents[1].stem.split("_")[-1]]
    #     _df.loc[:, "planning_year"] = period
    #     model_part = -5
    # model = f.parts[model_part].split("_")[0]
    # _df.loc[:, "model"] = model
    # df_list.append(_df)
    if not df_list:
        return pd.DataFrame()
    df = pd.concat(df_list, ignore_index=True)
    if fn == "costs.csv":
        try:
            df = add_genx_op_network_cost(df, data_path).pipe(calc_op_percent_total)
        except FileNotFoundError:
            pass
    if "Resource" in df.columns:
        df = df.rename(columns={"Resource": "resource_name"}).pipe(tech_to_type)
        try:
            df.loc[:, "zone"] = df["resource_name"].str.split("_").str[0]
        except:
            df.loc[:, "zone"] = df["resource_name"].str.split("_").list[0]
        df.loc[df["resource_name"].str.contains("TRE_WEST"), "zone"] = "TRE_WEST"
    return df


def _load_op_data(
    f: Path,
    hourly_data: bool,
    nrows=None,
    period_dict={"p1": 2030, "p2": 2040, "p3": 2050},
) -> pd.DataFrame:
    fn = f.name
    model_part = -3
    _df = pd.read_csv(f, nrows=nrows)  # , dtype_backend="pyarrow")
    if hourly_data:
        if fn == "nse.csv":
            _df = total_from_nse_hourly_data(_df)
        elif "Resource" in _df.columns:
            _df = total_from_resource_op_hourly_data(_df)
        else:
            raise ValueError(f"There is no hourly data function for file {fn}")
    if "Results_p" in str(f):
        period = period_dict[f.parent.stem.split("_")[-1]]
        _df.loc[:, "planning_year"] = period
        model_part = -4
    elif "Inputs_p" in str(f):
        period = period_dict[f.parents[1].stem.split("_")[-1]]
        _df.loc[:, "planning_year"] = period
        model_part = -5
    model = f.parts[model_part].split("_")[0]
    _df.loc[:, "model"] = model
    return _df


def total_from_resource_op_hourly_data(df: pd.DataFrame) -> pd.DataFrame:
    data = pd.DataFrame(
        {
            "Resource": df.columns[1:-1],
            "value": df.iloc[1, 1:-1],
        }
    ).reset_index(drop=True)

    return data


def total_from_nse_hourly_data(df: pd.DataFrame) -> pd.DataFrame:
    data = pd.DataFrame(
        {
            "zone": df.iloc[0, 1:-1],
            "value": df.iloc[1, 1:-1],
        }
    ).reset_index(drop=True)
    return data


def calc_op_percent_total(
    op_costs: pd.DataFrame, group_by=["model", "planning_year"]
) -> pd.DataFrame:
    by = [c for c in group_by if c in op_costs.columns]
    df_list = []
    for _, _df in op_costs.query("Costs != 'cTotal'").groupby(by):
        _df.loc[:, "percent_total"] = (_df["Total"] / _df["Total"].sum()).round(3)
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
        df.loc[:, "line_name"] = df["line_name"].str.replace(
            row["line_name"], reverse_line_name(row["line_name"])
        )

    return df


def chart_total_cap(
    cap: pd.DataFrame, x_var="model", col_var=None, row_var="planning_year", order=None
) -> alt.Chart:
    group_by = ["tech_type", x_var, row_var]
    _tooltips = [
        alt.Tooltip("tech_type", title="Technology"),
        alt.Tooltip("end_value", title="Capacity (MW)", format=",.0f"),
        alt.Tooltip(x_var),
    ]
    if col_var is not None:
        group_by.append(col_var)
        _tooltips.append(alt.Tooltip(col_var))
    if row_var is not None:
        _tooltips.append(alt.Tooltip(row_var))
    cap_data = cap.groupby(group_by, as_index=False)["end_value"].sum()

    chart = (
        alt.Chart(cap_data)
        .mark_bar()
        .encode(
            x=alt.X(x_var).sort(order),
            y=alt.Y("sum(end_value)").title("Capacity (MW)"),
            color=alt.Color("tech_type").scale(scheme="tableau20"),
            # column="zone",
            row=row_var,
            tooltip=_tooltips,
        )
        .properties(width=350, height=250)
    )
    if col_var is not None:
        chart = chart.encode(column=col_var)
    return chart


def chart_regional_cap(
    cap: pd.DataFrame,
    group_by=["agg_zone", "tech_type", "model", "planning_year"],
    order=None,
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
    row_var=None,
    order=None,
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
    if row_var is not None:
        _tooltips.append(alt.Tooltip(row_var))
        merge_by.append(row_var)
        group_by.append(row_var)
    merge_by = list(set(merge_by))
    group_by = list(set(group_by))
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
        _gen.fillna({"end_value": 0}, inplace=True)
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
            x=alt.X(x_var).sort(order),
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
    if row_var is not None:
        chart = chart.encode(row=row_var)
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
        _gen.fillna({"end_value": 0}, inplace=True)
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
    order=None,
) -> alt.Chart:
    _tooltip = [
        alt.Tooltip("sum(value)", format=",.0f"),
    ]
    if col_var is None or row_var is None:
        first_year = data["planning_year"].min()
        idx_cols = [c for c in [x_var, facet_col, col_var, row_var] if c is not None]
        data = data.set_index(idx_cols)
        first_data = data.query("planning_year == @first_year")
        df_list = []
        for year in data["planning_year"].unique():
            _df = data.query("planning_year == @year")
            if year == first_year:
                _df["line_growth"] = 0
                # df_list.append(_df)
            else:
                try:
                    _df["line_growth"] = (_df["value"] / first_data["value"]).fillna(0)
                except:
                    _df["line_growth"] = 0
            df_list.append(_df)
        data = pd.concat(df_list).reset_index()
        _tooltip.append(alt.Tooltip("line_growth", format=".1%"))

    if x_var == "case":
        _tooltip.append(
            alt.Tooltip("case"),
        )
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            # xOffset="model:N",
            x=alt.X(x_var).sort(order),
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
                x=alt.X(x_var).sort(order),
                y="sum(value):Q",
                text=alt.Text("sum(value):Q", format=".1e"),
            )
        )
        chart = alt.layer(chart, text, data=data).properties(width=alt.Step(40))
    if col_var is not None:
        chart = chart.encode(column=col_var)
    if row_var is not None:
        chart = chart.encode(row=row_var)
    return chart


def chart_emissions(
    emiss: pd.DataFrame, x_var="model", col_var=None, order=None
) -> alt.Chart:
    _tooltips = [alt.Tooltip("value", format=",.0f"), alt.Tooltip("zone")]
    if col_var is not None:
        _tooltips.append(alt.Tooltip(col_var))
    base = (
        alt.Chart()
        .mark_bar()
        .encode(
            x=alt.X(x_var).sort(order),
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
        .encode(
            x=alt.X(x_var).sort(order),
            y="sum(value):Q",
            text=alt.Text("sum(value):Q", format=".2e"),
        )
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
    op_costs: pd.DataFrame, x_var="model", col_var=None, row_var=None, order=None
) -> alt.Chart:
    if col_var is None and "planning_year" in op_costs.columns:
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
    if row_var is not None:
        _tooltip.append(alt.Tooltip(row_var))
        chart_cols.append(row_var)
    if op_costs.empty:
        return None
    base = (
        alt.Chart()
        .mark_bar()
        .encode(
            # xOffset="model:N",
            x=alt.X(x_var).sort(order),
            y=alt.Y("Total").title("Costs"),
            color="Costs:N",
            tooltip=_tooltip,
        )
    )

    text = (
        alt.Chart()
        .mark_text(dy=-5, fontSize=9)
        .encode(
            x=alt.X(x_var).sort(order),
            y="sum(Total):Q",
            text=alt.Text("sum(Total):Q", format=".2e"),
        )
    )

    chart = alt.layer(
        base,
        text,
        data=op_costs[chart_cols].query("Total!=0 and Costs != 'cTotal'"),
    ).properties(width=alt.Step(40), height=250)

    if row_var is None and col_var is None:
        return chart
    elif row_var is None and col_var is not None:
        chart = chart.facet(column=col_var)
    elif col_var is None and row_var is not None:
        chart = chart.facet(row=row_var)
    else:
        chart = chart.facet(row=row_var, column=col_var)

    return chart


def chart_op_nse(
    op_nse: pd.DataFrame, x_var="model", col_var=None, row_var=None, order=None
) -> alt.Chart:
    cols = ["Segment", "Total", "model"]
    if "planning_year" in op_nse and row_var != "planning_year":
        col_var = "planning_year"
    if col_var is not None:
        cols.append(col_var)
    if row_var is not None:
        cols.append(row_var)
    if op_nse.empty:
        return None

    chart = (
        alt.Chart(op_nse)
        .mark_bar()
        .encode(
            # xOffset="model:N",
            x=alt.X(x_var).sort(order),
            y=alt.Y("sum(value)").title("Annual non-served MWh"),
            color="model:N",
            tooltip=alt.Tooltip("sum(value)", format=",.0f", title="NSE"),
        )
        .properties(width=alt.Step(40), height=250)
    )
    if col_var is not None:
        chart = chart.encode(column=col_var)
    if row_var is not None:
        chart = chart.encode(row=row_var)

    return chart


def chart_op_emiss(
    op_emiss: pd.DataFrame,
    x_var="model",
    color="tech_type",
    col_var=None,
    row_var=None,
    order=None,
) -> alt.Chart:
    if (
        col_var is None
        and "planning_year" in op_emiss.columns
        and row_var != "planning_year"
    ):
        col_var = "planning_year"
    _tooltip = [
        alt.Tooltip("value", format=",.0f", title="Emissions"),
        alt.Tooltip(color),
    ]
    by = [color, x_var]

    color_scale = "category10"
    if op_emiss[color].nunique() > 10:
        color_scale = "tableau20"
    if col_var is not None:
        _tooltip.append(alt.Tooltip(col_var))
        by.append(col_var)
    if row_var is not None:
        _tooltip.append(alt.Tooltip(row_var))
        by.append(row_var)
    if op_emiss.empty:
        return None
    by = list(set(by))
    data = op_emiss.groupby(by, as_index=False)["value"].sum().query("value>0")
    base = (
        alt.Chart()
        .mark_bar()
        .encode(
            # xOffset="model:N",
            x=alt.X(x_var).sort(order),
            y=alt.Y("value").title("Emissions (tonnes)"),
            color=alt.Color(color).scale(scheme=color_scale),
            tooltip=_tooltip,
        )
    )

    text = (
        alt.Chart()
        .mark_text(dy=-5, fontSize=9)
        .encode(
            x=alt.X(x_var).sort(order),
            y="sum(value):Q",
            text=alt.Text("sum(value):Q", format=".2e"),
        )
    )

    chart = alt.layer(
        base,
        text,
        data=data,
    ).properties(width=alt.Step(40), height=250)

    if row_var is None and col_var is None:
        return chart
    elif row_var is None and col_var is not None:
        chart = chart.facet(column=col_var)
    elif col_var is None and row_var is not None:
        chart = chart.facet(row=row_var)
    else:
        chart = chart.facet(row=row_var, column=col_var)

    return chart


gdf = gpd.read_file("conus_26z_latlon_simple.geojson")
gdf = gdf.rename(columns={"model_region": "zone"})


def chart_tx_map(tx_exp: pd.DataFrame, gdf: gpd.GeoDataFrame) -> alt.Chart:
    gdf["lat"] = gdf.geometry.centroid.y
    gdf["lon"] = gdf.geometry.centroid.x
    tx_exp["lat1"] = tx_exp["start_region"].map(gdf.set_index("zone")["lat"])
    tx_exp["lon1"] = tx_exp["start_region"].map(gdf.set_index("zone")["lon"])
    tx_exp["lat2"] = tx_exp["dest_region"].map(gdf.set_index("zone")["lat"])
    tx_exp["lon2"] = tx_exp["dest_region"].map(gdf.set_index("zone")["lon"])

    model_figs = []
    for model in tx_exp.model.unique():
        background = (
            alt.Chart(gdf, title=f"{model}")
            .mark_geoshape(
                stroke="white",
                fill="lightgray",
            )
            .project(type="albersUsa")
        )
        lines = (
            alt.Chart(
                tx_exp.query("planning_year >= 2025 and model==@model and value > 0")
            )
            .mark_rule()
            .encode(
                latitude="lat1",
                longitude="lon1",
                latitude2="lat2",
                longitude2="lon2",
                strokeWidth="sum(value)",
                color=alt.Color("sum(value):Q").scale(scheme="plasma"),
                tooltip=[alt.Tooltip("line_name"), alt.Tooltip("sum(value)")],
            )
            .project(type="albersUsa")
        )

        model_figs.append(background + lines)

    return alt.vconcat(alt.hconcat(*model_figs[:2]), alt.hconcat(*model_figs[2:]))


def chart_tx_scenario_map(
    tx_exp: pd.DataFrame, gdf: gpd.GeoDataFrame, order=list
) -> alt.Chart:
    gdf["lat"] = gdf.geometry.centroid.y
    gdf["lon"] = gdf.geometry.centroid.x
    tx_exp["lat1"] = tx_exp["start_region"].map(gdf.set_index("zone")["lat"])
    tx_exp["lon1"] = tx_exp["start_region"].map(gdf.set_index("zone")["lon"])
    tx_exp["lat2"] = tx_exp["dest_region"].map(gdf.set_index("zone")["lat"])
    tx_exp["lon2"] = tx_exp["dest_region"].map(gdf.set_index("zone")["lon"])

    model_figs = []
    for model in tx_exp.model.unique():
        scenario_figs = []
        for scenario in order:
            background = (
                alt.Chart(gdf, title=f"{model}_{scenario}")
                .mark_geoshape(
                    stroke="white",
                    fill="lightgray",
                )
                .project(type="albersUsa")
            )
            lines = (
                alt.Chart(
                    tx_exp.query(
                        "planning_year >= 2025 and model==@model and value > 0 and case == @scenario"
                    )
                )
                .mark_rule()
                .encode(
                    latitude="lat1",
                    longitude="lon1",
                    latitude2="lat2",
                    longitude2="lon2",
                    strokeWidth="sum(value)",
                    color=alt.Color("sum(value):Q").scale(scheme="plasma"),
                    tooltip=[alt.Tooltip("line_name"), alt.Tooltip("sum(value)")],
                )
                .project(type="albersUsa")
            )

            scenario_figs.append(background + lines)

        model_figs.append(alt.hconcat(*scenario_figs))

    return alt.vconcat(*model_figs)


def chart_cap_factor_scatter(
    cap: pd.DataFrame,
    gen: pd.DataFrame,
    dispatch: pd.DataFrame = None,
    color="model",
    col_var=None,
    row_var=None,
    frac=None,
) -> alt.Chart:
    gen = gen.query("value >=0")
    cap = cap.query("end_value >= 50")
    merge_by = ["tech_type", "resource_name", "planning_year", "model"]
    group_by = ["resource_name", "planning_year", "model"]
    _tooltips = [
        alt.Tooltip("resource_name"),
        alt.Tooltip(color),
    ]
    if col_var is not None:
        group_by.append(col_var)
        merge_by.append(col_var)
        _tooltips.append(alt.Tooltip(col_var))
    if row_var is not None:
        _tooltips.append(alt.Tooltip(row_var))
        merge_by.append(row_var)
        group_by.append(row_var)
    merge_by = list(set(merge_by))
    group_by = list(set(group_by))

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
    _gen.fillna({"end_value": 0}, inplace=True)
    _gen["potential_gen"] = _gen["end_value"] * 8760

    data = _gen.groupby(group_by, as_index=False)[
        ["value", "potential_gen", "end_value"]
    ].sum()
    data["capacity_factor"] = (data["value"] / data["potential_gen"]).round(3)
    data = data.query("end_value >= 50").drop(columns=["potential_gen", "value"])
    _tooltips.extend(
        [
            alt.Tooltip("capacity_factor", title="Capacity Factor"),
            alt.Tooltip("end_value", title="Capacity (MW)", format=",.0f"),
        ]
    )
    selection = alt.selection_point(fields=["model"], bind="legend")
    selector = alt.selection_point(
        fields=["resource_name"]
    )  # , "model", "planning_year"
    data["end_value"] = data["end_value"].astype(int)
    if frac:
        data = data.sample(frac=frac)
    chart = (
        alt.Chart(data)
        .mark_point()
        .encode(
            x=alt.X("end_value").title("Capacity (MW)").scale(type="log"),
            y="capacity_factor",
            color=color,
            shape=color,
            tooltip=_tooltips,
            opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
        )
        .add_params(selection, selector)
        .properties(width=300, height=250)
    )
    if col_var is not None:
        chart = chart.encode(column=col_var)
    if row_var is not None:
        chart = chart.encode(row=row_var)
    if dispatch is not None:
        _dispatch = dispatch.groupby(
            ["model", "planning_year", "resource_name", "hour"], as_index=False
        )["value"].sum()
        _dispatch = _dispatch.query("value > 5")
        _dispatch = _dispatch.loc[
            _dispatch["resource_name"].isin(data["resource_name"].unique())
        ]
        _dispatch["value"] = _dispatch["value"].astype(int)
        timeseries = (
            alt.Chart(_dispatch)
            .mark_line()
            .encode(
                x="hour", y="value:Q", color=alt.Color(color), tooltip=["resource_name"]
            )
            .transform_filter(selector)
        )
        if col_var is not None:
            timeseries = timeseries.encode(column=col_var)
        if row_var is not None:
            timeseries = timeseries.encode(row=row_var)

        chart = alt.vconcat(chart, timeseries)

    return chart  # | timeseries
