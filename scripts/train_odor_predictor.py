#!/usr/bin/env python3
"""Prepare DREAM observations or benchmark measured dose endpoints explicitly."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DREAM_DIR = ROOT / "data/external/dream_olfaction/olfaction-prediction-master"
DREAM_TARGETS = (
    "INTENSITY/STRENGTH", "VALENCE/PLEASANTNESS", "BAKERY", "SWEET", "FRUIT",
    "FISH", "GARLIC", "SPICES", "COLD", "SOUR", "BURNT", "ACID", "WARM",
    "MUSKY", "SWEATY", "AMMONIA/URINOUS", "DECAYED", "WOOD", "GRASS", "FLOWER",
    "CHEMICAL",
)


def load_dream_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dream_dir = ROOT / "data/external/dream_olfaction"
    dds = list(dream_dir.glob("**/olfaction-prediction-master/data/"))
    dd = dds[0]
    train = pd.read_csv(dd / "TrainSet.txt", sep="\t")
    lb = pd.read_csv(dd / "leaderboard_set.txt", sep="\t")
    desc = pd.read_csv(dd / "molecular_descriptors_data.txt", sep="\t")
    return train, lb, desc


def prepare_dream_doses(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate source ratings at each molecule and declared dilution.

    Log dilution is a source preparation ratio, not liquid mass ppm or gas ppm.
    Missing endpoint observations remain missing, never zero-imputed.
    """
    frame = frame.copy()
    cid = "Compound Identifier"
    if frame[cid].isna().any():
        raise ValueError("Missing molecule identity")
    frame[cid] = frame[cid].astype(str).str.strip()
    if frame[cid].eq("").any():
        raise ValueError("Empty molecule identity")

    def log_dilution(value):
        try:
            numerator, denominator = map(float, str(value).replace(",", "").split("/"))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid source dilution: {value}") from exc
        if (not np.isfinite([numerator, denominator]).all()
                or numerator <= 0 or denominator <= 0 or numerator > denominator):
            raise ValueError(f"Invalid source dilution: {value}")
        return float(np.log10(numerator / denominator))

    frame["log10_source_dilution"] = frame["Dilution"].map(log_dilution)
    for target in DREAM_TARGETS:
        frame[target] = pd.to_numeric(frame.get(target, np.nan), errors="coerce")
        frame[target] = frame[target].where(np.isfinite(frame[target]))
    return frame.groupby([cid, "log10_source_dilution"], as_index=False)[
        list(DREAM_TARGETS)].mean()


def benchmark_dream_dose(frame: pd.DataFrame, *, folds: int = 5,
                         seed: int = 20260909) -> dict:
    """CID-disjoint OOF diagnostic of identity-free dose-only regressions.

    All three degrees are prespecified; no best-model selection on test folds.
    Polynomial coefficients use ascending powers of log10(source dilution).
    """
    grouped = prepare_dream_doses(frame)
    cid_key = "Compound Identifier"
    cids = np.array(sorted(grouped[cid_key].unique()))
    if folds < 2 or folds > len(cids):
        raise ValueError("Need at least two folds and at least one molecule per fold")
    rng = np.random.default_rng(seed)
    partitions = np.array_split(rng.permutation(cids), folds)
    split = [{"train_cids": sorted(set(cids) - set(test)),
              "test_cids": sorted(test.tolist())} for test in partitions]
    result = {
        "schema": "dream_dose_only_benchmark_v1", "seed": seed, "folds": split,
        "source_rows": len(frame), "molecules": len(cids),
        "molecule_dose_rows": len(grouped), "target_names": list(DREAM_TARGETS),
        "feature": "log10_source_dilution", "endpoints": {},
        "formula_prediction_authority": False,
        "limitations": [
            "Identity-free dose-only diagnostic, not a full perfume predictor.",
            "No molecular features, Dragon descriptors, leaderboard rows or mixture labels used.",
            "Source dilution is not calibrated mass ppm or headspace concentration.",
            "Concentrations were selected per molecule; cross-molecule dose effects may be confounded.",
            "Within-CID dose ordering is more interpretable than cross-CID dose-only associations.",
            "Descriptor endpoints are published derivatives: lineage records 418728 workbook blanks mapped to zero; these are not certified observed-zero ratings.",
            "CID-disjoint out-of-fold evaluation; participant-disjoint generalization untested.",
            "Population means, no participant uncertainty or external study validation.",
            "All model degrees prespecified; no held-out best-model selection.",
        ],
    }
    for target in DREAM_TARGETS:
        observed = grouped.dropna(subset=[target]).reset_index(drop=True)
        endpoint = {"n_observations": len(observed), "models": {}, "fitted_models": {},
                    "label_provenance": (
                        "PUBLISHED_DERIVATIVE_DESCRIPTOR_WITH_SOURCE_BLANK_TO_ZERO_TRANSFORM"
                        if target not in DREAM_TARGETS[:2]
                        else "PUBLISHED_RATING_MISSING_VALUES_EXCLUDED")}
        result["endpoints"][target] = endpoint
        if observed.empty:
            endpoint["status"] = "NO_OBSERVATIONS"
            continue
        y = observed[target].to_numpy(dtype=float)
        x = observed["log10_source_dilution"].to_numpy(dtype=float)
        for name, degree in (("intercept", 0), ("linear", 1), ("quadratic", 2)):
            design = np.vander(x, N=degree + 1, increasing=True)
            prediction = np.full(len(y), np.nan)
            fold_models = []
            for fold_index, fold in enumerate(split):
                train_mask = observed[cid_key].isin(fold["train_cids"]).to_numpy()
                test_mask = observed[cid_key].isin(fold["test_cids"]).to_numpy()
                if not train_mask.any():
                    fold_models.append({"fold": fold_index, "status": "NO_TRAIN_OBSERVATIONS"})
                    continue
                coef, _, rank, _ = np.linalg.lstsq(design[train_mask], y[train_mask], rcond=None)
                prediction[test_mask] = design[test_mask] @ coef
                fold_models.append({"fold": fold_index, "coefficients": coef.tolist(),
                                    "design_rank": int(rank)})
            valid = np.isfinite(prediction)
            errors = prediction[valid] - y[valid]
            pairs = correct = observed_ties = predicted_ties = 0
            for _, molecule in observed.groupby(cid_key):
                if len(molecule) < 2:
                    continue
                low = molecule["log10_source_dilution"].idxmin()
                high = molecule["log10_source_dilution"].idxmax()
                if not valid[low] or not valid[high]:
                    continue
                actual = y[high] - y[low]
                predicted = prediction[high] - prediction[low]
                if abs(actual) <= 1e-10:
                    observed_ties += 1
                    continue
                pairs += 1
                if abs(predicted) <= 1e-10:
                    predicted_ties += 1
                elif np.sign(actual) == np.sign(predicted):
                    correct += 1
            endpoint["models"][name] = {
                "n_oof": int(valid.sum()),
                "mae": float(np.abs(errors).mean()) if len(errors) else None,
                "rmse": float(np.sqrt(np.mean(errors ** 2))) if len(errors) else None,
                "dose_ordering": {"n_pairs": pairs, "correct": correct,
                                  "accuracy": correct / pairs if pairs else None,
                                  "observed_ties_excluded": observed_ties,
                                  "predicted_ties": predicted_ties},
                "fold_models": fold_models,
                "oof_predictions": [
                    {"cid": row[cid_key], "log10_source_dilution": float(x[i]),
                     "observed": float(y[i]),
                     "predicted": float(prediction[i]) if valid[i] else None}
                    for i, row in observed.iterrows()
                ],
            }
            coef, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
            endpoint["fitted_models"][name] = {
                "coefficients": coef.tolist(), "design_rank": int(rank),
                "coefficient_order": "ascending powers of log10_source_dilution",
                "training_log10_range": [float(x.min()), float(x.max())],
                "evaluation": "Full-data fit is not used for reported held-out metrics",
            }
        endpoint["status"] = "EVALUATED"
    return result


def train_odor_predictor(output: Path | None = None):
    """Compatibility entry point: prepare data only; never claim model training."""
    train = pd.read_csv(DREAM_DIR / "data/TrainSet.txt", sep="\t")
    grouped = prepare_dream_doses(train)
    result = {"status": "DATASET_PREPARATION_ONLY", "model_fitted": False,
              "source": "DREAM TrainSet.txt", "source_rows": len(train),
              "molecules": int(grouped["Compound Identifier"].nunique()),
              "molecule_dose_rows": len(grouped), "target_names": list(DREAM_TARGETS)}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({**result, "observations": json.loads(
            grouped.to_json(orient="records"))}, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, indent=2))


@lru_cache(maxsize=1024)
def _native_structure(smiles: str) -> tuple:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski

    molecule = Chem.MolFromSmiles(smiles.strip())
    if molecule is None or molecule.GetNumHeavyAtoms() == 0:
        raise ValueError(f"Invalid component SMILES: {smiles}")
    canonical = Chem.MolToSmiles(molecule, isomericSmiles=True)
    values = (Descriptors.MolWt(molecule), Descriptors.MolLogP(molecule),
              Descriptors.TPSA(molecule), Lipinski.NumHDonors(molecule),
              Lipinski.NumHAcceptors(molecule), Lipinski.RingCount(molecule),
              Lipinski.NumRotatableBonds(molecule),
              sum(atom.GetIsAromatic() for atom in molecule.GetAtoms()) /
              molecule.GetNumHeavyAtoms(), Descriptors.FractionCSP3(molecule),
              molecule.GetNumHeavyAtoms())
    return canonical, values


def dream_mixture_features(components: list[dict]) -> dict:
    """Native molecular features at nominal source-equivalent active fractions.

    Source stocks were mixed in equal volumes: fraction = stock dilution / N.
    Unknown solution densities preclude calling these exact mass fractions.
    """
    if not components:
        raise ValueError("At least one molecular component required")
    fractions = np.array([float(row["nominal_fraction"]) for row in components])
    if not np.isfinite(fractions).all() or np.any(fractions <= 0) or fractions.sum() > 1 + 1e-12:
        raise ValueError("Finite positive nominal fractions with total <=1 required")
    structures = [_native_structure(str(row["smiles"])) for row in components]
    values = np.array([row[1] for row in structures], dtype=float)
    weights = fractions / fractions.sum()
    weighted = np.sum(values * weights[:, None], axis=0)
    spread = np.sqrt(np.sum((values - weighted) ** 2 * weights[:, None], axis=0))
    names = ["mw", "logp", "tpsa", "hbd", "hba", "rings", "rotatable",
             "aromatic_fraction", "fraction_csp3", "heavy_atoms"]
    blind = np.concatenate([values.mean(axis=0), values.std(axis=0), [len(components)]])
    blind_names = [f"mean_{name}" for name in names] + [f"std_{name}" for name in names] + ["component_count"]
    aware = np.concatenate([blind, weighted, spread,
                            [np.log10(fractions.sum()), np.std(np.log10(fractions))]])
    aware_names = blind_names + [f"weighted_mean_{name}" for name in names] + [
        f"weighted_std_{name}" for name in names] + ["log10_nominal_total", "std_log10_nominal_fraction"]
    # Set rather than multiset also keeps repeated-component representations together.
    palette = json.dumps(sorted({row[0] for row in structures}), separators=(",", ":"))
    return {"palette": palette, "blind": blind.tolist(), "aware": aware.tolist(),
            "blind_names": blind_names, "aware_names": aware_names}


def prepare_dream_mixtures(component_table: pd.DataFrame, stimulus_table: pd.DataFrame,
                           ratings: pd.DataFrame, smiles_by_cid: dict) -> dict:
    """Exact stimulus/component joins; exclude an entire unsupported mixture."""
    components = component_table.copy()
    stimuli = stimulus_table.copy()
    for table in (components, stimuli):
        table["id"] = table["id"].astype(str)
        if table["id"].duplicated().any():
            raise ValueError("Duplicate source definition ID")
    if ratings["stimulus"].astype(str).duplicated().any():
        raise ValueError("Duplicate rated stimulus; aggregate protocol needed")
    cmap = components.set_index("id").to_dict("index")
    smap = stimuli.set_index("id")["components"].to_dict()
    rows, excluded = [], []
    targets = [column for column in ratings if column != "stimulus"]
    for _, rating in ratings.iterrows():
        stimulus = str(rating["stimulus"])
        try:
            ids = [key.strip() for key in str(smap[stimulus]).split(";")]
            members = []
            solvents = []
            for key in ids:
                component = cmap[key]
                smiles = smiles_by_cid[str(component["CID"])]
                dilution = float(component["dilution"])
                if not np.isfinite(dilution) or not 0 < dilution <= 1:
                    raise ValueError("Invalid source stock dilution")
                members.append({"smiles": smiles, "nominal_fraction": dilution / len(ids)})
                solvents.append((_native_structure(smiles)[0], str(component["solvent"])))
            features = dream_mixture_features(members)
        except (KeyError, ValueError, TypeError) as exc:
            excluded.append({"stimulus": stimulus, "reason": str(exc)})
            continue
        labels = {target: pd.to_numeric(rating[target], errors="coerce") for target in targets}
        labels = {key: float(value) if np.isfinite(value) else None for key, value in labels.items()}
        rows.append({"stimulus": stimulus, "components": members, **features,
                     "solvent_signature": json.dumps(sorted(solvents)), "targets": labels})
    return {"rows": rows, "excluded": excluded, "source_rows": len(ratings), "targets": targets}


def _fit_numeric_ridge(x: np.ndarray, y: np.ndarray, *, alpha: float = 10.) -> dict:
    from sklearn.linear_model import Ridge
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale == 0] = 1.
    estimator = Ridge(alpha=alpha).fit((x - mean) / scale, y)
    return {"feature_mean": mean.tolist(), "feature_scale": scale.tolist(),
            "coefficients": estimator.coef_.tolist(), "intercept": float(estimator.intercept_),
            "feature_min": x.min(axis=0).tolist(), "feature_max": x.max(axis=0).tolist(),
            "alpha": alpha}


def _predict_numeric_ridge(model: dict, x: np.ndarray) -> np.ndarray:
    return ((x - np.array(model["feature_mean"])) / np.array(model["feature_scale"])) @ np.array(
        model["coefficients"]) + model["intercept"]


def benchmark_dream_mixture(component_table: pd.DataFrame, stimulus_table: pd.DataFrame,
                            ratings: pd.DataFrame, smiles_by_cid: dict, *, folds: int = 5,
                            seed: int = 20260909) -> dict:
    """Prespecified alpha=10 ridge comparison with canonical-palette-held-out folds."""
    data = prepare_dream_mixtures(component_table, stimulus_table, ratings, smiles_by_cid)
    rows = data["rows"]
    palettes = sorted({row["palette"] for row in rows})
    if not 2 <= folds <= len(palettes):
        raise ValueError("Insufficient canonical palettes for requested folds")
    order = sorted(palettes, key=lambda value: hashlib.sha256(f"{seed}:{value}".encode()).hexdigest())
    tests = [order[index::folds] for index in range(folds)]
    split = [{"train_palettes": sorted(set(palettes) - set(test)), "test_palettes": test}
             for test in tests]
    result = {"schema": "dream2025_native_mixture_ridge_v1", "status": "EMPIRICAL_SOURCE_BENCHMARK",
              "source_rows": data["source_rows"], "included_rows": len(rows),
              "excluded": data["excluded"], "palettes": len(palettes), "folds": split,
              "seed": seed, "ridge_alpha": 10., "endpoints": {},
              "nominal_fraction_basis": "source stock dilution divided by equal-volume component count",
              "fitted_model": {"schema": "dream2025_native_mixture_ridge_model_v1",
                               "models": {}, "feature_names": rows[0]["aware_names"],
                               "training_palettes": palettes, "training_rows": len(rows)},
              "formula_prediction_authority": False,
              "limitations": [
                  "New source-domain model, not the authors' published model or full-perfume validation.",
                  "Equal component-solution volumes confirmed; nominal fractions are not exact mass fractions or gas concentrations.",
                  "Component stock dilution unit interpretation medium-confidence; solution densities unavailable.",
                  "Solvents retained for paired diagnostics but not encoded; solvent/domain confounding remains.",
                  "Palette-disjoint, not molecule-disjoint: constituent molecules may occur across palettes.",
                  "No personal liking, temporal, body or layering labels and no full-perfume transfer claim.",
                  "Ridge alpha fixed at10, no tuning or clipping on held-out ratings.",
                  "Task2 MIT code notice does not establish dataset redistribution/commercial rights.",
              ]}
    for target in data["targets"]:
        selected = [row for row in rows if row["targets"][target] is not None]
        endpoint = {"n_observations": len(selected), "models": {}}
        result["endpoints"][target] = endpoint
        if not selected:
            endpoint["status"] = "NO_OBSERVATIONS"
            continue
        y = np.array([row["targets"][target] for row in selected])
        for name, key in (("intercept", None), ("dose_blind", "blind"), ("dose_aware", "aware")):
            x = np.array([row[key] for row in selected]) if key else np.zeros((len(y), 1))
            predictions = np.full(len(y), np.nan)
            for fold in split:
                train = np.array([row["palette"] in fold["train_palettes"] for row in selected])
                test = ~train
                if train.any():
                    model = _fit_numeric_ridge(x[train], y[train])
                    predictions[test] = _predict_numeric_ridge(model, x[test])
            valid = np.isfinite(predictions)
            errors = predictions[valid] - y[valid]
            pairs = correct = ties = 0
            pair_details, pair_groups, paired_stimuli = [], set(), set()
            for left in range(len(selected)):
                for right in range(left + 1, len(selected)):
                    a, b = selected[left], selected[right]
                    if (a["palette"] != b["palette"] or a["solvent_signature"] != b["solvent_signature"]
                            or np.allclose(a["aware"], b["aware"], rtol=1e-12, atol=1e-12)
                            or not valid[left] or not valid[right] or abs(y[left] - y[right]) <= 1e-10):
                        continue
                    pairs += 1
                    delta = predictions[left] - predictions[right]
                    pair_groups.add((a["palette"], a["solvent_signature"]))
                    paired_stimuli.update((a["stimulus"], b["stimulus"]))
                    pair_details.append({"left_stimulus": a["stimulus"], "right_stimulus": b["stimulus"],
                                         "observed_difference": float(y[left] - y[right]),
                                         "predicted_difference": float(delta), "palette": a["palette"],
                                         "solvent_signature": a["solvent_signature"]})
                    if abs(delta) <= 1e-10:
                        ties += 1
                    elif np.sign(delta) == np.sign(y[left] - y[right]):
                        correct += 1
            endpoint["models"][name] = {
                "mae": float(np.abs(errors).mean()) if len(errors) else None,
                "rmse": float(np.sqrt(np.mean(errors ** 2))) if len(errors) else None,
                "n_oof": int(valid.sum()),
                "same_solvent_palette_dose_ordering": {"n_pairs": pairs, "correct": correct,
                    "predicted_ties": ties, "accuracy": correct / pairs if pairs else None,
                    "groups": len(pair_groups), "stimuli": len(paired_stimuli), "pairs": pair_details},
                "oof_predictions": [{"stimulus": row["stimulus"], "observed": float(y[i]),
                                     "predicted": float(predictions[i]) if valid[i] else None}
                                    for i, row in enumerate(selected)]}
            if name == "dose_aware":
                result["fitted_model"]["models"][target] = _fit_numeric_ridge(x, y)
        endpoint["status"] = "EVALUATED"
    return result


def predict_dream_mixture(model_json: dict, components: list[dict]) -> dict:
    """Source-domain raw endpoint estimates; no clipping or formula authority."""
    if model_json.get("schema") != "dream2025_native_mixture_ridge_model_v1":
        raise ValueError("Unsupported mixture model schema")
    features = dream_mixture_features(components)
    if model_json["feature_names"] != features["aware_names"]:
        raise ValueError("Mixture model feature schema mismatch")
    x = np.array(features["aware"])
    predictions, out_of_range = {}, set()
    for target, model in model_json["models"].items():
        predictions[target] = float(_predict_numeric_ridge(model, x))
        outside = (x < np.array(model["feature_min"]) - 1e-10) | (x > np.array(model["feature_max"]) + 1e-10)
        out_of_range.update(name for name, flag in zip(features["aware_names"], outside) if flag)
    return {"predictions": predictions, "out_of_range_features": sorted(out_of_range),
            "seen_training_palette": features["palette"] in model_json["training_palettes"],
            "formula_prediction_authority": False, "warnings": [
                "Nominal source-equivalent active fractions, not exact mass ppm or air concentration.",
                "Solvent and delivery transfer unvalidated; unmodeled components invalidate whole-mixture interpretation.",
                "Raw extrapolations are not clipped; feature-range checks are not calibrated uncertainty.",
            ]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--intensity-benchmark", type=Path,
                        help="Reproduce source-bound measured curves, without training legacy predictor")
    modes.add_argument("--dream-dose-benchmark", action="store_true",
                       help="CID-held-out diagnostic of dose-only human endpoint regressions")
    modes.add_argument("--dream-mixture-benchmark", action="store_true",
                       help="Canonical-palette-held-out native structure and nominal concentration ridge")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.dream_mixture_benchmark:
        directory = ROOT / "output/dataset_suitability_20260909"
        repository = directory / "Olfactory-Mixtures-Prediction-2025-1aff2ea1764b8434e703a0eb8c27302ec2910f60"
        component_path = directory / "Task2_TASK2_Component_definition.csv"
        stimulus_path = directory / "Task2_TASK2_Stimulus_definition.csv"
        rating_path = directory / "Task2_TASK2_Train_mixture_Dataset.csv"
        smiles_path = repository / "Task2/Output/Datasets/cid_to_smiles.json"
        result = benchmark_dream_mixture(
            pd.read_csv(component_path, dtype=str), pd.read_csv(stimulus_path, dtype=str),
            pd.read_csv(rating_path), json.loads(smiles_path.read_text(encoding="utf-8")))
        paths = [component_path, stimulus_path, rating_path, smiles_path,
                 repository / "Task2/LICENSE", Path(__file__),
                 ROOT / "docs/research/DREAM_2025_PROTOCOL_CLOSURE_20260909.md",
                 directory / "synapse_data_wiki_632380.json"]
        result["source_hashes"] = {str(path.relative_to(ROOT)): hashlib.sha256(
            path.read_bytes()).hexdigest() for path in paths}
        result["protocol_source"] = "https://www.synapse.org/Synapse:syn64743570/discussion/threadId=12185"
        result["code_source_commit"] = "1aff2ea1764b8434e703a0eb8c27302ec2910f60"
        result["fitted_model"]["source_hashes"] = result["source_hashes"]
        result["fitted_model"]["nominal_fraction_basis"] = result["nominal_fraction_basis"]
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"included": result["included_rows"], "excluded": len(result["excluded"]),
                          "palettes": result["palettes"], "output": str(args.output),
                          "rmse": {target: {name: model["rmse"] for name, model in
                                            result["endpoints"][target]["models"].items()}
                                   for target in ("Intensity", "Pleasantness", "Woody", "Pine", "Citrus")}}, indent=2))
    elif args.dream_dose_benchmark:
        source = DREAM_DIR / "data/TrainSet.txt"
        result = benchmark_dream_dose(pd.read_csv(source, sep="\t"))
        result["source_hashes"] = {str(path.relative_to(ROOT)): hashlib.sha256(
            path.read_bytes()).hexdigest() for path in (
                source, DREAM_DIR / "LICENSE", Path(__file__),
                ROOT / "data/source_manifests/dream_olfaction_fb47cb343cdf.json")}
        result["source_doi"] = "10.1126/science.aal2014"
        result["license_scope"] = "TrainSet.txt and repository LICENSE only; no third-party descriptors"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"molecules": result["molecules"], "output": str(args.output),
                          "endpoints": {target: {name: model["rmse"] for name, model in
                                                  endpoint["models"].items()}
                                        for target, endpoint in result["endpoints"].items()}}, indent=2))
    elif args.intensity_benchmark:
        from engine.dose_response import (
            benchmark_measured_intensity,
            parse_measured_intensity_parameters,
        )

        data_bytes = args.intensity_benchmark.read_bytes()
        data = json.loads(data_bytes)
        parameter_path = ROOT / data["parameter_path"]
        parameter_bytes = parameter_path.read_bytes()
        if hashlib.sha256(parameter_bytes).hexdigest() != data["parameter_sha256"]:
            raise ValueError("Measured parameter source hash mismatch")
        parameters = parse_measured_intensity_parameters(csv.DictReader(
            parameter_bytes.decode("utf-8-sig").splitlines(), delimiter="\t"))
        result = benchmark_measured_intensity(parameters["curves"], data)
        result.update(parameter_sha256=data["parameter_sha256"],
                      observation_sha256=hashlib.sha256(data_bytes).hexdigest(),
                      source_doi=data["source_doi"], license=data["license"],
                      curve_count=len(parameters["curves"]), excluded=parameters["excluded"],
                      source_hashes={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                     for name in ("engine/dose_response.py", "scripts/train_odor_predictor.py")})
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"curve_count": result["curve_count"], "excluded": result["excluded"],
                          "single_rmse": result["single"]["pooled_rmse"],
                          "mixture_mean_group_rmse": {k: v["mean_group_rmse"] for k, v in result["mixtures"].items()},
                          "output": str(args.output)}, indent=2))
    else:
        train_odor_predictor(args.output)
