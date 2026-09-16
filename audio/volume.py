import json
import threading

import numpy as np

from config import (
    DEFAULT_VOLUME,
    DEFAULT_VOLUME_STEP,
    STATE_DIR,
    VOLUME_STATE_FILE,
)


class VolumeController:

    def __init__(self):

        self._lock = threading.Lock()

        self.volume = DEFAULT_VOLUME
        self.previous_volume = DEFAULT_VOLUME
        self.muted = False

        STATE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.load()


    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _clamp(value):

        value = int(value)

        return max(
            0,
            min(
                100,
                value,
            ),
        )


    # ========================================================
    # LOAD / SAVE
    # ========================================================

    def load(self):

        try:

            if not VOLUME_STATE_FILE.exists():
                return

            data = json.loads(
                VOLUME_STATE_FILE.read_text(
                    encoding="utf-8"
                )
            )

            volume = self._clamp(
                data.get(
                    "volume",
                    DEFAULT_VOLUME,
                )
            )

            previous_volume = self._clamp(
                data.get(
                    "previous_volume",
                    volume or DEFAULT_VOLUME,
                )
            )

            muted = bool(
                data.get(
                    "muted",
                    False,
                )
            )

            self.volume = volume

            self.previous_volume = (
                previous_volume
                if previous_volume > 0
                else DEFAULT_VOLUME
            )

            self.muted = muted

        except Exception as error:

            print(
                "[VOLUME] Impossible de lire "
                "l'état sauvegardé :",
                error,
            )


    def save(self):

        data = {
            "volume": self.volume,
            "previous_volume": self.previous_volume,
            "muted": self.muted,
        }

        try:

            VOLUME_STATE_FILE.write_text(
                json.dumps(
                    data,
                    indent=2,
                ),
                encoding="utf-8",
            )

        except Exception as error:

            print(
                "[VOLUME] Impossible de sauvegarder :",
                error,
            )


    # ========================================================
    # STATUS
    # ========================================================

    def status(self):

        with self._lock:

            effective_volume = (
                0
                if self.muted
                else self.volume
            )

            return {
                "volume": self.volume,
                "muted": self.muted,
                "effective_volume": effective_volume,
            }


    # ========================================================
    # SET
    # ========================================================

    def set_volume(self, value):

        value = self._clamp(
            value
        )

        with self._lock:

            if value == 0:

                if self.volume > 0:

                    self.previous_volume = (
                        self.volume
                    )

                self.volume = 0
                self.muted = True

            else:

                self.volume = value
                self.previous_volume = value
                self.muted = False

            self.save()

            return self._status_unlocked()


    # ========================================================
    # INCREASE
    # ========================================================

    def increase(
        self,
        amount=DEFAULT_VOLUME_STEP,
    ):

        amount = max(
            1,
            int(amount),
        )

        with self._lock:

            if (
                self.muted
                or self.volume == 0
            ):

                base = (
                    self.previous_volume
                    or DEFAULT_VOLUME
                )

            else:

                base = self.volume

            new_value = self._clamp(
                base + amount
            )

            self.volume = new_value
            self.previous_volume = new_value
            self.muted = False

            self.save()

            return self._status_unlocked()


    # ========================================================
    # DECREASE
    # ========================================================

    def decrease(
        self,
        amount=DEFAULT_VOLUME_STEP,
    ):

        amount = max(
            1,
            int(amount),
        )

        with self._lock:

            if (
                self.muted
                or self.volume == 0
            ):

                base = (
                    self.previous_volume
                    or DEFAULT_VOLUME
                )

            else:

                base = self.volume

            new_value = self._clamp(
                base - amount
            )

            if new_value == 0:

                if base > 0:

                    self.previous_volume = base

                self.volume = 0
                self.muted = True

            else:

                self.volume = new_value
                self.previous_volume = new_value
                self.muted = False

            self.save()

            return self._status_unlocked()


    # ========================================================
    # MUTE
    # ========================================================

    def mute(self):

        with self._lock:

            if self.volume > 0:

                self.previous_volume = (
                    self.volume
                )

            self.muted = True

            self.save()

            return self._status_unlocked()


    # ========================================================
    # UNMUTE
    # ========================================================

    def unmute(self):

        with self._lock:

            if self.volume <= 0:

                self.volume = (
                    self.previous_volume
                    or DEFAULT_VOLUME
                )

            self.muted = False

            self.save()

            return self._status_unlocked()


    # ========================================================
    # MAX
    # ========================================================

    def maximum(self):

        with self._lock:

            self.volume = 100
            self.previous_volume = 100
            self.muted = False

            self.save()

            return self._status_unlocked()


    # ========================================================
    # APPLY AUDIO GAIN
    # ========================================================

    def apply(self, audio):

        audio = np.asarray(
            audio,
            dtype=np.int16,
        )

        with self._lock:

            muted = self.muted
            volume = self.volume

        if muted:

            return np.zeros_like(
                audio
            )

        gain = (
            volume
            / 100.0
        )

        result = (
            audio.astype(
                np.float32
            )
            * gain
        )

        result = np.clip(
            result,
            -32768,
            32767,
        )

        return result.astype(
            np.int16
        )


    def _status_unlocked(self):

        return {
            "volume": self.volume,
            "muted": self.muted,
            "effective_volume": (
                0
                if self.muted
                else self.volume
            ),
        }


volume_controller = (
    VolumeController()
)
