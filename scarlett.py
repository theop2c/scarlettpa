import os
import re
import json
import time
import base64
import socket
import asyncio
import ipaddress

from collections import deque
from urllib.parse import urlparse

import numpy as np
import sounddevice as sd
import onnxruntime as ort

from playwright.async_api import async_playwright
from openai import AsyncOpenAI


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_DEVICE = 2
OUTPUT_DEVICE = 1

MIC_RATE = 48000
WAKE_RATE = 16000
OPENAI_RATE = 24000
SPEAKER_RATE = 48000

CHANNELS = 1

OPENAI_MODEL = "gpt-realtime-2.1-mini"
WEB_MODEL = "gpt-5.6-luna"

VOICE = "marin"

MODELS_DIR = os.path.expanduser("~/scarlett/models")

MELSPEC_MODEL = os.path.join(
    MODELS_DIR,
    "melspectrogram.onnx"
)

EMBEDDING_MODEL = os.path.join(
    MODELS_DIR,
    "embedding_model.onnx"
)

WAKE_MODEL = os.path.join(
    MODELS_DIR,
    "hey_jarvis_v0.1.onnx"
)

WAKE_THRESHOLD = 0.20
WAKE_CHUNK_16K = 1280

CONVERSATION_TIMEOUT = 20

CHROMIUM_PATH = "/usr/bin/chromium"

MAX_PAGE_CHARS = 30000


# ============================================================
# OPENAI
# ============================================================

if "OPENAI_API_KEY" not in os.environ:
    raise RuntimeError(
        "OPENAI_API_KEY n'est pas définie.\n"
        'Utilise : export OPENAI_API_KEY="sk-..."'
    )

client = AsyncOpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)


# ============================================================
# SEARCH WEB
# ============================================================

async def search_web(query: str) -> str:

    print()
    print("====================================")
    print("🌐 RECHERCHE WEB")
    print("====================================")
    print("Recherche :", query)
    print()

    try:

        response = await client.responses.create(
            model=WEB_MODEL,
            tools=[
                {
                    "type": "web_search"
                }
            ],
            input=(
                "Recherche sur Internet des informations récentes "
                "et fiables pour répondre à la demande suivante. "
                "Réponds en français, de façon factuelle et concise. "
                "La réponse sera lue oralement par un assistant.\n\n"
                f"Demande : {query}"
            )
        )

        result = response.output_text

        print("Résultat web :")
        print(result)
        print()

        return result

    except Exception as error:

        print("Erreur search_web :", error)

        return (
            "La recherche Internet a échoué. "
            f"Erreur technique : {error}"
        )


# ============================================================
# SECURITY URL CHECK
# ============================================================

def url_is_allowed(url: str) -> tuple[bool, str]:

    try:

        parsed = urlparse(url)

        if parsed.scheme not in (
            "http",
            "https"
        ):
            return False, (
                "Seules les URL HTTP et HTTPS sont autorisées."
            )

        hostname = parsed.hostname

        if not hostname:
            return False, "Nom d'hôte invalide."

        addresses = socket.getaddrinfo(
            hostname,
            None
        )

        for address in addresses:

            ip_string = address[4][0]

            ip = ipaddress.ip_address(
                ip_string
            )

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return False, (
                    "Navigation refusée vers "
                    "une adresse locale ou privée."
                )

        return True, ""

    except Exception as error:

        return False, (
            f"Impossible de valider l'URL : {error}"
        )


# ============================================================
# BROWSE URL
# ============================================================

async def browse_url(
    url: str,
    question: str = ""
) -> str:

    print()
    print("====================================")
    print("🌍 NAVIGATION WEB")
    print("====================================")
    print("URL :", url)
    print("Question :", question)
    print()

    if not url.startswith(
        ("http://", "https://")
    ):
        url = "https://" + url

    allowed, reason = url_is_allowed(url)

    if not allowed:
        return reason

    if not os.path.exists(
        CHROMIUM_PATH
    ):
        return (
            "Chromium n'est pas installé "
            f"à l'emplacement {CHROMIUM_PATH}."
        )

    try:

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True,
                executable_path=CHROMIUM_PATH,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 "
                    "(X11; Linux aarch64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/130 Safari/537.36"
                ),
                viewport={
                    "width": 1280,
                    "height": 900
                }
            )

            page = await context.new_page()

            page.set_default_timeout(
                20000
            )

            print(
                "[WEB] Chargement de la page..."
            )

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=20000
            )

            try:

                await page.wait_for_load_state(
                    "networkidle",
                    timeout=5000
                )

            except Exception:
                pass

            # Vérifier l'URL après redirection
            final_url = page.url

            allowed, reason = url_is_allowed(
                final_url
            )

            if not allowed:

                await browser.close()

                return (
                    "Redirection refusée. "
                    + reason
                )

            title = await page.title()

            status = None

            if response is not None:
                status = response.status

            # Supprime le bruit non utile
            await page.evaluate(
                """
                () => {
                    const selectors = [
                        'script',
                        'style',
                        'noscript',
                        'svg',
                        'canvas'
                    ];

                    selectors.forEach(selector => {
                        document
                            .querySelectorAll(selector)
                            .forEach(el => el.remove());
                    });
                }
                """
            )

            text = await page.locator(
                "body"
            ).inner_text()

            await browser.close()

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        ).strip()

        if len(text) > MAX_PAGE_CHARS:

            text = (
                text[:MAX_PAGE_CHARS]
                + "\n\n[Contenu tronqué]"
            )

        print(
            f"[WEB] Page lue : {title}"
        )

        print(
            f"[WEB] {len(text)} caractères extraits"
        )

        result = (
            f"Titre : {title}\n"
            f"URL finale : {final_url}\n"
            f"HTTP : {status}\n\n"
            f"Question de l'utilisateur : "
            f"{question}\n\n"
            f"Contenu visible de la page :\n"
            f"{text}"
        )

        return result

    except Exception as error:

        print(
            "Erreur browse_url :",
            error
        )

        return (
            "Je n'ai pas réussi à ouvrir "
            "cette page. "
            f"Erreur technique : {error}"
        )


# ============================================================
# WAKE WORD ENGINE
# ============================================================

class WakeWordEngine:

    def __init__(self):

        print(
            "Chargement des modèles wake word..."
        )

        for path in (
            MELSPEC_MODEL,
            EMBEDDING_MODEL,
            WAKE_MODEL,
        ):

            if not os.path.isfile(path):

                raise RuntimeError(
                    f"Modèle introuvable : {path}"
                )

        options = ort.SessionOptions()

        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1

        providers = [
            "CPUExecutionProvider"
        ]

        self.melspec = (
            ort.InferenceSession(
                MELSPEC_MODEL,
                sess_options=options,
                providers=providers
            )
        )

        self.embedding = (
            ort.InferenceSession(
                EMBEDDING_MODEL,
                sess_options=options,
                providers=providers
            )
        )

        self.wake = (
            ort.InferenceSession(
                WAKE_MODEL,
                sess_options=options,
                providers=providers
            )
        )

        self.melspec_input = (
            self.melspec
            .get_inputs()[0]
            .name
        )

        self.embedding_input = (
            self.embedding
            .get_inputs()[0]
            .name
        )

        self.wake_input = (
            self.wake
            .get_inputs()[0]
            .name
        )

        wake_shape = (
            self.wake
            .get_inputs()[0]
            .shape
        )

        try:

            self.feature_frames = int(
                wake_shape[-2]
            )

        except Exception:

            self.feature_frames = 16

        if self.feature_frames <= 0:
            self.feature_frames = 16

        self.audio_buffer = deque(
            maxlen=WAKE_RATE * 3
        )

        print(
            "Wake Word engine prêt."
        )


    def reset(self):

        self.audio_buffer.clear()


    def _melspectrogram(
        self,
        audio
    ):

        audio = np.asarray(
            audio,
            dtype=np.int16
        )

        x = (
            audio[None, :]
            .astype(np.float32)
        )

        result = self.melspec.run(
            None,
            {
                self.melspec_input: x
            }
        )[0]

        spec = np.squeeze(
            result
        )

        spec = (
            spec / 10.0
            + 2.0
        )

        return spec.astype(
            np.float32
        )


    def _embeddings(
        self,
        spectrogram
    ):

        windows = []

        for i in range(
            0,
            spectrogram.shape[0],
            8
        ):

            window = spectrogram[
                i:i + 76
            ]

            if window.shape[0] == 76:

                windows.append(
                    window
                )

        if not windows:
            return None

        x = np.asarray(
            windows,
            dtype=np.float32
        )

        x = x[..., None]

        result = self.embedding.run(
            None,
            {
                self.embedding_input: x
            }
        )[0]

        embeddings = np.asarray(
            result,
            dtype=np.float32
        ).squeeze()

        if embeddings.ndim == 1:

            embeddings = (
                embeddings[None, :]
            )

        return embeddings


    def predict(
        self,
        audio_16k
    ):

        audio_16k = np.asarray(
            audio_16k,
            dtype=np.int16
        )

        self.audio_buffer.extend(
            audio_16k.tolist()
        )

        if len(
            self.audio_buffer
        ) < 32000:

            return 0.0

        audio = np.asarray(
            self.audio_buffer,
            dtype=np.int16
        )

        spec = self._melspectrogram(
            audio
        )

        embeddings = self._embeddings(
            spec
        )

        if embeddings is None:
            return 0.0

        if (
            embeddings.shape[0]
            < self.feature_frames
        ):
            return 0.0

        features = embeddings[
            -self.feature_frames:
        ]

        features = (
            features[None, :, :]
            .astype(np.float32)
        )

        result = self.wake.run(
            None,
            {
                self.wake_input: features
            }
        )[0]

        score = float(
            np.asarray(result)
            .reshape(-1)[-1]
        )

        return score


# ============================================================
# BEEP
# ============================================================

def play_beep():

    duration = 0.13
    frequency = 880

    t = np.arange(
        int(
            SPEAKER_RATE
            * duration
        )
    )

    wave = (
        np.sin(
            2
            * np.pi
            * frequency
            * t
            / SPEAKER_RATE
        )
        * 5000
    ).astype(np.int16)

    sd.play(
        wave,
        samplerate=SPEAKER_RATE,
        device=OUTPUT_DEVICE
    )

    sd.wait()


# ============================================================
# WAIT FOR WAKE WORD
# ============================================================

def wait_for_wakeword(
    engine
):

    engine.reset()

    print()
    print(
        "===================================="
    )
    print(
        "         SCARLETT EN VEILLE"
    )
    print(
        "===================================="
    )
    print()
    print(
        "Wake word temporaire : Hey Jarvis"
    )
    print()

    block_48k = (
        WAKE_CHUNK_16K
        * 3
    )

    with sd.InputStream(
        device=INPUT_DEVICE,
        samplerate=MIC_RATE,
        channels=1,
        dtype="int16",
        blocksize=block_48k
    ) as stream:

        while True:

            audio_48k, overflow = (
                stream.read(
                    block_48k
                )
            )

            if overflow:

                print(
                    "Micro overflow"
                )

            audio_48k = (
                audio_48k[:, 0]
            )

            audio_16k = (
                audio_48k[::3]
            )

            score = engine.predict(
                audio_16k
            )

            if score > 0.10:

                print(
                    f"\rWake score : "
                    f"{score:.3f}",
                    end="",
                    flush=True
                )

            if score >= WAKE_THRESHOLD:

                print()

                print(
                    "Wake word détecté ! "
                    f"score={score:.3f}"
                )

                engine.reset()

                return


# ============================================================
# REALTIME CONVERSATION
# ============================================================

async def run_openai_conversation():

    print()
    print(
        "Connexion à Scarlett..."
    )

    scarlett_is_speaking = False
    tool_running = False
    last_activity = time.time()

    async with client.realtime.connect(
        model=OPENAI_MODEL
    ) as connection:

        await connection.session.update(

            session={

                "type": "realtime",

                "model": OPENAI_MODEL,

                "output_modalities": [
                    "audio"
                ],

                "instructions": (

                    "Tu t'appelles Scarlett. "
                    "Tu es mon assistant vocal personnel. "
                    "Tu réponds principalement en français. "
                    "Tes réponses sont naturelles, claires "
                    "et adaptées à une conversation orale. "

                    "Tu disposes de deux outils Internet. "

                    "search_web sert à rechercher des "
                    "informations sur Internet, notamment "
                    "pour les actualités et les informations "
                    "récentes. "

                    "browse_url sert à ouvrir réellement "
                    "une URL ou un site précis et à lire "
                    "son contenu visible. "

                    "Utilise browse_url quand je te demande "
                    "d'aller sur, ouvrir, visiter, lire ou "
                    "analyser un site particulier. "

                    "Ne prétends jamais avoir lu une page "
                    "tant que browse_url n'a pas retourné "
                    "son contenu. "

                    "Après un appel d'outil, explique le "
                    "résultat oralement de façon naturelle. "

                    "Ne lis pas de longues URL à voix haute. "
                    "Réponds plutôt brièvement sauf si je "
                    "demande une explication détaillée."
                ),

                "tools": [

                    {
                        "type": "function",

                        "name": "search_web",

                        "description": (
                            "Recherche des informations "
                            "sur Internet."
                        ),

                        "parameters": {

                            "type": "object",

                            "properties": {

                                "query": {

                                    "type": "string",

                                    "description": (
                                        "Recherche à effectuer."
                                    )
                                }
                            },

                            "required": [
                                "query"
                            ],

                            "additionalProperties":
                                False
                        }
                    },

                    {
                        "type": "function",

                        "name": "browse_url",

                        "description": (
                            "Ouvre réellement une URL "
                            "dans Chromium, charge la page "
                            "et lit son contenu visible."
                        ),

                        "parameters": {

                            "type": "object",

                            "properties": {

                                "url": {

                                    "type": "string",

                                    "description": (
                                        "URL ou domaine "
                                        "à visiter."
                                    )
                                },

                                "question": {

                                    "type": "string",

                                    "description": (
                                        "Ce que l'utilisateur "
                                        "souhaite savoir "
                                        "sur la page."
                                    )
                                }
                            },

                            "required": [
                                "url"
                            ],

                            "additionalProperties":
                                False
                        }
                    }
                ],

                "tool_choice": "auto",

                "audio": {

                    "input": {

                        "format": {

                            "type":
                                "audio/pcm",

                            "rate":
                                OPENAI_RATE
                        },

                        "turn_detection": {

                            "type":
                                "server_vad"
                        }
                    },

                    "output": {

                        "format": {

                            "type":
                                "audio/pcm",

                            "rate":
                                OPENAI_RATE
                        },

                        "voice":
                            VOICE
                    }
                }
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

        loop = (
            asyncio.get_running_loop()
        )

        # ====================================================
        # MICRO
        # ====================================================

        def mic_callback(
            indata,
            frames,
            time_info,
            status
        ):

            nonlocal scarlett_is_speaking

            if status:

                print(
                    "Micro warning :",
                    status
                )

            # Le micro reste ouvert.
            # On ignore seulement son contenu
            # quand Scarlett parle.
            if scarlett_is_speaking:
                return

            audio_48k = (
                indata[:, 0]
            )

            audio_24k = (
                audio_48k[::2]
            )

            data = (
                audio_24k
                .astype(np.int16)
                .tobytes()
            )

            encoded = (
                base64
                .b64encode(data)
                .decode("utf-8")
            )

            asyncio.run_coroutine_threadsafe(

                connection
                .input_audio_buffer
                .append(
                    audio=encoded
                ),

                loop
            )


        input_stream = sd.InputStream(

            device=INPUT_DEVICE,

            samplerate=MIC_RATE,

            channels=1,

            dtype="int16",

            blocksize=1920,

            latency="low",

            callback=mic_callback
        )


        output_stream = sd.RawOutputStream(

            device=OUTPUT_DEVICE,

            samplerate=SPEAKER_RATE,

            channels=1,

            dtype="int16"
        )


        input_stream.start()
        output_stream.start()


        # ====================================================
        # RECEIVE EVENTS
        # ====================================================

        async def receive_events():

            nonlocal scarlett_is_speaking
            nonlocal tool_running
            nonlocal last_activity

            async for event in connection:

                # --------------------------------------------
                # AUDIO RESPONSE
                # --------------------------------------------

                if (
                    event.type
                    ==
                    "response.output_audio.delta"
                ):

                    scarlett_is_speaking = True

                    last_activity = time.time()

                    data = base64.b64decode(
                        event.delta
                    )

                    audio_24k = np.frombuffer(
                        data,
                        dtype=np.int16
                    )

                    audio_48k = np.repeat(
                        audio_24k,
                        2
                    )

                    output_stream.write(
                        audio_48k.tobytes()
                    )


                # --------------------------------------------
                # TRANSCRIPT
                # --------------------------------------------

                elif (
                    event.type
                    ==
                    "response.output_audio_transcript.delta"
                ):

                    print(
                        event.delta,
                        end="",
                        flush=True
                    )


                elif (
                    event.type
                    ==
                    "response.output_audio_transcript.done"
                ):

                    print()


                # --------------------------------------------
                # FUNCTION CALL
                # --------------------------------------------

                elif (
                    event.type
                    ==
                    "response.function_call_arguments.done"
                ):

                    tool_running = True
                    last_activity = time.time()

                    try:

                        function_name = (
                            event.name
                        )

                        arguments = json.loads(
                            event.arguments
                        )

                        call_id = (
                            event.call_id
                        )

                        print()
                        print(
                            "Tool demandé :",
                            function_name
                        )

                        # ====================================
                        # SEARCH WEB
                        # ====================================

                        if (
                            function_name
                            ==
                            "search_web"
                        ):

                            query = (
                                arguments.get(
                                    "query",
                                    ""
                                )
                            )

                            if not query:

                                tool_result = (
                                    "La requête est vide."
                                )

                            else:

                                tool_result = (
                                    await search_web(
                                        query
                                    )
                                )


                        # ====================================
                        # BROWSE URL
                        # ====================================

                        elif (
                            function_name
                            ==
                            "browse_url"
                        ):

                            url = arguments.get(
                                "url",
                                ""
                            )

                            question = (
                                arguments.get(
                                    "question",
                                    ""
                                )
                            )

                            if not url:

                                tool_result = (
                                    "Aucune URL fournie."
                                )

                            else:

                                tool_result = (
                                    await browse_url(
                                        url,
                                        question
                                    )
                                )


                        else:

                            tool_result = (
                                "Outil inconnu : "
                                + function_name
                            )


                        # ====================================
                        # SEND TOOL OUTPUT
                        # ====================================

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
                                        tool_result
                                }
                            )
                        )


                        # Demande à Scarlett
                        # de répondre avec le résultat

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
                            error
                        )


                    finally:

                        tool_running = False


                # --------------------------------------------
                # RESPONSE DONE
                # --------------------------------------------

                elif (
                    event.type
                    ==
                    "response.done"
                ):

                    scarlett_is_speaking = False

                    last_activity = time.time()

                    print()


                # --------------------------------------------
                # USER SPEECH
                # --------------------------------------------

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


                # --------------------------------------------
                # ERROR
                # --------------------------------------------

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

                        print(event)


        # ====================================================
        # TIMEOUT
        # ====================================================

        async def watch_timeout():

            nonlocal last_activity
            nonlocal scarlett_is_speaking
            nonlocal tool_running

            while True:

                await asyncio.sleep(1)

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
                        "Retour en veille."
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
                        timeout_task
                    ],

                    return_when=
                        asyncio.FIRST_COMPLETED
                )
            )

            for task in pending:

                task.cancel()

            await asyncio.gather(
                *pending,
                return_exceptions=True
            )


        finally:

            receiver_task.cancel()
            timeout_task.cancel()

            input_stream.stop()
            input_stream.close()

            output_stream.stop()
            output_stream.close()


# ============================================================
# MAIN
# ============================================================

async def main():

    engine = WakeWordEngine()

    print()
    print(
        "Scarlett V3 démarrée."
    )
    print(
        "Recherche web + navigation web activées."
    )

    while True:

        await asyncio.to_thread(
            wait_for_wakeword,
            engine
        )

        await asyncio.to_thread(
            play_beep
        )

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
                error
            )

        print()
        print(
            "Retour en veille..."
        )


# ============================================================
# START
# ============================================================

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
