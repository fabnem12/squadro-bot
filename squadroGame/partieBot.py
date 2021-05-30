from typing import Optional, List, Set, Dict, Tuple
from Partie import Partie

JoueurId = int
ChannelId = int
MessageId = int
situationsConnues: Dict[int, List[int]] = dict()

class PartieBot:
    def __init__(self, ia: Optional[int] = None, refresh: bool = True, salon: Optional[ChannelId] = None, moutons: bool = False):
        self.ia = ia
        self.dernierCoupIa: Optional[int] = None
        self.joueurs: List[Optional[JoueurId]] = []
        self.partie: Partie = Partie(situationsConnues, "10000000000", True, False, False, False, True)
        self.refresh = refresh
        self.salon = salon #None si la partie est en DM
        self.moutons = moutons
        self.situations: List[str] = ["10000000000"] #stocke les situations sucessives du plateau

        self.msgRefresh: Dict[ChannelId, Tuple[MessageId, MessageId]] = dict()

    def addJoueur(self, idJoueur: JoueurId) -> bool:
        #renvoie un bool disant si la partie peut commencer
        self.joueurs.append(idJoueur)

        if len(self.joueurs) == 1 and self.ia in (0, 1):
            self.joueurs.insert(self.ia, None)
            return True
        else:
            return len(self.joueurs) == 2

    def aQuiLeTour(self) -> Optional[JoueurId]: #None si c'est à l'ia de jouer
        if self.ia and self.partie.idJoueur == self.ia:
            return None
        else:
            return self.joueurs[self.partie.idJoueur]

    def addRefresh(self, channelId: ChannelId, msgPlateau: MessageId, msgInfo: MessageId) -> None:
        self.msgRefresh[channelId] = (msgPlateau, msgInfo)

    def coupValide(self, coup: int) -> bool:
        return self.partie.verifCoup(coup)

    def coupIA(self) -> int:
        return self.partie.coupIA()

    def faitCoup(self, coup: int) -> None:
        if self.partie.idJoueur == 0 and self.ia != 0:
            coup = 6 - coup

        if self.ia == self.partie.idJoueur:
            self.dernierCoupIa = coup if self.ia else 6 - coup

        self.partie.interaction(coup) #suppose que le coup est valide
        self.situations.append(self.partie.mini())

    def affi(self) -> str: #renvoie le lien vers le fichier de l'image
        return self.partie.affichePlateau(self.moutons)

    def back(self) -> bool: #renvoie un booléen indiquant si le retour a été fait ou pas
        if len(self.situations) >= 2:
            self.situations.pop() #on retire la dernière position
            self.partie = Partie(situationsConnues, self.situations[-1], True, False, False, False, True)

            return True
        else:
            return False

    def finie(self) -> bool:
        return self.partie.finPartie()

    def info(self) -> str:
        if self.finie():
            joueur = self.joueurs[self.partie.gagnant]
            return f"Le joueur {self.partie.gagnant+1} ({f'<@{joueur}>' if joueur else 'IA'}) a cordialement écrasé son adversaire !!!"
        else:
            joueur = self.joueurs[self.partie.idJoueur]
            return f"C'est au joueur {self.partie.idJoueur+1} de jouer ({f'<@{joueur}>' if joueur else 'IA'})" + (f"\nDernier coup de l'IA : {self.dernierCoupIa}" if self.dernierCoupIa and joueur else "")

    def joueursHumains(self) -> List[JoueurId]:
        return [x for x in self.joueurs if x]

    def gagnant(self) -> Tuple[bool, Optional[JoueurId]]:
        if self.partie.gagnant:
            return (True, self.joueurs[self.partie.gagnant])
        else:
            return (False, None)
