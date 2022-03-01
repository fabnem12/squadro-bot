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

listeScripts = ["pythonBot/pythonbot.py", "pythonBot/votenew.py", "discordUtils/ranks.py", "discordUtils/ranks2.py", "squadroGame/bot.py", "discordUtils/discordutils.py", "squadroGame/botNew.py", "voltBot/bump_leaderboard.py", "pythonBot/edtbot.py"]

killBot()

pickle.dump(set(), open("fichierPID.p", "wb"))
os.system("git pull")

with open("logs_bot.log", "w") as f: f.write(" ") #astuce pour effacer les logs au démarrage

foutput = open("logs_bot.log", "a")
for path in listeScripts:
    Popen(["python3", path], stdout = foutput, stderr = foutput)
Popen(["python3.8", "voltBot/modmail_main.py"])
