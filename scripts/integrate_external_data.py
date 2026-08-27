#!/usr/bin/env python3
"""
Integrate external perfume data sources into the engine data pipeline.

Sources:
  1. Pyrfume (Arctander, Leffingwell, GoodScents, IFRA 2019, Dravnieks)
  2. DREAM Olfaction Challenge (476 molecules, 21 perceptual attributes)
  3. HuggingFace molecular-odor-dataset (50-label odor classifier)

Usage:
    python scripts/integrate_external_data.py --source pyrfume
    python scripts/integrate_external_data.py --source dream
    python scripts/integrate_external_data.py --source huggingface
    python scripts/integrate_external_data.py --source all
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Pyrfume Integration ──────────────────────────────────────────────────


def integrate_pyrfume() -> dict:
    """Load Pyrfume datasets and extract ODT/VP/material data.

    Datasets available:
        arctander_1960, leffingwell, goodscents, ifra_2019,
        dravnieks_1985, flavornet, superscent, keller_2016
    """
    results = {"source": "pyrfume", "datasets": {}}
    try:
        import pyrfume

        # List available archives
        archives = pyrfume.list_archives()
        results["available"] = len(archives)

        key_archives = [
            "arctander_1960",
            "leffingwell",
            "goodscents",
            "ifra_2019",
            "dravnieks_1985",
            "flavornet",
        ]

        for archive in key_archives:
            if archive not in archives:
                continue
            try:
                molecules = pyrfume.load_data(f"{archive}/molecules.csv")
                results["datasets"][archive] = {
                    "molecules": len(molecules),
                    "columns": list(molecules.columns),
                }
                # Save to data/external/
                out_path = ROOT / f"data/external/pyrfume_{archive}.csv"
                molecules.to_csv(out_path, index=False)
                results["datasets"][archive]["saved"] = str(out_path)
            except Exception as e:
                results["datasets"][archive] = {"error": str(e)}

    except ImportError:
        results["error"] = "pyrfume not installed. Run: pip install pyrfume"
    except Exception as e:
        results["error"] = str(e)

    return results


# ── DREAM Olfaction Challenge Integration ────────────────────────────────


def integrate_dream() -> dict:
    """Load DREAM Olfaction Challenge dataset.

    Contains:
        - TrainSet.txt: 338 training molecules + perceptual ratings
        - leaderboard_set.txt: 69 molecules
        - molecular_descriptors_data.txt: 4884 Dragon descriptors per molecule
        - 21 perceptual attributes per molecule × 49 subjects
    """
    results = {"source": "dream_olfaction", "datasets": {}}

    dream_dir = ROOT / "data/external/dream_olfaction"
    if not dream_dir.exists():
        return {
            "error": f"DREAM data not found at {dream_dir}. Download from github.com/dream-olfaction/olfaction-prediction"
        }

    import pandas as pd

    # Find the actual data directory (may be nested)
    data_dirs = list(dream_dir.glob("**/data/"))
    if not data_dirs:
        # Try the master archive subdirectory
        data_dirs = list(dream_dir.glob("**/olfaction-prediction-master/data/"))

    if data_dirs:
        data_dir = data_dirs[0]
        results["data_dir"] = str(data_dir)

        # Load training set
        train_file = data_dir / "TrainSet.txt"
        if train_file.exists():
            train = pd.read_csv(train_file, sep="\t")
            results["datasets"]["TrainSet"] = {
                "molecules": len(train),
                "columns": list(train.columns)[:10],
            }

        # Load molecular descriptors
        desc_file = data_dir / "molecular_descriptors_data.txt"
        if desc_file.exists():
            desc = pd.read_csv(desc_file, sep="\t", nrows=5)
            results["datasets"]["descriptors"] = {
                "features": desc.shape[1],
                "first_features": list(desc.columns)[:20],
            }

    return results


# ── HuggingFace Molecular Odor Dataset ───────────────────────────────────


def integrate_huggingface_odor() -> dict:
    """Download HuggingFace molecular-odor-dataset.

    Contains: SMILES + 50 binary odor labels (fruity, green, sweet, etc.)
    Source: HuggingFace Hari5115/molecular-odor-dataset
    """
    results = {"source": "huggingface_odor", "datasets": {}}

    try:
        import pandas as pd
        import requests

        base_url = (
            "https://huggingface.co/datasets/Hari5115/molecular-odor-dataset/resolve/main/data"
        )

        for split in ["train.csv", "val.csv", "test.csv", "labels.csv"]:
            url = f"{base_url}/{split}"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                out_path = ROOT / f"data/external/hf_odor_{split}"
                out_path.write_bytes(resp.content)
                df = (
                    pd.read_csv(out_path)
                    if split != "labels.csv"
                    else pd.read_csv(out_path, header=None)
                )
                results["datasets"][split] = {
                    "rows": len(df),
                    "columns": len(df.columns) if hasattr(df, "columns") else 1,
                    "saved": str(out_path),
                }

    except ImportError:
        results["error"] = "requests not available"
    except Exception as e:
        results["error"] = str(e)

    return results


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Integrate external perfume data sources")
    parser.add_argument(
        "--source",
        "-s",
        choices=["pyrfume", "dream", "huggingface", "all"],
        default="all",
        help="Which data source to integrate",
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    all_results = {}

    if args.source in ("pyrfume", "all"):
        all_results["pyrfume"] = integrate_pyrfume()
    if args.source in ("dream", "all"):
        all_results["dream"] = integrate_dream()
    if args.source in ("huggingface", "all"):
        all_results["huggingface"] = integrate_huggingface_odor()

    if args.json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))
    else:
        for source, results in all_results.items():
            print(f"\n=== {source.upper()} ===")
            if "error" in results:
                print(f"  ERROR: {results['error']}")
            else:
                for ds_name, ds_data in results.get("datasets", {}).items():
                    if "error" in ds_data:
                        print(f"  {ds_name}: ERROR - {ds_data['error']}")
                    else:
                        print(
                            f"  {ds_name}: {ds_data.get('molecules', ds_data.get('rows', '?'))} entries"
                        )


if __name__ == "__main__":
    main()
