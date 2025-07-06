import argparse
from email.mime import audio
import json
import os
import unicodedata
from numpy import ndarray
import pandas as pd
import librosa
import soundfile as sf
import numpy as np
import noisereduce as nr
from save_spectrogram import save_spectrogram
import shutil

parser = argparse.ArgumentParser(description="Extract audio of length of 3 seconds")
parser.add_argument(
    "--normalization",
    default=False,
)
parser.add_argument(
    "--fmax",
    default=15000,
)
parser.add_argument(
    "--fmin",
    default=0,
)

parser.add_argument(
    "--denoise",
    default=False,
)

args = parser.parse_args()
is_normalized = args.normalization
fmax = args.fmax
fmin = args.fmin
is_denoised = args.denoise

PROJECT_PATH = os.getenv("PROJECT_PATH")
SPECIES_FILE = os.getenv("SPECIES_FILE")
SPECIES_COLUMN = os.getenv("SPECIES_COLUMN")


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


def extract_audio():
    species = open(SPECIES_FILE, "r", encoding="utf-8")
    species_label = json.load(species)

    shutil.rmtree(f"{PROJECT_PATH}/data/audio/extracted")
    os.makedirs(f"{PROJECT_PATH}/data/audio/extracted")

    for english_species_name, values in species_label.items():
        japanese_species_name = values.get("japanese_name")
        train_label = pd.read_excel(
            f"{PROJECT_PATH}/data/train.xlsx", sheet_name="merged"
        )

        if not os.path.exists(
            f"{PROJECT_PATH}/data/audio/extracted/{english_species_name}"
        ):
            os.makedirs(f"{PROJECT_PATH}/data/audio/extracted/{english_species_name}")
        if not os.path.exists(
            f"{PROJECT_PATH}/data/audio/train/{english_species_name}"
        ):
            os.makedirs(f"{PROJECT_PATH}/data/audio/train/{english_species_name}")
        if not os.path.exists(
            f"{PROJECT_PATH}/data/audio/extracted_spectrogram/{english_species_name}"
        ):
            os.makedirs(
                f"{PROJECT_PATH}/data/audio/extracted_spectrogram/{english_species_name}"
            )

        filtered_train_label = train_label[
            train_label[SPECIES_COLUMN] == japanese_species_name
        ]
        audio_link_list = filtered_train_label["path"].unique()
        print(f"{english_species_name} 音声ファイル数：{len(audio_link_list)}")
        print("Link list:", audio_link_list)

        audio_key_list = [
            name.split("=")[1].split("&")[0]
            if str(name).startswith("http")
            else str(name)
            for name in audio_link_list
        ]
        print("Key list:", audio_key_list)

        for audio_key, audio_link in zip(audio_key_list, audio_link_list):
            for file in [
                unicodedata.normalize("NFC", f)
                for f in os.listdir(
                    f"{PROJECT_PATH}/data/audio/raw/{english_species_name}"
                )
            ]:
                if not os.path.isdir(
                    f"{PROJECT_PATH}/data/audio/extracted/{english_species_name}"
                ):
                    os.makedirs(
                        f"{PROJECT_PATH}/data/audio/extracted/{english_species_name}",
                        exist_ok=True,
                    )

                if f"{audio_key}" in file:
                    print("FILE NAME:", file)
                    print("AUDIO NAME:", audio_key, audio_link)

                    df_with_same_audio = filtered_train_label[
                        filtered_train_label["path"].str.contains(
                            audio_key, na=False, regex=True
                        )
                    ]
                    print("RECORD_PER_FILE;", len(df_with_same_audio))

                    file_path = os.path.join(
                        f"{PROJECT_PATH}/data/audio/raw/{english_species_name}", file
                    )

                    end_time = 0
                    log = []
                    for col, row in df_with_same_audio.iterrows():
                        previous_end_time = end_time
                        start_time_string = row["start_time"]
                        start_time = int(start_time_string.split("m")[0]) * 60 + int(
                            start_time_string.split("m")[1].replace("s", "")
                        )
                        end_time_string = row["end_time"]
                        end_time = int(end_time_string.split("m")[0]) * 60 + int(
                            end_time_string.split("m")[1].replace("s", "")
                        )
                        print(file_path)
                        sample_rate = librosa.get_samplerate(file_path)
                        if start_time >= end_time:  # or end_time - start_time > 10:
                            # if english_species_name == ""
                            log.append(
                                {
                                    "file_path": file_path,
                                    "start_time": start_time,
                                    "message": "start_time is the same as end_time",
                                }
                            )
                            continue
                        else:
                            sig, rate = librosa.load(
                                file_path,
                                sr=sample_rate,
                                offset=start_time,
                                duration=end_time - start_time,
                                mono=True,
                                res_type="kaiser_fast",
                            )

                            filename = f"{audio_key}_{start_time_string}"

                            if is_denoised == "True":
                                print(
                                    "=========================DENOISE===================="
                                )
                                sig = nr.reduce_noise(sig, sr=sample_rate)
                                filename += "_denoised"

                            if is_normalized == "True":
                                print(
                                    "=========================NORMALIZATION===================="
                                )
                                sig = normalize(sig, sample_rate)
                                filename += "_normalized"

                            if not os.path.isfile(
                                f"{PROJECT_PATH}/data/audio/extracted/{english_species_name}/{filename}.mp3"
                            ):
                                sf.write(
                                    f"{PROJECT_PATH}/data/audio/extracted/{english_species_name}/{filename}.mp3",
                                    sig,
                                    sample_rate,
                                )

                            if not os.path.isfile(
                                f"{PROJECT_PATH}/data/audio/extracted_spectrogram/{filename}.png"
                            ):
                                save_spectrogram(sig, sample_rate, filename)

                    log = pd.DataFrame(log)
                    log.to_csv("log.csv")


if __name__ == "__main__":
    extract_audio()
