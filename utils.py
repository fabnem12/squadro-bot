from os.path import abspath, dirname, join
cheminOutputs = join(dirname(abspath(__file__)), "outputs/")

def stockePID():
    import os
    import pickle

    fichierPID = join(dirname(abspath(__file__)), "fichierPID.p")
    pids = pickle.load(open(fichierPID, "rb"))
    pids.add(os.getpid())

    pickle.dump(pids, open(fichierPID, "wb"))
