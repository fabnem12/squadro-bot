from random import randint

pieces2mini = ['\a','!', '"', '#', '$', '%', '&', '\'', '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y','z', '{', '|', '}', '~', ' ','\t']

def plateau2miniOld(plateau, jEnCours):
    mini = str(jEnCours.id)

    for joueur in (plateau.joueurParId(0), plateau.joueurParId(1)):
        for piece in joueur.pieces:
            posX = piece.positionVariable() if 1-joueur.id else piece.positionFixe()
            posY = int(6-piece.positionFixe()) if 1-joueur.id else 6-piece.positionVariable()

            idSubstitution = posY * 7 + posX
            if not piece.aller: idSubstitution += 48
            mini += pieces2mini[idSubstitution]

    return mini

def plateau2mini(plateau, jEnCours):
    mini = str(jEnCours.id + 1)

    for joueur in (plateau.joueurParId(0), plateau.joueurParId(1)):
        #on itère sur les pièces dans l'ordre "naturel pour un humain", de haut en bas pour le joueur 0 et de gauche à droite pour le joueur 1
        #d'où le reversed pour le joueur 0, vu que dans le repère utilisé, la pièce 1 est en bas, la pièce 5 en haut. il faut inverser
        for piece in joueur.pieces if joueur.id == 1 else reversed(joueur.pieces):
            domaine = "0123456" if piece.aller else "abcdefg"
            #on utilise des lettres pour indiquer la position dans le cas où la pièce est en retour
            mini += domaine[piece.positionVariable()]

    return mini

def mini2piecesOld(mini):
    idJoueurTrait = int(mini[0])
    mini = mini[1:]

    pieces = [[], []]

    for i, pieceStr in enumerate(mini):
        idSubstitution = -1
        for index in range(len(pieces2mini)):
            if pieces2mini[index] == pieceStr:
                idSubstitution = index

        aller = idSubstitution < 48
        idSubstitution %= 48

        posY = idSubstitution // 7
        posX = idSubstitution % 7

        piece = [0, 0, 0]
        piece[0] = int(6-posY) if i//5 else posX #posVariable
        piece[1] = posX if i//5 else 6-posY #posFixe
        piece[2] = aller

        pieces[i//5].append(piece)

    return (idJoueurTrait, pieces)

def mini2pieces(mini: str):
    idJoueurTrait = int(mini[0]) - 1
    mini = mini[1:].lower()
    mini = mini[4::-1] + mini[5:]

    pieces = [[], []]

    for i, pieceStr in enumerate(mini):
        domaine = "0123456" if pieceStr in "0123456" else "abcdefg"
        posVariable = domaine.index(pieceStr)

        #astuce pour récupérer la position fixe à partir de i et du numéro de joueur (i // 5)
        posFixe = 1 + i % 5#(5 - i) if i // 5 == 0 else i - 4
        aller = domaine == "0123456"

        infosPiece = (posVariable, aller)
        pieces[i//5].append(infosPiece)

    return (idJoueurTrait, pieces)

def coupPlusFrequent(coups):
    nbOccurences = [0 for _ in range(5)]
    for coup in coups: nbOccurences[coup-1] += 1

    max = randint(1, 5)
    maxOccurences = -1
    for i in range(5):
        if nbOccurences[i] > maxOccurences or (nbOccurences[i] == maxOccurences and randint(0,1)):
            maxOccurences = nbOccurences[i]
            max = i+1

    return max

def infosPartie():
    lignes = ["humain", "humain", "console", "volee", "0D=5.'LMNOP"]

    with open("config.cfg", "r") as f:
        idLigne = 0
        for ligne in f.readlines():
            ligne = ligne.replace("\n", "")
            if idLigne == 4 and len(ligne) != 11:
                continue

            lignes[idLigne] = ligne
            idLigne += 1
            if idLigne >= len(lignes): break

    infos = (lignes[0].lower() == "ia", lignes[1].lower() == "ia", lignes[2] == "console", lignes[3] == "volee", lignes[4])

    return infos

def lectureCSV(situationsConnues):
    with open("situations.csv", newline='') as f:
        for ligne in f.readlines():
            ligne = ligne.replace("\n", "")

            situation, coups = ligne.split(";")
            coupsInt = [int(x) for x in coups]

            situationsConnues[situation] = coupsInt

def enregistreCSV(situationsConnues):
    with open("situations.csv", "w") as f:
        for situation, coups in situationsConnues.items():
            f.write(situation + ";" + "".join([str(x) for x in coups]) + "\n")
