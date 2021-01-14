from situationsTOstring import plateau2mini, mini2pieces

class Partie:
    def __init__(self, situationsConnues, mini, console = True, apprentissage = True, IA1 = True, IA2 = True, apprentissageVolee = False):
        self.console = True
        self.apprentissage = apprentissage
        self.gagnant = None

        infosPieces = mini2pieces(mini)
        self.idJoueur, piecesJoueurs = infosPieces

        from Joueur import Joueur
        self.joueurs = [None, None]
        self.joueurs[0] = Joueur(situationsConnues, 0, piecesJoueurs[0], IA1, apprentissageVolee)
        self.joueurs[1] = Joueur(situationsConnues, 1, piecesJoueurs[1], IA2, apprentissageVolee)

        from Plateau import Plateau
        self.gameBoard = Plateau(self.joueurs)

        if not console:
            self.fenetre = None

    def interaction(self, coup = -1, IAManoeuvre = False):
        while not self.finPartie():
            if not self.apprentissage:
                self.enregistrement()

            if coup != -1:
                if IAManoeuvre:
                    y = coup
                else:
                    y = int(6 - coup) if 1-self.idJoueur else coup
                if not self.verifCoup(y):
                    return False
                else:
                    y -= 1
            else:
                y = self.demandeCoup()

            self.joueurs[self.idJoueur].coup(self.gameBoard, y)

            if not self.apprentissage:
                self.finCoup()
                self.affichePlateau()

            self.changementJoueur()

            if coup != -1: return True

        if coup != -1: return False

    def affichePlateau(self, moutons = False):
        foncDessin = self.gameBoard.affichageMoutons if moutons else self.gameBoard.affichage

        return foncDessin(self.joueurs[self.idJoueur])

    def changementJoueur(self):
        self.idJoueur = 1-self.idJoueur

    def demandeCoup(self, y = -1):
        y = int(6 - y) if 1-self.idJoueur else y

        if not self.verifCoup(y):
            if self.joueurEnCours().estIA:
                y, _ = self.joueurEnCours().IA_coup(self.gameBoard)
            else:
                if self.console:
                    print("À votre tour, Joueur", self.idJoueur+1, "!!")
                    y = int(input())

                    y = (6 - y) if 1-self.idJoueur else y
                else:
                    self.affichePlateau()

        return y-1

    def finCoup(self):
        self.affichePlateau()

        if self.console:
            pass
        else:
            pass

    def finPartie(self):
        perdant = self.idJoueur
        gagnant = 1-perdant

        if self.joueurs[gagnant].gagnant():
            for joueur in self.joueurs:
                joueur.enregistreCoups()
            if self.apprentissage: return True

            self.gagnant = gagnant
            if not self.apprentissage:
                print("Le joueur", gagnant+1, "a cordialement écrasé son adversaire !!!!")
                self.enregistrement()

            if not self.console:
                pass

            if self.joueurs[0].estIA and not self.joueurs[1].estIA:
                with open("parties_ia1_humain2.txt", "a") as f:
                    f.write("{}\n".format(gagnant+1))
            elif not self.joueurs[0].estIA and self.joueurs[1].estIA:
                with open("parties_humain1_ia2.txt", "a") as f:
                    f.write("{}\n".format(gagnant+1))

            return True

        return False

    def verifCoup(self, coup):
        if coup > 5 or coup <= 0: return False
        if self.joueurs[self.idJoueur].pieces[coup-1].arrive(): return False

        return True

    def enregistrement(self):
        return

        with open("config.cfg", "w") as f:
            printF = lambda *args: f.write(" ".join([str(x) for x in args]) + "\n")

            printF("ia" if self.joueurs[0].estIA else "humain")
            printF("ia" if self.joueurs[1].estIA else "humain")
            printF("console" if self.console else "fenetre")
            printF("volee")

            if self.joueurs[0].gagnant() or self.joueurs[1].gagnant():
                printF("0D=5.'LMNOP")
            else:
                printF(self.mini())

    def plateau(self):
        return self.gameBoard

    def joueurEnCours(self):
        return self.joueurs[self.idJoueur]

    def mieuxPlace(self):
        idEnCours = self.idJoueur

        MINI_DEPART = plateau2mini(self.gameBoard, self.joueurs[idEnCours])
        partieIA = Partie(self.joueurs[idEnCours].situationsConnues, MINI_DEPART, True, False, IA1=True, IA2=True, apprentissageVolee = True)
        partieIA.idJoueur = idEnCours
        coupIA, pourcentageVictoires = self.joueurs[idEnCours].IA_coup(self.gameBoard)

        if pourcentageVictoires < 50:
            gagnant = 1-idEnCours
            pourcentageVictoires = 100 - pourcentageVictoires
        else:
            gagnant = idEnCours

        return gagnant, pourcentageVictoires

    def mini(self):
        return plateau2mini(self.gameBoard, self.joueurs[self.idJoueur])
