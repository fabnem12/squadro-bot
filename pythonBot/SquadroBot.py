"""**SquadroBot** est un module additionnel qui va avec le bot Squadro.

Pour importer une constante ou une fonction, il faut utiliser la ligne de code python suivante :
from SquadroBot import NOM\_DU\_TRUC\_A\_IMPORTER

__**Constantes utiles**__ :
_**i**_, l'unité imaginaire
_**e**_, le nombre d'Euler
_**phi**_, le nombre d'or

__**Fonctions disponibles**__ :
**Imagine**, une fonction pour représenter des fonctions complexes sur une image
**img2gif**, une fonction pour faire un gif à partir d'images déjà générées

(pour voir comment utiliser les fonctions, faites help(SquadroBot.NOM_FONCTION))
"""
from cmath import phase, exp, isnan
from math import cos, sin, sqrt
from typing import Dict, List, Optional, Union

e = exp(1)
phi = (1 + sqrt(5)) / 2
i = 1j

def couleurDefautImagine(z):
    """Convertir un nombre complexe en la couleur dans laquelle le représenter
    """

    if isnan(z):
        return 0, 0, 0

    argument = phase(z)
    r, g = round(127.5 * (cos(argument) + 1)), round(127.5 * (sin(argument) + 1))
    b = 255 - r

    return r, g, b

class Imagine:
    """Imagine : Classe pour générer une image représentant une fonction complexe.
    Version C++ disponible sur : https://github.com/fabnem12/Imagine

    Prototype :
    Imagine(fonction, centre = 0 + 0*i, echelle = 200, pixelsX = 500, pixelsY = 500)

    Exemple d'utilisation :
    def f(z): return 1 / sin(z) + Re(z) + tan(Im(z))

    im = Imagine(f, 1 + i) #pour préparer l'image
    getFile(im.image()) #pour récupérer l'image (ne pas oublier le ".image()" !)


    Note  : echelle est en pixels par unité, c'est un unique nombre (le repère est orthonormé)
            echelle = 200 signifie ici qu'il y a 200 pixels entre le point d'affixe 0 et celui d'affixe 1, idem entre 0 et i
    Note2 : si la fonction n'est pas définie en un point, le programme considère qu'elle y vaut 0
    Note3 : vous pouvez multiplier la résolution de l'image par k en multipliant directement l'objet Imagine par k
    """

    def __init__(self, fonction: type(lambda: 0), centre = 0, echelle = 200, pixelsX = 500, pixelsY = 500, colorisation = couleurDefautImagine):
        #on vérifie que fonction est bien une fonction
        import inspect
        if not callable(fonction):
            raise ValueError("Vous ne m'avez pas donné de fonction à une variable !")
        if len(inspect.getfullargspec(fonction)[0]) == 0:
            raise ValueError("J'attends une fonction qui prend un paramètre un nombre complexe !")
        if not callable(colorisation):
            raise ValueError("Vous n'avez pas fourni un fonction de colorisation valable !")

        dimImage = (pixelsX, pixelsY)

        #on la modifie pour gérer les cas de non-définition, en fixant dans ce cas f(z) = 0
        def fun(z):
            try:
                return fonction(z)
            except NameError as e:
                raise e
            except:
                return float("NaN")

        self.fonction = fun
        self.foncCouleur = colorisation

        self.centre = complex(centre)
        self.echelle = echelle #pixels par unité
        self.dimImage = tuple(map(round, dimImage))

        if dimImage[0] <= 0:
            raise ValueError("Impossible de faire une image aussi étroite ({}) !".format(dimImage[0]))
        if dimImage[1] <= 0:
            raise ValueError("Impossible de faire une image aussi basse ({}) !".format(dimImage[1]))

        import os, time
        self.nomFichier = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs/{}.png").format(round(time.time(), 10))

    def __mul__(self, nb):
        pixelsX, pixelsY = map(lambda x: round(x * nb), self.dimImage)
        return Imagine(self.fonction, self.centre, self.echelle * nb, pixelsX, pixelsY, self.foncCouleur)
    def __rmul__(self, nb):
        return self * nb

    def __imul__(self, nb):
        self.echelle *= nb
        self.dimImage = tuple(map(lambda x: round(x * nb), self.dimImage))
        return self

    def __del__(self):
        if "dimImage" not in dir(self): return

        """largeur, hauteur = self.dimImage
        centre, echelle = self.centre, self.echelle"""

        import os
        try:
            os.remove(self.nomFichier)
        except:
            pass

    def z2couleur(self, z):
        return self.foncCouleur(z)

    def image(self):
        """Dessine l'image représentant la fonction et renvoie son chemin d'accès
        """

        from PIL import Image

        largeur, hauteur = self.dimImage
        centre, echelle = complex(self.centre), self.echelle
        img = Image.new("RGB", self.dimImage)
        pixels = img.load() #équivalent du loadPixels() de processing

        centreurX, centreurY = (largeur/2 - centre.real * echelle, hauteur/2 + centre.imag * echelle)

        z2couleur = self.z2couleur
        pos2z = lambda x, y: ((x - centreurX) - 1j * (y - centreurY)) / echelle
        fonc = self.fonction

        for y in range(hauteur):
            for x in range(largeur):
                pixels[x, y] = z2couleur(fonc(pos2z(x, y)))

        img.save(self.nomFichier, "png")
        return self.nomFichier, self

def brainfuckSquadroBot(foncPrint):
    print = foncPrint
    from numpy.random import randint

    def brainfuckTrue(code, entree = ""):
        """Fonction pour exécuter du code brainfuck

        prototype : brainfuck(code, entree = "")
        - code est un str qui contient du code brainfuck
        - entree est "l'entrée système", en pratique ici ce sera un str dont les caractères sont lisibles les uns après les autres
        - les commandes sont les commandes brainfuck standard https://fr.wikipedia.org/wiki/Brainfuck
        - il y a 2 autres commandes ajoutés gracieusement par <@619574125622722560> :
          - ! pour afficher directement le nombre de la case courante (si c'est 32, ! affiche 32 au lieu d'un espace)
          - ? pour générer un nombre aléatoire entre 0 et le nombre de la case courante (positif ou négatif)

        pour lancer le code :
        """

        def incrTab(tab, index, increment):
            if index not in tab: tab[index] = increment
            else: tab[index] += increment

        valTab = lambda tab, index: tab[index] if index in tab else 0
        def setTab(tab, index, val): tab[index] = val
        def valEntree(entree):
            if entree[0] == "": return 0
            else:
                premierChar = entree[0][0]
                entree[0] = entree[0][1:]
                return ord(premierChar)

        tableau = dict()
        pointeur = 0
        pointeurCode = 0
        entree = [entree, 0]

        while True:
            char = code[pointeurCode]
            if char == ">": pointeur += 1
            elif char == "<": pointeur -= 1
            elif char == "+": incrTab(tableau, pointeur, 1)
            elif char == "-": incrTab(tableau, pointeur, -1)
            elif char == ".": print(chr(valTab(tableau, pointeur)), end = "")
            elif char == "!": print(valTab(tableau, pointeur), end = " ")
            elif char == ",": setTab(tableau, pointeur, valEntree(entree))
            elif char == "?":
                maxRandom = valTab(tableau, pointeur)
                valRandom = randint(0, abs(maxRandom) + 1)
                if maxRandom < 0: valRandom *= -1
                setTab(tableau, pointeur, valRandom)

            elif char == "[" and valTab(tableau, pointeur) == 0:
                finsAIgnorer = 0
                for index, char2 in list(enumerate(code))[pointeurCode+1:]:
                    if char2 == "]":
                        if finsAIgnorer == 0:
                            pointeurCode = index
                            break
                        else: finsAIgnorer -= 1
                    elif char2 == "[":
                        finsAIgnorer += 1
            elif char == "]" and valTab(tableau, pointeur) != 0:
                debutsAIgnorer = 0
                for index in range(pointeurCode-1, -1, -1):
                    char2 = code[index]
                    if char2 == "[":
                        if debutsAIgnorer == 0:
                            pointeurCode = index - 1
                            break
                        else: debutsAIgnorer -= 1
                    elif char2 == "]":
                        debutsAIgnorer += 1

            pointeurCode += 1
            if pointeurCode >= len(code): break

        brainfuckTrue.tab = tableau

    return brainfuckTrue

def getPlot():
    from random import randint
    import os
    import matplotlib.pyplot as plt

    fileName = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs/{}.png".format(randint(10000, 100000)))

    plt.savefig(fileName)

    return fileName

def img2gif(images, fps = 1):
    """Pour générer un gif à partir d'une liste d'images déjà générées

    Prototype : img2gif(images, fps = 1)
    """

    from time import time
    import imageio

    nomFichier = "outputs/gif{}.gif".format(round(time(), 10))
    imageio.mimsave(nomFichier, [imageio.imread(x) for x in images], fps = fps)

    return nomFichier

def ptrlib():
    """Module pour gérer des pointeurs dans Python
    """

    pointeurs = dict()
    nullptr = 0

    def new(obj):
        ptrObj = id(obj)
        pointeurs[ptrObj] = obj

        return ptrObj

    def malloc(type = None):
        from random import randint

        #on sélectionne une case non occupée dans pointeurs
        ptr = randint(1e9, 1e10)
        while ptr in pointeurs: ptr = randint(1e9, 1e10)
        #on y met None, puis on renvoie le pointeur correspondant
        pointeurs[ptr] = None

        return ptr

    def star(ptr):
        if ptr in pointeurs:
            return pointeurs[ptr]
        else:
            raise Exception("Segfault")

    def change(ptr, val):
        if ptr in pointeurs:
            pointeurs[ptr] = val
        else:
            raise Exception("Segfault")

    def delete(ptr):
        if ptr in pointeurs:
            del pointeurs[ptr]
        else:
            raise Exception("Segfault")

    return {"new": new, "amp": new, "star": star, "delete": delete, "free": delete, "change": change, "malloc": malloc, "nullptr": nullptr, "NULL": nullptr}


def linkedlistlib():
    """Module pour manipuler des listes chaînées en Python"""

    class Liste:
        def __init__(self, val, suivant = None):
            self.val = val
            self.suivant = suivant

        def __str__(self):
            if self.val is None: return "[]"
            else:
                txt = str(self.val)
                bloc = self

                while bloc.suivant is not None:
                    bloc = bloc.suivant
                    txt += " :: " + str(bloc.val)

                return txt

        def __repr__(self): return str(self)

    def ajoute(val, liste):
        return Liste(val, liste)

    def empile(val, liste):
        if isinstance(liste, Liste) and liste.val is not None:
            tmp = ajoute(liste.val, liste.suivant)
            liste.val = val
            liste.suivant = tmp
        else:
            pass

    def premier(liste):
        if not isinstance(liste, Liste):
            raise ValueError("Pas de premier élément à une liste vide")
        else:
            return liste.val

    def suite(liste):
        if not isinstance(liste, Liste):
            raise ValueError("Pas de suite à une liste vide")
        else:
            return liste.suivant

    def initVide(liste):
        if isinstance(liste, Liste):
            liste.val = None
            liste.suivant = None
            return liste
        else:
            return ajoute(None, None)

    return locals()

class TransitionTuring:
    """
    Représentation d'une transition d'état de machine de Turing.
    """

    def __init__(self, char: str, arrivee: 'EtatTuring', direction: str, newChar: Optional[str] = None):
        self.arrivee = arrivee #arrivee est un EtatTuring
        self.char, self.direction, self.newChar = char, direction, char if newChar is None else newChar

        if self.direction not in "DGI":
            raise ValueError(f"La direction '{direction}' n'est pas valide")

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"{self.char}{self.direction}{self.newChar if self.char != self.newChar else ''} vers #{self.arrivee}"

class EtatTuring:
    """
    Représentation d'un état de machine de Turing.
    """

    def __init__(self, ident: str, acceptant: bool = False, transitions: Dict[str, TransitionTuring] = None):
        self.ident, self.acceptant = ident, acceptant
        self.transitions = dict() if transitions is None else transitions

    def addTransition(self, transition: TransitionTuring):
        self.transitions[transition.char] = transition

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        infosTransitions = "\n".join(f"- {str(tr)}" for tr in self.transitions.values())
        return f"État #{self.ident}, transitions :\n{infosTransitions}"

    def __contains__(self, key):
        return key in self.transitions

    def __getitem__(self, item: str):
        return self.transitions[item]

    def __setitem__(self, item: str, val: Union[tuple, TransitionTuring]):
        if isinstance(val, tuple):
            if len(val) < 2: raise Exception("Pas assez d'infos pour la transition")
            else:
                self.transitions[item] = TransitionTuring(*list((item,) + val))
        elif isinstance(val, TransitionTuring):
            val.char = item
            self.transitions[item] = val
        else:
            raise TypeError("Il faut un objet de type TransitionTuring or tuple")

class MachineTuring:
    """
    Représentation d'une machine de Turing mono-infinie à une bande. (+ améliorations à venir !)
    Le triangle initial de la bande est représenté par la chaîne "|>".
    L'état initial de la machine de Turing doit avoir l'identifiant 0.
    """

    def __init__(self, etats: Optional[Dict[int, EtatTuring]] = None):
        if etats is None:
            etats = dict()

        self.etats = etats
        self.dernierParcours = []
        self.print = print

    def addState(self, etat: EtatTuring):
        self.etats[etat.ident] = etat

    def __getitem__(self, ident):
        return self.etats[ident]

    def __setitem__(self, ident, val):
        if isinstance(val, EtatTuring):
            val.ident = ident
            self.etats[ident] = val
        else:
            raise TypeError("Il faut un objet de type EtatTuring")

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "\n".join(str(e) for e in self.etats.values())

    def affiBande(bande, pointeur = None):
        affi = "".join(bande[x] for x in sorted(bande.keys()))
        if pointeur is not None:
            affi += "\n" + "".join(" " if i != pointeur else "^" for i in range(-1, len(bande))) #-1 parce que le triangle du début prend deux caractères

        return affi

    def run(self, mot: str, verbose: bool = False):
        #on initialise la bande avec l'input
        bande = {i+1: lettre for i, lettre in enumerate(mot)}
        bande[0] = "|>"

        #exécution de la machine
        parcours = []

        currentState = self.etats[0]
        currentPoint = 1

        while True:
            if currentPoint not in bande: bande[currentPoint] = " "
            parcours.append(currentState.ident)

            if verbose:
                self.print(currentState.ident, currentPoint)
                self.print(MachineTuring.affiBande(bande, currentPoint))
                self.print("---")

            char = bande[currentPoint]
            if char in currentState:
                #on extrait la transition appliquée
                tr = currentState[char]
                currentState, direction, newChar = self.etats[tr.arrivee], tr.direction, tr.newChar

                #écriture de la nouvelle valeur sur le pointeur actuel
                bande[currentPoint] = newChar

                #déplacement du curseur
                if direction == "D": currentPoint += 1
                elif direction == "G": currentPoint -= 1
                else: pass #immobile
            else: break

        self.dernierParcours = parcours.copy()

        return currentState.acceptant
