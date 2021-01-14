from math import cos, sin, pi
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from PIL import Image, ImageDraw, ImageFont
import os

def filtreCouleur(img, couleur, retraitTransparent = False): #couleur : 'r', 'g', 'b', 'y', 'm', 'c', 'gra', 'n', 'w', 'dy', 'dr'
    for idLig in range(img.size[0]):                         #red, green, blue, yellow, magenta, cyan, gray, noir, white, dark yellow, dark red
        for idCol in range(img.size[1]):
            pixel = img.getpixel((idCol, idLig))
            if couleur == 'r': newPx = (pixel[0], 0, 0)
            elif couleur == 'g': newPx = (0, pixel[1], 0)
            elif couleur == 'b': newPx = (0, 0, pixel[2])
            elif couleur == 'y': newPx = (pixel[0], pixel[1], 0)
            elif couleur == 'm': newPx = (pixel[0], 0, pixel[2])
            elif couleur == 'c': newPx = (0, pixel[1], pixel[2])
            elif couleur == 'gra': newPx = (min(pixel),) * 3
            elif couleur == 'n': newPx = (0, 0, 0)
            elif couleur == 'w': newPx = (255,) * 3
            elif couleur == 'dy': newPx = (0.1, 0.1, 0, 0.25)
            elif couleur == 'dr': newPx = (0.1, 0, 0, 0.25)
            else: raise ValueError("Cette couleur {} est inconnue".format(couleur))

            if len(newPx) == 4: return img

            if retraitTransparent and len(newPx):
                img.putpixel((idCol, idLig), newPx + (255,))
            else:
                img.putpixel((idCol, idLig), newPx + (pixel[3],))

    return img

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
        cote = 70

        imagePlateau = Image.new("RGBA", (cote*7, cote*7))
        imagePlateauDraw = ImageDraw.Draw(imagePlateau)
        imageMouton = Image.open("graphics/mouton.png").convert("RGBA").resize((cote, cote))

        imageMouton1 = filtreCouleur(imageMouton.copy(), 'y')
        imageMouton2 = filtreCouleur(imageMouton.copy(), 'r')

        fontDeplacement = ImageFont.truetype("graphics/BrokenGlass.ttf", 30)
        fontIdCase = ImageFont.truetype("graphics/verdana.ttf", 40)

        for joueur in (self.joueurs[1], self.joueurs[0]):
            for piece in joueur.pieces:
                posX = piece.positionVariable() if 1-joueur.id else piece.positionFixe()
                posY = int(6-piece.positionFixe()) if 1-joueur.id else 6-piece.positionVariable()

                #dessin du mouton sur l'image
                imageDeCeMouton = imageMouton1.copy() if 1-joueur.id else imageMouton2.copy()
                if piece.arrive(): imageDeCeMouton = filtreCouleur(imageDeCeMouton, 'n')

                if piece.aller:
                    imageDeCeMouton = imageDeCeMouton.transpose(Image.FLIP_LEFT_RIGHT)

                if joueur.id: #pour le joueur 2 seulement
                    imageDeCeMouton = imageDeCeMouton.transpose(Image.ROTATE_90)

                imagePlateau.paste(imageDeCeMouton, (posX * cote, posY * cote, (posX + 1) * cote, (posY + 1) * cote))

                #nbCases déplacement
                x = float(7*cote/8) if 1-joueur.id else (posX+7/8)*cote
                y = float((posY+1)*cote-cote/4) if 1-joueur.id else 6.85*cote
                w, h = imagePlateauDraw.textsize(str(self.nbCasesDeplacement(piece)), font=fontDeplacement)
                imagePlateauDraw.text((x-w/2, y-h/2), str(self.nbCasesDeplacement(piece)), fill=(0, 0, 0), font=fontDeplacement)

                if piece.arrive(): continue #on n'affiche pas les numéros des pièces arrivées
                #id de la case
                if 1-joueur.id:
                    x = ((posX+0.27) * cote) if piece.aller else (posX+1-0.27) * cote
                else:
                    x = (posX+0.5) * cote
                y = (posY+0.4)*cote
                idPiece = piece.positionFixe() if joueur.id else 6-piece.positionFixe()
                w, h = imagePlateauDraw.textsize(str(idPiece), font=fontIdCase)
                imagePlateauDraw.text((x-w/2, y-h/2), str(idPiece), fill=(0, 0, 0) if 1-joueur.id else (255, 255, 255), font=fontIdCase)

        for idLigne in range(1, 6+1):
            imagePlateauDraw.line((0, idLigne * cote, cote * 7, idLigne * cote), fill=(0, 0, 0))
        for idColonne in range(1, 6+1):
            imagePlateauDraw.line((idColonne * cote, 0, idColonne * cote, cote * 7), fill=(0, 0, 0))

        fondPlateau = filtreCouleur(Image.new(mode="RGBA", size=(cote * 7, cote * 7)), "w", True)
        fondPlateau.paste(imagePlateau, (0, 0), imagePlateau)
        imagePlateauFinal = fondPlateau
        imagePlateauFinal.save("outputs/output2.png")

        return "outputs/output2.png"

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
