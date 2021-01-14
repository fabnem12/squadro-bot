from random import shuffle

#on regarde les dernières couleurs du joueur. il ne peut faire 3 parties d'affilée avec la même couleur
def derniereCouleursJoueur(rencontres, joueur):
    couleursDuJoueur = []

    for joueur1, joueur2 in rencontres:
        if joueur1 == joueur:
            couleursDuJoueur.append(1) #le joueur a joué la rencontre avec les jaunes
        elif joueur2 == joueur:
            couleursDuJoueur.append(2) #avec les rouges

    return couleursDuJoueur #on ne renvoie que les 2 dernières couleurs du joueur

def penaliteDuDuel(duel, ordreInit, nbPoints, rencontres):
    """
    Calcule la pénalité associée au duel (non changement de couleur d'un des joueurs, différence de nb de points...)
    """
    couleur = lambda joueur: 1 if duel[0] == joueur else 2
    couleursPassees = lambda joueur: derniereCouleursJoueur(rencontres, joueur)

    joueur1, joueur2 = duel
    penalite = 0

    penalite += 2000 * abs(nbPoints[joueur1] - nbPoints[joueur2])**2 #on favorise les rencontres de personnes de même nb de points

    for joueur in duel: #on s'assure aussi qu'un joueur ne joue pas 3 fois d'affilée avec la même couleur
        compteCouleurIdentique = 1
        for index, couleurPassee in enumerate(reversed(couleursPassees(joueur))): #on regarde les dernières couleurs
            if couleurPassee == couleur(joueur):
                compteCouleurIdentique += 1

            if index == 1 and compteCouleurIdentique >= 3:
                #on n'a vu que les 2 dernières couleurs et ce sont les mêmes que celle en cours. on dit stop !
                return float("inf")

        if len(couleursPassees(joueur)) > 0:
            if couleursPassees(joueur)[-1] == couleur(joueur):
                penalite += 100 #on met une pénalité de 30 si le joueur joue 2 fois la même couleur d'affilée
            penalite += 50 * (compteCouleurIdentique-1) #on rajoute 15 points de pénalité par compteCouleurIdentique (-1) pour ne pas en mettre dans le cas général, ou compteCouleurIdentique vaut 1

    #tie-breaker 1: on favorise les duels entre personnes ayant des indexs proches dans ordreInit
    penalite += (abs(ordreInit.index(joueur1) - ordreInit.index(joueur2)) - 1)**5 #-1 car l'écart minimum possible est 1

    #tie-breaker 2: en cas d'ex-aequo à ce stade, on préfère un joueur 1 avec un id plus faible
    penalite += joueur1.id / (joueur1.id + joueur2.id)

    return penalite

def penaliteTour(duels, ordreInit, nbPoints, rencontres):
    """
    Pénalité du tour (qui est un ensemble de matchs) -> comparer les tours pour garder "l'optimum"
    """
    penalite = sum([abs(penaliteDuDuel(duel, ordreInit, nbPoints, rencontres)) for duel in duels])
    #tie-breaker
    #en cas d'ex-aequo, on départage en faisant la somme des ids des joueurs1 et en divisant par la somme de tous les ids
    penalite += sum([duel[0].id for duel in duels])/sum([joueur.id for duel in duels for joueur in duel])

    return penalite

def permutations(listeDuels):
    """
    Les arrangemements faits dans genereToursPossibles sont en ordre "croissant",
    si les joueurs sont (a,b,c,d), il ne fera que ~ ((a,b), (c, d)) et ((a, c), (b, d))
    alors qu'il faut aussi ((b, a), (c, d)), ((b, a), (d, c)), ((a, b), (d, c)), etc.
    -> permutations génère les nouveaux "permutés"
    """
    permutes = [0 for _ in listeDuels]

    for i in range(2**len(permutes)):
        permutation = [duel[::-1] if permutes[index] else duel for index, duel in enumerate(listeDuels)]

        index = len(permutes) -1
        permutes[index] += 1
        while permutes[index] > 1:
            permutes[index] = 0
            permutes[index-1] += 1

            index -= 1

        yield permutation

def genereToursPossibles(ordreInit, nbPoints, rencontresPassees):
    """
    Génère les "tours" possibles (càd s'il y a 'n' participants (avec 'n' pair), tous les n/2 matchs possibles entre eux lors d'un tour, où chaque participant participe 1 seule fois)
    Ensuite une fonction de "pénalité" permet de les classer et de garde "l'optimum"
    Renvoie un tour si possible, None sinon.
    Ce dernier cas arrive car la fonction s'interdit de demander à deux joueurs s'étant recontrés de se rencontrer de nouveau.
    """
    toursPossibles = []

    #on fait tous les arrangements par paire cohérents possibles
    for decalage in range(1, len(ordreInit)):
        duelsPossibles = []

        for index in range(len(ordreInit)):
            joueur1 = ordreInit[index]
            joueur2 = [ordreInit[idx-decalage] for idx in range(len(ordreInit))][index]

            if (joueur1, joueur2) not in rencontresPassees and (joueur2, joueur1) not in rencontresPassees:
                #il ne faut pas que deux joueurs se rencontrent 2 fois
                duelsPossibles.append((joueur1, joueur2))

        duelsConfirmes = []
        joueursCases = set()

        for duel in duelsPossibles:
            #l'intersection entre les joueurs du duel et les joueurs déjà casés est-il l'ensemble vide ?
            if len(set(duel) & joueursCases) == 0:
                #si oui, on peut rajouter le duel sans soucis !
                duelsConfirmes.append(duel)
                joueursCases.update(duel)

        if len(duelsConfirmes) != len(ordreInit) / 2: continue

        #on a fini le tour possible, on l'enregistre
        for permutation in permutations(duelsConfirmes):
            toursPossibles.append((permutation, penaliteTour(permutation, ordreInit, nbPoints, rencontresPassees)))

    #on fait le classement des tours du meilleur au moins bon du point de vue de la pénalité
    #sachant que plus la pénalité est faible, meilleur est le tour
    toursPossibles.sort(key=lambda x: x[1])

    #on affiche les duels du meilleur tour possible
    if len(toursPossibles) > 0: return toursPossibles[0][0], [x[1] for x in toursPossibles]
    else: return None, []



#LE NOUVEL ALGORITHME BEAUCOUP MIEUX QUI FAIT CE QU'ON LUI DEMANDE#
#SE TROUVE JUSTE EN DESSOUS #######################################
#|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||#
#|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||#
#|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||#
#|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||#
#VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV#

def preferenceEntreJoueurs(ordreInit, nbPoints, joueur1, joueur2):
    #ils préfèrent les joueurs ayant un nb de points proche
    #en cas d'ex-aequo, ceux qui ont l'index dans ordreInit le plus proche
    #en cas d'ex-aequo, ceux qui ont un id discord plus proche
    return (abs(nbPoints[joueur1] - nbPoints[joueur2]), abs(ordreInit.index(joueur1) - ordreInit.index(joueur2)), abs(joueur1.id % 100 - joueur2.id % 100), abs(joueur1.id - joueur2.id))
    #on fait d'abord % 100 pour qu'il y ait plus de hasard, vu qu'a priori les 2 derniers chiffres sont plus aléatoires que la distribution des ids
    #c'est aussi un moyen de s'assurer que les écarts entre "ids" sont comparables.
    #on ne les prend directement qu'en cas d'ex-aequo

    """avec cette fonction, lower is better
    """

def mariagesStables(ordreInit, nbPoints, rencontres):
    """
    On génère le tour suivant de match avec l'algorithme des mariages stables,
    (Gale-Shapley https://fr.wikipedia.org/wiki/Algorithme_de_Gale_et_Shapley)
    en considérant que les joueurs 1 sont les "hommes" et les joueurs 2 sont les "femmes".
    Ça permet de s'assurer que tout le monde change de "couleur" d'un tour à l'autre
    """
    #on regarde qui a été joueur 1 au dernier tour
    dernierTour = rencontres[-len(ordreInit) // 2:]
    joueurs1 = [x[0] for x in dernierTour]
    joueurs2 = [x for x in ordreInit if x not in joueurs1]

    #on initialise le dico où enregistrer les "préférences" des joueurs 1
    preferencesJoueurs1 = dict()

    #les joueurs 1 ne veulent pas des joueurs avec qui ils ont déjà joué
    for joueur in joueurs1:
        preferencesJoueurs1[joueur] = []
        joueursNonRencontres = [y for y in joueurs2 if (joueur, y) not in rencontres and (y, joueur) not in rencontres]
        preferencesJoueurs1[joueur] = joueursNonRencontres

        #on a les joueurs "possibles" (qui n'ont pas encore été rencontrés par ce joueur 1)
        #reste à les trier
        preferencesJoueurs1[joueur].sort(key=lambda x: preferenceEntreJoueurs(ordreInit, nbPoints, joueur, x))

    #on peut lancer l'algorithme des mariages stables à proprement parler
    propositionsMariage = dict() #pour stocker les propositions de "mariage" faites aux joueurs 2
    for joueur in joueurs2: propositionsMariage[joueur] = None

    joueurs1cases = dict() #pour se rappeler de quels joueurs 1 sont "casés" avec un joueur 2
    for joueur in joueurs1: joueurs1cases[joueur] = False

    #c'est parti !
    joueurs1enAttente = [x for x in joueurs1 if not joueurs1cases[x] and preferencesJoueurs1[x] != []]
    while joueurs1enAttente != []:
        joueur = joueurs1enAttente[0]
        joueur2prefere = preferencesJoueurs1[joueur][0]

        if propositionsMariage[joueur2prefere] is None: #le joueur 2 est "célibataire"
            propositionsMariage[joueur2prefere] = joueur #on enregistre les "fiançailles"
            joueurs1cases[joueur] = True
            del preferencesJoueurs1[joueur][0] #le joueur 1 n'aura plus le droit de se présenter face au joueur 2 en cours
        else:
            del preferencesJoueurs1[joueur][0] #on retire la 1ère préférence du joueur 1, elle est perdue "à jamais"

            preferenceJoueur2 = lambda joueur: preferenceEntreJoueurs(ordreInit, nbPoints, joueur, joueur2prefere)

            if preferenceJoueur2(joueur) < preferenceJoueur2(propositionsMariage[joueur2prefere]):
                #on "jette" l'ancien fiancé
                fianceRejete = propositionsMariage[joueur2prefere]
                joueurs1cases[fianceRejete] = False

                #le proposant est préféré par le joueur 2 à son précédent "partenaire"
                #(pour la fonction preferenceJoueur2, "lower is better", d'où le <)
                propositionsMariage[joueur2prefere] = joueur
                joueurs1cases[joueur] = True

        joueurs1enAttente = [x for x in joueurs1 if not joueurs1cases[x] and preferencesJoueurs1[x] != []]

    #on a fini l'algorithme de Gale-Shapley, il reste à générer les matchs à partir de ça
    matchs = [(x, y) for x, y in propositionsMariage.items()]

    #on regarde les personnes qui n'ont pas été casées
    nonCases = []
    for joueur in ordreInit:
        if [x for x in matchs if joueur in x] == []: #le joueur n'a pas été casé
            nonCases.append(joueur)
    for match in matchs.copy():
        if None in match: matchs.remove(match)

    shuffle(nonCases)
    ajout = [(joueur, nonCases[index+len(nonCases) // 2]) for index, joueur in enumerate(nonCases[:len(nonCases) // 2])]

    matchs += ajout
    print(matchs, ajout)

    return matchs, len(ajout)



#NOUVELLE VERSION PLUS SYMPA
#matches est un dictionnaire de (int, int) -> int (id des deux joueurs du match et le gagnant)
def scores(matches, joueurs): #pour compter le nombre de victoires au total de chaque joueur
    ret = {j: 0 for j in joueurs}
    for gagnant in matches.values(): ret[gagnant] += 1

    return ret

def joueursRencontres(matches, joueurs):
    ret = {j: set() for j in joueurs}
    for (j1, j2) in matches:
        if j1: ret[j1].add(j2)
        if j2: ret[j2].add(j1)

    return ret

def appariementEasy(joueurs):
    nbJoueurs = len(joueurs)

    if nbJoueurs % 2 == 0:
        match = lambda a, b: (joueurs[a], joueurs[b])

        return [match(2*i, 2*i+1) for i in range(nbJoueurs // 2)], None
    else:
        appPair, _ = appariementEasy(joueurs[1:])
        return appPair, joueurs[0]

def appariement(joueurs, matches, ordreInit):
    scoresJoueurs = scores(matches, joueurs)
    rencontres = joueursRencontres(matches, joueurs)

    joueurs.sort(key = lambda x: (scoresJoueurs[x], ordreInit[x]))

    appariementRet, toutSeul = appariementEasy(joueurs)

    #on détecte les doublons de match et on les corrige (du moins on tente de le faire)
    for idMatch, (j1, j2) in enumerate(appariementRet):
        if (j1, j2) in matches or (j2, j1) in matches:
            #il faut changer le match et trouver un autre adversaire

            nouv = None
            for id2, (j3, j4) in enumerate(appariementRet[idMatch+1:]):
                if j3 not in rencontres[j1]:
                    nouv, autre = j3, j4
                    break
                elif j4 not in rencontres[j1]:
                    nouv, autre = j4, j3
                    break

            if nouv:
                appariementRet[idMatch], appariementRet[id2] = (j1, nouv), (j2, autre)
            else:
                return appariementRet, toutSeul, False

    return appariementRet, toutSeul, True

def test():
    from math import log
    from random import choice

    reussis = {k:[0, round( log(k)/log(2) )] for k in range(2, 100, 2)}
    for n in range(2, 100, 2):
        joueurs = list(range(n))
        ordreInit = {k:k for k in joueurs}
        matches = dict()

        for idMatch in range(round( log(n)/log(2) )):
            app, _, ok = appariement(joueurs, matches, ordreInit)
            if ok:
                reussis[n][0] += 1
                for match in app:
                    matches[match] = choice(match)
            else:
                continue

    return reussis
