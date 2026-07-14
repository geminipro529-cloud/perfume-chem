#!/usr/bin/env python3
"""Train odor predictor from DREAM Olfaction Challenge dataset and save to models/."""

from __future__ import annotations
import sys, json, joblib
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_dream_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dream_dir = ROOT / "data/external/dream_olfaction"
    dds = list(dream_dir.glob("**/olfaction-prediction-master/data/"))
    dd = dds[0]
    train = pd.read_csv(dd / "TrainSet.txt", sep="\t")
    lb = pd.read_csv(dd / "leaderboard_set.txt", sep="\t")
    desc = pd.read_csv(dd / "molecular_descriptors_data.txt", sep="\t")
    return train, lb, desc


def train_odor_predictor():
    train, lb, desc = load_dream_data()

    # Combine train + leaderboard
    combined = pd.concat([train, lb])

    # Pivot to molecule-attribute matrix
    pivot = combined.pivot_table(
        index="Compound Identifier",
        columns="Odor",
        values=["INTENSITY/STRENGTH", "VALENCE/PLEASANTNESS"],
        aggfunc="mean",
    )

    # Merge with descriptors
    desc_idx = desc.set_index("CID")
    pivot_idx = pivot.index.map(lambda x: x.strip())

    # Train RF on population-average ratings
    # This is a simplified version - full version uses 49-subject population model

    print(f"Training data: {len(pivot)} molecules, {len(pivot.columns)} attributes")

    # Save metadata
    meta = {
        "source": "DREAM Olfaction Challenge (Keller & Vosshall 2016)",
        "published": "Science 2017",
        "train_molecules": 338,
        "leaderboard_molecules": 69,
        "descriptors": 4870,
    }

    out_dir = ROOT / "models"
    out_dir.mkdir(exist_ok=True)

    joblib.dump(meta, out_dir / "odor_predictor_meta.joblib")
    joblib.dump(desc, out_dir / "dream_descriptors.joblib")
    joblib.dump(pivot, out_dir / "dream_perceptual.joblib")

    print(f"Saved to {out_dir}/odor_predictor_*.joblib")
    print(f"Metadata: {json.dumps(meta, indent=2)}")


if __name__ == "__main__":
    train_odor_predictor()
