"""
permutation_test_h5.py — Permutation test for H5 (Random Forest classifier significance)

Runs a group-aware permutation test (n_perm=1000) to determine whether the
Random Forest classifier's balanced accuracy is significantly above chance (50%).

Usage:
    python analysis/permutation_test_h5.py

Output:
    - Prints p-value and summary statistics
    - Saves results to analysis/permutation_test_results.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT = Path(__file__).parent.parent
METRICS_PATH = PROJECT / "data" / "processed" / "metrics_results.json"
RESULTS_PATH = PROJECT / "analysis" / "permutation_test_results.json"

# ── The 8 locked metrics ──────────────────────────────────────────────────
METRIC_KEYS = [
    "word_length",
    "sentence_length",
    "sentence_length_var",
    "ttr",
    "mtld",
    "conj_freq",
    "paragraph_length",
    "paragraph_length_var",
]


def load_metrics():
    """Load the pre-computed metrics from metrics.py output."""
    with open(METRICS_PATH) as f:
        data = json.load(f)
    return data


def build_dataframe(data):
    """Convert raw metrics JSON into a tidy DataFrame with one row per (prompt, condition)."""
    rows = []
    for entry in data:
        pid = entry["prompt_id"]
        for condition, m in entry.items():
            if condition == "prompt_id":
                continue
            if m is None:  # missing data for this condition
                continue
            row = {"prompt_id": pid, "condition": condition}
            for k in METRIC_KEYS:
                row[k] = m[k]
            rows.append(row)
    return pd.DataFrame(rows)


def run_permutation_test(X, y, groups, n_perm=1000, random_state=42):
    """
    Run a group-aware permutation test for the Random Forest classifier.

    Parameters:
    -----------
    X : array-like, shape (n_samples, n_features)
        Feature matrix
    y : array-like, shape (n_samples,)
        Binary labels (0=AI, 1=Human)
    groups : array-like, shape (n_samples,)
        Group IDs for StratifiedGroupKFold
    n_perm : int
        Number of permutations
    random_state : int
        Random seed for reproducibility

    Returns:
    --------
    dict with keys:
        - observed_balanced_accuracy: float
        - permuted_balanced_accuracies: list of float
        - p_value: float
        - n_permutations: int
    """
    rng = np.random.RandomState(random_state)

    # Set up classifier and CV
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        class_weight="balanced",
    )
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Compute observed balanced accuracy
    fold_bal_accs = []
    for train_idx, test_idx in cv.split(X_scaled, y, groups):
        X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        fold_bal_accs.append(balanced_accuracy_score(y_test, y_pred))

    observed_bal_acc = np.mean(fold_bal_accs)
    print(f"Observed balanced accuracy: {observed_bal_acc:.4f}")

    # Pre-compute group indices for faster permutation
    unique_groups = np.unique(groups)
    group_masks = {g: groups == g for g in unique_groups}

    # Run permutations
    permuted_bal_accs = []
    for i in range(n_perm):
        if (i + 1) % 100 == 0:
            print(f"  Running permutation {i + 1}/{n_perm}...")

        # Shuffle labels within each group (prompt_id)
        # This preserves the group structure while breaking the signal
        y_perm = y.copy()
        for g in unique_groups:
            mask = group_masks[g]
            y_perm[mask] = rng.permutation(y_perm[mask])

        # Evaluate on permuted data
        fold_bal_accs_perm = []
        for train_idx, test_idx in cv.split(X_scaled, y_perm, groups):
            X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
            y_train, y_test = y_perm[train_idx], y_perm[test_idx]
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)
            fold_bal_accs_perm.append(balanced_accuracy_score(y_test, y_pred))

        permuted_bal_accs.append(np.mean(fold_bal_accs_perm))

    # Compute p-value (one-tailed: observed > permuted)
    permuted_bal_accs = np.array(permuted_bal_accs)
    p_value = np.mean(permuted_bal_accs >= observed_bal_acc)

    return {
        "observed_balanced_accuracy": float(observed_bal_acc),
        "permuted_balanced_accuracies": permuted_bal_accs.tolist(),
        "p_value": float(p_value),
        "n_permutations": n_perm,
        "permuted_mean": float(np.mean(permuted_bal_accs)),
        "permuted_std": float(np.std(permuted_bal_accs)),
    }


def main():
    print("Loading metrics...")
    data = load_metrics()
    df = build_dataframe(data)

    # Prepare features and labels
    human_mask = df["condition"] == "human"
    ai_mask = ~human_mask

    # Keep only human and AI observations
    keep = human_mask | ai_mask
    df_sub = df[keep].copy()

    X = df_sub[METRIC_KEYS].values
    y = (df_sub["condition"] == "human").astype(int).values  # 1=Human, 0=AI
    groups = df_sub["prompt_id"].values

    print(f"Total samples: {len(y)}")
    print(f"Human samples: {np.sum(y == 1)}")
    print(f"AI samples: {np.sum(y == 0)}")

    # Run permutation test
    print("\nRunning permutation test (n_perm=1000)...")
    results = run_permutation_test(X, y, groups, n_perm=1000, random_state=42)

    # Print results
    print("\n" + "=" * 60)
    print("PERMUTATION TEST RESULTS (H5)")
    print("=" * 60)
    print(f"Observed balanced accuracy: {results['observed_balanced_accuracy']:.4f}")
    print(f"Permuted mean ± SD: {results['permuted_mean']:.4f} ± {results['permuted_std']:.4f}")
    print(f"P-value (one-tailed): {results['p_value']:.4f}")
    print(f"Significant at α=0.05: {'YES' if results['p_value'] < 0.05 else 'NO'}")
    print("=" * 60)

    # Save results
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {RESULTS_PATH}")

    return results


if __name__ == "__main__":
    main()
