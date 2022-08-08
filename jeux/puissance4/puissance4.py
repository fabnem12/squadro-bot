from cairosvg import svg2png

class Game:
    def __init__(self, player1, player2):
        self.players = (player1, player2)
        self.currentPlayer = 1
        self.tab = {(i, j): None for i in range(1, 7+1) for j in range(1, 6+1)}

    def action(self, col):
        row = None

        for j in range(1, 6+1):
            if self.tab[col, j] is None:
                row = j
                break

        if row is None:
            return False
        else:
            self.tab[col, row] = self.currentPlayer
            self.currentPlayer = 3-self.currentPlayer
            return True

    def four(self): #vérifier l'existence d'une suite de 4 pions de même couleur
        tab = self.tab
        def verifHori(i, j, player):
            return all(tab.get((i + k, j)) == player for k in range(1, 4))
        def verifVert(i, j, player):
            return all(tab.get((i, j + k)) == player for k in range(1, 4))
        def verifGauc(i, j, player):
            return all(tab.get((i - k, j + k)) == player for k in range(1, 4))
        def verifDroi(i, j, player):
            return all(tab.get((i + k, j + k)) == player for k in range(1, 4))

        for j in range(1, 6+1):
            for i in range(1, 7+1):
                foncs = []
                if j <= 3: foncs += [verifVert]
                if i <= 4: foncs += [verifHori]
                if i <= 4 and j <= 3: foncs += [verifDroi]
                if i >= 4 and j <= 3: foncs += [verifGauc]

                if tab[i, j] is not None:
                    player = tab[i, j]
                    if any(fonc(i, j, player) for fonc in foncs):
                        return player

        if all(tab[i, 6] for i in range(1, 7+1)):
            return False
        else:
            return None

    def drawTab(self):
        code = '<svg version="1.1" baseProfile="full" width="700" height="700" xmlns="http://www.w3.org/2000/svg">\n'
        code += '<rect width="100%" height="100%" fill="blue" />\n\n'

        #affi grille
        for (i, j), player in self.tab.items():
            code += f'<circle cx="{-50+i*100}" cy="{650-j*100}" r="40" fill="white" />\n'
            if player:
                cols = ('#aa0000', '#ff0000') if player == 1 else ('#aaaa00', '#ffff00')
                code += f'<circle cx="{-50+i*100}" cy="{650-j*100}" r="40" fill="{cols[0]}" />\n'
                code += f'<circle cx="{-50+i*100}" cy="{650-j*100}" r="30" fill="{cols[1]}" />\n'

        for i in range(1, 7+1):
            code += f'<rect width="100" height="100" x="{-100+100*i}" y="600" fill="#F0F0F0" />'
            code += f'<circle cx="{-47+i*100}" cy="650" r="25" fill="#0F502A" />'
            code += f'<circle cx="{-50+i*100}" cy="650" r="25" fill="#1FA055" />'
            code += f'<circle cx="{-50+i*100}" cy="650" r="24" fill="#eeee99" />'
            code += f'<text x="{-50+100*i}" y="650" dominant-baseline="middle" text-anchor="middle" fill="#1FA055" font-size="30">{i}</text>'

        code += "</svg>"

        svg2png(bytestring = code, write_to = f"{'-'.join(str(x) for x in self.players)}.png")
        return f"{'-'.join(str(x) for x in self.players)}.png"
