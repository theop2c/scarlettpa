"""Authentification Spotify (à lancer une seule fois).

Usage, depuis ~/scarlett :

    .venv/bin/python scripts/spotify_auth.py

Le script affiche une URL à ouvrir dans un navigateur
(sur n'importe quelle machine). Après connexion à Spotify,
le navigateur redirige vers une adresse 127.0.0.1 qui ne
charge pas : c'est normal. Copier l'URL complète de la barre
d'adresse et la coller ici.

Le jeton est ensuite sauvegardé dans state/spotify_token.json
et renouvelé automatiquement par Scarlett.
"""

import sys

from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__)
        .resolve()
        .parent
        .parent
    ),
)

import spotipy

from config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_CACHE_FILE,
)

from tools.spotify import (
    build_auth_manager,
)


def main():

    if (
        not SPOTIFY_CLIENT_ID
        or not SPOTIFY_CLIENT_SECRET
    ):

        print(
            "SPOTIFY_CLIENT_ID et "
            "SPOTIFY_CLIENT_SECRET doivent "
            "être renseignés dans .env"
        )

        sys.exit(1)

    auth = build_auth_manager()

    print()
    print(
        "1. Ouvre cette URL dans un navigateur "
        "(sur n'importe quelle machine) :"
    )

    print()
    print(
        auth.get_authorize_url()
    )

    print()
    print(
        "2. Connecte-toi à Spotify et accepte."
    )

    print(
        "3. Le navigateur va rediriger vers "
        "une page 127.0.0.1 qui ne charge pas : "
        "c'est normal."
    )

    print(
        "4. Copie l'URL complète de la barre "
        "d'adresse et colle-la ci-dessous."
    )

    print()

    response = ""

    while not response:

        response = input(
            "URL de redirection "
            "(http://127.0.0.1:8888/callback?code=...) : "
        ).strip()

    code = auth.parse_response_code(
        response
    )

    token = auth.get_access_token(

        code=code,

        as_dict=False,
    )

    if not token:

        print(
            "Échec de l'authentification."
        )

        sys.exit(1)

    sp = spotipy.Spotify(
        auth=token
    )

    me = sp.me()

    print()
    print(
        "Authentification réussie pour :",
        me.get("display_name"),
        f"({me.get('product', 'inconnu')})",
    )

    print(
        "Jeton sauvegardé dans :",
        SPOTIFY_CACHE_FILE,
    )

    devices = (
        sp.devices()
        .get("devices", [])
    )

    print()

    if devices:

        print(
            "Appareils Spotify visibles :"
        )

        for device in devices:

            active = (
                " (actif)"
                if device.get("is_active")
                else ""
            )

            print(
                f" - {device['name']}"
                f"{active}"
            )

    else:

        print(
            "Aucun appareil Spotify visible "
            "pour l'instant. Vérifier que "
            "raspotify est démarré."
        )


if __name__ == "__main__":

    main()
