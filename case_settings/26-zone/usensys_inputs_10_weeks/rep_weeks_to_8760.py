"Convert inputs from representative weeks to 8760 using Period_map.csv file"

from pathlib import Path
from typing import List
import pandas as pd

CWD = Path.cwd()


def find_period_map_files() -> List[Path]:
    map_fns = list(CWD.rglob("Period_map.csv"))

    return map_fns


def tdr_to_8760(folder: Path):
    period_map = pd.read_csv(folder / "Period_map.csv")
    load_data = pd.read_csv(folder / "Load_data.csv")
    gen_var = pd.read_csv(folder / "Generators_variability.csv")
    fuel_data = pd.read_csv(folder / "Fuels_data.csv")
    rep_period = pd.read_csv(folder / "Representative_Period.csv")

    # load_data.to_csv(folder / "Load_data_TDR.csv", index=False)
    # gen_var.to_csv(folder / "Generators_variability_TDR.csv", index=False)

    timesteps = int(load_data.loc[0, "Timesteps_per_Rep_Period"])
    num_rep_periods = int(load_data.loc[0, "Rep_Periods"])

    load_first_cols = load_data.loc[:, "Voll":"Sub_Weights"]

    just_load_data = load_data.loc[:, "Time_Index":]

    rep_period_idx = []
    for period in rep_period["slot"]:
        period_num = int(period[1:])
        rep_period_idx.extend([period_num] * timesteps)
    just_load_data["rep_period_idx"] = rep_period_idx
    gen_var["rep_period_idx"] = rep_period_idx

    full_load_list = []
    gen_var_list = []
    for idx, row in period_map.iterrows():
        full_load_list.append(
            just_load_data.loc[just_load_data["rep_period_idx"] == row["Rep_Period"], :]
        )
        gen_var_list.append(
            gen_var.loc[gen_var["rep_period_idx"] == row["Rep_Period"], :]
        )

    full_load_df = pd.concat(full_load_list, ignore_index=True)
    full_gen_var_df = pd.concat(gen_var_list, ignore_index=True)
    full_load_df["Time_Index"] = range(1, len(full_load_df) + 1)
    full_gen_var_df["Time_Index"] = range(1, len(full_gen_var_df) + 1)

    complete_load = pd.merge(
        load_first_cols, full_load_df, left_index=True, right_index=True, how="outer"
    )
    # complete_load = complete_load.drop(columns="rep_period_idx")
    # full_gen_var_df = full_gen_var_df.drop(columns="rep_period_idx")
    complete_load.to_csv(folder / "Load_data_full_year.csv", index=False)
    full_gen_var_df.to_csv(folder / "Generators_variability_full_year.csv")


def main():
    period_map_files = find_period_map_files()
    input_folders = [f.parent for f in period_map_files]
    for f in input_folders:
        if not (f / "Load_data_TDR.csv").exists():
            tdr_to_8760(f)


if __name__ == "__main__":
    main()
