import os
import pandas as pd
from stem.descriptor.reader import DescriptorReader
import fnmatch
import json


# Parses network consensus documents and saves result in a CSV
# Warning: overwrites previous results
def network_consensus():
    content_list = sorted(os.listdir("../data/consensuses"))
    current_year = "0"
    year = "0"
    for content in content_list:
        year = content[-7:-3]
        if year != current_year:
            current_year = year
            with open("../data/cons_csv/netw_cons_" + current_year + ".csv", "w") as file:
                file.write("digest_cons,valid_after,position\n")
        print(content)
        with DescriptorReader("../data/consensuses/" + content) as d_reader:
            with open("../data/cons_csv/netw_cons_" + current_year + ".csv", "a") as file:
                doc1 = ""
                for router_stat in d_reader:
                    flags = router_stat.flags
                    if flags is not None:
                        if "Running" in flags:
                            doc2 = router_stat.document.valid_after
                            if doc1 != doc2:
                                doc1 = doc2
                            file.write(router_stat.digest + "," + router_stat.document.valid_after.__str__()[0:10])
                            if "Exit" in flags and "BadExit" not in flags:
                                file.write(",e\n")
                            elif "Guard" in flags:
                                file.write(",g\n")
                            else:
                                file.write(",m\n")
                    else:
                        with open("../logs/netw_cons.txt", "a") as log:
                            log.write("Flags is None, Date: " + router_stat.document.valid_after.__str__() + "\n")


# Parses server descriptor documents and saves result in a CSV
# Warning: overwrites previous results
def server_descriptors():
    content_list = sorted(os.listdir("../data/"))
    current_year = "0"
    year = "0"

    def none_then_zero(value, bw_key):
        if value is None:
            with open("../logs/serv_desc.txt", "a") as log:
                log.write(bw_key + " value is None, Date: " + year + " Address: " + desc.address + "\n")
            return 0
        return value

    for content in content_list:
        if os.path.isfile("../data/server-descr-arch/" + content) and fnmatch.fnmatch(content, "server-descriptor*.tar.xz"):
            year = content[-14:-10]
            if year != current_year:
                current_year = year
                with open("../data/serv_csv/server_descr_" + current_year + ".csv", "w") as file:
                    file.write("digest_server,address,obs_bandwidth\n")
            print(content)
            with DescriptorReader("../data/server-descr-arch/" + content) as d_reader:
                with open("../data/serv_csv/server_descr_" + current_year + ".csv", "a") as file:
                    for desc in d_reader:
                        file.write(desc.digest() + "," + desc.address + "," +
                                   str(min(none_then_zero(desc.observed_bandwidth, "obs_bw"),
                                       none_then_zero(desc.average_bandwidth, "avg_bw"),
                                       none_then_zero(desc.burst_bandwidth, "bur_bw"))) + "\n")


# Loads and merges parsed server descriptors / network consensuses.
def load_and_merge(netw: str, serv: str):
    print("Loading files {}, {}".format(netw, serv))
    if netw[-9:-4] == serv[-9:-4]:
        netw_df = pd.read_csv("../data/cons_csv/" + netw, parse_dates=["valid_after"],
                              usecols=["digest_cons", "valid_after", "position"], infer_datetime_format=True,
                              dtype={"position": "category"})
        serv_df = pd.read_csv("../data/serv_csv/" + serv, usecols=["digest_server", "address", "obs_bandwidth"],
                              dtype={"address": "category", "obs_bandwidth": int})
        dupes = serv_df[serv_df["digest_server"].duplicated(False)]
        if not dupes.empty:
            with open("../logs/load_and_merge.txt", "a") as log:
                log.write("{}\n".format(dupes))
            serv_df.drop_duplicates(subset="digest_server", inplace=True)
        merge = pd.merge(netw_df, serv_df, left_on="digest_cons", right_on="digest_server", validate="many_to_one")
    else:
        print("Dates are not equal: " + netw + " " + serv)
        return None

    return merge.drop(columns=["digest_server", "digest_cons"])


# Calculates daily mean bandwidth, adds /16 subnet address, drops nodes with bandwidth less than the 25% quantile of that year.
def transform_df(merge: pd.DataFrame, year: str):
    merge = pd.DataFrame(
        merge.groupby(["address", "position", pd.Grouper(key="valid_after", freq="D")])[
            "obs_bandwidth"].mean()).reset_index()
    merge.loc[:, "obs_bandwidth"] = merge.loc[:, "obs_bandwidth"].astype(int)
    merge["ip16"] = merge["address"].str.split(".").str[0:2].str.join(".")
    merge.sort_values(["valid_after", "ip16"], inplace=True)
    merge.rename(columns={"valid_after": "d", "address": "i", "obs_bandwidth": "b", "ip16": "i1", "position": "p"},
                 inplace=True)
    # Set quantile
    quant = 0.25
    quantile = merge["b"].quantile(quant)
    with open("../logs/quantile-log.txt", "a")as log:
        log.write("{} quantile of year {}: {}\n".format(quant, year, quantile))
    return merge.drop(index=merge[merge["b"] < quantile].index)


# Creates hierachical JSON structure used by the visualization
def create_json(merge: pd.DataFrame, year: str):
    # gr_m = merge.groupby(pd.Grouper(key="d", freq="D"))
    gr_m = merge.groupby("d")
    total_amount = len(gr_m)
    with open("../logs/size-log.txt", "a") as log:
        log.write("{} days in year {}\n".format(total_amount, year))
    i_0 = 0
    data_list = []
    for name_0, group_0 in gr_m:
        data_list.append({"d": name_0.date().__str__(), "c": []})
        g = group_0.groupby("i1")
        i_1 = 0

        for name_1, group_1 in g:
            data_list[i_0]["c"].append({"i1": name_1, "c": []})
            g2 = group_1.groupby("p")

            for name_2, group_2 in g2:
                if group_2.empty:
                    continue
                values = group_2.loc[:, ["b", "i"]].to_dict("records")
                data_list[i_0]["c"][i_1]["c"].append({"p": name_2, "c": values})
            i_1 += 1

        if i_0 % 10 == 0:
            print("Processed {} out of {} days".format(i_0, total_amount))
        i_0 += 1
    with open("network_json/network_quantile_small" + year + ".json", "w") as file:
        file.write(json.dumps(data_list))


def main():
    # Warning: overwrites previous results
    network_consensus()
    server_descriptors()
    print("Data collected and stored in csv files")
    netw_cons_list = sorted(os.listdir("../data/cons_csv/"))
    serv_desc_list = sorted(os.listdir("../data/serv_csv/"))
    for netw, serv in zip(netw_cons_list, serv_desc_list):
        print(netw[-8:-4])
        merge = load_and_merge(netw, serv)
        if merge is None:
            continue
        print("Data merged")
        merge = transform_df(merge, serv[-8:-4])
        print("Data transformation finished. \nStarting JSON creation")
        create_json(merge, serv[-8:-4])


if __name__ == '__main__':
    main()

