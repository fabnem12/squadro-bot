from random import shuffle, randint

jures = ("fabnem", "clus", "isak", "chip", "tijmen", "joker")
chansons = list(range(1, 18))

chansonsPond = sum((randint(2, 20) * [i] for i in chansons), [])
def extrait10(liste, nb = 10):
    pris = [liste[0]]
    for val in liste:
        if val not in pris:
            pris.append(val)
            if len(pris) == nb:
                return pris

points = lambda x: 12 if i == 0 else (10 if i == 1 else max(10-i, 0))
donneTop = 10

def hare(votes, nbPoints):
    totalVotes = sum(votes.values())
    points = {k: (nbPoints * p) // totalVotes for k, p in votes.items()}

    for k in sorted(votes, key=lambda x: (nbPoints * votes[x]) % totalVotes, reverse=True)[:nbPoints-sum(points.values())]:
        points[k] += 1

    return points

for jure in jures:
    shuffle(chansonsPond)
    for i, e in zip(range(donneTop), extrait10(chansonsPond)):
        print(f"{e};{jure};{points(i)}")

public = {k: 0 for k in chansons}
for _ in range(15):
    shuffle(chansonsPond)
    for chanson, points in zip(extrait10(chansonsPond, 3), (3, 2, 1)):
        public[chanson] += points

pointsPublic = hare(public, len(jures)*58)

for e in sorted(chansons):
    print(f"{e};public;{pointsPublic[e]}")
