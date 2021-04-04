from math import ceil
from typing import List
from os.path import abspath, dirname, join
cheminOutputs = join(dirname(abspath(__file__)), "outputs/")

def stockePID():
    import os
    import pickle

    fichierPID = join(dirname(abspath(__file__)), "fichierPID.p")
    if not os.path.exists(fichierPID):
        pickle.dump(set(), open(fichierPID, "wb"))

    pids = pickle.load(open(fichierPID, "rb"))
    pids.add(os.getpid())

    pickle.dump(pids, open(fichierPID, "wb"))

def decoupeMessages(listeMsgs: List[str]):
    """
    Pour découper les messages en morceaux plus petits qui passent sur discord
    (1950 caractères)
    """

    res = []
    for msg in listeMsgs:
        if len(msg) > 1950:
            msgSplit = msg.split("\n")

            sousMsgs = [""]
            for sousMsg in (x+"\n" for x in msgSplit):
                lenSousMsg = len(sousMsg)

                if len(sousMsgs[-1]) + lenSousMsg <= 1950:
                    sousMsgs[-1] += sousMsg
                elif lenSousMsg > 1950:
                    for i in range(ceil(lenSousMsg / 1950)):
                        sousMsgs.append(sousMsg[1950*i:1950+1950*i])
                else:
                    sousMsgs.append(sousMsg)

            res += sousMsgs
        else:
            res.append(msg)

    return res
