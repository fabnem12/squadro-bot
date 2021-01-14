from random import choice
import time

from situationsTOstring import plateau2mini, coupPlusFrequent

class Joueur:
    def __init__(self, situationsConnues, ident, positionsPieces, IA = True, apprentissageVolee = False):
        self.id = ident
        self.estIA = IA
        self.situationsConnues = situationsConnues
        self.pieces = []
        self.coups = dict()

        from Piece import Piece
        for posFixe, posPiece in enumerate(positionsPieces):
            posVariable, aller = posPiece

            piece = Piece(self, posVariable, posFixe+1, aller) #+1 car posFixe va de 0 à 4 au lieu de 1 à 5
            self.pieces.append(piece)

        self.apprentissageVolee = apprentissageVolee

    def coup(self, plateau, y):
        positionVoulue = self.pieces[y].positionVoulueX(plateau)
        plateau.deplaceNew(positionVoulue, self.pieces[y], self.id)

    def gagnant(self):
        return self.nbPiecesArrivees() >= 4

    def enregistreCoups(self):
        if self.gagnant():
            for mini, coup in self.coups.items():
                if mini not in self.situationsConnues:
                    self.situationsConnues[mini] = []

                self.situationsConnues[mini].append(coup)

    def estIA(self):
        return self.estIA

    def IA_coup(self, plateau):
        situation = plateau2mini(plateau, self)
        situationConnue = situation in self.situationsConnues
        loiProba = [] if not situationConnue else self.situationsConnues[situation]
        pourcentageVictoires = 0

        coupsConnusPre = len(loiProba)

        if self.apprentissageVolee:
            debut = time.time()

            nbParties = 0
            from Partie import Partie
            while time.time() - debut < 3: #3 secondes
                partie = Partie(self.situationsConnues, situation)
                partie.interaction()

                nbParties += 1

            nbGagnants = 0 if situation not in self.situationsConnues else len(self.situationsConnues[situation])
            pourcentageVictoires = 100 * (nbGagnants - coupsConnusPre) / nbParties

            loiProba = [] if situation not in self.situationsConnues or len(self.situationsConnues[situation]) < 30 else self.situationsConnues[situation]

        if self.apprentissageVolee:
            coup = coupPlusFrequent(self.situationsConnues[situation])

            self.coups[situation] = coup
            return coup, pourcentageVictoires

        for i in range(1, 5+1):
            if i not in loiProba and not self.pieces[i-1].arrive():
                loiProba.append(i)

        coup = choice(loiProba)
        self.coups[situation] = coup
        return coup, pourcentageVictoires

    def nbPiecesArrivees(self):
        compteur = 0
        for piece in self.pieces:
            compteur += piece.arrive()

        return compteur
