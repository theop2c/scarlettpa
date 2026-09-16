import asyncio

from audio.player import (
    play_beep,
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


if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print(
            "Scarlett arrêtée."
        )
