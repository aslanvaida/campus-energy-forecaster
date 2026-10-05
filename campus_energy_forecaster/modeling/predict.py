"""Score a CSV (same columns as the test file) with a saved model; writes id,prediction."""
import argparse
import pickle
from pathlib import Path

import pandas as pd

from campus_energy_forecaster.config import MODEL_PATH, PROCESSED_DATA_DIR, TEST_CSV
from campus_energy_forecaster.modeling import models  # noqa: F401  (classes needed to unpickle)


def main(input_path=TEST_CSV, model_path=MODEL_PATH, output_path=PROCESSED_DATA_DIR / "predictions.csv"):
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    df = pd.read_csv(input_path)
    out = pd.DataFrame({"id": df["id"], "prediction": model.predict(df)})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"saved {output_path} {out.shape}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=TEST_CSV)
    ap.add_argument("--model", type=Path, default=MODEL_PATH)
    ap.add_argument("--output", type=Path, default=PROCESSED_DATA_DIR / "predictions.csv")
    a = ap.parse_args()
    main(a.input, a.model, a.output)
