from arrow import utcnow #récupérer la date du jour
from datetime import datetime
from icalendar import Calendar
from reportlab.graphics import renderPM #pour convertir le svg en png
from svglib.svglib import svg2rlg #pour convertir le svg en png
import requests #récupérer le fichier ics de l'agenda
import recurring_ical_events
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import cheminOutputs

import pickle

nomFichierEDT = os.path.join(cheminOutputs, "edt-info.p")

NOMS_JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

HAUTEUR = 2000
LARGEUR = 1300
HAUTEUR_COURS = (HAUTEUR - 100) / 12

def chargeAgenda(url): #récupère l'agenda depuis le lien .ics
    icsAgenda = requests.get(url).text
    return Calendar.from_ical(icsAgenda)

def lectureEventsJournee(calendar, shift = 0):
    now = utcnow().to("Europe/Paris").shift(days = shift)

    #on récupère la liste des évènements du jour
    events = recurring_ical_events.of(calendar).at((now.year, now.month, now.day))
    #events = recurring_ical_events.of(calendar).between((2020, 9, 29), (2020, 9, 30)) #pour voir les évènements d'un jour en particulier (en phase de tests)

    TOUTE_JOURNEE = [] #liste des évènements qui durent tte la journée. l'agenda est maintenu de sorte à ce que ça ne corresponde qu'à "cours en présentiel/distanciel"
    EVENTS = [] #les cours
    for event in events:
        if not isinstance(event["DTSTART"].dt, datetime): #c'est un truc qui dure toute la journée
            TOUTE_JOURNEE.append(event)
        else:
            EVENTS.append(event)

    return TOUTE_JOURNEE, EVENTS

def dessine(couleurDefaut, toute_journee, liste_cours, COULEUR_PRESENTIEL, COULEUR_DISTANCIEL, COULEUR_PARTIEL):
    lignesSvg = [""]
    def printF(*args): #fonction pour écrire facilement dans le str du code svg
        lignesSvg[0] += " ".join(str(x) for x in args) + "\n"

    #header du svg
    printF('<?xml version="1.0" standalone="no"?>')
    printF('<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}">'.format(LARGEUR, HAUTEUR))
    printF('<rect width="100%" height="100%" fill="white" />') #pour le fond blanc

    #l'évènement toute la journée (présentiel/distanciel)
    if toute_journee != []:
        txtPresentiel = toute_journee[0]["SUMMARY"]
        presentiel = "PRÉSENTIEL" in txtPresentiel
    else:
        presentiel = True
    couleur = COULEUR_PRESENTIEL if presentiel else COULEUR_DISTANCIEL

    dateJour = liste_cours[0]["DTSTART"].dt if len(liste_cours) > 0 else None

    printF("<rect x='0' y='0' width='{}' height='100' fill='{}' />".format(LARGEUR, couleur))
    if dateJour:
        titre = "Cours du {} {}".format(NOMS_JOURS[dateJour.isoweekday() - 1], dateJour.strftime("%d/%m"))
    else:
        titre = "Pas de cours demain !"
    printF("<text x='{}' y='65' font-size='50' fill='white' text-anchor='middle'>{}</text>".format(LARGEUR / 2, titre))

    #affichage des heures
    offsetY = 100
    for heure in range(8, 20):
        printF(f"<text x='8' y='{offsetY + 35 + (heure - 8) * HAUTEUR_COURS}' font-size='30'>{str(heure).zfill(2)}:00</text>")
        printF("<line x1='0' y1='{y}' x2='{largeur}' y2='{y}' style='stroke: #000; stroke-width: 1;' />".format(y = offsetY + (heure - 8) * HAUTEUR_COURS, largeur = LARGEUR))

    offsetX = 100
    printF("<line x1='{x}' y1='{y1}' x2='{x}' y2='{y2}' style='stroke: #000; stroke-width: 1;' />".format(x = offsetX, y1 = offsetY, y2 = HAUTEUR))

    #affichage des cours
    for cours in liste_cours:
        heure_debut_dt = cours["DTSTART"].dt
        heure_fin_dt = cours["DTEND"].dt

        #il y des évènements qui n'ont pas de timezone enregistrée dans le .ics (les évènements "non récurrents")
        #ils sont enregistrés en utc, donc il faut le remettre à l'heure de Paris
        if "TZID" not in cours["DTSTART"].params:
            import pytz

            timezone_Paris = pytz.timezone("Europe/Paris")
            heure_debut_dt, heure_fin_dt = map(lambda x: x.astimezone(timezone_Paris), (heure_debut_dt, heure_fin_dt))

        heure_debut_str = "{}:{}".format(*map(lambda x: str(x).zfill(2), (heure_debut_dt.hour, heure_debut_dt.minute)))
        heure_fin_str = "{}:{}".format(*map(lambda x: str(x).zfill(2), (heure_fin_dt.hour, heure_fin_dt.minute)))
        titre = cours["SUMMARY"].replace("&","&amp;")
        lieu = cours["LOCATION"]

        heure_debut = heure_debut_dt.hour + heure_debut_dt.minute / 60 #conversion de l'heure en float
        heure_fin = heure_fin_dt.hour + heure_fin_dt.minute / 60
        duree = heure_fin - heure_debut #durée en heure

        if titre.startswith("PRÉSENTIEL"):
            couleur = COULEUR_PRESENTIEL
            presentielCours = True
        elif titre.startswith("DISTANCIEL"):
            couleur = COULEUR_DISTANCIEL
            presentielCours = False
        elif titre.startswith("EXAMEN") or titre.startswith("PARTIEL"):
            couleur = COULEUR_PARTIEL
            presentielCours = True
        else:
            couleur = couleurDefaut
            presentielCours = presentiel

        yRect = offsetY + (heure_debut - 8) * HAUTEUR_COURS
        xText = offsetX + 20
        printF("<rect x='{}' y='{}' width='{}' height='{}' fill='{}' />".format(offsetX, yRect, LARGEUR - offsetX, HAUTEUR_COURS * duree, couleur))

        #affichage du titre du cours et du lieu et de l'heure
        printF("<text x='{}' y='{}' font-size='52' fill='white' text-decoration='underline'>{}</text>".format(xText, yRect + 50, titre))
        printF("<text x='{}' y='{}' font-size='40' fill='white' font-weight='bold'>{}</text>".format(xText, yRect + 105, "{} à {}".format(heure_debut_str, heure_fin_str)))

        if lieu != "":
            if not presentielCours: lieu = "chez toi ;)"
            printF("<text x='{}' y='{}' font-size='40' fill='white'>Lieu : {}</text>".format(xText, yRect + 150, lieu))

    #fin du svg
    printF("</svg>")

    #enregistrement dans un fichier svg
    with open("outputs/edt.svg", "w") as f:
        f.write(lignesSvg[0])

    #conversion du svg en png
    from cairosvg import svg2png
    svg2png(open("outputs/edt.svg", 'rb').read(), write_to=open("outputs/edt.png", 'wb'))

    return "outputs/edt.png" #on envoie le lien du fichier pour usage futur

def genereEDT(groupeId, shift = 0):
    if os.path.exists(nomFichierEDT):
        GROUPES, COULEUR_PRESENTIEL, COULEUR_DISTANCIEL, COULEUR_PARTIEL = pickle.load(open(nomFichierEDT, "rb"))
    else:
        GROUPES = {
            "8A":("#1E7FCB", "https://calendar.google.com/calendar/ical/1c5jnhnhjgqsnl028fjjrbrdgs%40group.calendar.google.com/private-7ccc201c4de3ce2e89fe10195ce1da73/basic.ics"),
            "8B":("#FF866A", "https://calendar.google.com/calendar/ical/ab2h8bi3kgra0c1tjloihdec8c%40group.calendar.google.com/private-4f5453dabff64790fc0d2caa6f453cbe/basic.ics"),
            "9A":("#357AB7", "https://calendar.google.com/calendar/ical/euqulah1cshf788g67g1hqi454%40group.calendar.google.com/private-a6bdd67de7357b8e6265f6e5695d8d4e/basic.ics"),
            "9B":("#ED7F10", "https://calendar.google.com/calendar/ical/rbhvris59e710laq9uccgp3bmk%40group.calendar.google.com/private-39800ae6a811d9c397bea82916319a8b/basic.ics")
        }
        COULEUR_PRESENTIEL = "#00AA00"
        COULEUR_DISTANCIEL = "#AA8800"
        COULEUR_PARTIEL    = "#F4511E"

        pickle.dump((GROUPES, COULEUR_PRESENTIEL, COULEUR_DISTANCIEL, COULEUR_PARTIEL), open(nomFichierEDT, "wb"))

    #on télécharge l'agenda
    couleur, urlAgenda = GROUPES[groupeId]
    agenda = chargeAgenda(urlAgenda)
    #on récupère les évènements
    toute_journee, cours = lectureEventsJournee(agenda, shift)
    #dessin du svg et conversion en png du même coup
    lienImage = dessine(couleur, toute_journee, cours, COULEUR_PRESENTIEL, COULEUR_DISTANCIEL, COULEUR_PARTIEL)

    return lienImage

def genereEDTNew(urlAgenda, couleur, shift):
    COULEUR_PRESENTIEL = "#00AA00"
    COULEUR_DISTANCIEL = "#AAAA00"
    COULEUR_PARTIEL    = "#F4511E"

    agenda = chargeAgenda(urlAgenda)
    toute_journee, cours = lectureEventsJournee(agenda, shift)
    lienImage = dessine(couleur, toute_journee, cours, COULEUR_PRESENTIEL, COULEUR_DISTANCIEL, COULEUR_PARTIEL)

    return lienImage, cours != []
