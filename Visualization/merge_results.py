import pandas as pd
import numpy as np
import os

# Takes results from Mator located in ../results/mator-X-XXXX merges them, computes daily mean, merges them to one dataframe and finally saves it in a csv.
# Raw results should be located in:
# Mator1PSTor: "../results/mator-1-tor"
# Mator1Distributor: "../results/mator-1-distri"
# Mator2: "../results/mator-2"

def load_results_mator1(results_folder: str, column_prefix: str):
    df_list = []
    for content in sorted(os.listdir("../results/" + results_folder)):
        if os.path.isfile("../results/" + results_folder + "/" + content):
            df_list.append(pd.read_csv("../results/" + results_folder + "/" + content,
                                       dtype={"SA": np.float, "RA": np.float, "RelA": np.float},
                                       index_col="Date", parse_dates=["Date"]))
    df = pd.concat(df_list, axis=0, sort=False)
    df.rename(columns={"SA": column_prefix + "SA",
                       "RA": column_prefix + "RA",
                       "RelA": column_prefix + "RelA"}, inplace=True)
    return df.resample('D').mean()


def load_results_mator2(loc_mator2: str):
    df = pd.read_csv("../results/" + loc_mator2, sep=";", index_col="consensus", parse_dates=["consensus"])
    df = df.pivot(columns="adversary", values=["SA", "RA", "RelA", "PreciseSA", "PreciseRA", "PreciseRelA"])
    df.columns = df.columns.map("m_2_{0[0]}-{0[1]}".format)
    return df.resample("D").mean().dropna(axis=1, how="all")


def merge_res():
    loc_and_name = [("mator-1-tor", "m_1_tor-"),
                    ("mator-1-distri", "m_1_dist-")
                    ]
    loc_mator2 = "mator-2/mator-2-results.csv"
    df_list = []
    for entry in loc_and_name:
        df_list.append(load_results_mator1(entry[0], entry[1]))

    df = pd.concat(df_list, axis=1, sort=False)
    # Reorder columns
    df = df.iloc[:, [0, 3, 1, 4, 2, 5]]
    df = pd.concat([df, load_results_mator2(loc_mator2)], axis=1, sort=True)
    df.to_csv("daily-mean-anon.csv")


def main():
    merge_res()


if __name__ == '__main__':
    main()
