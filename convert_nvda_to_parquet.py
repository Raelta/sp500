import os
import pandas as pd

INPUT_FILE = "NVDA.csv"
OUTPUT_FILE = "nvda_data_6yr.parquet"


def main():
    if not os.path.exists(INPUT_FILE):
        raise SystemExit(f"{INPUT_FILE} not found")

    print(f"Reading {INPUT_FILE}...")
    df = pd.read_csv(
        INPUT_FILE,
        dtype={
            "Date": "string",
            "Time": "string",
            "Open": "float64",
            "High": "float64",
            "Low": "float64",
            "Close": "float64",
            "Volume": "int64",
        },
    )
    print(f"  rows: {len(df):,}")

    df["date"] = pd.to_datetime(
        df["Date"] + " " + df["Time"], format="%Y/%m/%d %H:%M"
    )
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("date").reset_index(drop=True)

    df.to_parquet(OUTPUT_FILE, index=False)
    size_mb = os.path.getsize(OUTPUT_FILE) / 1024 / 1024
    print(
        f"Wrote {OUTPUT_FILE} ({size_mb:.1f} MB, {len(df):,} rows, "
        f"{df['date'].min()} → {df['date'].max()})"
    )


if __name__ == "__main__":
    main()
