import argparse
import json
import os
import unicodedata

import librosa
import noisereduce as nr
import numpy as np
import soundfile as sf
from narwhals import Boolean

parser = argparse.ArgumentParser(description="Extract audio of length of 3 seconds")
parser.add_argument(
    "--normalization",
    default=False,
)
parser.add_argument(
    "--denoise",
    default=False,
)

args = parser.parse_args()
is_normalized = args.normalization
is_denoised = args.denoise

PROJECT_PATH = os.getenv("PROJECT_PATH")


def normalize(y, sample_rate):
    return librosa.util.normalize(y)
    # return librosa.pcen(
    #     y * (2**31),
    #     sr=sample_rate,
    #     gain=1.1,
    #     hop_length=512,
    #     bias=2,
    #     power=0.5,
    #     time_constant=0.8,
    #     eps=1e-06,
    #     max_size=2,
    # )


def reconstruct_audio(frames, frame_length, hop_length):
    """Reconstructs an audio signal from framed data.

    Args:
        frames (np.ndarray): The framed audio data (output of librosa.util.frame).
        frame_length (int): The length of each frame.
        hop_length (int): The hop length used for framing.

    Returns:
        np.ndarray: The reconstructed audio signal.
    """

    n_frames = frames.shape[0]
    signal_length = (
        frame_length + (n_frames - 1) * hop_length
    )  # Calculate signal length
    print("signal length: ", signal_length)
    reconstructed_signal = np.zeros(signal_length)

    for i in range(n_frames):
        frame = frames[i, :]
        start = i * hop_length
        reconstructed_signal[start : start + frame_length] += frame

    # Windowing compensation (important!):
    window = librosa.filters.get_window(
        "hann", frame_length
    )  # Or the window used during framing
    for i in range(n_frames):
        start = i * hop_length
        reconstructed_signal[start : start + frame_length] *= window

    return reconstructed_signal


def normalize_by_window(signal, frame_length, hop_length):
    frames = librosa.util.frame(
        signal, frame_length=frame_length, hop_length=hop_length, axis=0
    )
    print("frame shape:", frames.shape)
    normalized_frames = normalize(
        frames,
    )

    # print(normalized_frames)

    reconstructed_signal = reconstruct_audio(
        normalized_frames, frame_length=frame_length, hop_length=hop_length
    )
    print(reconstructed_signal.shape)
    return reconstructed_signal


def normalize_test_audio():
    test_files = [
        unicodedata.normalize("NFC", f)
        for f in os.listdir(f"{PROJECT_PATH}/data/audio/test")
    ]
    print("TEST_FILES:", len(test_files))

    for file in test_files:
        filepath = os.path.join(f"{PROJECT_PATH}/data/audio/test", file)
        sample_rate = librosa.get_samplerate(filepath)
        filename = file.replace(".mp3", "")
        sig = []

        if (
            (is_denoised == "True" and "denoise" not in filename)
            or (is_normalized == "True" and "normalized" not in filename)
            or (is_normalized == "True" or is_denoised == "True")
        ):
            sig, rate = librosa.load(
                filepath,
                sr=sample_rate,
                mono=True,
                res_type="kaiser_fast",
            )

        if is_denoised == "True" and "denoise" not in filename:
            filename += "_denoised"
            if os.path.exists(
                f"{PROJECT_PATH}/data/audio/test/{filename}.mp3",
            ):
                continue
            sig = nr.reduce_noise(
                sig,
                sr=sample_rate,
            )

        if is_normalized == "True" and "normalized" not in filename:
            filename += "_normalized"
            if os.path.exists(
                f"{PROJECT_PATH}/data/audio/test/{filename}.mp3",
            ):
                continue
            sig = normalize(sig, sample_rate=sample_rate)

        if is_normalized == "True" or is_denoised == "True":
            if os.path.exists(
                f"{PROJECT_PATH}/data/audio/test/{filename}.mp3",
            ):
                continue
            sf.write(
                f"{PROJECT_PATH}/data/audio/test/{filename}.mp3",
                sig,
                sample_rate,
            )


if __name__ == "__main__":
    normalize_test_audio()
