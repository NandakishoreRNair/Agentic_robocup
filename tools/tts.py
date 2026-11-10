import io
import wave

import sounddevice as sd
import soundfile as sf
from piper import PiperVoice

VOICE_PATH = "models/en_US-lessac-medium.onnx"
voice = PiperVoice.load(VOICE_PATH)   # load once, it takes ~1 s


def say(text):
    """Turn text into speech with Piper and play it."""
    print(f"Robot: {text}")

    buffer = io.BytesIO()                   # in-memory WAV, no file on disk
    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    buffer.seek(0)
    audio, sample_rate = sf.read(buffer)
    sd.play(audio, sample_rate)
    sd.wait()                               # block until playback is done


if __name__ == "__main__":
    say("Hello, I am your guide robot. Please follow me to the laboratory.")