import asyncio

from config import (
    MAX_SITE_PAGES,
    MAX_SITE_DEPTH,
    DEFAULT_VOLUME_STEP,
)

from audio.volume import (
    volume_controller,
)

from tools.web_search import (
    search_web,
)

from tools.browser import (
    browse_url,
)

from tools.site_browser import (
    browse_site,
)

from tools.spotify import (
    spotify_play,
    spotify_control,
    spotify_info,
)

from tools.radio import (
    radio_play,
    radio_control,
    stop_radio_silent,
)


def format_volume_state(
    state: dict
) -> str:

    volume = state.get(
        "volume",
        0,
    )

    muted = state.get(
        "muted",
        False,
    )

    effective = state.get(
        "effective_volume",
        0,
    )

    if muted:

        return (
            "Le son est coupé. "
            f"Le volume mémorisé est {volume} pour cent."
        )

    return (
        f"Le volume est maintenant à "
        f"{effective} pour cent."
    )


async def execute_tool(
    name: str,
    arguments: dict,
):

    # ========================================================
    # VOLUME
    # ========================================================

    if name == "set_volume":

        action = arguments.get(
            "action",
            "",
        )

        value = arguments.get(
            "value",
            DEFAULT_VOLUME_STEP,
        )

        try:

            if action == "set":

                state = (
                    volume_controller
                    .set_volume(
                        value
                    )
                )

            elif action == "increase":

                state = (
                    volume_controller
                    .increase(
                        value
                    )
                )

            elif action == "decrease":

                state = (
                    volume_controller
                    .decrease(
                        value
                    )
                )

            elif action == "mute":

                state = (
                    volume_controller
                    .mute()
                )

            elif action == "unmute":

                state = (
                    volume_controller
                    .unmute()
                )

            elif action == "max":

                state = (
                    volume_controller
                    .maximum()
                )

            else:

                return (
                    "Action de volume inconnue."
                )

            print()
            print(
                "[VOLUME]",
                state,
            )

            return format_volume_state(
                state
            )

        except Exception as error:

            print(
                "[VOLUME] Erreur :",
                error,
            )

            return (
                "Je n'ai pas réussi "
                "à modifier le volume."
            )


    if name == "get_volume":

        state = (
            volume_controller
            .status()
        )

        return format_volume_state(
            state
        )


    # ========================================================
    # WEB SEARCH
    # ========================================================

    if name == "search_web":

        query = arguments.get(
            "query",
            "",
        )

        if not query:

            return (
                "La requête de recherche "
                "est vide."
            )

        return await search_web(
            query
        )


    # ========================================================
    # SINGLE PAGE
    # ========================================================

    if name == "browse_url":

        url = arguments.get(
            "url",
            "",
        )

        question = arguments.get(
            "question",
            "",
        )

        if not url:

            return (
                "Aucune URL "
                "n'a été fournie."
            )

        return await browse_url(
            url,
            question,
        )


    # ========================================================
    # SMART SITE BROWSING
    # ========================================================

    if name == "browse_site":

        url = arguments.get(
            "url",
            "",
        )

        question = arguments.get(
            "question",
            "",
        )

        if not url:

            return (
                "Aucun site "
                "n'a été fourni."
            )

        if not question:

            question = (
                "Analyse ce site et identifie "
                "les informations principales."
            )

        return await browse_site(
            start_url=url,
            question=question,
            max_pages=MAX_SITE_PAGES,
            max_depth=MAX_SITE_DEPTH,
        )


    # ========================================================
    # SPOTIFY
    # ========================================================

    if name == "spotify_play":

        query = arguments.get(
            "query",
            "",
        )

        kind = arguments.get(
            "type",
            "track",
        )

        if not query:

            return (
                "Aucune musique "
                "n'a été demandée."
            )

        # Une seule source sonore à la fois :
        # lancer Spotify coupe la radio.

        stop_radio_silent()

        return await spotify_play(
            query,
            kind,
        )


    if name == "spotify_control":

        action = arguments.get(
            "action",
            "",
        )

        value = arguments.get(
            "value",
        )

        if not action:

            return (
                "Aucune action Spotify "
                "n'a été demandée."
            )

        return await spotify_control(
            action,
            value,
        )


    if name == "spotify_info":

        what = arguments.get(
            "what",
            "current_track",
        )

        return await spotify_info(
            what
        )


    # ========================================================
    # RADIO
    # ========================================================

    if name == "radio":

        action = arguments.get(
            "action",
            "",
        )

        if action == "play":

            station = arguments.get(
                "station",
                "",
            )

            if not station:

                return (
                    "Aucune station "
                    "n'a été demandée."
                )

            # Une seule source sonore à la
            # fois : lancer la radio met
            # Spotify en pause.

            try:

                from tools.spotify import (
                    _control_sync,
                )

                await asyncio.to_thread(
                    _control_sync,
                    "pause",
                )

            except Exception:

                pass

            return await radio_play(
                station
            )

        if action in (
            "stop",
            "volume",
            "current",
        ):

            return await radio_control(
                action,
                arguments.get("value"),
            )

        return (
            "Action radio inconnue."
        )


    # ========================================================
    # UNKNOWN TOOL
    # ========================================================

    return (
        "Outil inconnu : "
        f"{name}"
    )
