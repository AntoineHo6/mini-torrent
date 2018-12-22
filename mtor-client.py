#! /usr/bin/python3

"""
Client qui télécharge un fichier

Auteur: Antoine Ho (1767487)
Date: 2018/12/06
"""

import socket
import sys
import os
from threading import Thread, Lock
import pickle

verrou = Lock()
listeBlocsManquants = []
listeIPServActif = []

def main():
    if len(sys.argv) != 3:
        print("Usage: mtor-client.py <nomFichier.mtr> <port>", file=sys.stderr)
        sys.exit(1)

    #    infoMtr[0]       infoMtr[1]        infoMtr[2:]
    #   nom fichier     taille fichier     addresses ip
    infoMtr = [line.rstrip('\n') for line in open(sys.argv[1])]
    infoMtr[0] = infoMtr[0][1:]                 # Enlève le BOM(\ufeff) du debut de la premiere ligne
    infoMtr = list(filter(None, infoMtr))       # Enlève les espaces vides de la liste
    print(infoMtr)

    global listeIPServActif
    listeIPServActif = infoMtr[2:]

    tailleFich = int(infoMtr[1])
    nbrBlocs = len(listeIPServActif) * 4         # 4 blocs minimum par serveurs
    fracOctets = int(tailleFich / nbrBlocs)     # cast int pour arrondir
    listeBlocs = creationlisteBlocs(tailleFich, fracOctets, nbrBlocs)

    # creation fichier de la bonne taille
    fichier = open(infoMtr[0], 'wb')
    fichier.seek(tailleFich - 1)
    fichier.write(b'\0')

    telechargement(False, listeBlocs, fichier)

    # Si un des serveurs s'est déconnecté
    if len(listeBlocsManquants) > 0:
        while True:
            telechargement(True, listeBlocsManquants, fichier)

            if len(listeBlocsManquants) == 0:
                break

    fichier.close()
    print('Fichier téléchargé')


def creationlisteBlocs(tailleFich, fracOctets, nbrBlocs):
    """
    Créé la liste de blocs à télécharger.

    :param tailleFich: La taille total du fichier en octets.
    :param fracOctets: Une douzieme de la taille du fichier.
    :return listeBlocs: Une liste qui contient les blocs d'octets a télécharger.
    """
    listeBlocs = []
    # 1. Creation de la liste d'octets a telecharger
    debutSectionOctets = 0
    for i in range(nbrBlocs):
        listeBlocs.append((debutSectionOctets, fracOctets))
        debutSectionOctets += fracOctets

    # 2. Ajoute un bloc a telechager dans la liste si il y a un reste
    nbrOctetsReste = tailleFich - fracOctets * nbrBlocs
    if nbrOctetsReste > 0:
        listeBlocs.append((debutSectionOctets, nbrOctetsReste))

    return listeBlocs


def telechargement(isListeManquant, listeDeBlocs, fichier):
    """
    Télécharge des parties du fichiers par blocs.

    :param isListeManquant: Boolean qui indique si on utilise la liste des blocs manquants (serveur déconnecté).
    :param listeDeBlocs: La liste de blocs à télécharger.
    :param fichier: Le fichier ouvert en écriture,
    :return None:
    """
    i = 0           # pour alterner entre les addresses IP des serveurs
    liste_threads = []
    for bloc in listeDeBlocs:
        if len(listeIPServActif) > 0:
            ipAddr = listeIPServActif[i]
        # Si un mauvais port a été entré ou tous les serveurs sont fermés
        else:
            sys.exit(1)

        liste_threads.append(Thread(target=fonction_thread, args=(ipAddr, bloc, fichier)))
        liste_threads[len(liste_threads) - 1].start()
        i += 1
        if i >= len(listeIPServActif):
            i = 0

        if isListeManquant:
            print("Téléchargement des blocs manquants...")
            listeBlocsManquants.remove(bloc)
        else:
            print("Téléchargement...")

    for threads in liste_threads:
        threads.join()


def fonction_thread(ipAddr, bloc, fichier):
    """
    Créé la liste de blocs à télécharger.

    :param ipAddr: L'addresse IP du serveur.
    :param bloc: Les octets à télécharger.
    :param fichier: Le fichier ouvert en binaire dans lequel il faut écrire.
    :return None:
    """
    try:
        socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_client.connect((ipAddr, int(sys.argv[2])))
        dataEnvoie = pickle.dumps((fichier.name, bloc))
        socket_client.send(dataEnvoie)

        dataRecvArray = []
        dataRecvTotal = 0
        while True:
            dataRecv = socket_client.recv(1024)
            dataRecvArray.append(dataRecv)
            dataRecvTotal += len(dataRecv)
            if not dataRecv:
                if dataRecvTotal < bloc[1]:
                    nouveauBloc = (bloc[0], bloc[1] - dataRecvTotal)
                    listeBlocsManquants.append(nouveauBloc)
                    print("bloc incomplet: ", nouveauBloc)
                else:
                    verrou.acquire()
                    fichier.seek(bloc[0], 0)
                    for octets in dataRecvArray:
                        fichier.write(octets)
                    verrou.release()
                break
        socket_client.close()

    # Un serveur se déconnecte soudainement
    except ConnectionResetError:
        if ipAddr in listeIPServActif:
            listeIPServActif.remove(ipAddr)
            print(ipAddr, " a été déconnecté")
        listeBlocsManquants.append(bloc)
        print("bloc incomplet: ", bloc)

    # Addresse IP d'un serveur invalide ou mauvais port
    except ConnectionRefusedError:
        if ipAddr in listeIPServActif:
            listeIPServActif.remove(ipAddr)
            print("{} n'est pas accessible".format(ipAddr))
        listeBlocsManquants.append(bloc)


if __name__ == '__main__':
    os.system("reset")
    main()
