from __future__ import annotations

import argparse
import random
from pathlib import Path

import pandas as pd

FIRST_NAMES = ["Ali", "Ayesha", "Fatima", "Hamza", "Hassan", "Mariam", "Noor", "Omar"]
CITIES = ["Lahore", "Karachi", "Islamabad", "Dubai", "Abu Dhabi", "Sharjah"]
STATUSES = ["active", "inactive", "pending"]
GENERATOR_VERSION = "1.0.0"


def generate(rows: int, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    records = []
    for index in range(rows):
        customer_id = index + 1
        name = f" {rng.choice(FIRST_NAMES)} {rng.choice(['Khan', 'Nawaz', 'Ahmed', 'Ali'])} "
        email = f"customer{customer_id}@example.com"
        age: int | str | None = rng.randint(18, 75)
        if index % 97 == 0:
            email = "invalid-email"
        if index % 113 == 0:
            age = "unknown"
        if index % 127 == 0:
            name = "N/A"
        records.append(
            {
                "customer_id": customer_id,
                "name": name,
                "email": email,
                "age": age,
                "city": rng.choice(CITIES),
                "status": rng.choice(STATUSES),
                "created_at": f"2026-{rng.randint(1, 9):02d}-{rng.randint(1, 28):02d}",
            }
        )
    frame = pd.DataFrame.from_records(records)
    duplicate_count = min(max(rows // 100, 1), len(frame))
    return pd.concat([frame, frame.head(duplicate_count)], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("sample_data/customers.csv"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate(args.rows, args.seed).to_csv(args.output, index=False)
    print(f"Wrote {args.output} with {args.rows} generated rows plus controlled duplicates.")


if __name__ == "__main__":
    main()
