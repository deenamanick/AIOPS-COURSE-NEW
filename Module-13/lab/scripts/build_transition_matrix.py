#!/usr/bin/env python3
"""
Build a state transition matrix from a state log CSV.

Reads consecutive state pairs, counts transitions, normalises to
probabilities, saves the matrix as CSV, and generates a heatmap.

Usage:
  python3 build_transition_matrix.py
  python3 build_transition_matrix.py --input data/state_log.csv --output data/transition_matrix.csv
  python3 build_transition_matrix.py --no-plot
"""

import argparse
import csv
import os
import sys
import numpy as np

STATES = ["Healthy", "Degraded", "Critical", "Failed"]
SCRIPT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "output")


def load_states(filepath: str) -> list[str]:
    """Load the state column from a state log CSV."""
    with open(filepath) as f:
        return [row["state"] for row in csv.DictReader(f)]


def count_transitions(states: list[str]) -> np.ndarray:
    """Count state-to-state transitions and return a count matrix."""
    n = len(STATES)
    counts = np.zeros((n, n), dtype=int)
    state_to_idx = {s: i for i, s in enumerate(STATES)}

    for prev, cur in zip(states, states[1:]):
        if prev in state_to_idx and cur in state_to_idx:
            counts[state_to_idx[prev]][state_to_idx[cur]] += 1

    return counts


def normalise(counts: np.ndarray, smoothing: float = 0.0) -> np.ndarray:
    """Normalise count matrix to row-stochastic probability matrix.

    Args:
        counts: raw transition count matrix
        smoothing: Laplace smoothing factor (0 = no smoothing)
    """
    smoothed = counts.astype(float) + smoothing
    row_sums = smoothed.sum(axis=1, keepdims=True)
    # Avoid division by zero for rows with no observations
    row_sums[row_sums == 0] = 1.0
    return smoothed / row_sums


def save_matrix_csv(matrix: np.ndarray, filepath: str):
    """Save the transition matrix to CSV with state labels."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([""] + STATES)
        for i, state in enumerate(STATES):
            writer.writerow([state] + [f"{v:.4f}" for v in matrix[i]])


def print_matrix(title: str, matrix: np.ndarray, fmt: str = ".4f"):
    """Pretty-print a matrix to the terminal."""
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")
    header = "            " + "  ".join(f"{s:>8s}" for s in STATES)
    print(header)
    for i, state in enumerate(STATES):
        row = "  ".join(f"{matrix[i][j]:{fmt}}" for j in range(len(STATES)))
        print(f"  {state:10s}  {row}")
    print(f"{'═' * 60}")


def generate_heatmap(matrix: np.ndarray, output_path: str):
    """Generate a colour-coded heatmap of the transition matrix."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  ⚠️  matplotlib not installed. Skipping heatmap.")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")

    # Annotate cells
    for i in range(len(STATES)):
        for j in range(len(STATES)):
            val = matrix[i][j]
            colour = "white" if val > 0.5 else "black"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    color=colour, fontsize=12, fontweight="bold")

    ax.set_xticks(range(len(STATES)))
    ax.set_yticks(range(len(STATES)))
    ax.set_xticklabels(STATES)
    ax.set_yticklabels(STATES)
    ax.set_xlabel("To State", fontsize=12)
    ax.set_ylabel("From State", fontsize=12)
    ax.set_title("State Transition Probability Matrix", fontsize=14, fontweight="bold")
    plt.colorbar(im, label="Probability")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"  📊 Heatmap saved: {output_path}")


def compute_steady_state(matrix: np.ndarray, iterations: int = 1000) -> np.ndarray:
    """Compute the steady-state distribution via power iteration."""
    vec = np.ones(len(STATES)) / len(STATES)
    for _ in range(iterations):
        vec = vec @ matrix
    return vec


def main():
    parser = argparse.ArgumentParser(description="Build a Markov transition matrix")
    parser.add_argument("--input", default=os.path.join(DATA_DIR, "state_log.csv"),
                        help="Path to state log CSV")
    parser.add_argument("--output", default=os.path.join(DATA_DIR, "transition_matrix.csv"),
                        help="Path to save the transition matrix CSV")
    parser.add_argument("--smoothing", type=float, default=0.0,
                        help="Laplace smoothing factor (default: 0, try 1.0 for sparse data)")
    parser.add_argument("--no-plot", action="store_true",
                        help="Skip heatmap generation")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"❌ {args.input} not found. Run generate_state_data.py first.")

    states = load_states(args.input)
    print(f"Loaded {len(states)} state observations from {args.input}")

    counts = count_transitions(states)
    print_matrix(f"Transition Counts ({len(states) - 1} transitions)", counts, fmt="5d")

    matrix = normalise(counts, smoothing=args.smoothing)
    print_matrix("Transition Probability Matrix", matrix)

    # Validate rows sum to 1.0
    for i, state in enumerate(STATES):
        row_sum = matrix[i].sum()
        if abs(row_sum - 1.0) > 0.01:
            print(f"  ⚠️  Row {state} sums to {row_sum:.4f} (expected 1.0)")

    save_matrix_csv(matrix, args.output)
    print(f"\n  ✅ Matrix saved to {args.output}")

    if not args.no_plot:
        heatmap_path = os.path.join(OUTPUT_DIR, "transition_heatmap.png")
        generate_heatmap(matrix, heatmap_path)

    # Steady state
    steady = compute_steady_state(matrix)
    print(f"\n  📈 Steady-state distribution:")
    for i, state in enumerate(STATES):
        print(f"     {state:10s}: {steady[i]:.3f} ({steady[i]*100:.1f}%)")
    print()


if __name__ == "__main__":
    main()
