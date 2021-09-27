class Noeud:
    def __init__(self, nom):
        self.nom = nom
        self.suivants = set()

    def ajouteSuiv(self, suiv):
        self.suivants.add(suiv)

    def retireSuiv(self, suiv):
        self.suivants.remove(suiv)

    def retireTout(self):
        self.suivants.clear()

    def __repr__(self): return str(self.nom)
    def __str__(self): return str(self.nom)

class Graphe:
    def __init__(self):
        self.noeuds = set()
        self.aretes = dict()

    def ajoutNoeud(self, noeud):
        if noeud not in self.noeuds:
            self.noeuds.add(noeud)

    def ajoutArete(self, a, b, poids = 1, bidirectionnel = False):
        def add(x, y):
            self.ajoutNoeud(x)
            self.ajoutNoeud(y)

            self.aretes[x, y] = poids #arête de x à y de poids "poids"
            x.ajouteSuiv(y)

        add(a, b)
        if bidirectionnel:
            add(b, a)

    def retraitArete(self, a, b):
        del self.aretes[a, b]
        a.retireSuiv(b)

    def retraitNoeud(self, noeud):
        noeud.retireTout()

        aretes = self.aretes
        for (a, b) in tuple(aretes.keys()):
            if noeud in (a, b):
                del aretes[(a, b)]
                if a == noeud: b.suivants.remove(a)
                else: a.suivants.remove(b)

        self.noeuds.remove(noeud)

    def cycle(self, depart):
        def aux(x, vus):
            if depart == x:
                return True
            elif x not in vus:
                vus[x] = any(aux(suiv, vus) for suiv in x.suivants)
                #s'il n'y a pas de suivant, any retourne False

            return vus[x]

        return any(aux(suiv, dict()) for suiv in depart.suivants)
