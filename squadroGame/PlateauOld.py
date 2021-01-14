from math import cos, sin, pi
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import os

class Plateau:
    def __init__(self, joueurs):
        self.joueurs = joueurs

    def nbCasesDeplacement(self, piece):
        proprio = piece.proprio

        if (1-proprio.id and piece.aller) or (proprio.id and not piece.aller):
            deplacements = [1, 3, 2, 3, 1]
        else:
            deplacements = [3, 1, 2, 1, 3]

        return deplacements[piece.positionFixe()-1]

    def affichage(self, jEnCours):
        #piecesJEnCours = jEnCours.pieces
        affi = [""]
        cote = 70
        rTriangle = (cote / 2) * 0.8

        def printF(*args):
            affi[0] += " ".join([str(x) for x in args]) + "\n"

        printF("<?xml version=\"1.0\" standalone=\"no\"?>")
        printF("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{}\" height=\"{}\">".format(cote * 7, cote * 7))

        classes = {
            "ligne":"stroke: #000; stroke-width: 1;",
            1:"fill: #ff0; stroke-width:0;", #le joueur 1 est en jaune
            2:"fill: #f00; stroke-width:0;" #le joueur 2 est en rouge
        }
        classesArrive = { #les couleurs des pièces arrivées
            1:"fill:#880; stroke-width:0; fill-opacity:0.5;", #le joueur 1 est jaune sombre
            2:"fill:#800; stroke-width:0; fill-opacity:0.5;" #le joueur 2 est rouge sombre
        }

        printF("\t<rect width='100%' height='100%' fill='white' />")

        for idLigne in range(1, 6+1):
            printF("\t<line x1='{}' y1='{}' x2='{}' y2='{}' style='{}' />".format(0, idLigne * cote, cote * 7, idLigne * cote, classes["ligne"]))
        for idColonne in range(1, 6+1):
            printF("\t<line x1='{}' y1='{}' x2='{}' y2='{}' style='{}' />".format(idColonne * cote, 0, idColonne * cote, cote * 7, classes["ligne"]))

        for joueur in (self.joueurs[1], self.joueurs[0]):
            for piece in joueur.pieces:
                posX = piece.positionVariable() if 1-joueur.id else piece.positionFixe()
                posY = int(6-piece.positionFixe()) if 1-joueur.id else 6-piece.positionVariable()
                posCentreX, posCentreY = (posX * cote + cote//2, posY * cote + cote//2)

                if 1-joueur.id:
                    angle0 = 0 if piece.aller else pi
                    angle1 = 2*pi/3 if piece.aller else pi/3
                    angle2 = 4*pi/3 if piece.aller else -pi/3
                else:
                    angle0 = (pi/2) if piece.aller else 3*pi/2
                    angle1 = (pi/2 + 2*pi/3) if piece.aller else 3*pi/2 + 2*pi/3
                    angle2 = (pi/2 + 4*pi/3) if piece.aller else 3*pi/2 + 4*pi/3

                p1 = (posCentreX + rTriangle*cos(angle0), posCentreY - rTriangle*sin(angle0))
                p2 = (posCentreX + rTriangle*cos(angle1), posCentreY - rTriangle*sin(angle1))
                p3 = (posCentreX + rTriangle*cos(angle2), posCentreY - rTriangle*sin(angle2))

                couleur = classes[joueur.id+1] if not piece.arrive() else classesArrive[joueur.id+1]
                printF("\t<polygon points='{} {} {}' style='{}' />".format(str(p1)[1:-1], str(p2)[1:-1], str(p3)[1:-1], couleur))

                #nbCases déplacement
                x = float(5*cote/6) if 1-joueur.id else (posX+1)*cote-cote/4
                y = float((posY+1)*cote-cote/4) if 1-joueur.id else 7*cote
                printF("\t<text x='{}' y='{}' font-family='Verdana' font-size='20'>{}</text>".format(x, y, self.nbCasesDeplacement(piece)))

                #id de la case
                x = (posX+0.5)*cote
                y = (posY+0.65)*cote
                idPiece = piece.positionFixe() if joueur.id else 6-piece.positionFixe()
                printF("\t<text x='{}' y='{}' text-anchor='middle' font-size='35' fill='{couleur}'>{}</text>".format(x, y, idPiece, couleur="#000" if 1-joueur.id else "#fff"))

        printF("</svg>")
        affi = affi[0]

        #svg2png(bytestring=affi, write_to="outputs/output.png") #on écrit le png
        if "outputs" not in os.listdir(): os.mkdir("outputs")
        with open("outputs/output.svg", "w") as f: #on écrit le svg
            f.write(affi)

        drawing = svg2rlg("outputs/output.svg")
        renderPM.drawToFile(drawing, "outputs/output.png", fmt="PNG")

        return "outputs/output.png"

    def affichageFenetre(self, fenetre, jEnCours):
        pass

    def deplaceNew(self, posVoulue, piece, idJoueur):
        piecesAdversesPertinentes = [x for x in self.joueurs[1-idJoueur].pieces if x.positionVariable() == piece.positionFixe()]

        casesRestantes = abs(posVoulue - piece.positionVariable())
        aMange = False
        increment = 1 if piece.aller else -1

        while casesRestantes > 0:
            piecesBloquantes = [x for x in piecesAdversesPertinentes if x.positionFixe() == piece.positionVariable() + increment]

            piece.setPosVariable(piece.positionVariable() + increment)
            if len(piecesBloquantes) == 0:
                if aMange: casesRestantes = 0

                if (piece.positionVariable() == 6 and piece.aller) or (piece.positionVariable() == 0):
                    if piece.aller: piece.setAller()
                    casesRestantes = 0
                else:
                    casesRestantes -= 1
            else:
                piecesBloquantes[0].retourDepart()
                aMange = True

    def joueurParId(self, id):
        return self.joueurs[id]
