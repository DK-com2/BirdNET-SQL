import math
import os
import librosa
import numpy as np
import matplotlib.pyplot as plt
import librosa.display


PROJECT_PATH = os.getenv("PROJECT_PATH")


def save_spectrogram(signal, sampling_rate, filename, data_type="extracted"):
    print(signal)
    duration = math.floor(librosa.get_duration(signal, sampling_rate))
    D = np.abs(librosa.stft(signal, n_fft=2048))
    print(len(signal), sampling_rate, duration)
    DB = librosa.amplitude_to_db(D, ref=np.max)
    plt.figure()  ##figsize=(duration, 5))
    librosa.display.specshow(
        data=DB, sr=sampling_rate, x_axis="time", y_axis="linear", fmax=100
    )
    plt.ylim(0, 1500)

    subfolder = (
        "extracted_spectrogram" if data_type == "extracted" else "test_spectrogram"
    )

    plt.savefig(f"{PROJECT_PATH}/data/audio/{subfolder}/{filename}.png")
    plt.close()


# if __name__ == "__main__":
#     file_path = "data/audio/test/オオタカ①202303070600my4305-4311.mp3"
#     filename = os.path.basename(file_path).replace(".mp3", "")
#     sample_rate = librosa.get_samplerate(file_path)
#     sig, rate = librosa.load(
#         file_path,
#         sr=sample_rate,
#         mono=True,
#         res_type="kaiser_fast",
#     )
#     save_spectrogram(sig, sample_rate, filename)
