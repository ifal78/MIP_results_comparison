import os
from typing import Dict, List

os.environ["USE_PYGEOS"] = "0"

import pandas as pd
import geopandas as gpd
import altair as alt
from pathlib import Path

alt.renderers.enable("png")

data_path = Path.cwd()
gdf = gpd.read_file("conus_26z_latlon_simple.geojson")
gdf = gdf.rename(columns={"model_region": "zone"})
gdf["lat"] = gdf.geometry.centroid.y
gdf["lon"] = gdf.geometry.centroid.x

print("\n\nstarting figure script\n\n")

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


# %%
def load_data(fn: str) -> pd.DataFrame:
    df_list = []
    for f in data_path.rglob(fn):
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


def load_genx_operations_data(fn: str) -> pd.DataFrame:
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


# %% [markdown]
# ## Capacity

# %%
cap = load_data("resource_capacity.csv")
cap = cap.query("unit=='MW' and not tech_type.isna()")
cap["additions"] = cap["end_value"] - cap["start_value"]
# cap.head()

# %%

fig_num = 0
# %%
# A faceted choropleth with capacity of each tech_type for each year
# for year, _df in cap.groupby("planning_year"):
#     fig_num += 1
#     cap_group = _df.groupby(["model", "zone", "tech_type", "case"], as_index=False)[
#         "end_value"
#     ].sum()

#     chart = alt.hconcat(
#         *(
#             alt.vconcat(
#                 *(
#                     alt.Chart(gdf, title=f"{m}_{tech}")
#                     .mark_geoshape(stroke="white")
#                     .encode(
#                         color="end_value:Q",
#                         # column="model:N",
#                         # row="tech_type:N",
#                     )
#                     .transform_lookup(
#                         lookup="zone",
#                         from_=alt.LookupData(
#                             cap_group.query("tech_type==@tech and model==@m"),
#                             "zone",
#                             list(cap_group.columns),
#                         ),
#                     )
#                     .project("albersUsa")
#                     .properties(width=300, height=150)
#                     for tech in cap_group["tech_type"].unique()
#                 )
#             )
#             for m in cap_group["model"].unique()
#         )
#     )
#     chart.save(f"{str(fig_num).zfill(2)} - {year} regional capacity map.png")


# %%
fig_num += 1
cap_group = cap.groupby(
    ["model", "planning_year", "zone", "tech_type"]  # , as_index=False
)["end_value"].sum()
years = cap["planning_year"].unique()
idx = pd.IndexSlice
df_list = []
for prev_year, year in list(zip(years[:-1], years[1:]))[::-1]:
    print(prev_year, year)
    cap_group.loc[idx[:, year]] = (
        cap_group.loc[idx[:, year]]
        - cap_group.loc[idx[:, prev_year]].reindex(
            cap_group.loc[idx[:, year]].index, fill_value=0
        )
    ).values


cap_group = cap_group.to_frame().reset_index()
cap_group["end_value"] = cap_group["end_value"].where(
    cond=cap_group["end_value"] > 0, other=0
)
chart = (
    alt.Chart(cap_group)
    .mark_bar()
    .encode(
        xOffset="model",
        x="tech_type",
        y=alt.Y("sum(end_value)").title("Capacity (MW)"),
        color="model:N",
        opacity=alt.Opacity("planning_year:O", sort="descending"),
        facet=alt.Facet("zone", columns=5),
        order=alt.Order(
            # Sort the segments of the bars by this field
            "planning_year",
            sort="ascending",
        ),
    )
    .properties(width=225, height=125)
)

chart.save(
    f"{str(fig_num).zfill(2)} - regional capacity across models by year.png",
    scale_factor=2,
)

# %%
fig_num += 1
cap_group = cap.groupby(
    ["model", "planning_year", "agg_zone", "tech_type", "case"]  # , as_index=False
)["end_value"].sum()
years = cap["planning_year"].unique()
idx = pd.IndexSlice
df_list = []
for prev_year, year in list(zip(years[:-1], years[1:]))[::-1]:
    print(prev_year, year)
    cap_group.loc[idx[:, year]] = (
        cap_group.loc[idx[:, year]]
        - cap_group.loc[idx[:, prev_year]].reindex(
            cap_group.loc[idx[:, year]].index, fill_value=0
        )
    ).values


cap_group = cap_group.to_frame().reset_index()
cap_group["end_value"] = cap_group["end_value"].where(
    cond=cap_group["end_value"] > 0, other=0
)
chart = (
    alt.Chart(cap_group)
    .mark_bar()
    .encode(
        xOffset="model",
        x="tech_type",
        y=alt.Y("sum(end_value)").title("Capacity (MW)"),
        color="model:N",
        opacity=alt.Opacity("planning_year:O", sort="descending"),
        facet=alt.Facet("agg_zone", columns=4),
        order=alt.Order(
            # Sort the segments of the bars by this field
            "planning_year",
            sort="ascending",
        ),
    )
    .properties(width=250, height=150)
)

chart.save(
    f"{str(fig_num).zfill(2)} - aggregated regional capacity across models by year.png",
    scale_factor=2,
)

# %%
# stacked bar of capacity by model and planning year
fig_num += 1
data = cap.groupby(["tech_type", "model", "planning_year"], as_index=False)[
    "end_value"
].sum()
chart = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        x="model",
        y=alt.Y("sum(end_value)").title("Capacity (MW)"),
        color=alt.Color("tech_type").scale(scheme="tableau20"),
        # column="zone",
        row="planning_year:O",
    )
    .properties(width=350, height=250)
)

chart.save(f"{str(fig_num).zfill(2)} - stacked capacity across models by year.png")
# chart

# %%
# stacked bar of capacity additions by model and planning year
fig_num += 1
data = cap.groupby(["tech_type", "model", "planning_year"], as_index=False)[
    "additions"
].sum()
chart = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        x="model",
        y=alt.Y("additions").title("Capacity additions (MW)"),
        color=alt.Color("tech_type").scale(scheme="tableau20"),
        # column="zone",
        row="planning_year:O",
    )
    .properties(width=350, height=250)
)

chart.save(
    f"{str(fig_num).zfill(2)} - stacked capacity additions across models by year.png"
)

# %%
fig_num += 1
data = cap.groupby(["agg_zone", "tech_type", "model", "planning_year"], as_index=False)[
    "end_value"
].sum()
chart = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        x="model",
        y=alt.Y("end_value").title("Capacity (MW)"),
        color=alt.Color("tech_type").scale(scheme="tableau20"),
        column="agg_zone",
        row="planning_year:O",
    )
    .properties(width=350, height=250)
)

chart.save(
    f"{str(fig_num).zfill(2)} - regional stacked capacity across models by year.png"
)

# %%
fig_num += 1
data = cap.groupby(["agg_zone", "tech_type", "model", "planning_year"], as_index=False)[
    "additions"
].sum()
chart = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        x="model",
        y=alt.Y("additions").title("Capacity additions (MW)"),
        color=alt.Color("tech_type").scale(scheme="tableau20"),
        column="agg_zone",
        row="planning_year:O",
    )
    .properties(width=350, height=250)
)

chart.save(
    f"{str(fig_num).zfill(2)} - regional stacked capacity additions across models by year.png"
)
# %% [markdown]
# ## Generation

# %%
gen = load_data("generation.csv")

# %%
# A faceted choropleth with generation of each tech_type for each year
# for year, _df in cap.groupby("planning_year"):
#     fig_num += 1
#     cap_group = _df.groupby(["model", "zone", "tech_type", "case"], as_index=False)[
#         "end_value"
#     ].sum()

#     chart = alt.hconcat(
#         *(
#             alt.vconcat(
#                 *(
#                     alt.Chart(gdf, title=f"{m}_{tech}")
#                     .mark_geoshape(stroke="white")
#                     .encode(
#                         color="end_value:Q",
#                         # column="model:N",
#                         # row="tech_type:N",
#                     )
#                     .transform_lookup(
#                         lookup="zone",
#                         from_=alt.LookupData(
#                             cap_group.query("tech_type==@tech and model==@m"),
#                             "zone",
#                             list(cap_group.columns),
#                         ),
#                     )
#                     .project("albersUsa")
#                     .properties(width=300, height=150)
#                     for tech in cap_group["tech_type"].unique()
#                 )
#             )
#             for m in cap_group["model"].unique()
#         )
#     )
#     chart.save(f"{str(fig_num).zfill(2)} - {year} regional generation map.png")

# %%
fig_num += 1
gen_group = gen.groupby(
    ["model", "planning_year", "zone", "tech_type", "case"]  # , as_index=False
)["value"].sum()
years = gen["planning_year"].unique()
idx = pd.IndexSlice
df_list = []
for prev_year, year in list(zip(years[:-1], years[1:]))[::-1]:
    print(prev_year, year)
    gen_group.loc[idx[:, year]] = (
        gen_group.loc[idx[:, year]]
        - gen_group.loc[idx[:, prev_year]].reindex(
            gen_group.loc[idx[:, year]].index, fill_value=0
        )
    ).values


gen_group = gen_group.to_frame().reset_index()
gen_group["value"] = gen_group["value"].where(cond=gen_group["value"] > 0, other=0)
chart = (
    alt.Chart(gen_group)
    .mark_bar()
    .encode(
        xOffset="model",
        x="tech_type",
        y=alt.Y("sum(value)").title("Generation (MWh)"),
        color="model:N",
        opacity=alt.Opacity("planning_year:O", sort="descending"),
        facet=alt.Facet("zone", columns=5),
        order=alt.Order(
            # Sort the segments of the bars by this field
            "planning_year",
            sort="ascending",
        ),
    )
    .properties(width=225, height=125)
)

chart.save(
    f"{str(fig_num).zfill(2)} - regional generation across models by year.png",
    scale_factor=2,
)

# %%
fig_num += 1
gen_group = gen.groupby(
    ["model", "planning_year", "agg_zone", "tech_type", "case"]  # , as_index=False
)["value"].sum()
years = gen["planning_year"].unique()
idx = pd.IndexSlice
df_list = []
for prev_year, year in list(zip(years[:-1], years[1:]))[::-1]:
    print(prev_year, year)
    gen_group.loc[idx[:, year]] = (
        gen_group.loc[idx[:, year]]
        - gen_group.loc[idx[:, prev_year]].reindex(
            gen_group.loc[idx[:, year]].index, fill_value=0
        )
    ).values


gen_group = gen_group.to_frame().reset_index()
gen_group["value"] = gen_group["value"].where(cond=gen_group["value"] > 0, other=0)
chart = (
    alt.Chart(gen_group)
    .mark_bar()
    .encode(
        xOffset="model",
        x="tech_type",
        y=alt.Y("sum(value)").title("Generation (MWh)"),
        color="model:N",
        opacity=alt.Opacity("planning_year:O", sort="descending"),
        facet=alt.Facet("agg_zone", columns=4),
        order=alt.Order(
            # Sort the segments of the bars by this field
            "planning_year",
            sort="ascending",
        ),
    )
    .properties(width=250, height=150)
)

chart.save(
    f"{str(fig_num).zfill(2)} - aggregated regional generation across models by year.png",
    scale_factor=2,
)

# %%
# stacked bar of generation by model and planning year
fig_num += 1
data = gen.groupby(["tech_type", "model", "planning_year"], as_index=False)[
    "value"
].sum()
chart = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        x="model",
        y=alt.Y("value").title("Generation (MWh)"),
        color=alt.Color("tech_type").scale(scheme="tableau20"),
        # column="zone",
        row="planning_year:O",
    )
    .properties(width=350, height=250)
)

chart.save(f"{str(fig_num).zfill(2)} - stacked generation across models by year.png")
# chart

# %%
fig_num += 1
data = gen.groupby(["agg_zone", "tech_type", "model", "planning_year"], as_index=False)[
    "value"
].sum()
chart = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        x="model",
        y=alt.Y("value").title("Generation (MWh)"),
        color=alt.Color("tech_type").scale(scheme="tableau20"),
        column="agg_zone",
        row="planning_year:O",
    )
    .properties(width=350, height=250)
)

chart.save(
    f"{str(fig_num).zfill(2)} - regional stacked generation across models by year.png"
)
# %% [markdown]
# ## Capacity factors


# %% [markdown]
# ## Transmission expansion
# %%
tx = load_data("transmission.csv")


tx["start_region"] = tx["line_name"].str.split("_to_").str[0]
tx["dest_region"] = tx["line_name"].str.split("_to_").str[1]
tx["lat1"] = tx["start_region"].map(gdf.set_index("zone")["lat"])
tx["lon1"] = tx["start_region"].map(gdf.set_index("zone")["lon"])
tx["lat2"] = tx["dest_region"].map(gdf.set_index("zone")["lat"])
tx["lon2"] = tx["dest_region"].map(gdf.set_index("zone")["lon"])

first_year = tx["planning_year"].min()
starting_tx = tx.loc[tx["planning_year"] == first_year, :]
starting_tx = starting_tx.rename(columns={"start_value": "value"})
starting_tx["planning_year"] = 2023
# %%
tx_exp = load_data("transmission_expansion.csv")


tx_exp["start_region"] = tx_exp["line_name"].str.split("_to_").str[0]
tx_exp["dest_region"] = tx_exp["line_name"].str.split("_to_").str[1]
tx_exp["lat1"] = tx_exp["start_region"].map(gdf.set_index("zone")["lat"])
tx_exp["lon1"] = tx_exp["start_region"].map(gdf.set_index("zone")["lon"])
tx_exp["lat2"] = tx_exp["dest_region"].map(gdf.set_index("zone")["lat"])
tx_exp["lon2"] = tx_exp["dest_region"].map(gdf.set_index("zone")["lon"])


# %%
# fig_num += 1
# all_figs = []

# for year in tx_exp.planning_year.unique():
#     year_figs = []
#     for model in tx_exp.model.unique():
#         background = (
#             alt.Chart(gdf, title=f"{str(year)}_{model}")
#             .mark_geoshape(
#                 stroke="white",
#                 fill="lightgray",
#             )
#             .project(type="albersUsa")
#         )
#         lines = (
#             alt.Chart(tx_exp.query("planning_year==@year and model==@model"))
#             .mark_rule()
#             .encode(
#                 latitude="lat1",
#                 longitude="lon1",
#                 latitude2="lat2",
#                 longitude2="lon2",
#                 # strokeWidth="value",
#                 color=alt.Color("value:Q").scale(scheme="plasma"),
#             )
#             .project(type="albersUsa")
#         )

#         year_figs.append(background + lines)
#     all_figs.append(alt.hconcat(*year_figs))

# chart = alt.vconcat(*all_figs)

# chart.save(f"{str(fig_num).zfill(2)} - transmission expansion map across models.png")
# # chart


# %%
for year, _df in tx_exp.groupby("planning_year"):
    fig_num += 1
    chart = (
        alt.Chart(_df, title=f"Transmission expansion {str(year)}")
        .mark_bar()
        .encode(
            # xOffset="model:N",
            x="model",
            y=alt.Y("value").title("Transmission expansion (MW)"),
            color="model:N",
            facet=alt.Facet("line_name", columns=10),
        )
    )

    chart.save(f"{str(fig_num).zfill(2)} - {year} transmission expansion bar chart.png")

# %%
fig_num += 1

chart = (
    alt.Chart(pd.concat([starting_tx, tx_exp]))
    .mark_bar()
    .encode(
        # xOffset="model:N",
        x="model",
        y=alt.Y("sum(value)").title("Total transmission expansion (MW)"),
        color="model:N",
        opacity=alt.Opacity("planning_year:O", sort="descending"),
        facet=alt.Facet("line_name", columns=10),
        order=alt.Order(
            # Sort the segments of the bars by this field
            "planning_year",
            sort="ascending",
        ),
    )
)

chart.save(f"{str(fig_num).zfill(2)} - total transmission expansion bar chart.png")


# %% [markdown]
# ## Transmission


# # %%
# fig_num += 1
# all_figs = []

# for year in tx.planning_year.unique():
#     year_figs = []
#     for model in tx.model.unique():
#         background = (
#             alt.Chart(gdf, title=f"{str(year)}_{model}")
#             .mark_geoshape(
#                 stroke="white",
#                 fill="lightgray",
#             )
#             .project(type="albersUsa")
#         )
#         lines = (
#             alt.Chart(tx.query("planning_year==@year and model==@model"))
#             .mark_rule()
#             .encode(
#                 latitude="lat1",
#                 longitude="lon1",
#                 latitude2="lat2",
#                 longitude2="lon2",
#                 # strokeWidth=alt.StrokeWidth("end_value:Q", bin=alt.Bin(step=5000)),
#                 color=alt.Color("end_value:Q").scale(scheme="plasma"),
#             )
#             .project(type="albersUsa")
#         )

#         year_figs.append(background + lines)
#     all_figs.append(alt.hconcat(*year_figs))

# chart = alt.vconcat(*all_figs)

# chart.save(f"{str(fig_num).zfill(2)} - transmission map across models.png")
# chart

# %% [markdown]
# ## Emissions

# %%
emiss = load_data("emissions.csv")
emiss.head()

emiss.loc[emiss["unit"] == "kg", "value"] /= 1000

# %%
fig_num += 1
chart = (
    alt.Chart(emiss)
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="zone",
        y=alt.Y("value").title("CO2 emissions (tonnes)"),
        color="model:N",
        # column="zone",
        row="planning_year:O",
    )
)

chart.save(f"{str(fig_num).zfill(2)} - regional emissions across cases.png")
# chart

# %%

fig_num += 1
chart = (
    alt.Chart(emiss)
    .mark_bar()
    .encode(
        x="model",
        y=alt.Y("value").title("CO2 emissions (tonnes)"),
        color=alt.Color("zone").scale(scheme="tableau20"),
        # column="agg_zone",
        row="planning_year:O",
    )
    .properties(width=350, height=250)
    .resolve_scale(y="independent")
)

chart.save(f"{str(fig_num).zfill(2)} - stacked emissions across models by year.png")
# %%
dispatch = load_data("dispatch.csv")
# dispatch["hour"] = dispatch["hour"].astype("category")
dispatch = dispatch.groupby(
    [
        "planning_year",
        "model",
        "agg_zone",
        "zone",
        "tech_type",
        "resource_name",
        "hour",
    ],
    as_index=False,
)["value"].sum()
group_cols = ["planning_year", "model", "agg_zone", "zone", "tech_type"]
hours = dispatch["hour"].unique()
index_cols = ["resource_name"]
df_list = []
for _, _df in dispatch.groupby(group_cols):
    multi_index = pd.MultiIndex.from_product(
        [_df[col].unique() for col in index_cols] + [hours],
        names=index_cols + ["hour"],
    )
    _df = _df.set_index(index_cols + ["hour"])
    _df = _df.reindex(index=multi_index, fill_value=0)
    _df = _df.reset_index()
    for val, col in zip(_, group_cols):
        _df[col] = val
    df_list.append(_df)

dispatch = pd.concat(df_list, ignore_index=True)

# %%
for year, _df in dispatch.groupby("planning_year"):
    fig_num += 1
    data = _df.groupby(["model", "tech_type", "agg_zone", "hour"], as_index=False)[
        "value"
    ].sum()
    alt.data_transformers.disable_max_rows()
    chart = (
        alt.Chart(data)
        .mark_line()
        .encode(x="hour", y="value", color="model", row="tech_type", column="agg_zone")
        .properties(width=250, height=150)
    ).resolve_scale(y="independent")

    chart.save(
        f"{str(fig_num).zfill(2)} - {year} dispatch by tech type and region.png",
        scale_factor=2,
    )

# %%
wind_dispatch = dispatch.query("resource_name.str.contains('landbasedwind')")
wind_dispatch["cluster"] = wind_dispatch["resource_name"].str.split("_").str[-1]

alt.data_transformers.disable_max_rows()
for year, _df in wind_dispatch.groupby("planning_year"):
    fig_num += 1
    chart = (
        alt.Chart(_df)
        .mark_line()
        .encode(
            x="hour",
            y="sum(value)",
            color="model",
            strokeDash="cluster",
            facet=alt.Facet("zone", columns=5),
        )
        .properties(width=250, height=150)
        .resolve_scale(y="independent")
    )
    chart.save(
        f"{str(fig_num).zfill(2)} - {year} new-build wind dispatch by region.png",
        scale_factor=2,
    )

# %%
solar_dispatch = dispatch.query("resource_name.str.contains('utilitypv')")
solar_dispatch["cluster"] = solar_dispatch["resource_name"].str.split("_").str[-1]

alt.data_transformers.disable_max_rows()
for year, _df in solar_dispatch.groupby("planning_year"):
    fig_num += 1
    chart = (
        alt.Chart(_df)
        .mark_line()
        .encode(
            x="hour",
            y="sum(value)",
            color="model",
            strokeDash="cluster",
            facet=alt.Facet("zone", columns=5),
        )
        .properties(width=250, height=150)
        .resolve_scale(y="independent")
    )
    chart.save(
        f"{str(fig_num).zfill(2)} - {year} new-build solar dispatch by region.png",
        scale_factor=2,
    )

# %%
op_costs = load_genx_operations_data("costs.csv")
fig_num += 1
chart = (
    alt.Chart(
        op_costs[["Costs", "Total", "model"]].query("Total>0 and Costs != 'cTotal'")
    )
    .mark_bar()
    .encode(
        # xOffset="model:N",
        x="model:N",
        y=alt.Y("Total").title("Costs"),
        color="Costs:N",
    )
)
chart.save(
    f"{str(fig_num).zfill(2)} - operational costs in GenX by model.png",
    scale_factor=2,
)


# %%
op_nse = load_genx_operations_data("nse.csv")
fig_num += 1
chart = (
    alt.Chart(op_nse[["Segment", "Total", "model"]].query("Segment == 'AnnualSum'"))
    .mark_bar()
    .encode(
        # xOffset="model:N",
        x="model:N",
        y=alt.Y("Total").title("Annual non-served MWh"),
        color="model:N",
    )
)
chart.save(
    f"{str(fig_num).zfill(2)} - operational NSE in GenX by model.png",
    scale_factor=2,
)

# %%
from pathlib import Path

fig_files = list(Path.cwd().rglob("*.png"))
for f in fig_files:
    print(f, "\n")

print("\n\nFinshed with figure script\n\n")
