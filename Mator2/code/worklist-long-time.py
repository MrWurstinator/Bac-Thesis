import os
from worklist import *
from mator import *
from database import *
from calendar import monthrange

from moneyadv import costs_money


def costs_BW(relay, cost):
    return relay.averagedBandwidth


def costs_country(relay, cost, cc):
    if relay.country == cc:
        return 0
    else:
        return 1000


def costs_country_DE(relay, costs):
    return costs_country(relay, costs, "DE")


def costs_country_US(relay, costs):
    return costs_country(relay, costs, "US")


def costs_country_FR(relay, costs):
    return costs_country(relay, costs, "FR")


def costs_country_GB(relay, costs):
    return costs_country(relay, costs, "GB")


def costs_country_NL(relay, costs):
    return costs_country(relay, costs, "NL")


FIVEEYES = ["AU", "CA", "GB", "NZ", "US"]


def costs_country_FVEYES(relay, costs):
    if relay.country in FIVEEYES:
        return 0
    else:
        return 1000


# Just for debugging purposes - what C++ knows about our hardware
print("MATor detected", hardwareConcurrency(), "CPU Cores.")

# Sample code
basedir = ""  # svn branch root

years = [str(x) for x in range(2012, 2019)]

# Create Spec classes as in C++
# IP Lookup for this data was done on 25.03.2019
s1 = SenderSpec("144.118.66.83", 39.9597, -75.1968)  # IP: Drexel University (Philadelphia), coordinates: Philadelphia
s2 = SenderSpec("129.79.78.192", 39.174729, -86.507890)  # IP: Indiana University, coordinates: Indiana University in Bloomington
r1 = RecipientSpec("130.83.47.181", 49.8719, 8.6484)  # IP: Darmstadt, coordinates: Darmstadt
r2 = RecipientSpec("134.58.64.12", 50.8796, 4.7009)  # IP: KU Leuven, coordinates: Leuven
# Path selection algorithm.
psTor = PSTorSpec()
# Access class elements as in C++
r1.ports = set([443])
r2.ports = set([443])
# Create a MATor configuration (ideal to store in a worklist...)
Configs = {
    "PSTor-PSTor-443": MATorConfig(s1, s2, r1, r2, psTor, psTor)
}

# Create the adversaries


Adversaries = {
               "k-of-N-10": MATorAdversary(10),
               "BW-1GB/s": MATorAdversary(1000000000, costs_BW),
               "MONEY-100k": MATorAdversary(100000, costs_money),
               "FIVE-EYES": MATorAdversary(1, costs_country_FVEYES)
}

# open csv-database (filename, "default keys")
# keys are the part of a row that have to be unique (and can be used to identify a specific calculation)

matorConsensusBaseDir = "/home/user/mator-src/build/Release/data/consensuses/consensuses-"
matorDatabaseBaseDir = "/home/user/MATor-master/data/serv-descr-db/server-descriptors-"

def strTwoDigit(i):
    ks = str(i)
    if len(ks) == 1:
        ks = "0" + ks
    return ks


with Database("output.csv", ["consensus", "config", "adversary"]) as db:
    wl = MATorWorklist(db)
    for Y in years:
        for M in [f"{n:02}" for n in range(1, 13)]:
            YM = Y + "-" + M
            days = monthrange(int(YM.split("-")[0]), int(YM.split("-")[1]))
            print("added: " + YM)
            for D in [f"{n:02}" for n in range(1, days[1] + 1)]:
                for H in [f"{n:02}" for n in range(0, 19, 6)]:
                    wl.addConsensus(YM + "-" + D + "-" + H, MATorConsensus(matorConsensusBaseDir + YM + "/" + D + "/" + YM + "-" + D + "-" + H + "-00-00-consensus", matorDatabaseBaseDir + YM + ".db"), False)

    for CO in Configs.keys():
        wl.addConfig(CO, Configs[CO])

    for adv in Adversaries.keys():
        wl.addAdversary(adv, Adversaries[adv])

    wl.progress()

