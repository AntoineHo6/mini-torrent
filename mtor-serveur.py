#! /usr/bin/python3

"""
Serveur qui envoie bloc d'octets d'un fichier au client

Auteur: Antoine Ho (1767487)
Date: 2018/12/06
"""

import socket
import sys
import pickle
import os
from threading import Thread, Lock

verrou = Lock()
dossierFichiers = "dossier_fichiers"


def main():
    if len(sys.argv) != 3:
        print("Usage: mtor-serveur.py <Nom dossier> <port>", file=sys.stderr)
        sys.exit(1)

    socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_serveur.bind(("", int(sys.argv[2])))
    socket_serveur.listen(5)

    print("En écoute...")

    while True:
        conn, addr = socket_serveur.accept()
        Thread(target=envoieBloc, args=(conn,)).start()


def envoieBloc(conn):
    """
    Envoie au client le bloc d'octets du fichier.

    :param conn: Socket pour communiquer avec le client.
    :return None:
    """
    data = conn.recv(1024)
    (nomFichier, bloc) = pickle.loads(data)

    cheminFichier = "./{0}/{1}".format(dossierFichiers, nomFichier)
    offset, taille = bloc

    verrou.acquire()
    fichier = open(cheminFichier, 'rb')
    fichier.seek(offset, 0)
    data = fichier.read(taille)
    fichier.close()
    verrou.release()

    conn.send(data)
    print("Blocs envoyés ({}): {}".format(nomFichier, bloc))
    conn.close()


if __name__ == '__main__':
    os.system("reset")
    main()
