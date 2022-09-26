from Graphe import Noeud, Graphe

#pour l'affichage du graphe des duels
#import matplotlib.pyplot as plt
#import networkx as nx
from random import shuffle #juste pour ne pas avoir un fichier de détails de vote avec l'ordre qui correspond aux votes
from typing import List, Dict, Optional, Tuple

class Votant:
    def __init__(self, election, optionsVote: List[str], ident: int):
        self.election = election
        self.id = ident
        self.listeCandidats = optionsVote.copy()
        shuffle(self.listeCandidats)

    #méthodes à définir
    # def prefere(self):
    # def resumePref(self):
    # def optionAFaire(self):

class VotantRank(Votant):
    def __init__(self, election, optionsVote: List[str], ident: int):
        super().__init__(election, optionsVote, ident)
        self.classements: Dict[str, int] = dict()
        self.duels: Dict[Tuple[str, str], Optional[str]] = {(x, x): None for x in optionsVote}
        #gagnants des duels

    def classement(self, candidat):
        return self.classements[candidat] if candidat in self.classements else None

    def prefere(self, candidats = None):
        if candidats is None:
            classements = self.classements
        else:
            classements = {key: val for key, val in self.classements.items() if key in candidats}
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

    def optionAFaire(self):
        tab = self.listeCandidats.copy()

        def separe(low, high):
            pivot, up, down, UpGoing = tab[low], low, high, False

            for i in range(high - low):
                if UpGoing:
                    if (tab[up], pivot) not in self.duels: return (tab[up], pivot)

                    if self.duels[tab[up],pivot] in (tab[up], None): up += 1
                    else:
                        tab[down] = tab[up]
                        down -= 1
                        UpGoing = False
                else:
                    if (pivot, tab[down]) not in self.duels: return (pivot, tab[down])

                    if self.duels[pivot, tab[down]] in (pivot, None): down -= 1
                    else:
                        tab[up] = tab[down]
                        up += 1
                        UpGoing = True

            tab[up] = pivot
            return up

        def TR(d, f):
            if d < f:
                pp = separe(d, f)

                if isinstance(pp, int):
                    a = TR(pp+1, f)
                    if a: return a
                    b = TR(d, pp-1)
                    if b: return b
                else:
                    return pp #c'est un duel, on le renvoie au niveau précédent

        ret = TR(0, len(self.listeCandidats)-1)
        #si ret est non nul, il faut faire un nouveau duel. sinon, ben on enregistre le classement
        if not ret: self.listeCandidats = tab
        return ret

    def ajoutPreference(self, opt1, opt2, prefere):
        self.duels[opt1, opt2] = prefere
        self.duels[opt2, opt1] = prefere

    def calculClassement(self):
        self.classements = {x: i for i, x in enumerate(self.listeCandidats)}
        return list(enumerate(self.listeCandidats))

class Election:
    sysVotes = {"Borda", "sumaut", "approbation", "Copeland", "RankedPairs", "RCV"}

    def __init__(self, sysVote = "Borda"):
        self.candidats = set()
        self.nom2candidat = dict()
        self.candidat2nom = dict()
        self.votants = dict()
        self.sysVote = sysVote
        self.commence = False
        self.msgInfo = []
        self.resultats = []

    def nbCandidats(self):
        return len(self.candidats)

    def fini(self):
        return self.resultats != []

    def calculVote(self):
        if isinstance(self.votants, list):
            self.votants = tuple(self.votants)
        if not isinstance(self.votants, tuple):
            self.votants = tuple(self.votants.values())
        #on anonymise le vote : désormais on ne peut plus identifier les bulletins de vote

        #on vérifie d'abord que tous les votes sont valides (en éliminant ceux qui ne le sont pas)
        nbOptions = len(self.candidats)
        if self.votants != tuple() and isinstance(self.votants[0], VotantRank):
            self.votants = [x for x in self.votants if len(x.classements.values()) == nbOptions]

        if self.sysVote == "RankedPairs":
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
                if a.submissionTime < b.submissionTime:
                    ptsA += .1
                else:
                    ptsB += .1

                #on tente de mettre une arête du perdant vers le gagnant. à la fin le gagnant de condorcet a alors un degré sortant nul
                if ptsA > ptsB:
                    gagnant, perdant, ptsWin, ptsLose = a, b, ptsA, ptsB
                    neWin, neLose = neA, neB
                elif ptsA < ptsB:
                    gagnant, perdant, ptsWin, ptsLose = b, a, ptsB, ptsA
                    neWin, neLose = neB, neA
                #else: #en cas d'égalité on considère que le duel a été gagné par a et par b (parce qu'un duel n'est affiché que s'il est gagné...)
                #    victoires[a].append((b, ptsA, ptsB, ptsNone))
                #    victoires[b].append((a, ptsB, ptsA, ptsNone))
                #    continue
                else:
                    continue #ne peut pas arriver, le tie-breaker est défini ligne 156

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
        elif self.sysVote == "RCV":
            votants, candidats = self.votants, tuple(self.candidats)
            threshold = len(votants) // 2 + 1

            listePreferes = []
            preferes = {candidat: set() for candidat in candidats}
            dernier = None

            while True:
                if dernier:
                    votants = preferes[dernier]

                preferes = {candidat: votes.copy() for candidat, votes in preferes.items() if candidat != dernier}
                if len(votants) != 0: listePreferes.append(preferes)

                for votant in votants:
                    preferes[votant.prefere(candidats)].add(votant)

                premier = max(preferes.keys(), key=lambda x: len(preferes[x]))
                if len(preferes[premier]) >= threshold:
                    self.resultats = (premier, listePreferes)
                    return self.resultats

                else: #en cas d'égalité, le dernier est retiré selon un certain critère, donc pas de pb
                    dernier = min(preferes.keys(), key=lambda x: (len(preferes[x]), -int(self.candidat2nom[x].split(" ")[1])))
                    candidats = tuple(x for x in candidats if x != dernier)

        else:
            raise ValueError("Système de vote non géré pour le moment")

        return self.resultats

    def getResultats(self):
        if self.resultats == []:
            self.calculVote()
        return self.resultats

    def getVotant(self, userId, reset = False):
        userHash = userId#hash(userId) #on fait un hashage de l'id d'utilisateur

        if reset or userHash not in self.votants:
            self.votants[userHash] = VotantRank(self, list(self.candidats), userHash)

        return self.votants[userHash]

    def isVotant(self, userId: int) -> bool:
        return userId in self.votants

    def affi(self):
        return affiCondorcet(self)

    def nbVotesValides(self):
        nbCandidats = len(self.candidats)
        return len(tuple(x for x in self.votants.values()))

def resume(election):
    if election.fini():
        classements = dict()

        for votant in election.votants:
            if isinstance(votant, VotantRank):
                clsVotant = tuple(sorted(votant.classements.items(), key=lambda x: (x[1], x[0])))
                if clsVotant not in classements:
                    classements[clsVotant] = 1
                else:
                    classements[clsVotant] += 1

        with open("resume.txt", "w") as f:
            infosVotes = list(classements.items())
            shuffle(infosVotes)

            for classement, nbVotants in infosVotes:
                f.write(f"{nbVotants}:{' > '.join(election.candidat2nom[x[0]] for x in classement) if isinstance(classement, tuple) else classement}\n")

        return "resume.txt"

def detailsVotes(election):
    if election.fini():
        classements = dict()

        for votant in election.votants:
            if isinstance(votant, VotantRank):
                clsVotant = tuple(map(lambda x: election.candidat2nom[x], sorted(votant.classements.keys(), key=lambda x: votant.classements[x])))
                if clsVotant not in classements:
                    classements[clsVotant] = {votant.id}
                else:
                    classements[clsVotant].add(votant.id)

        return classements

def affiCondorcet(election):
    msgs = []

    nbExaequo = 0
    duelsPrec = -1000
    for index, (candidat, duels) in enumerate(election.resultats):
        numero = index+1

        msgs.append(f"#**{numero}** {election.candidat2nom[candidat]} won {len(duels)} duels:\n")
        for (perdant, ptsA, ptsB, ptsNone) in duels:
            msgDuel = f"- against {election.candidat2nom[perdant]} ({ptsA} - {ptsB} votes)"
            msgs[-1] += msgDuel + "\n"

        duelsPrec = len(duels)

    return msgs, detailsVotes(election), [resume(election)]
