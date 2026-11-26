"""Generate a deterministic synthetic retail / supply-chain order dataset.

All data is randomly generated with a fixed seed. It does not come from any
real company and the numbers are not real-world metrics.
"""
import numpy as np
import pandas as pd

SEED = 42
N_ORDERS = 4000
OUT = "data/orders.csv"

REGIONS = ["Northeast", "Midwest", "South", "West"]
CHANNELS = ["Online", "Retail", "Wholesale"]
CATEGORIES = {
    # category: (unit_price_range, unit_cost_ratio_range)
    "Electronics": ((120, 900), (0.55, 0.75)),
    "Furniture": ((80, 600), (0.50, 0.70)),
    "Apparel": ((15, 120), (0.35, 0.55)),
    "Grocery": ((3, 40), (0.60, 0.80)),
    "Office Supplies": ((5, 150), (0.40, 0.60)),
}


def main() -> None:
    rng = np.random.default_rng(SEED)
    categories = list(CATEGORIES)
    order_dates = pd.to_datetime("2025-01-01") + pd.to_timedelta(
        rng.integers(0, 365, N_ORDERS), unit="D"
    )
    category = rng.choice(categories, N_ORDERS, p=[0.22, 0.18, 0.25, 0.20, 0.15])
    price_lo_hi = np.array([CATEGORIES[c][0] for c in category])
    cost_lo_hi = np.array([CATEGORIES[c][1] for c in category])
    unit_price = np.round(rng.uniform(price_lo_hi[:, 0], price_lo_hi[:, 1]), 2)
    cost_ratio = rng.uniform(cost_lo_hi[:, 0], cost_lo_hi[:, 1])
    unit_cost = np.round(unit_price * cost_ratio, 2)
    units = rng.integers(1, 12, N_ORDERS)

    # Fulfilment: promised 5 days out; actual lead time varies by region.
    region = rng.choice(REGIONS, N_ORDERS)
    base_lead = {"Northeast": 3.5, "Midwest": 4.2, "South": 4.8, "West": 5.1}
    lead = np.array([rng.poisson(base_lead[r]) for r in region])
    promised = order_dates + pd.to_timedelta(5, unit="D")
    ship_date = order_dates + pd.to_timedelta(lead, unit="D")

    returned = rng.random(N_ORDERS) < 0.06

    df = pd.DataFrame(
        {
            "order_id": [f"SO-{100000 + i}" for i in range(N_ORDERS)],
            "order_date": order_dates.strftime("%Y-%m-%d"),
            "ship_date": ship_date.strftime("%Y-%m-%d"),
            "promised_date": promised.strftime("%Y-%m-%d"),
            "region": region,
            "channel": rng.choice(CHANNELS, N_ORDERS, p=[0.45, 0.35, 0.20]),
            "category": category,
            "units": units,
            "unit_price": unit_price,
            "unit_cost": unit_cost,
            "is_returned": returned.astype(int),
        }
    )
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(df)} orders, "
          f"{df['order_date'].min()} to {df['order_date'].max()}")


if __name__ == "__main__":
    main()
