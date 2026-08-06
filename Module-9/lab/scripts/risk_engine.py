#!/usr/bin/env python3
"""
Infrastructure Risk Score Engine — Module 9

Calculates a weighted composite risk score from CPU, memory, disk,
and error rate metrics. Outputs a formatted report and comparison chart.

Usage:
  python3 risk_engine.py
"""

import os
import sys
from dataclasses import dataclass

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


@dataclass
class RiskInput:
    cpu: float
    memory: float
    disk: float
    error_rate: float


@dataclass
class RiskResult:
    score: float
    severity: str
    color: str
    emoji: str
    breakdown: dict


def calculate_risk(inputs: RiskInput, weights: dict = None) -> RiskResult:
    if weights is None:
        weights = {"cpu": 0.20, "memory": 0.20, "disk": 0.30, "error_rate": 0.30}

    values = {
        "cpu": max(0, min(100, inputs.cpu)),
        "memory": max(0, min(100, inputs.memory)),
        "disk": max(0, min(100, inputs.disk)),
        "error_rate": max(0, min(100, inputs.error_rate)),
    }

    score = sum(values[k] * weights[k] for k in weights)
    score = round(score, 1)

    if score < 40:
        severity, color, emoji = "Low", "Green", "🟢"
    elif score < 71:
        severity, color, emoji = "Medium", "Yellow", "🟡"
    else:
        severity, color, emoji = "High", "Red", "🔴"

    breakdown = {k: round(values[k] * weights[k], 1) for k in weights}

    return RiskResult(score=score, severity=severity, color=color, emoji=emoji,
                      breakdown=breakdown)


def print_scenario(name, inputs, result):
    print(f"\n{'─' * 50}")
    print(f"  Scenario: {name}")
    print(f"{'─' * 50}")
    print(f"  Inputs:  CPU={inputs.cpu}%  Memory={inputs.memory}%  "
          f"Disk={inputs.disk}%  Errors={inputs.error_rate}%")
    print(f"  Score:   {result.score} — {result.emoji} {result.color} ({result.severity})")
    print(f"  Breakdown:")
    print(f"    CPU contribution:        {result.breakdown['cpu']}")
    print(f"    Memory contribution:     {result.breakdown['memory']}")
    print(f"    Disk contribution:       {result.breakdown['disk']}")
    print(f"    Error rate contribution: {result.breakdown['error_rate']}")


def generate_chart(scenarios):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("\n  ⚠️  matplotlib not installed. Skipping chart generation.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    names = [s[0] for s in scenarios]
    scores = [s[2].score for s in scenarios]
    colors_map = {"Green": "#22c55e", "Yellow": "#eab308", "Red": "#ef4444"}
    bar_colors = [colors_map.get(s[2].color, "#6366f1") for s in scenarios]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(names, scores, color=bar_colors, width=0.5, edgecolor="white", linewidth=2)

    # Zone lines
    ax.axhline(y=40, color="#22c55e", linewidth=1, linestyle="--", alpha=0.5, label="Green threshold")
    ax.axhline(y=70, color="#eab308", linewidth=1, linestyle="--", alpha=0.5, label="Yellow threshold")

    # Score labels on bars
    for bar, score in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                f"{score}", ha="center", va="bottom", fontweight="bold", fontsize=12)

    ax.set_title("Infrastructure Risk Score Comparison", fontsize=14, fontweight="bold")
    ax.set_ylabel("Risk Score (0–100)")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()

    filename = os.path.join(OUTPUT_DIR, "risk_comparison.png")
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"\n  📊 Chart saved: {filename}")


def main():
    print("=" * 50)
    print("  Infrastructure Risk Score Engine")
    print("  Weights: CPU=0.2  Memory=0.2  Disk=0.3  Errors=0.3")
    print("=" * 50)

    scenarios = [
        ("Healthy System",
         RiskInput(cpu=25, memory=40, disk=55, error_rate=1), None),
        ("Disk Pressure",
         RiskInput(cpu=30, memory=45, disk=88, error_rate=5), None),
        ("Cascading Failure",
         RiskInput(cpu=85, memory=90, disk=97, error_rate=45), None),
    ]

    # Calculate risk for each scenario
    scenarios = [(name, inputs, calculate_risk(inputs)) for name, inputs, _ in scenarios]

    for name, inputs, result in scenarios:
        print_scenario(name, inputs, result)

    generate_chart(scenarios)
    print()


if __name__ == "__main__":
    main()
