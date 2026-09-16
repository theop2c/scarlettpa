import asyncio
import json
import os
import socket
import subprocess
import time
import unicodedata

from config import (
    MPV_PATH,
    MPV_IPC_SOCKET,
    RADIO_OUTPUT,
    RADIO_DEFAULT_VOLUME,
)


# ============================================================
# STATIONS
# ============================================================

STATIONS = {

    "fip": {
        "name": "FIP",
        "url": "https://icecast.radiofrance.fr/fip-midfi.mp3",
        "aliases": ["fip"],
    },

    "france inter": {
        "name": "France Inter",
        "url": "https://icecast.radiofrance.fr/franceinter-midfi.mp3",
        "aliases": ["inter"],
    },

    "france info": {
        "name": "France Info",
        "url": "https://icecast.radiofrance.fr/franceinfo-midfi.mp3",
        "aliases": ["info", "infos"],
    },

    "france musique": {
        "name": "France Musique",
        "url": "https://icecast.radiofrance.fr/francemusique-midfi.mp3",
        "aliases": ["musique classique"],
    },

    "france culture": {
        "name": "France Culture",
        "url": "https://icecast.radiofrance.fr/franceculture-midfi.mp3",
        "aliases": ["culture"],
    },

    "nova": {
        "name": "Radio Nova",
        "url": "https://novazz.ice.infomaniak.ch/novazz-128.mp3",
        "aliases": ["radio nova"],
    },

    "skyrock": {
        "name": "Skyrock",
        "url": "https://icecast.skyrock.net/s/natio_mp3_128k",
        "aliases": ["sky"],
    },

    "nrj": {
        "name": "NRJ",
        "url": "https://scdn.nrjaudio.fm/audio1/fr/30001/mp3_128.mp3",
        "aliases": ["energie", "energy"],
    },

    "fun radio": {
        "name": "Fun Radio",
        "url": "https://icecast.funradio.fr/fun-1-44-128",
        "aliases": ["fun"],
    },

    "rtl": {
        "name": "RTL",
        "url": "https://icecast.rtl.fr/rtl-1-44-128",
        "aliases": [],
    },

    "rmc": {
        "name": "RMC",
        "url": "https://audio.bfmtv.com/rmcradio_128.mp3",
        "aliases": ["rmc radio"],
    },

    "bfm": {
        "name": "BFM Business",
        "url": "https://audio.bfmtv.com/bfmbusiness_128.mp3",
        "aliases": ["bfm business", "bfm tv"],
    },

    "europe 1": {
        "name": "Europe 1",
        "url": "https://stream.europe1.fr/europe1.mp3",
        "aliases": ["europe un"],
    },
}


NOT_INSTALLED = (
    "Le lecteur radio mpv "
    "n'est pas installé."
)


_process = None


# ============================================================
# HELPERS
# ============================================================

def _normalize(text):

    decomposed = unicodedata.normalize(
        "NFD",
        text.lower(),
    )

    return "".join(
        char
        for char in decomposed
        if unicodedata.category(char) != "Mn"
    ).strip()


def find_station(query):

    target = _normalize(query)

    if not target:

        return None

    for key, station in STATIONS.items():

        names = (
            [key]
            + station["aliases"]
        )

        for name in names:

            name = _normalize(name)

            if (
                name == target
                or name in target
                or target in name
            ):

                return station

    return None


def station_list():

    return ", ".join(
        station["name"]
        for station in STATIONS.values()
    )


def _mpv_command(command):

    # Envoie une commande JSON IPC à mpv
    # et retourne sa réponse.

    client = socket.socket(
        socket.AF_UNIX,
        socket.SOCK_STREAM,
    )

    client.settimeout(2)

    try:

        client.connect(
            str(MPV_IPC_SOCKET)
        )

        payload = (
            json.dumps(
                {
                    "command": command,
                }
            )
            + "\n"
        )

        client.sendall(
            payload.encode()
        )

        response = (
            client.recv(4096)
            .decode()
        )

        for line in response.splitlines():

            data = json.loads(line)

            if "error" in data:

                return data

        return None

    finally:

        client.close()


def _mpv_get(prop):

    client = socket.socket(
        socket.AF_UNIX,
        socket.SOCK_STREAM,
    )

    client.settimeout(2)

    try:

        client.connect(
            str(MPV_IPC_SOCKET)
        )

        client.sendall(
            (
                json.dumps(
                    {
                        "command": [
                            "get_property",
                            prop,
                        ],
                    }
                )
                + "\n"
            ).encode()
        )

        response = (
            client.recv(4096)
            .decode()
        )

        for line in response.splitlines():

            data = json.loads(line)

            if data.get("error") == "success":

                return data.get("data")

        return None

    finally:

        client.close()


def _radio_running():

    global _process

    if (
        _process is not None
        and _process.poll() is None
    ):

        return True

    return False


def _stop_sync():

    global _process

    stopped = False

    if _radio_running():

        stopped = True

    # Tue aussi les mpv orphelins d'une
    # ancienne instance de Scarlett
    # (repérés par le chemin du socket).

    result = subprocess.run(
        [
            "pkill",
            "-f",
            str(MPV_IPC_SOCKET),
        ],
        capture_output=True,
    )

    if result.returncode == 0:

        stopped = True

    _process = None

    return stopped


# ============================================================
# ACTIONS (sync)
# ============================================================

def _play_sync(query):

    global _process

    if not os.path.exists(MPV_PATH):

        return NOT_INSTALLED

    station = find_station(query)

    if station is None:

        return (
            f"Je ne connais pas la radio {query}. "
            "Les stations disponibles sont : "
            + station_list()
            + "."
        )

    _stop_sync()

    try:

        _process = subprocess.Popen(

            [
                MPV_PATH,
                "--no-video",
                "--really-quiet",
                "--no-terminal",
                f"--audio-device=alsa/{RADIO_OUTPUT}",
                f"--input-ipc-server={MPV_IPC_SOCKET}",
                f"--volume={RADIO_DEFAULT_VOLUME}",
                station["url"],
            ],

            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    except Exception as error:

        return (
            "Impossible de lancer la radio. "
            f"Erreur : {error}"
        )

    # Laisse le flux démarrer, puis vérifie
    # que mpv n'est pas mort (URL cassée...).

    time.sleep(2.5)

    if _process.poll() is not None:

        _process = None

        return (
            f"La radio {station['name']} "
            "n'a pas pu démarrer. "
            "Le flux est peut-être indisponible."
        )

    return (
        True,
        f"Je lance {station['name']}.",
    )


def _control_sync(
    action,
    value=None,
):

    if action == "stop":

        if _stop_sync():

            return (
                True,
                "Radio coupée.",
            )

        return (
            "Aucune radio n'est en cours."
        )

    if not _radio_running():

        return (
            "Aucune radio n'est en cours."
        )

    if action == "volume":

        if value is None:

            return (
                "Quel volume pour la radio ?"
            )

        volume = max(
            0,
            min(
                100,
                int(value),
            ),
        )

        try:

            _mpv_command(
                [
                    "set_property",
                    "volume",
                    volume,
                ]
            )

            return (
                True,
                "Volume de la radio "
                f"à {volume} pour cent.",
            )

        except Exception as error:

            return (
                "Je n'ai pas réussi à changer "
                "le volume de la radio. "
                f"Erreur : {error}"
            )

    if action == "current":

        try:

            title = None

            # Le titre ICY (métadonnées du
            # flux), sinon media-title qui
            # retombe sur le nom du fichier.

            for prop in (
                "metadata/by-key/icy-title",
                "media-title",
            ):

                data = _mpv_get(prop)

                if (
                    data
                    and not data.endswith(
                        (".mp3", ".aac")
                    )
                    and "128" not in data
                ):

                    title = data

                    break

            if title:

                return (
                    "En ce moment "
                    f"à la radio : {title}."
                )

            return (
                "La radio joue, mais la station "
                "n'indique pas le titre en cours."
            )

        except Exception:

            return (
                "La radio joue, mais je n'ai pas "
                "réussi à lire le titre en cours."
            )

    return (
        "Action radio inconnue : "
        f"{action}."
    )


# ============================================================
# WRAPPERS ASYNC
# ============================================================

async def radio_play(query):

    print()
    print(
        "===================================="
    )
    print(
        "📻 RADIO"
    )
    print(
        "===================================="
    )
    print(
        "Station :",
        query,
    )
    print()

    result = await asyncio.to_thread(
        _play_sync,
        query,
    )

    # Une chaîne nue = message d'erreur
    # (les succès sont des tuples).

    if isinstance(result, str):

        return (
            False,
            result,
        )

    return result


async def radio_control(
    action,
    value=None,
):

    print()
    print(
        "[RADIO]",
        action,
        value if value is not None else "",
    )

    result = await asyncio.to_thread(
        _control_sync,
        action,
        value,
    )

    if isinstance(result, str):

        return (
            False,
            result,
        )

    return result


def stop_radio_silent():

    # Utilisé par le router avant de lancer
    # Spotify : coupe la radio sans échouer.

    try:

        _stop_sync()

    except Exception:

        pass
