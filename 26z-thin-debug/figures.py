import os
os.environ['USE_PYGEOS'] = '0'

import pandas as pd
import geopandas as gpd
import altair as alt
from pathlib import Path

alt.renderers.enable("png")

data_path = Path.cwd()
gdf = gpd.read_file("conus_26z_latlon.geojson")
gdf = gdf.rename(columns={"model_region": "zone"})
gdf["lat"] = gdf.geometry.centroid.y
gdf["lon"] = gdf.geometry.centroid.x

print("\n\nstarting figure script\n\n")


# %%
def load_data(fn: str) -> pd.DataFrame:
    df_list = []
    for f in data_path.rglob(fn):
        _df = pd.read_csv(f)
        df_list.append(_df)
    df = pd.concat(df_list)
    if "resource_name" in df.columns:
        df.loc[df["resource_name"].str.contains("ccs"), "tech_type"] = "CCS"
    if "line_name" in df.columns:
        df["line_name"] = df["line_name"].str.replace(
            "Eastern_to_ERCOT", "ERCOT_to_Eastern"
        )

    return df


# %% [markdown]
# ## Capacity

# %%
cap = load_data("resource_capacity.csv")
cap = cap.query("unit=='MW' and not tech_type.isna()")
# cap.head()

# %%

fig_num = 0
# %%
# A faceted choropleth with capacity of each tech_type for each year
for year, _df in cap.groupby("planning_year"):
    fig_num += 1
    cap_group = _df.groupby(["model", "zone", "tech_type", "case"], as_index=False)["end_value"].sum()

    chart = alt.hconcat(*
(alt.vconcat(*(
    alt.Chart(gdf, title=f"{m}_{tech}").mark_geoshape(
    stroke='white'
).encode(
    color="end_value:Q",
    # column="model:N",
    # row="tech_type:N",
).transform_lookup(
    lookup='zone',
    from_=alt.LookupData(cap_group.query("tech_type==@tech and model==@m"), 'zone', list(cap_group.columns))
).project(
    'albersUsa'
).properties(
    width=300,
    height=150
)
    for tech in cap_group["tech_type"].unique()
)
          )
            for m in cap_group["model"].unique()
)
           )
    chart.save(f"{str(fig_num).zfill(2)} - {year} regional capacity map.png")


# %%
# stacked bar of capacity by model and planning year
fig_num += 1
chart = alt.Chart(cap).mark_bar().encode(
    x="model",
    y=alt.Y("sum(end_value)").title("Capacity (MW)"),
    color="tech_type",
    # column="zone",
    row="planning_year:O",
).properties(
    width=350, height=250
)

chart.save(f"{str(fig_num).zfill(2)} - stacked capacity across models by year.png")
# chart

# %% [markdown]
# ## Generation

# %%
gen = load_data("generation.csv")

# %%
# A faceted choropleth with generation of each tech_type for each year
for year, _df in cap.groupby("planning_year"):
    fig_num += 1
    cap_group = _df.groupby(["model", "zone", "tech_type", "case"], as_index=False)["end_value"].sum()

    chart = alt.hconcat(*
(alt.vconcat(*(
    alt.Chart(gdf, title=f"{m}_{tech}").mark_geoshape(
    stroke='white'
).encode(
    color="end_value:Q",
    # column="model:N",
    # row="tech_type:N",
).transform_lookup(
    lookup='zone',
    from_=alt.LookupData(cap_group.query("tech_type==@tech and model==@m"), 'zone', list(cap_group.columns))
).project(
    'albersUsa'
).properties(
    width=300,
    height=150
)
    for tech in cap_group["tech_type"].unique()
)
          )
            for m in cap_group["model"].unique()
)
           )
    chart.save(f"{str(fig_num).zfill(2)} - {year} regional generation map.png")


# %%
# stacked bar of generation by model and planning year
fig_num += 1
chart = alt.Chart(cap).mark_bar().encode(
    x="model",
    y=alt.Y("sum(end_value)").title("Capacity (MW)"),
    color="tech_type",
    # column="zone",
    row="planning_year:O",
).properties(
    width=350, height=250
)

chart.save(f"{str(fig_num).zfill(2)} - stacked generation across models by year.png")
# chart

# %% [markdown]
# ## Capacity factors

# %%


# %% [markdown]
# ## Transmission expansion

# %%
tx_exp = load_data("transmission_expansion.csv")


tx_exp["start_region"] = tx_exp["line_name"].str.split("_to_").str[0]
tx_exp["dest_region"] = tx_exp["line_name"].str.split("_to_").str[1]
tx_exp["lat1"] = tx_exp["start_region"].map(gdf.set_index("zone")["lat"])
tx_exp["lon1"] = tx_exp["start_region"].map(gdf.set_index("zone")["lon"])
tx_exp["lat2"] = tx_exp["dest_region"].map(gdf.set_index("zone")["lat"])
tx_exp["lon2"] = tx_exp["dest_region"].map(gdf.set_index("zone")["lon"])

# %%
fig_num += 1
all_figs = []

for year in tx_exp.planning_year.unique():
    year_figs = []
    for model in tx_exp.model.unique():
        background = alt.Chart(gdf, title=f"{str(year)}_{model}").mark_geoshape(
        stroke='white',
        fill="lightgray",
    ).project(
        type='albersUsa'
    )
        lines = alt.Chart(tx_exp.query("planning_year==@year and model==@model")).mark_rule().encode(
            latitude="lat1",
            longitude="lon1",
            latitude2="lat2",
            longitude2="lon2",
            # strokeWidth="value",
            color=alt.Color("value:Q").scale(scheme="plasma"),
        ).project(
            type='albersUsa'
        )
    
        year_figs.append(background + lines)
    all_figs.append(alt.hconcat(*year_figs))

chart = alt.vconcat(*all_figs)

chart.save(f"{str(fig_num).zfill(2)} - transmission expansion map across models.png")
# chart

# %%


# %% [markdown]
# ## Transmission

# %%
tx = load_data("transmission.csv")


tx["start_region"] = tx["line_name"].str.split("_to_").str[0]
tx["dest_region"] = tx["line_name"].str.split("_to_").str[1]
tx["lat1"] = tx["start_region"].map(gdf.set_index("zone")["lat"])
tx["lon1"] = tx["start_region"].map(gdf.set_index("zone")["lon"])
tx["lat2"] = tx["dest_region"].map(gdf.set_index("zone")["lat"])
tx["lon2"] = tx["dest_region"].map(gdf.set_index("zone")["lon"])

# %%
fig_num += 1
all_figs = []

for year in tx.planning_year.unique():
    year_figs = []
    for model in tx.model.unique():
        background = alt.Chart(gdf, title=f"{str(year)}_{model}").mark_geoshape(
        stroke='white',
        fill="lightgray",
    ).project(
        type='albersUsa'
    )
        lines = alt.Chart(tx.query("planning_year==@year and model==@model")).mark_rule().encode(
            latitude="lat1",
            longitude="lon1",
            latitude2="lat2",
            longitude2="lon2",
            # strokeWidth=alt.StrokeWidth("end_value:Q", bin=alt.Bin(step=5000)),
            color=alt.Color("end_value:Q").scale(scheme="plasma"),
        ).project(
            type='albersUsa'
        )
    
        year_figs.append(background + lines)
    all_figs.append(alt.hconcat(*year_figs))

chart = alt.vconcat(*all_figs)

chart.save(f"{str(fig_num).zfill(2)} - transmission map across models.png")
# chart

# %% [markdown]
# ## Emissions

# %%
emiss = load_data("emissions.csv")
emiss.head()

emiss.loc[emiss["unit"] == "kg", "value"] /= 1000
emiss.loc[emiss["unit"] == "kg", "unit"] = "tons"

# %%
fig_num += 1
chart = alt.Chart(emiss).mark_bar().encode(
    xOffset="model:N",
    x="zone",
    y=alt.Y("value").title("CO2 emissions (tonnes)"),
    color="model:N",
    # column="zone",
    row="planning_year:O",
)

chart.save(f"{str(fig_num).zfill(2)} - regional emissions across cases.png")
# chart

# %%

from pathlib import Path

fig_files = list(Path.cwd().rglob("*.png"))
for f in fig_files:
    print(f, "\n")

print("\n\nFinshed with figure script\n\n")
# %%
