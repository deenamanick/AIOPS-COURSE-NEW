# 03 — Markov State Modeling

This lesson takes the `state_log.csv` from Lesson 02 and builds a **transition probability matrix**. You'll count every state-to-state transition, normalize the counts into probabilities, visualize the matrix as a heatmap, and save the result for the forecasting engine.

---

## The Process

```text
state_log.csv ──► Count Transitions ──► Normalize ──► transition_matrix.csv
     720 rows         (4×4 counts)      (4×4 probs)       (saved to disk)
                                             │
                                             ▼
                                    output/transition_heatmap.png
```

---

## Step 1: Build the Transition Matrix

```bash
cd Module-13/lab
python3 scripts/build_transition_matrix.py
```

Expected output:

```text
═══════════════════════════════════════════════════════════════
  Transition Counts (719 transitions from 720 data points)
═══════════════════════════════════════════════════════════════
              Healthy  Degraded  Critical  Failed
  Healthy         460        68        12       2
  Degraded         32        64        18       4
  Critical          5        10        27      16
  Failed            2         1         1       8

═══════════════════════════════════════════════════════════════
  Transition Probability Matrix
═══════════════════════════════════════════════════════════════
              Healthy  Degraded  Critical  Failed
  Healthy       0.849     0.125     0.022   0.004
  Degraded      0.271     0.542     0.153   0.034
  Critical      0.086     0.172     0.466   0.276
  Failed        0.167     0.083     0.083   0.667

  ✅ Matrix saved to data/transition_matrix.csv
  📊 Heatmap saved to output/transition_heatmap.png
═══════════════════════════════════════════════════════════════
```

---

## Step 2: Interpret the Matrix

Read each row as: "Given I am in this state, here is the probability distribution of where I'll be in the next time step."

### Row-by-Row Analysis

**Healthy row** `[0.849, 0.125, 0.022, 0.004]`:
- 84.9% chance of staying healthy — the system is stable.
- 12.5% chance of degrading — corresponds to daily load patterns.
- 2.2% chance of jumping to critical — rare but possible (sudden spikes).
- 0.4% chance of direct failure — almost never happens from healthy.

**Degraded row** `[0.271, 0.542, 0.153, 0.034]`:
- 27.1% chance of recovering — many degradations self-resolve.
- 54.2% chance of staying degraded — the most likely outcome.
- 15.3% chance of worsening to critical — load continues to increase.
- 3.4% chance of failing directly — uncommon but tracked.

**Critical row** `[0.086, 0.172, 0.466, 0.276]`:
- Only 8.6% chance of full recovery — rare from critical.
- 17.2% chance of improving to degraded — partial recovery.
- 46.6% chance of staying critical — most common.
- **27.6% chance of failure** — this is the key number for prediction.

**Failed row** `[0.167, 0.083, 0.083, 0.667]`:
- 16.7% chance of full recovery — represents auto-remediation (Module 10).
- 66.7% chance of remaining failed — without intervention, failure persists.

---

## Step 3: Visualize with a Heatmap

The script generates a heatmap in `output/transition_heatmap.png`:

```python
def generate_heatmap(matrix, states, output_path):
    """Generate a color-coded heatmap of the transition matrix."""
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix.values, cmap="YlOrRd", vmin=0, vmax=1)

    # Annotate each cell with the probability
    for i in range(len(states)):
        for j in range(len(states)):
            val = matrix.iloc[i, j]
            color = "white" if val > 0.5 else "black"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    color=color, fontsize=12, fontweight="bold")

    ax.set_xticks(range(len(states)))
    ax.set_yticks(range(len(states)))
    ax.set_xticklabels(states)
    ax.set_yticklabels(states)
    ax.set_xlabel("To State", fontsize=12)
    ax.set_ylabel("From State", fontsize=12)
    ax.set_title("State Transition Probability Matrix", fontsize=14, fontweight="bold")
    plt.colorbar(im, label="Probability")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
```

The heatmap makes patterns immediately visible:
- **Diagonal dominance**: the darkest cells are on the diagonal, meaning self-transitions (staying in the same state) are most common. This is expected for a stable system.
- **Upper-right gradient**: probabilities increase toward the Failed column as you move down (from Healthy to Failed).
- **Bottom-left cells**: recovery probabilities—nonzero, indicating auto-remediation is working.

---

## Matrix Properties

### Every Row Sums to 1.0

```python
for state in states:
    assert abs(matrix.loc[state].sum() - 1.0) < 1e-6
```

If a row doesn't sum to 1.0, you have a normalization bug.

### Absorbing States

A state is **absorbing** if the system can never leave it: `P(state → state) = 1.0`. In our matrix, no state is absorbing—even Failed has recovery paths. This is because we designed auto-remediation in Module 10.

If Failed were absorbing (`P(Failed → Failed) = 1.0`), the long-run prediction for any system would be: "eventually it will fail and stay failed." That's mathematically true but operationally useless.

### Steady-State Distribution

Over infinite time, the system converges to a **steady-state distribution** regardless of starting state:

```python
# Power iteration to find steady state
v = np.array([0.25, 0.25, 0.25, 0.25])
for _ in range(1000):
    v = v @ matrix.values
print(f"Steady state: {v}")
# Approximately: [0.65, 0.18, 0.10, 0.07]
```

This tells you: in the long run, the system spends ~65% of its time Healthy, ~18% Degraded, ~10% Critical, and ~7% Failed. If the steady-state Failed percentage is too high, you need better remediation.

---

## Handling Edge Cases

| Edge Case | Problem | Solution |
|---|---|---|
| Zero transitions for a pair | Division by zero during normalization | Add Laplace smoothing: add 1 to every count before normalizing |
| Only one state observed | Matrix is all zeros except one row | Need more diverse historical data |
| Very few data points | Probabilities are unreliable | Require minimum 100 data points (Module uses 720) |
| Time step inconsistency | Some gaps are 1 hour, others 5 hours | Resample data to uniform intervals before counting |

---

## Validation Checklist

- [ ] `transition_matrix.csv` generated with 4×4 probabilities.
- [ ] Every row sums to 1.0 (within floating-point tolerance).
- [ ] Heatmap saved to `output/transition_heatmap.png` and visually reviewed.
- [ ] Diagonal dominance confirmed (self-transitions are largest per row).
- [ ] Critical → Failed probability identified as the key forecasting input.
- [ ] Steady-state distribution computed and interpreted.

In the next lesson, you'll use this matrix to predict failure probability over a time horizon and trigger automated remediation.
