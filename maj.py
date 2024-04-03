from subprocess import Popen, DEVNULL
import os
import pickle
import psutil
import sys

def killBot():
    if "fichierPID.p" in os.listdir():
        try:
            pidsBot = pickle.load(open("fichierPID.p", "rb"))
        except:
            pass
        else:
            for pid in pidsBot:
                if psutil.pid_exists(pid):
                    psutil.Process(pid).terminate()

listeScripts = ["pythonBot/pythonbot.py", "discordUtils/discordutils.py", "radio_eurovision.py"]

killBot()

pickle.dump(set(), open("fichierPID.p", "wb"))
os.system("git pull")

with open("logs_bot.log", "w") as f: f.write(" ") #astuce pour effacer les logs au démarrage

foutput = open("logs_bot.log", "a")
for path in listeScripts:
    Popen(["python3", path], stdout = foutput, stderr = foutput)
