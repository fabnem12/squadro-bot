class Piece:
    def __init__(self, proprio, posVariable, posFixe, aller = True):
        self.positions = [posVariable, posFixe]
        self.aller = aller
        self.proprio = proprio

    def arrive(self):
        return self.positions[0] == 0 and not self.aller

    def positionVariable(self):
        return self.positions[0]

    def positionFixe(self):
        return self.positions[1]

    def setPosVariable(self, posX):
        self.positions[0] = posX

    def setAller(self):
        self.aller = not self.aller

    def retourDepart(self):
        if self.aller:
            self.setPosVariable(0)
        else:
            self.setPosVariable(6)

    def positionVoulueX(self, plateau):
        posVoulue = self.positionVariable()

        if self.aller:
            posVoulue += plateau.nbCasesDeplacement(self)
        else:
            posVoulue -= plateau.nbCasesDeplacement(self)

        return posVoulue
