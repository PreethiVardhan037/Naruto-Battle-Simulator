"""Turn raw AI-vs-AI battle logs into clean, analysis-ready tables.

Expected raw input: one row per battle (CSV), columns:
  battle_id, ai_a, ai_b, depth_a, depth_b, winner, turns,
  hp_a_end, hp_b_end, chakra_a_end, chakra_b_end,
  decision_time_a, decision_time_b, nodes_a, nodes_b
`winner` is "A", "B" or "draw". Time in seconds.

Usage: python experiments/prepare_results.py raw.csv processed/
Requires: pandas
"""
import sys
from pathlib import Path
import pandas as pd

REQUIRED = ["battle_id", "ai_a", "ai_b", "winner", "turns",
            "hp_a_end", "hp_b_end"]
NUMERIC = ["turns", "hp_a_end", "hp_b_end", "chakra_a_end", "chakra_b_end",
           "decision_time_a", "decision_time_b", "nodes_a", "nodes_b"]


def load_and_clean(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = df.drop_duplicates(subset="battle_id")
    for col in NUMERIC:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["winner"] = df["winner"].astype(str).str.strip().str.upper().replace({"DRAW": "draw"})
    df = df[df["winner"].isin(["A", "B", "draw"])]
    df = df.dropna(subset=["turns", "hp_a_end", "hp_b_end"])
    df = df[(df["turns"] > 0) & (df["hp_a_end"] >= 0) & (df["hp_b_end"] >= 0)]
    return df.reset_index(drop=True)


def _label(ai: pd.Series, depth: pd.Series) -> pd.Series:
    d = depth.fillna(0).astype(int)
    return ai.where(d == 0, ai + " (d" + d.astype(str) + ")")


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (battle, player) so both sides can be aggregated together."""
    rows = []
    for side, other in (("a", "b"), ("b", "a")):
        depth = df.get(f"depth_{side}", pd.Series(0, index=df.index))
        part = pd.DataFrame({
            "battle_id": df["battle_id"],
            "agent": _label(df[f"ai_{side}"], depth),
            "opponent": _label(df[f"ai_{other}"],
                               df.get(f"depth_{other}", pd.Series(0, index=df.index))),
            "win": (df["winner"] == side.upper()).astype(int),
            "draw": (df["winner"] == "draw").astype(int),
            "turns": df["turns"],
            "hp_end": df[f"hp_{side}_end"],
            "chakra_end": df.get(f"chakra_{side}_end"),
            "decision_time": df.get(f"decision_time_{side}"),
            "nodes": df.get(f"nodes_{side}"),
        })
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


def summarize(long_df: pd.DataFrame) -> pd.DataFrame:
    g = long_df.groupby(["agent", "opponent"])
    out = g.agg(battles=("battle_id", "count"),
                win_rate=("win", "mean"),
                draw_rate=("draw", "mean"),
                avg_hp_end=("hp_end", "mean"),
                avg_chakra_end=("chakra_end", "mean"),
                avg_turns=("turns", "mean"),
                avg_decision_time=("decision_time", "mean"),
                avg_nodes=("nodes", "mean")).reset_index()
    # 95% normal-approximation CI half-width for win rate
    out["win_rate_ci95"] = 1.96 * (out["win_rate"] * (1 - out["win_rate"]) / out["battles"]) ** 0.5
    return out.round(4)


if __name__ == "__main__":
    raw, outdir = sys.argv[1], Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    clean = load_and_clean(raw)
    long_df = to_long(clean)
    clean.to_csv(outdir / "battles_clean.csv", index=False)
    long_df.to_csv(outdir / "battles_long.csv", index=False)
    summarize(long_df).to_csv(outdir / "summary.csv", index=False)
    print(f"{len(clean)} clean battles -> {outdir}")
