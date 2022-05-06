# -*- coding: utf8 -*-
from copy import deepcopy
from tkinter import *
from tkinter.messagebox import *
from typing import Optional
from PIL import Image, ImageTk

#data
infoboxes = dict() #1 entry per act
class Infobox:
    def __init__(self, id: int, act: str, username: str, userAvatar: str, points: int = 0, newPoints: Optional[int] = None):
        self.id, self.act, self.username, self.userAvatar, self.points, self.newPoints = id, act, username, userAvatar, points, newPoints
        self.photoImage = None

votesJury = dict() #1 entry per voter
votesPublic = dict() #1 entry per act
biggestNumberPoints = 12

def genData():
    #let's create 1 infobox per act
    with open("data_contest/acts.csv", "r") as f:
        linesActInfo = list(x[:-1] for i, x in enumerate(f.readlines()) if i)

    for line in linesActInfo:
        idAct, act, username, userAvatar = line.split(";")
        idAct = int(idAct)
        infoboxes[idAct] = Infobox(idAct, act, username, userAvatar, 0)

    #let's register all the votes to show them later
    with open("data_contest/votes.csv", "r") as f:
        linesVotes = list(x[:-1] for i, x in enumerate(f.readlines()) if i)

    for line in linesVotes:
        idAct, username, points = line.split(";")
        idAct = int(idAct)

        if username == "public":
            votesPublic[idAct] = int(points)
        else:
            if username not in votesJury:
                votesJury[username] = dict()
            votesJury[username][idAct] = int(points)

def rankActs(points: dict, publicIncluded: bool = False):
    def countOf(l: list, e: int):
        return sum(x == e for x in l)

    if publicIncluded:
        #ranking criteria:
        #1st the total number of points, then the number of points given by the public
        #then the number of jurors who gave at least some points
        #then the number of biggestNumberPoints given by jurors
        #then the id
        f = lambda x: (sum(points[x]), points[x][-1], len(points[x]), countOf(points[x][:-1], biggestNumberPoints), -x)
    else:
        #same as when the public is included, except that the number of points
        #given by the public is ignored since it's 0 for all
        f = lambda x: (sum(points[x]), len(points[x]), countOf(points[x], biggestNumberPoints), -x)

    return sorted(points, key=f, reverse = True)

def addPointsJury(voter: str, maxPoints: bool = False):
    if not maxPoints:
        for infobox in infoboxes.values():
            infobox.newPoints = None

    for idAct, points in votesJury[voter].items():
        if (points != biggestNumberPoints and not maxPoints) or (points == biggestNumberPoints and maxPoints):
            addPoints(idAct, points)

def addPoints(idAct: str, points: int, public: int = False):
    if public:
        currentPoints[idAct][-1] = points
    else:
        currentPoints[idAct].append(points)
    infobox = infoboxes[idAct]
    infobox.newPoints = points if points != 0 or public else None
    infobox.points += points

genData()
nbActs = len(infoboxes)
halfNbActs = nbActs // 2 + nbActs % 2

currentPoints = {k: [] for k in infoboxes}
listOfVoters = list(votesJury.keys())
rankJuryForPublicVote = rankActs({act: [votes[act] for votes in votesJury.values() if act in votes] for act in infoboxes.keys()})
#rankJuryForPublicVote will be used to give points of the public in the ascending order
#of jury results

#graphic variables
infosGraphic = {"animstep":0, "widthInfo":0, "heightInfo":0, "centerScreenHori":0,
"posInfoboxes": dict(), "prevPoints": deepcopy(currentPoints), "publicIncluded": False,
"heightScreen": 0, "showJuror": (False, False), "voter": "the jury"}

boxVerticalOffset = 90
boxHorizontalOffset = 10
nbFramesAnim = 50

#graphic functions
def getAvatar(infobox: Infobox, size: int):
    if infobox.photoImage is None:
        img = Image.open(f"data_contest/{infobox.userAvatar}").resize((size, size), Image.ANTIALIAS)
        infobox.photoImage = ImageTk.PhotoImage(img)
    return infobox.photoImage

def drawInfobox(canvas: Canvas, infobox: Infobox, x: int, y: int):
    #x, y are the coordinated of the top left corner of the infobox

    width, height = infosGraphic["widthInfo"], infosGraphic["heightInfo"]
    sizeImage = height - 4

    avatar = getAvatar(infobox, sizeImage)

    #box
    canvas.create_rectangle(x, y, x+width, y+height, outline="white", width=2)

    #name of the act + avatar of the author
    canvas.create_image(x+2, y+2, image=avatar, anchor="nw")
    canvas.create_text(x+sizeImage+5, y+height/2, text=infobox.act, fill="white", anchor="w", font=("Ubuntu", round(sizeImage/3), "bold"))

    #new points
    if infobox.newPoints is not None:
        newPoints = infobox.newPoints
        if newPoints == biggestNumberPoints or infosGraphic["publicIncluded"]:
            canvas.create_rectangle(x+width-2*sizeImage, y, x+width-sizeImage, y+height, width=0, fill="white")
            canvas.create_text(x+width-3*(sizeImage//2), y+height//2, text=str(infobox.newPoints), font=("Ubuntu", round(sizeImage/3)), fill="#5F288F", anchor="center")
        else:
            canvas.create_text(x+width-3*(sizeImage//2), y+height//2, text=str(infobox.newPoints), font=("Ubuntu", round(sizeImage/3)), fill="white", anchor="center")

    #points
    canvas.create_rectangle(x+width-sizeImage, y, x+width, y+height, width=0, fill="#4F187F")
    canvas.create_text(x+width-sizeImage//2, y+height//2, text=str(infobox.points), font=("Ubuntu", round(sizeImage/3), "bold"), fill="white", anchor="center")

def calPosInfoboxes(publicFix: bool = False):
    animstep, prevPoints = infosGraphic["animstep"], infosGraphic["prevPoints"]
    publicIncluded = infosGraphic["publicIncluded"]
    posInfoboxes = infosGraphic["posInfoboxes"]
    centerScreen = infosGraphic["centerScreenHori"]
    height = infosGraphic["heightInfo"]

    def posByRank(rank: int):
        x = boxHorizontalOffset + (rank >= halfNbActs) * centerScreen
        y = boxVerticalOffset + (rank % halfNbActs) * height
        return x, y

    if animstep == 0: #no animation, no need to care about previous points
        rankedActs = rankActs(currentPoints if not publicFix else prevPoints, publicIncluded)

        for i, idAct in enumerate(rankedActs):
            posInfoboxes[idAct] = posByRank(i)
    else:
        rate = 1 - animstep / nbFramesAnim
        rankByAct = {k: i for i, k in enumerate(rankActs(currentPoints, publicIncluded))}
        prevRank = {k: i for i, k in enumerate(rankActs(prevPoints, publicIncluded))}

        for idAct in currentPoints:
            x, y = posByRank(rankByAct[idAct])
            xPrec, yPrec = posByRank(prevRank[idAct])

            posInfoboxes[idAct] = (rate*x + (1-rate)*xPrec, rate*y + (1-rate)*yPrec)

def affi(canvas: Canvas):
    canvas.delete("all")

    if not infosGraphic["showJuror"][0]:
        title = f"Votes from {infosGraphic['voter']}" if rankJuryForPublicVote != [] or infosGraphic["showJuror"] != (False, False) or infosGraphic["animstep"] != 0 else "Final results"
        canvas.create_text(infosGraphic["centerScreenHori"], 50, text=title, font=("Ubuntu", -50, "bold"), fill="white")

        calPosInfoboxes(infosGraphic["voter"] == "the public" and infosGraphic["showJuror"][1])
        for idAct, (x, y) in infosGraphic["posInfoboxes"].items():
            drawInfobox(canvas, infoboxes[idAct], x, y)

        if infosGraphic["animstep"] > 0:
            infosGraphic["animstep"] -= 1
    else:
        affiVoteJury(canvas, infosGraphic["showJuror"][1])

    canvas.after(10, lambda: affi(canvas))

def affiVoteJury(canvas: Canvas, firstAppearance: bool = True):
    if listOfVoters != []:
        canvas.delete("all")

        juror = listOfVoters[0]
        rankJuror = sorted(votesJury[juror].items(), key=lambda x: x[1], reverse = True)

        centerScreen = infosGraphic["centerScreenHori"]
        height = round((infosGraphic["heightScreen"] - 150) / 5)

        canvas.create_text(centerScreen, 50, text=f"First votes from {juror}", font=("Ubuntu", -50, "bold"), fill="white")

        def posByRank(rank: int):
            x = boxHorizontalOffset + (rank >= 5) * centerScreen
            y = boxVerticalOffset + (rank % 5) * height
            return x, y

        for i, (idAct, points) in enumerate(rankJuror[1:]):
            infobox = infoboxes[idAct]
            drawInfobox(canvas, infoboxes[idAct], *posByRank(i))

        if firstAppearance:
            infosGraphic["showJuror"] = (True, False)

def updateJury():
    if listOfVoters != []:
        if infosGraphic["showJuror"][0]: #time to go back to the scoreboard, still waiting for the biggestNumberPoints points
            infosGraphic["showJuror"] = (False, True)
            infosGraphic["prevPoints"] = deepcopy(currentPoints)
        elif infosGraphic["showJuror"] == (False, True): #let's see who got biggestNumberPoints points!
            addPointsJury(listOfVoters.pop(0), True)
            infosGraphic["animstep"] = nbFramesAnim

            infosGraphic["showJuror"] = (False, False)
        else: #let's see the details of acts ranked 2 to 5 by the juror
            infosGraphic["showJuror"] = (True, True)
            infosGraphic["voter"] = listOfVoters[0]
            infosGraphic["prevPoints"] = deepcopy(currentPoints)
            infosGraphic["animstep"] = nbFramesAnim // 5
            addPointsJury(listOfVoters[0], False)
    else:
        if infosGraphic["voter"] == "the jury":
            infosGraphic["voter"] = "the public"
        else: #time to switch to the vote of the public
            if infosGraphic["voter"] == "the public":
                updatePublic()
            else:
                if listOfVoters == []: #the public will vote soon
                    infosGraphic["animstep"] = 0
                    infosGraphic["publicIncluded"] = True
                    for infobox in infoboxes.values():
                        infobox.newPoints = None
                        currentPoints[infobox.id].append(0)

                    infosGraphic["voter"] = "the jury"

def updatePublic():
    if infosGraphic["showJuror"] == (False, True):
        if infosGraphic["animstep"] == 0:
            infosGraphic["animstep"] = nbFramesAnim
        infosGraphic["showJuror"] = (False, False)
    else:
        if rankJuryForPublicVote != []:
            infosGraphic["showJuror"] = (False, True)
            infosGraphic["animstep"] = 0
            infosGraphic["prevPoints"] = deepcopy(currentPoints)
            idAct = rankJuryForPublicVote.pop()
            addPoints(idAct, votesPublic[idAct], True)
#window
window = Tk()
window.title("Results of the contest")
window.geometry(f"{window.winfo_screenwidth() // 2}x{window.winfo_screenheight() // 2}")

infosGraphic["widthInfo"] = round(window.winfo_screenwidth()/2 - 40) // 2
infosGraphic["heightInfo"] = round((window.winfo_screenheight() - 100 - 10*halfNbActs) / halfNbActs) // 2
infosGraphic["heightScreen"] = window.winfo_screenheight() // 2
infosGraphic["centerScreenHori"] = window.winfo_screenwidth() // 4

canvas = Canvas(window, width=window.winfo_screenwidth(), height=window.winfo_screenheight(), bg="#5F288F")
canvas.pack()

affi(canvas)

canvas.bind_all("<Return>", lambda x: updateJury())


window.protocol("WM_DELETE_WINDOW", lambda event=None: window.destroy())
window.mainloop()
