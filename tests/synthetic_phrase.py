"""PCM timing fixtures only: never synthetic evidence of recognized words/syllables."""
import io
import wave


def wav(rate=48000, bits=16, duration=8, channels=1):
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(bits // 8)
        w.setframerate(rate)
        w.writeframes(b'\x00' * (round(rate * duration) * channels * (bits // 8)))
    return out.getvalue()
