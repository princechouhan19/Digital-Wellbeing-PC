"""
audio_visualizer.py — Real-time Windows Audio Loopback FFT Visualizer.
Captures system audio playback via Windows WASAPI loopback,
computes FFT frequency bands (Bass, Low-Mid, Mid, High-Mid, Treble),
and provides real-time amplitude/pitch levels to the Dynamic Island soundbar.
"""
from __future__ import annotations

import math
import time
from typing import Optional

import numpy as np
from PySide6.QtCore import QThread, Signal

try:
    import soundcard as sc
    HAS_SOUNDCARD = True
except Exception:
    HAS_SOUNDCARD = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
    from comtypes import CLSCTX_ALL
    import ctypes
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False


class AudioVisualizerWorker(QThread):
    """
    Background worker thread capturing real-time loopback audio
    and computing a 5-band frequency spectrum (Bass, Low-Mid, Mid, High-Mid, Treble).
    """

    levels_updated = Signal(list)  # list of 5 floats: 0.0 to 1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self._current_levels = [0.0, 0.0, 0.0, 0.0, 0.0]
        self._bands = [
            (20, 250),      # Sub-bass & Bass
            (250, 600),     # Low-Mid (warmth, bassline)
            (600, 2200),    # Mid (vocals, instruments)
            (2200, 6000),   # High-Mid (presence, snare)
            (6000, 12000),  # Treble (high pitch, cymbals, brilliance)
        ]

    def run(self):
        samplerate = 22050
        blocksize = 512

        while self.running:
            captured = False
            if HAS_SOUNDCARD:
                try:
                    spk = sc.default_speaker()
                    if spk:
                        mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
                        if mic:
                            with mic.recorder(samplerate=samplerate, blocksize=blocksize) as rec:
                                while self.running:
                                    data = rec.record(numframes=blocksize)
                                    if not self.running:
                                        break
                                    mono = np.mean(data, axis=1) if data.ndim > 1 else data
                                    fft_vals = np.abs(np.fft.rfft(mono))
                                    freqs = np.fft.rfftfreq(len(mono), 1.0 / samplerate)

                                    raw_levels = []
                                    for low, high in self._bands:
                                        idx = np.where((freqs >= low) & (freqs < high))[0]
                                        if len(idx) > 0:
                                            # Energy in band
                                            val = float(np.mean(fft_vals[idx]))
                                        else:
                                            val = 0.0
                                        raw_levels.append(val)

                                    # Boost & dynamic compression for natural dancing soundbars
                                    # Sensitivities tailored per frequency band
                                    multipliers = [1.2, 1.4, 2.0, 3.2, 5.0]
                                    new_levels = []
                                    for i in range(5):
                                        scaled = math.log1p(raw_levels[i] * multipliers[i]) * 0.75
                                        scaled = max(0.0, min(1.0, scaled))
                                        # Fast attack (immediate bounce), smooth exponential decay
                                        if scaled > self._current_levels[i]:
                                            smooth = scaled
                                        else:
                                            smooth = self._current_levels[i] * 0.82 + scaled * 0.18
                                        new_levels.append(smooth)

                                    self._current_levels = new_levels
                                    self.levels_updated.emit(new_levels)
                                captured = True
                except Exception:
                    captured = False

            # Fallback to pycaw peak meter if soundcard failed or speaker changed
            if not captured and self.running:
                try:
                    if HAS_PYCAW:
                        spk = AudioUtilities.GetSpeakers()
                        meter = spk._dev.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
                        meter_info = ctypes.cast(meter, ctypes.POINTER(IAudioMeterInformation))
                        while self.running:
                            peak = meter_info.GetPeakValue()
                            # Simulate 5-bar rhythm from live peak amplitude
                            t = time.time()
                            sim = [
                                max(0.0, min(1.0, peak * (1.1 + 0.3 * math.sin(t * 12)))),
                                max(0.0, min(1.0, peak * (1.3 + 0.4 * math.sin(t * 15 + 1)))),
                                max(0.0, min(1.0, peak * (1.0 + 0.3 * math.sin(t * 18 + 2)))),
                                max(0.0, min(1.0, peak * (0.8 + 0.4 * math.sin(t * 22 + 3)))),
                                max(0.0, min(1.0, peak * (0.6 + 0.3 * math.sin(t * 25 + 4)))),
                            ]
                            self._current_levels = sim
                            self.levels_updated.emit(sim)
                            time.sleep(0.03)
                except Exception:
                    pass

            time.sleep(0.5)

    def stop(self):
        self.running = False
