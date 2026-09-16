import json
import time
import asyncio
import base64

import numpy as np
import sounddevice as sd

from config import (
    INPUT_DEVICE,
    OUTPUT_DEVICE,
    MIC_RATE,
    OPENAI_RATE,
    SPEAKER_RATE,
    OPENAI_MODEL,
    VOICE,
    CONVERSATION_TIMEOUT,
    PROMPT_FILE,
)

from audio.volume import (
    volume_controller,
)

from realtime.client import (
    get_openai_client,
)

from realtime.tool_definitions import (
    TOOLS,
)

from realtime.tools_router import (
    execute_tool,
)


def load_prompt():

    return PROMPT_FILE.read_text(
        encoding="utf-8"
    )


async def run_openai_conversation():

    client = get_openai_client()

    instructions = load_prompt()

    print()
    print(
        "Connexion à Scarlett..."
    )

    scarlett_is_speaking = False
    tool_running = False

    last_activity = time.time()

    async with (
        client.realtime.connect(
            model=OPENAI_MODEL
        )
        as connection
    ):

        await connection.session.update(

            session={

                "type":
                    "realtime",

                "model":
                    OPENAI_MODEL,

                "output_modalities": [
                    "audio"
                ],

                "instructions":
                    instructions,

                "tools":
                    TOOLS,

                "tool_choice":
                    "auto",

                "audio": {

                    "input": {

                        "format": {

                            "type":
                                "audio/pcm",

                            "rate":
                                OPENAI_RATE,
                        },

                        "turn_detection": {

                            "type":
                                "server_vad",
                        },
                    },

                    "output": {

                        "format": {

                            "type":
                                "audio/pcm",

                            "rate":
                                OPENAI_RATE,
                        },

                        "voice":
                            VOICE,
                    },
                },
            }
        )

        print()
        print(
            "===================================="
        )
        print(
            "          SCARLETT ÉCOUTE"
        )
        print(
            "===================================="
        )
        print()

        current_volume = (
            volume_controller
            .status()
        )

        print(
            "[VOLUME]",
            current_volume,
        )

        loop = (
            asyncio.get_running_loop()
        )


        # ====================================================
        # MICRO CALLBACK
        # ====================================================

        def mic_callback(
            indata,
            frames,
            time_info,
            status,
        ):

            nonlocal scarlett_is_speaking

            if status:

                print(
                    "Micro warning :",
                    status,
                )

            # Le microphone reste physiquement ouvert.
            # On ignore uniquement son contenu
            # lorsque Scarlett parle afin d'éviter
            # la boucle enceinte -> micro.

            if scarlett_is_speaking:

                return

            audio_48k = (
                indata[:, 0]
            )

            # 48 kHz -> 24 kHz

            audio_24k = (
                audio_48k[::2]
            )

            raw_audio = (
                audio_24k
                .astype(
                    np.int16
                )
                .tobytes()
            )

            encoded = (
                base64
                .b64encode(
                    raw_audio
                )
                .decode(
                    "utf-8"
                )
            )

            try:

                asyncio.run_coroutine_threadsafe(
                    connection
                    .input_audio_buffer
                    .append(
                        audio=encoded
                    ),
                    loop,
                )

            except Exception as error:

                print(
                    "Erreur envoi micro :",
                    error,
                )


        # ====================================================
        # AUDIO STREAMS
        # ====================================================

        input_stream = (
            sd.InputStream(

                device=
                    INPUT_DEVICE,

                samplerate=
                    MIC_RATE,

                channels=1,

                dtype=
                    "int16",

                blocksize=
                    1920,

                latency=
                    "low",

                callback=
                    mic_callback,
            )
        )


        output_stream = (
            sd.RawOutputStream(

                device=
                    OUTPUT_DEVICE,

                samplerate=
                    SPEAKER_RATE,

                channels=1,

                dtype=
                    "int16",
            )
        )


        input_stream.start()
        output_stream.start()


        # ====================================================
        # RECEIVE REALTIME EVENTS
        # ====================================================

        async def receive_events():

            nonlocal scarlett_is_speaking
            nonlocal tool_running
            nonlocal last_activity

            async for event in connection:

                # ============================================
                # SCARLETT AUDIO
                # ============================================

                if (
                    event.type
                    ==
                    "response.output_audio.delta"
                ):

                    scarlett_is_speaking = True

                    last_activity = (
                        time.time()
                    )

                    raw_audio = (
                        base64.b64decode(
                            event.delta
                        )
                    )

                    audio_24k = (
                        np.frombuffer(
                            raw_audio,
                            dtype=np.int16,
                        )
                    )

                    # OpenAI 24 kHz
                    # ->
                    # USB speaker 48 kHz

                    audio_48k = (
                        np.repeat(
                            audio_24k,
                            2,
                        )
                    )

                    # Application du volume logiciel

                    audio_48k = (
                        volume_controller
                        .apply(
                            audio_48k
                        )
                    )

                    output_stream.write(
                        audio_48k.tobytes()
                    )


                # ============================================
                # TRANSCRIPT
                # ============================================

                elif (
                    event.type
                    ==
                    "response.output_audio_transcript.delta"
                ):

                    print(
                        event.delta,
                        end="",
                        flush=True,
                    )


                elif (
                    event.type
                    ==
                    "response.output_audio_transcript.done"
                ):

                    print()


                # ============================================
                # TOOL CALL
                # ============================================

                elif (
                    event.type
                    ==
                    "response.function_call_arguments.done"
                ):

                    tool_running = True

                    last_activity = (
                        time.time()
                    )

                    try:

                        function_name = (
                            event.name
                        )

                        call_id = (
                            event.call_id
                        )

                        raw_arguments = (
                            event.arguments
                            or "{}"
                        )

                        arguments = (
                            json.loads(
                                raw_arguments
                            )
                        )

                        print()
                        print(
                            "Tool demandé :",
                            function_name,
                        )

                        print(
                            "Arguments :",
                            arguments,
                        )

                        tool_result = (
                            await execute_tool(
                                function_name,
                                arguments,
                            )
                        )

                        # Les tools média renvoient
                        # {"output", "silent"} :
                        # action réussie -> pas de
                        # réponse vocale, Scarlett
                        # reste à l'écoute.

                        silent = False

                        if isinstance(
                            tool_result,
                            dict,
                        ):

                            silent = (
                                tool_result.get(
                                    "silent",
                                    False,
                                )
                            )

                            tool_result = (
                                tool_result.get(
                                    "output",
                                    "",
                                )
                            )

                        print(
                            "Résultat tool :",
                            tool_result,
                        )

                        await (
                            connection
                            .conversation
                            .item
                            .create(

                                item={

                                    "type":
                                        "function_call_output",

                                    "call_id":
                                        call_id,

                                    "output":
                                        tool_result,
                                }
                            )
                        )

                        if silent:

                            print(
                                "[MEDIA] Action faite, "
                                "Scarlett reste "
                                "silencieuse."
                            )

                        else:

                            await (
                                connection
                                .response
                                .create()
                            )

                        last_activity = (
                            time.time()
                        )

                    except Exception as error:

                        print()
                        print(
                            "Erreur tool :",
                            error,
                        )

                    finally:

                        tool_running = False


                # ============================================
                # RESPONSE DONE
                # ============================================

                elif (
                    event.type
                    ==
                    "response.done"
                ):

                    scarlett_is_speaking = False

                    last_activity = (
                        time.time()
                    )

                    print()


                # ============================================
                # USER SPEECH
                # ============================================

                elif (
                    event.type
                    ==
                    "input_audio_buffer.speech_started"
                ):

                    last_activity = (
                        time.time()
                    )


                elif (
                    event.type
                    ==
                    "input_audio_buffer.speech_stopped"
                ):

                    last_activity = (
                        time.time()
                    )


                # ============================================
                # OPENAI ERROR
                # ============================================

                elif (
                    event.type
                    ==
                    "error"
                ):

                    print()
                    print(
                        "Erreur OpenAI :"
                    )

                    try:

                        print(
                            event.error.message
                        )

                    except Exception:

                        print(
                            event
                        )


        # ====================================================
        # TIMEOUT
        # ====================================================

        async def watch_timeout():

            nonlocal last_activity
            nonlocal scarlett_is_speaking
            nonlocal tool_running

            while True:

                await asyncio.sleep(
                    1
                )

                if (
                    scarlett_is_speaking
                    or tool_running
                ):

                    continue

                inactivity = (
                    time.time()
                    - last_activity
                )

                if (
                    inactivity
                    >= CONVERSATION_TIMEOUT
                ):

                    print()
                    print(
                        f"{CONVERSATION_TIMEOUT} "
                        "secondes de silence."
                    )

                    print(
                        "Scarlett retourne "
                        "en veille."
                    )

                    return


        receiver_task = (
            asyncio.create_task(
                receive_events()
            )
        )

        timeout_task = (
            asyncio.create_task(
                watch_timeout()
            )
        )


        try:

            done, pending = (
                await asyncio.wait(

                    [
                        receiver_task,
                        timeout_task,
                    ],

                    return_when=
                        asyncio.FIRST_COMPLETED,
                )
            )

            for task in pending:

                task.cancel()

            await asyncio.gather(
                *pending,
                return_exceptions=True,
            )


        finally:

            receiver_task.cancel()
            timeout_task.cancel()

            try:
                input_stream.stop()
            except Exception:
                pass

            try:
                input_stream.close()
            except Exception:
                pass

            try:
                output_stream.stop()
            except Exception:
                pass

            try:
                output_stream.close()
            except Exception:
                pass
