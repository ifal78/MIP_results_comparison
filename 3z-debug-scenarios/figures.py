import pandas as pd
import altair as alt
from pathlib import Path

alt.renderers.enable("png")

data_path = Path.cwd()


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
cap.head()

# %%


# %%
# 2040 case
chart = (
    alt.Chart(
        cap.query("unit=='MW' and not tech_type.isna() and planning_year == 2040")
    )
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="tech_type",
        y=alt.Y("sum(end_value)").title("Capacity (MW)"),
        color="model:N",
        column="zone",
        row="case",
    )
    .properties(width=350, height=250)
)

chart.save("01 - 2040 regional capacity across cases.png")

# chart

# %%
# 2050 case
chart = (
    alt.Chart(
        cap.query("unit=='MW' and not tech_type.isna() and planning_year == 2050")
    )
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="tech_type",
        y=alt.Y("sum(end_value)").title("Capacity (MW)"),
        color="model:N",
        column="zone",
        row="case",
    )
    .properties(width=350, height=250)
)

chart.save("02 - 2050 regional capacity across cases.png")
# chart

# %%
chart = (
    alt.Chart(cap.query("unit=='MW' and planning_year == 2040"))
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="tech_type",
        y=alt.Y("sum(end_value)").title("Capacity (MW)"),
        color="model:N",
        row="case",
    )
    .properties(width=500, height=250)
)

chart.save("03 - 2040 total capacity across cases.png")
# chart

# %%
chart = (
    alt.Chart(cap.query("unit=='MW' and planning_year == 2050"))
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="tech_type",
        y=alt.Y("sum(end_value)").title("Capacity (MW)"),
        color="model:N",
        row="case",
    )
    .properties(width=500, height=250)
)

chart.save("04 - 2050 total capacity across cases.png")
# chart

# %% [markdown]
# ## Generation

# %%
gen = load_data("generation.csv")
gen.head()

# %%
chart = (
    alt.Chart(gen.query("planning_year == 2040"))
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="tech_type",
        y=alt.Y("sum(value)").title("Generation (MWh)"),
        color="model:N",
        row="case",
        column="zone",
    )
    .properties(width=350, height=250)
)

chart.save("05 - 2040 regional generation across cases.png")
# chart

# %%
chart = (
    alt.Chart(gen.query("planning_year == 2050"))
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="tech_type",
        y=alt.Y("sum(value)").title("Generation (MWh)"),
        color="model:N",
        row="case",
        column="zone",
    )
    .properties(width=350, height=250)
)

chart.save("06 - 2050 regional generation across cases.png")
# chart

# %%
chart = (
    alt.Chart(gen.query("planning_year == 2040"))
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="model",
        y=alt.Y("sum(value)").title("Generation (MWh)"),
        color="tech_type:N",
        row="case",
    )
    .properties(width=350, height=250)
)

chart.save("07 - 2040 total generation across cases.png")
# chart

# %%
chart = (
    alt.Chart(gen.query("planning_year == 2050"))
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="model",
        y=alt.Y("sum(value)").title("Generation (MWh)"),
        color="tech_type:N",
        row="case",
    )
    .properties(width=350, height=250)
)

chart.save("08 - 2050 total generation across cases.png")
# chart

# %% [markdown]
# ## Capacity factors

# %%
cf = gen.groupby(["model", "zone", "case", "tech_type", "planning_year"], sort=False)[
    "value"
].sum() / (
    cap.groupby(["model", "zone", "case", "tech_type", "planning_year"], sort=False)[
        "end_value"
    ].sum()
    * 8760
)
cf.name = "capacity_factor"
cf = pd.DataFrame(cf)

cf["capacity"] = cap.groupby(["model", "zone", "case", "tech_type", "planning_year"])[
    "end_value"
].sum()
cf = cf.reset_index()
cf.loc[cf["capacity_factor"] > 1, "capacity_factor"] = 1
cf.head()

# %%
cf.query("case=='greenfield' and planning_year==2050 and tech_type=='Wind'")

# %%
drop_techs = ["Geothermal"]  # , "Battery"] "CCS",
year = 2040

base = alt.Chart().encode(
    xOffset="model:N",
    x="tech_type:N",
)

chart_cf = base.mark_point(color="black").encode(
    alt.Y("capacity_factor").title("Capacity Factor", titleColor="blue"),
)

chart_cap = base.mark_bar().encode(
    alt.Y("capacity").title("Capacity (MW)"),
    color="model",
    # tooltip=["case", "zone", "model", "tech_type", "planning_year", "capacity"],
)


layer = []
for case in cf.case.unique():
    row = []
    for zone in cf.zone.unique():
        row.append(
            alt.layer(
                chart_cap,
                chart_cf,
                title=f"{zone}_{year}",
                data=cf.query(
                    "~tech_type.isin(@drop_techs) and zone == @zone and case == @case and planning_year == @year"
                ),
            )
            .resolve_scale(y="independent")
            .properties(width=350, height=250)
        )
    layer.append(alt.concat(*row).properties(title=case))

chart = alt.vconcat(*layer)

chart.save("09 - 2040 regional capacity and CF across cases.png")
# chart

# %%
drop_techs = ["Geothermal"]  # , "Battery"] "CCS",
year = 2050

base = alt.Chart().encode(
    xOffset="model:N",
    x="tech_type:N",
)

chart_cf = base.mark_point(color="black").encode(
    alt.Y("capacity_factor").title("Capacity Factor", titleColor="blue"),
)

chart_cap = base.mark_bar().encode(
    alt.Y("capacity").title("Capacity (MW)"),
    color="model",
    # tooltip=["case", "zone", "model", "tech_type", "planning_year", "capacity"],
)


layer = []
for case in cf.case.unique():
    row = []
    for zone in cf.zone.unique():
        row.append(
            alt.layer(
                chart_cap,
                chart_cf,
                title=f"{zone}_{year}",
                data=cf.query(
                    "~tech_type.isin(@drop_techs) and zone == @zone and case == @case and planning_year == @year"
                ),
            )
            .resolve_scale(y="independent")
            .properties(width=350, height=250)
        )
    layer.append(alt.concat(*row).properties(title=case))

chart = alt.vconcat(*layer)
chart.save("10 - 2050 regional capacity and CF across cases.png")
# chart

# %% [markdown]
# ## Transmission expansion

# %%
tx_exp = load_data("transmission_expansion.csv")
tx_exp.head()

# %%
chart = (
    alt.Chart(tx_exp)
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="line_name",
        y=alt.Y("sum(value)").title("Transmission expansion (MW)"),
        color="model:N",
        column="planning_year",
        row="case",
    )
    .resolve_scale(y="independent")
)

chart.save("11 - transmission expansion across cases.png")
chart

# %%


# %% [markdown]
# ## Transmission

# %%
tx = load_data("transmission.csv")
tx.head()

# %%
chart = (
    alt.Chart(tx.query("planning_year >= 2030"))
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="line_name",
        y=alt.Y("sum(end_value)").title("Transmission (MW)"),
        color="model:N",
        column="planning_year",
        row="case",
    )
    .resolve_scale(y="independent")
)

chart.save("12 - total transmission across cases.png")
# chart

# %% [markdown]
# ## Emissions

# %%
emiss = load_data("emissions.csv")
emiss.head()

# %%
chart = (
    alt.Chart(emiss)
    .mark_bar()
    .encode(
        xOffset="model:N",
        x="zone",
        y=alt.Y("value").title("CO2 emissions (tonnes)"),
        color="model:N",
        column="planning_year",
        row="case",
    )
    .resolve_scale(y="independent")
)

chart.save("13 - regional emissions across cases.png")
# chart

# %%

from pathlib import Path

fig_files = list(Path.cwd().rglob("*.png"))
for f in fig_files:
    print(f, "\n")

print("\n\nFinshed with figure script\n\n")
# %%
