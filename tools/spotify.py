import asyncio
import unicodedata

import spotipy

from spotipy.oauth2 import (
    SpotifyOAuth,
)

from spotipy.cache_handler import (
    CacheFileHandler,
)

from config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_DEVICE_NAME,
    SPOTIFY_CACHE_FILE,
    SPOTIFY_SCOPES,
)


NOT_CONFIGURED = (
    "Spotify n'est pas encore configuré. "
    "Il faut renseigner les identifiants "
    "et lancer le script d'authentification."
)

NO_DEVICE = (
    "Aucun appareil Spotify n'est disponible. "
    "L'enceinte Scarlett ne semble pas "
    "connectée à Spotify."
)


_client = None


# ============================================================
# CLIENT
# ============================================================

def build_auth_manager():

    return SpotifyOAuth(

        client_id=
            SPOTIFY_CLIENT_ID,

        client_secret=
            SPOTIFY_CLIENT_SECRET,

        redirect_uri=
            SPOTIFY_REDIRECT_URI,

        scope=
            SPOTIFY_SCOPES,

        cache_handler=
            CacheFileHandler(
                str(SPOTIFY_CACHE_FILE)
            ),

        open_browser=
            False,
    )


def get_spotify():

    global _client

    if _client is not None:

        return _client

    if (
        not SPOTIFY_CLIENT_ID
        or not SPOTIFY_CLIENT_SECRET
    ):

        return None

    if not SPOTIFY_CACHE_FILE.exists():

        # Jamais authentifié : ne pas déclencher
        # le flux OAuth interactif en pleine
        # session vocale.

        return None

    _client = spotipy.Spotify(

        auth_manager=
            build_auth_manager(),

        requests_timeout=
            10,

        retries=
            1,
    )

    return _client


# ============================================================
# DEVICE
# ============================================================

def find_device(sp):

    devices = (
        sp.devices()
        .get(
            "devices",
            [],
        )
    )

    for device in devices:

        if (
            device.get("name", "").lower()
            == SPOTIFY_DEVICE_NAME.lower()
        ):

            return device

    for device in devices:

        if device.get("is_active"):

            return device

    if devices:

        return devices[0]

    return None


# ============================================================
# HELPERS
# ============================================================

def _normalize(text):

    # minuscules + suppression des accents

    decomposed = unicodedata.normalize(
        "NFD",
        text.lower(),
    )

    return "".join(
        char
        for char in decomposed
        if unicodedata.category(char) != "Mn"
    ).strip()


def pick_best(
    items,
    query,
):

    # L'API Spotify classe mal avec limit=1
    # (ex. "Jacques Brel" -> Francis Cabrel) :
    # on cherche large puis on choisit par
    # correspondance de nom.

    if not items:

        return None

    target = _normalize(query)

    for item in items:

        if (
            _normalize(item.get("name", ""))
            == target
        ):

            return item

    for item in items:

        name = _normalize(
            item.get("name", "")
        )

        if (
            name.startswith(target)
            or target.startswith(name)
        ):

            return item

    return items[0]


def format_track(item):

    if not item:

        return "un morceau inconnu"

    name = item.get(
        "name",
        "inconnu",
    )

    artists = ", ".join(
        artist.get("name", "")
        for artist in item.get(
            "artists",
            [],
        )
    )

    if artists:

        return f"{name} de {artists}"

    return name


def spotify_error_message(error):

    status = getattr(
        error,
        "http_status",
        None,
    )

    if status == 404:

        return NO_DEVICE

    if status == 403:

        return (
            "Spotify a refusé la commande. "
            "Un compte Premium est nécessaire "
            "pour contrôler la lecture."
        )

    if status == 401:

        return (
            "L'authentification Spotify a expiré. "
            "Il faut relancer le script "
            "d'authentification."
        )

    return (
        "La commande Spotify a échoué. "
        f"Erreur technique : {error}"
    )


# ============================================================
# PLAY (recherche + lecture)
# ============================================================

def _find_user_playlist(sp, query):

    query_lower = query.lower()

    offset = 0

    while offset < 200:

        page = sp.current_user_playlists(

            limit=50,

            offset=offset,
        )

        items = page.get(
            "items",
            [],
        )

        if not items:

            break

        for playlist in items:

            name = (
                playlist.get("name", "")
                .lower()
            )

            if (
                query_lower in name
                or name in query_lower
            ):

                return playlist

        if not page.get("next"):

            break

        offset += 50

    return None


def _play_sync(
    query: str,
    kind: str,
):

    sp = get_spotify()

    if sp is None:

        return NOT_CONFIGURED

    try:

        device = find_device(sp)

        if device is None:

            return NO_DEVICE

        device_id = device["id"]

        # ----------------------------------------------------
        # PLAYLIST : d'abord celles de l'utilisateur
        # ----------------------------------------------------

        if kind == "playlist":

            playlist = _find_user_playlist(
                sp,
                query,
            )

            if playlist is None:

                results = sp.search(

                    q=query,

                    type="playlist",

                    limit=5,
                )

                items = [
                    item
                    for item in (
                        results
                        .get("playlists", {})
                        .get("items", [])
                    )
                    if item
                ]

                playlist = pick_best(
                    items,
                    query,
                )

            if playlist is None:

                return (
                    False,
                    "Je n'ai pas trouvé de playlist "
                    f"correspondant à {query}.",
                )

            sp.start_playback(

                device_id=device_id,

                context_uri=
                    playlist["uri"],
            )

            return (
                True,
                "Je lance la playlist "
                f"{playlist['name']} sur Spotify.",
            )

        # ----------------------------------------------------
        # ARTIST / ALBUM : lecture d'un contexte
        # ----------------------------------------------------

        if kind in ("artist", "album"):

            results = sp.search(

                q=query,

                type=kind,

                limit=5,
            )

            items = (
                results
                .get(f"{kind}s", {})
                .get("items", [])
            )

            if not items:

                return (
                    False,
                    "Je n'ai rien trouvé sur Spotify "
                    f"pour {query}.",
                )

            item = pick_best(
                items,
                query,
            )

            sp.start_playback(

                device_id=device_id,

                context_uri=
                    item["uri"],
            )

            if kind == "artist":

                return (
                    True,
                    "Je lance les titres de "
                    f"{item['name']} sur Spotify.",
                )

            return (
                True,
                "Je lance l'album "
                f"{format_track(item)} sur Spotify.",
            )

        # ----------------------------------------------------
        # TRACK (défaut)
        # ----------------------------------------------------

        results = sp.search(

            q=query,

            type="track",

            limit=5,
        )

        items = (
            results
            .get("tracks", {})
            .get("items", [])
        )

        if not items:

            return (
                False,
                "Je n'ai pas trouvé ce morceau "
                f"sur Spotify : {query}.",
            )

        track = items[0]

        sp.start_playback(

            device_id=device_id,

            uris=[
                track["uri"],
            ],
        )

        return (
            True,
            "Je lance "
            f"{format_track(track)} sur Spotify.",
        )

    except spotipy.SpotifyException as error:

        print(
            "[SPOTIFY] Erreur :",
            error,
        )

        return spotify_error_message(
            error
        )

    except Exception as error:

        print(
            "[SPOTIFY] Erreur :",
            error,
        )

        return (
            "La commande Spotify a échoué. "
            f"Erreur technique : {error}"
        )


# ============================================================
# CONTROL (pause, resume, next, previous, volume)
# ============================================================

def _control_sync(
    action: str,
    value=None,
):

    sp = get_spotify()

    if sp is None:

        return NOT_CONFIGURED

    try:

        device = find_device(sp)

        if device is None:

            return NO_DEVICE

        device_id = device["id"]

        if action == "pause":

            sp.pause_playback(
                device_id=device_id
            )

            return (True, "Musique en pause.")

        if action == "resume":

            sp.start_playback(
                device_id=device_id
            )

            return (True, "Je relance la musique.")

        if action == "next":

            sp.next_track(
                device_id=device_id
            )

            return (True, "Morceau suivant.")

        if action == "previous":

            sp.previous_track(
                device_id=device_id
            )

            return (True, "Morceau précédent.")

        if action == "volume":

            if value is None:

                return (
                    False,
                    "Quel volume pour la musique ?",
                )

            # librespot est en volume fixe (son
            # softvol coupait le son de façon
            # erratique) : le volume "musique"
            # pilote le volume général matériel,
            # fiable à 100 %.

            from audio.volume import (
                volume_controller,
            )

            state = (
                volume_controller
                .set_volume(
                    value
                )
            )

            return (
                True,
                "Volume à "
                f"{state['effective_volume']} "
                "pour cent.",
            )

        return (
            False,
            "Action Spotify inconnue : "
            f"{action}.",
        )

    except spotipy.SpotifyException as error:

        print(
            "[SPOTIFY] Erreur :",
            error,
        )

        return spotify_error_message(
            error
        )

    except Exception as error:

        print(
            "[SPOTIFY] Erreur :",
            error,
        )

        return (
            "La commande Spotify a échoué. "
            f"Erreur technique : {error}"
        )


# ============================================================
# INFO (morceau en cours, playlists)
# ============================================================

def _info_sync(
    what: str,
):

    sp = get_spotify()

    if sp is None:

        return NOT_CONFIGURED

    try:

        if what == "playlists":

            page = sp.current_user_playlists(
                limit=15
            )

            names = [
                playlist.get("name", "")
                for playlist in page.get(
                    "items",
                    [],
                )
                if playlist
            ]

            if not names:

                return (
                    "Tu n'as aucune playlist "
                    "sur Spotify."
                )

            return (
                "Voici tes playlists Spotify : "
                + ", ".join(names)
                + "."
            )

        playback = (
            sp.current_playback()
        )

        if (
            not playback
            or not playback.get("item")
        ):

            return (
                "Rien n'est en cours de lecture "
                "sur Spotify."
            )

        track = format_track(
            playback["item"]
        )

        if playback.get("is_playing"):

            return (
                f"En ce moment : {track}."
            )

        return (
            f"En pause : {track}."
        )

    except spotipy.SpotifyException as error:

        print(
            "[SPOTIFY] Erreur :",
            error,
        )

        return spotify_error_message(
            error
        )

    except Exception as error:

        print(
            "[SPOTIFY] Erreur :",
            error,
        )

        return (
            "La commande Spotify a échoué. "
            f"Erreur technique : {error}"
        )


# ============================================================
# WRAPPERS ASYNC
# ============================================================

async def spotify_play(
    query: str,
    kind: str = "track",
):

    print()
    print(
        "===================================="
    )
    print(
        "🎵 SPOTIFY PLAY"
    )
    print(
        "===================================="
    )
    print(
        "Demande :",
        query,
        f"({kind})",
    )
    print()

    result = await asyncio.to_thread(
        _play_sync,
        query,
        kind,
    )

    # Une chaîne nue = message d'erreur
    # (les succès sont des tuples).

    if isinstance(result, str):

        return (
            False,
            result,
        )

    return result


async def spotify_control(
    action: str,
    value=None,
):

    print()
    print(
        "[SPOTIFY]",
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


async def spotify_info(
    what: str = "current_track",
):

    return await asyncio.to_thread(
        _info_sync,
        what,
    )
