from collections import deque

import numpy as np
import onnxruntime as ort
import sounddevice as sd

from config import (
    INPUT_DEVICE,
    MIC_RATE,
    WAKE_RATE,
    WAKE_THRESHOLD,
    WAKE_CHUNK_16K,
    MELSPEC_MODEL,
    EMBEDDING_MODEL,
    WAKE_MODEL,
)


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

            if not path.is_file():

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
                str(MELSPEC_MODEL),
                sess_options=options,
                providers=providers,
            )
        )

        self.embedding = (
            ort.InferenceSession(
                str(EMBEDDING_MODEL),
                sess_options=options,
                providers=providers,
            )
        )

        self.wake = (
            ort.InferenceSession(
                str(WAKE_MODEL),
                sess_options=options,
                providers=providers,
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

        # Pipeline incrémental : à chaque bloc
        # de 1280 échantillons (80 ms), on ne
        # calcule que les 8 nouvelles trames mel
        # et 1 nouvel embedding, au lieu de tout
        # recalculer sur 3 s d'audio.

        self._reset_buffers()

        print(
            "Wake Word engine prêt."
        )


    def _reset_buffers(self):

        # 400 échantillons de contexte pour que
        # les trames mel (fenêtre 400, pas 160)
        # restent alignées entre deux blocs.

        self._context = np.zeros(
            400,
            dtype=np.int16,
        )

        self._pending = np.empty(
            0,
            dtype=np.int16,
        )

        self.spec_frames = deque(
            maxlen=76
        )

        self.embeddings_buffer = deque(
            maxlen=self.feature_frames
        )


    def reset(self):

        self._reset_buffers()


    def _melspectrogram(
        self,
        audio
    ):

        audio = np.asarray(
            audio,
            dtype=np.int16,
        )

        x = (
            audio[None, :]
            .astype(np.float32)
        )

        result = self.melspec.run(
            None,
            {
                self.melspec_input:
                    x
            },
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


    def _embed_window(
        self,
        frames_76,
    ):

        x = np.asarray(
            frames_76,
            dtype=np.float32,
        )[None, :, :, None]

        result = self.embedding.run(
            None,
            {
                self.embedding_input:
                    x
            },
        )[0]

        return np.asarray(
            result,
            dtype=np.float32,
        ).reshape(-1)


    def predict(
        self,
        audio_16k
    ):

        audio_16k = np.asarray(
            audio_16k,
            dtype=np.int16,
        )

        self._pending = np.concatenate(
            (
                self._pending,
                audio_16k,
            )
        )

        # Un bloc = 1280 échantillons (80 ms)
        # -> 8 trames mel -> 1 embedding.

        while len(self._pending) >= WAKE_CHUNK_16K:

            block = (
                self._pending[
                    :WAKE_CHUNK_16K
                ]
            )

            self._pending = (
                self._pending[
                    WAKE_CHUNK_16K:
                ]
            )

            audio = np.concatenate(
                (
                    self._context,
                    block,
                )
            )

            self._context = (
                block[-400:]
            )

            spec = self._melspectrogram(
                audio
            )

            self.spec_frames.extend(
                spec
            )

            if (
                len(self.spec_frames)
                == 76
            ):

                self.embeddings_buffer.append(
                    self._embed_window(
                        self.spec_frames
                    )
                )

        if (
            len(self.embeddings_buffer)
            < self.feature_frames
        ):

            return 0.0

        features = np.asarray(
            self.embeddings_buffer,
            dtype=np.float32,
        )[None, :, :]

        result = self.wake.run(
            None,
            {
                self.wake_input:
                    features
            },
        )[0]

        return float(
            np.asarray(result)
            .reshape(-1)[-1]
        )


    def wait_for_wakeword(self):

        self.reset()

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

        # Blocs de 160 ms (2 chunks wake) :
        # une inférence toutes les 160 ms
        # au lieu de 80 ms, CPU divisé par 2,
        # latence de détection inchangée
        # à l'oreille.

        block_48k = (
            WAKE_CHUNK_16K
            * 3
            * 2
        )

        with sd.InputStream(

            device=INPUT_DEVICE,

            samplerate=MIC_RATE,

            channels=1,

            dtype="int16",

            blocksize=block_48k,

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

                # 48 kHz -> 16 kHz

                audio_16k = (
                    audio_48k[::3]
                )

                score = self.predict(
                    audio_16k
                )

                if score > 0.10:

                    print(
                        f"\rWake score : "
                        f"{score:.3f}",
                        end="",
                        flush=True,
                    )

                if (
                    score
                    >= WAKE_THRESHOLD
                ):

                    print()

                    print(
                        "Wake word détecté ! "
                        f"score={score:.3f}"
                    )

                    self.reset()

                    return
