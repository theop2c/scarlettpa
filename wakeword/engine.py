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


    def _embeddings(
        self,
        spectrogram
    ):

        windows = []

        for i in range(
            0,
            spectrogram.shape[0],
            8,
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
            dtype=np.float32,
        )

        x = x[..., None]

        result = self.embedding.run(
            None,
            {
                self.embedding_input:
                    x
            },
        )[0]

        embeddings = np.asarray(
            result,
            dtype=np.float32,
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
            dtype=np.int16,
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
            dtype=np.int16,
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

        block_48k = (
            WAKE_CHUNK_16K
            * 3
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
