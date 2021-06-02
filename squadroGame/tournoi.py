from typing import List, Set, Tuple, Optional, Dict
from partieBot import PartieBot

Participant = Optional[int]
Heure = int
ChannelId = int
MessageId = int
Duel = Tuple[Participant, Participant]

class Elo:
    def __init__(self):
        self.scores: Dict[Participant, float] = dict()

    def addPartie(self, j1: Participant, j2: Participant, gagnant: Participant) -> None:
        scores = self.scores
        if j1 not in scores: scores[j1] = 1500
        if j2 not in scores: scores[j2] = 1500
        perdant = j2 if j1 == gagnant else j1

        probaGain = 1 / (1 + 10**(-(scores[gagnant]-scores[perdant]) / 400))

        scores[gagnant] += 40 * (1-probaGain)
        scores[perdant] -= 40 * (1-probaGain)

    def score(self, joueur: Participant) -> float:
        if joueur not in self.scores:
            self.scores[joueur] = 1500

        return self.scores[joueur]

    def leaderBoard(self) -> List[Tuple[Participant, float]]:
        return sorted(self.scores.items(), key=lambda x: x[1])

    def setScore(self, joueur: Participant, newScore: float) -> None:
        self.scores[joueur] = newScore

class Tournoi:
    creneauxPossibles: List[Heure] = [13, 14, 15, 16, 17, 18, 19, 20]

    def __init__(self, participants: List[Participant], salon: ChannelId, salon2: ChannelId, salonObservateur: ChannelId, ident: int, elo: Elo):
        self.participants = participants
        self.salon = salon
        self.salon2 = salon2
        self.salonObservateur = salonObservateur
        self.elo = elo
        self.id = ident

        self.nbVictoires: Dict[Participant, int] = {x: 0 for x in participants + [None]}
        self.vus: Dict[Participant, Set[Participant]] = {x: set() for x in participants + [None]}
        self.couleurs: Dict[Participant, List[int]] = {x: [] for x in participants + [None]}
        self.dispos: Dict[Participant, Set[int]] = {x: set() for x in participants}
        self.duelsAFaire: List[Duel] = []
        self.planning: Dict[Duel, Heure] = dict()
        self.msgPlanning: Optional[MessageId] = None
        self.partiesEnCours: Dict[PartieBot, Duel] = dict()

    def faitTour(self) -> List[Duel]:
        participants = self.participants.copy()
        nbVictoires = self.nbVictoires
        vus = self.vus
        couleurs = self.couleurs

        if len(participants) % 2 != 0: #on a un nombre impair de participants, on rajoute l'ia pour revenir à un nombre pair
            participants.append(None)

        if sum(self.nbVictoires.values()) == 0: #aucun match n'a été fait, on reprend l'ordre initial
            nbParticipants = len(participants)
            moitie = nbParticipants // 2

            self.duelsAFaire = [(p, participants[moitie + i]) for i, p in enumerate(participants[:moitie])]
            return self.duelsAFaire
        else:
            def poidsDuel(a: Participant, b: Participant) -> int:
                couleurA, couleurB = 0, 1

                if len(couleurs[a]) > 0:
                    return abs(nbVictoires[a] - nbVictoires[b]) + 5*(couleurs[a][-1] == couleurA) + 5*(couleurs[b][-1] == couleurB) + abs(self.elo(a) - self.elo(b)) / 1500
                else: #on est au premier tour, tous les duels sont possibles
                    return 0

            def couleurOk(participant: Participant, couleur: int) -> bool:
                #pour interdire à 1 participant de faire 3 matches d'affilée avec la même couleur
                pos: int = couleurs[participant]
                return len(pos) < 2 or pos[-2] != pos[-1] or pos[-1] != couleur

            def aux(participants: List[Participant]):
                if len(participants) == 2:
                    a, b = participants

                    if b in vus[a] or (not couleurOk(a, 0)) or (not couleurOk(b, 1)):
                        return [], 0
                    else:
                        return [(a, b)], poidsDuel(a, b)
                else:
                    a = participants[0]
                    minPoids = float("inf")
                    duelsOk = []
                    newDuel: Optional[Duel] = None
                    longueurAttendue = len(participants)//2 - 1

                    for i in range(1, len(participants)):
                        b = participants[i]

                        if b not in vus[a] and (len(participants) <= 10 or randint(0, 100) / 100 < 1/len(participants)):
                            participantsSuivants = [x for x in participants if x not in (a, b)]

                            for duelCourant in ((a, b), (b, a)):
                                poidsDuelCourant = poidsDuel(*duelCourant)
                                duels, poids = aux(participantsSuivants)

                                if len(duels) == longueurAttendue and poids + poidsDuelCourant < minPoids:
                                    minPoids = poids + poidsDuelCourant
                                    duelsOk = duels
                                    newDuel = duelCourant

                                if minPoids == 0:
                                    duelsOk.append(duelCourant)
                                    return duelsOk, minPoids

                    if duelsOk != []: #on n'ajoute le duel que si le sous-ensemble de duels calculé récursivement est valide
                        duelsOk.append(newDuel)

                    return duelsOk, minPoids

            for _ in range(10):
                duels, _ = aux(participants)
                if duels != []:
                    self.duelsAFaire = duels
                    return duels

            return []

    def addMsgPlanning(self, msgId: MessageId) -> None:
        self.msgPlanning = msgId
        self.dispos = {x: set() for x in self.participants}

    def addDispo(self, userId: Participant, creneau: Heure) -> None:
        if userId in self.dispos:
            if creneau not in self.dispos[userId]:
                self.dispos[userId].add(creneau)
            else:
                self.dispos[userId].remove(creneau)

    def calculPlanning(self) -> bool:
        if self.duelsAFaire != []:
            tentativePlanning: Dict[Heure, Duel] = dict()
            dispos = self.dispos
            dispos[None] = set(self.creneauxPossibles)

            possibilites: Dict[Duel, Set[Heure]] = {(a, b): dispos[a] & dispos[b] for a, b in self.duelsAFaire}
            if any(x == set() for x in possibilites.values()):
                return False
            else:
                #on cherche une configuration d'heures qui fait le moins de collisions possibles
                #et qui soit possible compte-tenu des disponibilités
                possibilitesBis: List[Tuple[Duel, Set[Heure]]] = list(possibilites.items())

                def poidsConfig(heures: Dict[Heure, int]) -> int:
                    return max(heures.values(), default = 0)

                def aux(index: int) -> Tuple[Dict[Duel, Heure], Dict[Heure, int]]: #le premier dico donne à chaque duel son heure, le 2e donne le nb d'occurrences
                    if index < 0:
                        return dict(), dict()
                    else:
                        assignation, heures = aux(index-1)
                        poidsPrec = poidsConfig(heures)
                        duel, heuresDuel = possibilitesBis[index]

                        poidsMin = float("inf")
                        heureMin: Optional[Heure] = None
                        for heure in heuresDuel:
                            if heure not in heures:
                                heures[heure] = 1
                                assignation[duel] = heure

                                return assignation, heures
                            elif heures[heure] < poidsPrec: #et on a forcément poidsPrec <= poidsMin…
                                poidsMin = heures[heure] + 1
                                heureMin = heure
                            else: #on a par construction heures[heure] == poidsPrec
                                if poidsPrec + 1 < poidsMin:
                                    poidsMin = poidsPrec + 1
                                    heureMin = heure

                        if heureMin is None:
                            return dict(), dict()
                        else:
                            assignation[duel] = heureMin
                            heures[heureMin] += 1

                            return assignation, heures

                config, _ = aux(len(possibilitesBis)-1)
                if len(config) == len(self.duelsAFaire):
                    self.planning = config
                    self.dispos = {x: set() for x in self.participants}
                    return True
                else:
                    return False

    def matchsHeure(self, heure: Heure) -> List[Duel]:
        return [duel for duel, heureDuel in self.planning.items() if heureDuel == heure]

    def heureMatch(self, duel: Duel) -> Optional[Heure]:
        return self.planning.get(duel)

    def addPartie(self, partie: PartieBot, duel: Duel) -> None:
        self.partiesEnCours[partie] = duel

    def enregistreFinPartie(self, partie: PartieBot) -> bool:
        #renvoie un booléen indiquant si l'enregistrement a marché
        if partie in self.partiesEnCours:
            estGagne, idGagnant = partie.gagnant()

            if estGagne:
                a, b = self.partiesEnCours[partie]
                #self.elo.addPartie(a, b, idGagnant) #en fait c'est déjà fait par le bot...

                self.vus[a].add(b)
                self.vus[b].add(a)
                self.nbVictoires[idGagnant] += 1

                self.duelsAFaire.remove((a, b))

                del self.partiesEnCours[partie]
                del self.planning[(a, b)]
                return True

        return False
