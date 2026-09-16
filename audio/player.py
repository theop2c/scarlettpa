import numpy as np
import sounddevice as sd

from config import (
    OUTPUT_DEVICE,
    SPEAKER_RATE,
)

from audio.volume import (
    volume_controller,
)


def play_beep():

    duration = 0.13
    frequency = 880

    samples = np.arange(
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
            * samples
            / SPEAKER_RATE
        )
        * 5000
    ).astype(
        np.int16
    )

    wave = (
        volume_controller
        .apply(
            wave
        )
    )

    sd.play(
        wave,
        samplerate=SPEAKER_RATE,
        device=OUTPUT_DEVICE,
    )

    sd.wait()
