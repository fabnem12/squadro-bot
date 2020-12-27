from Graphe import Noeud, Graphe

#pour l'affichage du graphe des duels
import matplotlib.pyplot as plt
import networkx as nx

class Votant:
    def __init__(self, election, optionsVote):
        self.classements = dict()
        self.election = election

        self.inferieurs = {opt: set() for opt in optionsVote}
        self.superieurs = {opt: set() for opt in optionsVote}
        self.egaux = {opt: set() for opt in optionsVote}
        self.options = optionsVote.copy()
        self.duelsFaits = set()
        self.messagesDuels = dict()

    def ajouteMessageDuel(self, duel, message):
        self.messagesDuels[duel] = message

    def classement(self, candidat):
        return self.classements[candidat] if candidat in self.classements else None

    def prefere(self):
        classements = self.classements
        return min(classements.keys(), key = lambda x: classements[x])

    def prefere2(self, candidatA, candidatB):
        classements = self.classements

        if candidatA in classements and candidatB in classements:
            if classements[candidatA] < classements[candidatB]: #A est préféré
                return candidatA
            elif classements[candidatA] > classements[candidatB]: #B est préféré
                return candidatB

        return None #un candidat non classé ou de même degré de préférence

    def resumePref(self): #résumé de l'ordre de préférence du votant
        return "\n".join("**{}** {}".format(b, a) for a, b in sorted(self.classements.items(), key = lambda x: x[1]))

    def duelAFaire(self, start = False):
        #on renvoie un duel à faire s'il faut en faire un, None sinon
        from random import shuffle

        options = self.options
        if start:
            self.inferieurs, self.superieurs = {opt: set() for opt in options}, {opt: set() for opt in options}
            self.egaux = {opt: set() for opt in options}
            self.duelsFaits = set()

        shuffle(options) #pour randomiser le duel qui va être choisi, s'il y en a plusieurs

        for opt in options:
            infOpt, supOpt, egauxOpt = self.inferieurs[opt], self.superieurs[opt], self.egaux[opt]

            if len(infOpt) + len(supOpt) + len(egauxOpt) + 1 < len(options):
                #on ne connaît pas le classement relatif de cette option par rapport à tous les autres
                #on va donc faire un duel avec cette option et une autre
                adversaire = None
                for optPossible in options:
                    if optPossible == opt or optPossible in infOpt or optPossible in supOpt: #on a déjà le classement de l'opt par la personne
                        continue
                    else:
                        adversaire = optPossible
                        break

                #on a forcément un adversaire à ce stade
                #puisque les ensembles inf, sup et egaux sont disjoints et options c'est leur union + opt
                return (opt, adversaire)

        return None

    def ajoutPreference(self, opt1, opt2, prefere):
        inf, sup, egaux = self.inferieurs, self.superieurs, self.egaux

        if prefere is None: #l'électeur estime que opt1 = opt2 (en pratique le bot discord associé ne le permet pas encore)
            #étape 0 : l'un est l'égal de l'autre
            egaux[opt1].add(opt2)
            egaux[opt2].add(opt1)

            #étape 1 : tous ceux qui sont supérieurs à l'un sont supérieurs à l'autre
            sup[opt1] |= sup[opt2]
            sup[opt2] = sup[opt1]

            #étape 2 : tous ceux qui sont inférieurs à l'un sont inférieurs à l'autre
            inf[opt1] |= inf[opt2]
            inf[opt2] = inf[opt1]
        else:
            gagnant, perdant = prefere, opt2 if opt1 == prefere else opt1
            classeGagnant = {gagnant} | egaux[gagnant]
            classePerdant = {perdant} | egaux[perdant]

            #étape 0 : le gagnant et ses égaux sont supérieurs au perdant et à ses égaux
            for inferieur in classePerdant:
                sup[inferieur] |= classeGagnant
            for superieur in classeGagnant:
                inf[superieur] |= classePerdant

            #étape 1 : tous ceux qui sont supérieurs au gagnant sont supérieurs au perdant
            for superieur in sup[gagnant].copy():
                for inferieur in classePerdant:
                    sup[inferieur].add(superieur)
                    inf[superieur].add(inferieur)

            #étape 2 : tous ceux qui sont inférieurs au perdant sont inférieurs au gagnant
            for inferieur in inf[perdant].copy():
                for superieur in classeGagnant:
                    inf[superieur].add(inferieur)
                    sup[inferieur].add(superieur)

        self.duelsFaits.add((opt1, opt2))

    def duelFait(self, a, b):
        return (a, b) in self.duelsFaits or (b, a) in self.duelsFaits

    def calculClassement(self):
        sup, options = self.superieurs, self.options
        self.classements = {opt: len(sup[opt]) for opt in options}

        return list(sorted(self.classements.items(), key = lambda x: x[1]))

class Election:
    sysVotes = {"Borda", "sumaut", "approbation", "Copeland", "RankedPairs"}

    def __init__(self, sysVote = "Borda"):
        self.candidats = set()
        self.votants = dict()
        self.sysVote = sysVote
        self.commence = False
        self.msgInfo = []
        self.resultats = []

        self.roles = {}

    def nbCandidats(self):
        return len(self.candidats)

    def fini(self):
        return self.resultats != []

    def calculVote(self):
        self.votants = tuple(self.votants.values())
        #on anonymise le vote : désormais on ne peut plus identifier les bulletins de vote

        #on vérifie d'abord que tous les votes sont valides (en éliminant ceux qui ne le sont pas)
        nbOptions = len(self.candidats)
        self.votants = [x for x in self.votants if len(x.classements.values()) == nbOptions]

        if self.sysVote == "Borda":
            points = {candidat: 0 for candidat in self.candidats} #on initialise les compteurs de points

            for votant in self.votants: #on demande à chaque votant combien de points il donne à chaque candidat…
                pointsVotant = lambda x: 1 + max(votant.classements.values()) - votant.classement(x)
                nbPoints = lambda x: points[x] + pointsVotant(x)

                points.update({candidat: nbPoints(candidat) for candidat in self.candidats}) #… et on met à jour les compteurs de points


            self.resultats = list(sorted(points.items(), key = lambda x: x[1], reverse = True)) #on trie la liste des candidats

        elif self.sysVote == "sumaut":
            points = {candidat: 0 for candidat in self.candidats} #on initialise les compteurs de points
            for votant in self.votants: #on demande à chaque votant son candidat préféré
                points[votant.prefere()] += 1

            self.resultats = list(sorted(points.items(), key = lambda x: x[1], reverse = True)) #on trie la liste des candidats

        elif self.sysVote == "approbation":
            points = {candidat: 0 for candidat in self.candidats}
            for votant in self.votants:
                for candidat in votant.classement: #tous les candidats classés par le votant sont considérés comme approuvés
                    points[candidat] += 1

            self.resultats = list(sorted(points.items(), key = lambda x: x[1], reverse = True))

        elif self.sysVote == "Copeland":
            votants, candidats = self.votants, self.candidats

            def infosDuel(a, b):
                points = {a:0, b:0, None:0}
                for votant in votants: points[votant.prefere2(a, b)] += 1

                if points[a] == points[b]:
                    gagnant = None
                else:
                    gagnant = a if points[a] > points[b] else b

                return gagnant, points[a], points[b], points[None]

            duels = {(x, y): infosDuel(x, y) for x in candidats for y in candidats if x != y}

            victoires = {candidat: [] for candidat in candidats}
            for duel, (gagnant, ptsA, ptsB, ptsNone) in duels.items():
                if gagnant is not None and gagnant == duel[0]:
                    perdant = duel[0] if gagnant == duel[1] else duel[1]

                    victoires[gagnant].append((perdant, ptsA, ptsB, ptsNone))
                elif gagnant is None:
                    victoires[duel[0]].append((duel[1], ptsA, ptsB, ptsNone))
                    victoires[duel[1]].append((duel[0], ptsA, ptsB, ptsNone))

            self.resultats = list(sorted(victoires.items(), key = lambda x: len(x[1]), reverse = True))

        elif self.sysVote == "RankedPairs":
            votants, candidats = self.votants, list(self.candidats)

            def infosDuel(a, b):
                points = {a:0, b:0, None:0}
                for votant in votants: points[votant.prefere2(a, b)] += 1

                return a, b, points[a], points[b], points[None]

            duels = [infosDuel(x, y) for i, x in enumerate(candidats) for y in candidats[i+1:]]
            #on organise tous les duels de candidats
            duels.sort(key = lambda x: abs(x[3]-x[2]), reverse = True)
            #on trie par ordre décroissant d'écart de voix dans le duel

            g = Graphe()
            noeuds = {k: Noeud(k) for k in candidats}

            victoires = {k: [] for k in candidats}

            for (a, b, ptsA, ptsB, ptsNone) in duels: #on tente d'ajouter les duels dans le graphe des duels, en retirant ceux qui créent un cycle
                neA, neB = noeuds[a], noeuds[b]

                #on tente de mettre une arête du perdant vers le gagnant. à la fin le gagnant de condorcet a alors un degré sortant nul
                if ptsA > ptsB:
                    gagnant, perdant, ptsWin, ptsLose = a, b, ptsA, ptsB
                    neWin, neLose = neA, neB
                elif ptsA < ptsB:
                    gagnant, perdant, ptsWin, ptsLose = b, a, ptsB, ptsA
                    neWin, neLose = neB, neA
                else: #en cas d'égalité on considère que le duel a été gagné par a et par b (parce qu'un duel n'est affiché que s'il est gagné...)
                    victoires[a].append((b, ptsA, ptsB, ptsNone))
                    victoires[b].append((a, ptsB, ptsA, ptsNone))
                    continue

                g.ajoutArete(neLose, neWin)

                if g.cycle(neWin): #on retire l'arête si elle a créé un cycle
                    g.retraitArete(neLose, neWin)

                victoires[gagnant].append((perdant, ptsWin, ptsLose, ptsNone)) #on enregistre la victoire

            #on fait maintenant un classement en trouvant un sommet de degré sortant nul (aka le gagnant), en le retirant du graphe, et ainsi de suite
            classement = []
            for _ in candidats: #on récupère les candidats les uns après les autres, donc on fait autant de tours de boucle que de candidats
                for noeud in g.noeuds:
                    if noeud.suivants == set(): #on a trouvé notre gagnant, on le retire du graphe des duels
                        classement.append((noeud.nom, victoires[noeud.nom]))
                        g.retraitNoeud(noeud)

                        break

            self.resultats = classement

        else:
            raise ValueError("Système de vote non géré pour le moment")

        return self.resultats

    def getResultats(self):
        if self.resultats == []:
            return self.calculVote()
        else:
            return self.resultats

    def getVotant(self, userId):
        userHash = hash(userId) #on fait un hashage de l'id d'utilisateur

        if userHash not in self.votants:
            self.votants[userHash] = Votant(self, list(self.candidats))

        return self.votants[userHash]

    def affi(self):
        if self.sysVote in ("Copeland", "RankedPairs"):
            return affiCondorcet(self)
        else:
            return affiPoints(self)

    def nbVotesValides(self):
        if self.sysVote in ("approbation", "sumaut"):
            return len(self.votants)
        else:
            nbCandidats = len(self.candidats)
            return len(tuple(x for x in self.votants.values() if len(x.classements) == nbCandidats))

def graphe(election):
    g = nx.DiGraph()

    for gagnant, duels in election.resultats:
        for (perdant, ptsA, ptsB, ptsNone) in duels:
            if ptsA != ptsB:
                g.add_edge(gagnant, perdant, weight = ptsA-ptsB) #on a par construction ptsA > ptsB
            #on ne met pas d'arête en cas d'ex-aequo

    nx.draw(g, nx.circular_layout(g), with_labels = True)
    plt.savefig("graphe.png")
    plt.clf()

    return "graphe.png"

def resume(election):
    if election.fini():
        classements = dict()

        for votant in election.votants:
            clsVotant = tuple(sorted(votant.classements.items(), key=lambda x: (x[1], x[0])))
            if clsVotant not in classements:
                classements[clsVotant] = 1
            else:
                classements[clsVotant] += 1

        with open("resume.txt", "w") as f:
            for classement, nbVotants in classements.items():
                f.write("{}:{}\n".format(nbVotants, ">".join(x[0] for x in classement)))

        return "resume.txt"

def affiCondorcet(election):
    msgs = []

    nbExaequo = 0
    duelsPrec = -1000
    for index, (candidat, duels) in enumerate(election.resultats):
        if len(duels) == duelsPrec: nbExaequo += 1
        else: nbExaequo = 0
        numero = index+1-nbExaequo

        msgs.append("**{}{}** {} avec {} duels gagnés :".format(numero, "e" if numero-1 else "er", candidat, len(duels)))
        for (perdant, ptsA, ptsB, ptsNone) in duels:
            msgDuel = "- contre {} ({} votes contre {})".format(perdant, ptsA, ptsB)
            if ptsNone:
                msgDuel += " + {} abstentions".format(ptsNone)

            msgs.append(msgDuel)

        duelsPrec = len(duels)

    return msgs, [resume(election), graphe(election)]

def affiPoints(election):
    msgs = []

    nbExaequo = 0
    pointsPrec = -1000
    for index, (candidat, points) in enumerate(election.resultats):
        if points == pointsPrec: nbExaequo += 1
        else: nbExaequo = 0
        numero = index+1-nbExaequo

        msgs.append("**{}{}** {} avec {} votes".format(numero, "e" if numero-1 else "er", candidat, points))

        pointsPrec = points

    return msgs, [resume(election)]
