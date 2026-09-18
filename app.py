import asyncio
import fcntl
import sys

from pathlib import Path

from audio.player import (
    play_beep,
)

from audio.volume import (
    volume_controller,
)

from wakeword.engine import (
    WakeWordEngine,
)

from realtime.session import (
    run_openai_conversation,
)


async def main():

    engine = (
        WakeWordEngine()
    )

    print()
    print(
        "Scarlett V3.1 démarrée."
    )

    print(
        "Web Search : actif"
    )

    print(
        "Navigation URL : active"
    )

    print(
        "Navigation multi-pages : active"
    )

    while True:

        # ================================================
        # 1. ATTENTE WAKE WORD
        # ================================================

        await asyncio.to_thread(
            engine.wait_for_wakeword
        )


        # ================================================
        # 2. BIP
        # ================================================

        # Garde-fou : dire le wake word implique
        # qu'on veut entendre Scarlett. Si le son
        # est coupé, on le rétablit — sinon elle
        # répondrait dans le vide sans pouvoir
        # dire qu'elle est muette.

        if (
            volume_controller
            .status()["muted"]
        ):

            state = (
                volume_controller
                .unmute()
            )

            print(
                "[VOLUME] Son rétabli au réveil :",
                state,
            )

        await asyncio.to_thread(
            play_beep
        )


        # ================================================
        # 3. CONVERSATION
        # ================================================

        try:

            await (
                run_openai_conversation()
            )

        except KeyboardInterrupt:

            raise

        except Exception as error:

            print()
            print(
                "Erreur session Scarlett :",
                error,
            )

        print()
        print(
            "Retour en veille..."
        )


def acquire_single_instance_lock():

    # Empêche deux Scarlett en même temps
    # (service systemd + lancement manuel) :
    # elles se disputeraient le micro.

    lock_path = (
        Path(__file__)
        .resolve()
        .parent
        / "state"
        / "scarlett.lock"
    )

    lock_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_file = open(
        lock_path,
        "w",
    )

    try:

        fcntl.flock(
            lock_file,
            fcntl.LOCK_EX
            | fcntl.LOCK_NB,
        )

    except OSError:

        print(
            "Une autre instance de Scarlett "
            "tourne déjà (service systemd ?). "
            "Arrête-la d'abord : "
            "sudo systemctl stop scarlett"
        )

        sys.exit(1)

    # Garder le fichier ouvert : le verrou
    # tombe tout seul à la fin du process.

    return lock_file


if __name__ == "__main__":

    _lock = (
        acquire_single_instance_lock()
    )

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print(
            "Scarlett arrêtée."
        )
