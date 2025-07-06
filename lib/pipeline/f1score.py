from fileinput import filename
import json
import os
import numpy as np
from tensorflow import keras
import pandas as pd
import argparse
import warnings

warnings.filterwarnings("ignore")


parser = argparse.ArgumentParser(description="Extract audio of length of 3 seconds")
parser.add_argument(
    "--name",
    default="all_birds",
)


args = parser.parse_args()
model_id = args.name

PROJECT_PATH = os.getenv("PROJECT_PATH")
all_result = []
TEST_DIR = f"{PROJECT_PATH}/data/audio/test"
train = pd.read_excel(f"{PROJECT_PATH}/data/train.xlsx")
SPECIES_FILE = os.getenv("SPECIES_FILE")
SPECIES_COLUMN = os.getenv("SPECIES_COLUMN")

for path in os.listdir(TEST_DIR):
    file_name = path.replace(".mp3", "")
    file_basename = file_name.replace("_normalized", "").replace("_denoised", "")
    y_true_file_name = train[
        train["path"].str.contains(file_basename, na=False, regex=True)
    ]
    y_pred_file_name = pd.read_csv(
        f"{PROJECT_PATH}/model/{model_id}/{file_name}.BirdNET.results.csv"
    )

    species = open(SPECIES_FILE, "r", encoding="utf-8")
    species_true_label = json.load(species)
    for english_species_name, values in species_true_label.items():
        japanese_species_name = values.get("japanese_name")
        y_true_df = y_true_file_name[
            y_true_file_name[SPECIES_COLUMN] == japanese_species_name
        ]
        y_pred_df = y_pred_file_name[
            y_pred_file_name["Common name"] == english_species_name
        ]

        if len(y_true_df) > 0:  # print(y_true_df, y_pred_file_name)
            start_time = []
            true_label = []
            memo = []

            y_true_df["start_seconds"] = [
                int(s.split("m")[0]) * 60 + int(s.split("m")[1].replace("s", ""))
                for s in y_true_df["start_time"]
            ]

            y_true_df["end_seconds"] = [
                int(e.split("m")[0]) * 60 + int(e.split("m")[1].replace("s", ""))
                for e in y_true_df["end_time"]
            ]
            y_pred_df["start_seconds"] = [
                int(s.split("m")[0]) * 60 + int(s.split("m")[1].replace("s", ""))
                for s in y_pred_df["Start (s)"]
            ]
            y_pred_df["end_seconds"] = [
                int(e.split("m")[0]) * 60 + int(e.split("m")[1].replace("s", ""))
                for e in y_pred_df["End (s)"]
            ]

            total_time = pd.DataFrame(data={"start_time": np.arange(0, 59 * 60 + 59)})

            for k, v in y_true_df.iterrows():
                for t in np.arange(v["start_seconds"], v["end_seconds"] + 1):
                    # print(v["original_species"])
                    start_time.append(t)
                    true_label.append(1)
                    memo.append(
                        f"{v['original_species']}; {v['備考１']}; {v['備考２']}; {v['備考３']} "
                    )

            data = {"start_time": start_time, "true_label": true_label, "memo": memo}
            encoded_result = pd.DataFrame(data)

            if any(encoded_result.duplicated()):
                print("ラベルデータに重複あります")
                encoded_result = encoded_result.drop_duplicates()

            y_true_df = total_time.merge(
                encoded_result, how="left", on="start_time"
            ).fillna(0)

            y_pred_df = total_time.merge(
                y_pred_df, how="left", left_on="start_time", right_on="start_seconds"
            ).fillna(0)[["start_time", "Confidence"]]

            print(
                file_name,
                "for target",
                english_species_name,
                len(y_true_df),
                len(y_pred_df),
            )

            # compared_result = y_true_df.merge(y_pred_df, on="start_time")
            # if os.path.exists(f"{PROJECT_PATH}/model_result/{file_name}") is False:
            #     os.makedirs(f"{PROJECT_PATH}/model_result/{file_name}/target/{english_species_name}")

            # if (
            #     os.path.exists(
            #         f"{PROJECT_PATH}/model_result/{file_name}/target/{english_species_name}"
            #     )
            #     is False
            # ):
            #     os.makedirs(f"{PROJECT_PATH}/model_result/{file_name}/target/{english_species_name}")

            # y_true_df.to_csv(
            #     f"{PROJECT_PATH}/model_result/{file_name}/target/{english_species_name}/{model_id}_y_true.csv",
            #     index=False,
            # )
            # y_pred_df.to_csv(
            #     f"{PROJECT_PATH}/model_result/{file_name}/target/{english_species_name}/{model_id}_y_pred.csv",
            #     index=False,
            # )
            # compared_result.to_csv(
            #     f"{PROJECT_PATH}/model_result/{file_name}/target/{english_species_name}/{model_id}_target_result.csv",
            #     index=False,
            # )

            f1_score_metric = keras.metrics.F1Score(threshold=0.1)
            f1_score_metric.update_state(
                y_true_df[["true_label"]], y_pred_df[["Confidence"]]
            )
            f1_score = f1_score_metric.result()
            precision_metric = keras.metrics.Precision(thresholds=0.1)
            precision_metric.update_state(
                y_true_df[["true_label"]], y_pred_df[["Confidence"]]
            )
            precision = precision_metric.result()
            recall_metric = keras.metrics.Recall(thresholds=0.1)
            recall_metric.update_state(
                y_true_df[["true_label"]], y_pred_df[["Confidence"]]
            )
            recall = recall_metric.result()

            all_result.append(
                {
                    "file_name": file_name,
                    "species": japanese_species_name,
                    "F1_score": f1_score.numpy(),
                    "Precision": precision.numpy(),
                    "Recall": recall.numpy(),
                }
            )

        else:
            print(file_name, "の正解ラベルがない")

pd.DataFrame(all_result).to_csv(f"{PROJECT_PATH}/model/{model_id}/results.csv")
