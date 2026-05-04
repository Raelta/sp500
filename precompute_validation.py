import os
import pickle
import sys

sys.path.append(os.getcwd())

from src.data_loader import (
    DATASETS,
    _compute_yearly_size_vol,
    _expected_minutes,
    _validation_pickle_path,
    load_data_uncached,
)
from src.data_validator import validate_dataset


def precompute(symbol, include_extended_hours):
    info = DATASETS[symbol]
    suffix = "extended" if include_extended_hours else "regular"
    print(f"\n=== {symbol} ({info['path']}) — {suffix} hours ===")

    if not os.path.exists(info["path"]):
        print(f"  SKIP: parquet not found at {info['path']}")
        return False

    df = load_data_uncached(symbol, include_extended_hours=include_extended_hours)
    print(f"  Loaded {len(df):,} rows")

    val_report = validate_dataset(
        df, expected_minutes_per_day=_expected_minutes(symbol, include_extended_hours)
    )
    val_report["yearly_size_vol"] = _compute_yearly_size_vol(df)

    out = _validation_pickle_path(symbol, include_extended_hours)
    with open(out, "wb") as f:
        pickle.dump(val_report, f)
    print(f"  Wrote {out}")
    return True


def main():
    print("Pre-computing validation reports for all registered datasets...")
    any_done = False
    for symbol, info in DATASETS.items():
        # Always emit the canonical pickle (regular hours for extended-hours
        # datasets, full data otherwise).
        if precompute(symbol, include_extended_hours=False):
            any_done = True
        # For datasets that *can* show extended hours, also emit the full pickle.
        if info.get("has_extended_hours"):
            precompute(symbol, include_extended_hours=True)

    if not any_done:
        print("No datasets were processed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
