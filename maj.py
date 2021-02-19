from subprocess import Popen, DEVNULL
import os
import pickle
import psutil
import sys

listeScripts = ["pythonBot/pythonbot.py", "pythonBot/votenew.py", "pythonBot/ranks.py", "squadroGame/bot.py", "discordUtils/discordutils.py"]

if "fichierPID.p" in os.listdir():
    pidsBot = pickle.load(open("fichierPID.p", "rb"))

    for pid in pidsBot:
        if psutil.pid_exists(pid):
            psutil.Process(pid).terminate()

pickle.dump(set(), open("fichierPID.p", "wb"))
os.system("git pull")

foutput = open("logs_bot.log".format(), "a")
for path in listeScripts:
    Popen(["python3", path], stdout = foutput, stderr = foutput)
