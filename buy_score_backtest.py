"""
Buy-Score backtest -- does the recommendation predict future price drops?

For each (game, date) pair in the historical data we recompute the Buy-Score
using ONLY data available at that date (no look-ahead). Then we measure how
much the price actually dropped over the next `horizon` days. If the score
is informative, "Excellent Buy" recommendations should be followed by small
drops (the buy was justified) and "Avoid" recommendations by large drops
(the score correctly told you to wait).

Score formula mirrors includes/logic.php getBuyScore() exactly:
  * Price Score 0..100 from current vs (min, midpoint) of historical range.
  * Review Score 0..100 = positive-review percentage.
  * Sentiment-adaptive blend (review weight rises with positivity).

    python buy_score_backtest.py --horizon 60
"""
from __future__ import annotations

import os
import glob
import re
import argparse
import pandas as pd


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

LABELS = [
    (85, 100, "Excellent Buy"),
    (70,  84, "Good Value"),
    (55,  69, "Fair Deal"),
    (35,  54, "Wait a Bit"),
    ( 0,  34, "Avoid"),
]


def bucket(score: float) -> str:
    for lo, hi, name in LABELS:
        if lo <= score <= hi:
            return name
    return "Avoid"


def buy_score(current: float, hist_prices: pd.Series, pos_pct: float) -> float:
    """Port of includes/logic.php getBuyScore. Inputs are restricted to data
    available at the evaluation date (point-in-time, no look-ahead)."""
    if current <= 0 or len(hist_prices) == 0:
        return 100.0

    mn, mx = float(hist_prices.min()), float(hist_prices.max())
    avg = (mn + mx) / 2.0

    if current <= mn:
        ps = 100.0
    elif current > avg:
        ps = 20.0
    else:
        ps = 20.0 + ((avg - current) / max(0.01, avg - mn)) * 80.0

    rs = pos_pct  # 0..100

    if   pos_pct >= 95: rw, pw = 0.75, 0.25
    elif pos_pct >= 80: rw, pw = 0.65, 0.35
    elif pos_pct >= 65: rw, pw = 0.55, 0.45
    elif pos_pct >= 50: rw, pw = 0.45, 0.55
    elif pos_pct >= 30: rw, pw = 0.35, 0.65
    else:               rw, pw = 0.25, 0.75

    return rs * rw + ps * pw


VALIDATION_FILE = os.path.join(os.path.dirname(__file__), "validation_appids.txt")


def load_validation_set() -> set | None:
    """Appids of the fixed Buy-Score validation subset. The live portal tracks
    the full catalogue under data/, but the headline backtest figure quoted in
    the project (Spearman r = -0.66 over ~1.7k samples) is pinned to this fixed
    set so it stays reproducible as the catalogue grows. Returns None if the
    manifest is absent."""
    if not os.path.exists(VALIDATION_FILE):
        return None
    ids = set()
    with open(VALIDATION_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                ids.add(line)
    return ids or None


def list_games(only: set | None = None) -> dict:
    games: dict = {}
    for p in glob.glob(os.path.join(DATA_DIR, "*_prices.csv")):
        m = re.match(r"(.+)_([0-9]+)_prices\.csv", os.path.basename(p))
        if not m: continue
        games.setdefault(m.group(2), {"name": m.group(1)})["prices"] = p
    for r in glob.glob(os.path.join(DATA_DIR, "*_reviews.csv")):
        m = re.match(r"(.+)_([0-9]+)_reviews\.csv", os.path.basename(r))
        if not m: continue
        games.setdefault(m.group(2), {"name": m.group(1)})["reviews"] = r
    games = {k: v for k, v in games.items() if "prices" in v and "reviews" in v}
    if only is not None:
        games = {k: v for k, v in games.items() if k in only}
    return games


def load_game(g: dict):
    pr = pd.read_csv(g["prices"], parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
    rv = pd.read_csv(g["reviews"], parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
    pr.columns = [c.strip().lower() for c in pr.columns]
    rv.columns = [c.strip().lower() for c in rv.columns]
    total = (rv["positive_reviews"] + rv["negative_reviews"]).clip(lower=1)
    rv["pct"] = rv["positive_reviews"] / total * 100.0
    return pr, rv


def backtest(horizon_days: int = 60, warmup: int = 3, min_per_bucket: int = 30,
             only: set | None = None):
    rows = []
    games = list_games(only=only)
    for appid, g in games.items():
        try:
            pr, rv = load_game(g)
        except Exception:
            continue
        if len(pr) < warmup + 2:
            continue

        for i in range(warmup, len(pr) - 1):
            d   = pr.loc[i, "date"]
            now = float(pr.loc[i, "price"])
            if now < 100:                       # drop free/promo points; missed% is unstable when current ~ 0
                continue
            hist = pr.loc[:i, "price"]

            past_rv = rv[rv["date"] <= d]
            pct = float(past_rv.iloc[-1]["pct"]) if len(past_rv) else 70.0

            future = pr[(pr["date"] > d) & (pr["date"] <= d + pd.Timedelta(days=horizon_days))]
            if len(future) == 0:
                continue
            min_fut = float(future["price"].min())
            missed_pct = (now - min_fut) / now * 100.0
            missed_pct = max(-100.0, min(100.0, missed_pct))   # clip price-went-up tail

            s = buy_score(now, hist, pct)
            rows.append((appid, g["name"], d, now, s, bucket(s), missed_pct))

    if not rows:
        print("no data"); return

    df = pd.DataFrame(rows, columns=["appid", "name", "date", "price", "score",
                                     "bucket", "missed_savings_pct"])

    scope = "full catalogue" if only is None else f"validation set ({len(only)} titles)"
    print(f"\nBuy-Score backtest -- does the score predict future price drops?")
    print(f"scope = {scope}")
    print(f"horizon = {horizon_days} days, warmup = {warmup} price points")
    print(f"{df['appid'].nunique()} games, {len(df)} evaluated (game, date) samples\n")

    print(f"{'recommendation':<16}{'n':>6}{'mean missed%':>16}{'median%':>10}"
          f"{'drop>=5% rate':>16}")
    print("-" * 64)
    for _, _, name in LABELS:
        sub = df[df["bucket"] == name]
        if len(sub) < min_per_bucket:
            print(f"{name:<16}{len(sub):>6}   (too few samples)")
            continue
        m  = sub["missed_savings_pct"].mean()
        md = sub["missed_savings_pct"].median()
        hit = (sub["missed_savings_pct"] >= 5).mean() * 100
        print(f"{name:<16}{len(sub):>6}{m:>15.2f}%{md:>9.2f}%{hit:>14.1f}%")

    corr = df[["score", "missed_savings_pct"]].corr().iloc[0, 1]
    p_spearman = df[["score", "missed_savings_pct"]].corr("spearman").iloc[0, 1]
    print(f"\nPearson  r(score, missed_savings) = {corr:+.4f}")
    print(f"Spearman r(score, missed_savings) = {p_spearman:+.4f}")
    print("Expectation if the score is informative: NEGATIVE "
          "(higher score -> smaller future drop)")

    out = os.path.join(os.path.dirname(__file__), "buy_score_backtest_results.csv")
    df.to_csv(out, index=False)
    print(f"\nPer-sample detail saved to {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=60)
    ap.add_argument("--warmup",  type=int, default=3)
    ap.add_argument("--all", action="store_true",
                    help="backtest the full catalogue instead of the fixed validation set")
    args = ap.parse_args()
    only = None if args.all else load_validation_set()
    backtest(horizon_days=args.horizon, warmup=args.warmup, only=only)
