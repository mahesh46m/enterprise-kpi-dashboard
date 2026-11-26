"""Compute the KPIs defined in metrics/metrics.yml from the synthetic order
data and render a one-page executive dashboard (dashboard.png) plus a
markdown KPI summary (kpi_summary.md).

Run generate_data.py first (or let this script run it for you).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "orders.csv"
METRICS = ROOT / "metrics" / "metrics.yml"


def load_orders() -> pd.DataFrame:
    if not DATA.exists():
        import generate_data  # noqa: PLC0415 - sibling script

        generate_data.main()
    df = pd.read_csv(
        DATA, parse_dates=["order_date", "ship_date", "promised_date"]
    )
    df["gross_sales"] = df["units"] * df["unit_price"]
    df["returned_value"] = df["gross_sales"] * df["is_returned"]
    df["net_revenue"] = df["gross_sales"] - df["returned_value"]
    df["gross_profit"] = (
        (df["unit_price"] - df["unit_cost"]) * df["units"] * (1 - df["is_returned"])
    )
    df["on_time"] = df["ship_date"] <= df["promised_date"]
    return df


def compute_kpis(df: pd.DataFrame) -> dict:
    net_revenue = df["net_revenue"].sum()
    gross_profit = df["gross_profit"].sum()
    total_orders = df["order_id"].nunique()
    kpis = {
        "net_revenue": net_revenue,
        "gross_profit": gross_profit,
        "gross_margin_pct": 100 * gross_profit / net_revenue,
        "total_orders": total_orders,
        "avg_order_value": net_revenue / total_orders,
        "on_time_ship_pct": 100 * df["on_time"].mean(),
        "return_rate_pct": 100 * (df["units"] * df["is_returned"]).sum() / df["units"].sum(),
    }
    return kpis


def fmt(name: str, value: float, definitions: dict) -> str:
    kind = definitions[name].get("format", "number")
    if kind == "currency_usd":
        return f"${value:,.0f}" if abs(value) >= 1000 else f"${value:,.2f}"
    if kind == "percent_1dp":
        return f"{value:.1f}%"
    if kind == "integer":
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def render_dashboard(df: pd.DataFrame, kpis: dict, definitions: dict) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc"})
    fig = plt.figure(figsize=(16, 9), facecolor="#0f1b2d")
    fig.suptitle(
        "Enterprise KPI Dashboard - Retail & Supply Chain (synthetic data)",
        color="white", fontsize=18, fontweight="bold", y=0.97,
    )

    cards = ["net_revenue", "gross_margin_pct", "on_time_ship_pct", "return_rate_pct"]
    for i, name in enumerate(cards):
        ax = fig.add_axes([0.04 + i * 0.245, 0.78, 0.21, 0.13])
        ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, color="#1c2f4a", transform=ax.transAxes))
        ax.text(0.5, 0.62, definitions[name]["label"], ha="center",
                color="#9db2cc", fontsize=12, transform=ax.transAxes)
        ax.text(0.5, 0.28, fmt(name, kpis[name], definitions), ha="center",
                color="white", fontsize=22, fontweight="bold", transform=ax.transAxes)

    ax1 = fig.add_axes([0.05, 0.42, 0.55, 0.28])
    monthly = df.set_index("order_date")["net_revenue"].resample("ME").sum()
    ax1.plot(monthly.index, monthly.values / 1000, color="#4da3ff", lw=2, marker="o", ms=3)
    ax1.set_title("Net revenue by month ($k)", color="white", fontsize=12, loc="left")
    ax1.tick_params(colors="#9db2cc", labelsize=9)
    for s in ax1.spines.values():
        s.set_color("#33475f")
    ax1.set_facecolor("#0f1b2d")
    ax1.grid(alpha=0.2, color="#33475f")

    ax2 = fig.add_axes([0.68, 0.42, 0.28, 0.28])
    cat = df.groupby("category")["net_revenue"].sum().sort_values() / 1000
    ax2.barh(cat.index, cat.values, color="#2fbf8f")
    ax2.set_title("Net revenue by category ($k)", color="white", fontsize=12, loc="left")
    ax2.tick_params(colors="#9db2cc", labelsize=9)
    for s in ax2.spines.values():
        s.set_color("#33475f")
    ax2.set_facecolor("#0f1b2d")
    ax2.grid(alpha=0.2, axis="x", color="#33475f")

    ax3 = fig.add_axes([0.05, 0.07, 0.42, 0.26])
    ot = df.groupby("region")["on_time"].mean().sort_values() * 100
    bars = ax3.bar(ot.index, ot.values, color="#f2a541")
    ax3.axhline(95, color="#e05d5d", ls="--", lw=1)
    ax3.text(len(ot) - 0.4, 95.4, "95% target", color="#e05d5d", fontsize=9, ha="right")
    ax3.set_ylim(min(ot.min() - 5, 80), 100)
    ax3.set_title("On-time ship % by region", color="white", fontsize=12, loc="left")
    ax3.tick_params(colors="#9db2cc", labelsize=9)
    for b, v in zip(bars, ot.values):
        ax3.text(b.get_x() + b.get_width() / 2, v + 0.4, f"{v:.1f}%",
                 ha="center", color="white", fontsize=9)
    for s in ax3.spines.values():
        s.set_color("#33475f")
    ax3.set_facecolor("#0f1b2d")
    ax3.grid(alpha=0.2, axis="y", color="#33475f")

    ax4 = fig.add_axes([0.55, 0.07, 0.41, 0.26])
    chan = df.groupby("channel").agg(
        net=("net_revenue", "sum"), margin=("gross_profit", "sum")
    )
    chan["margin_pct"] = 100 * chan["margin"] / chan["net"]
    x = range(len(chan))
    ax4.bar([i - 0.2 for i in x], chan["net"] / 1000, width=0.4,
            label="Net revenue ($k)", color="#4da3ff")
    ax4b = ax4.twinx()
    ax4b.bar([i + 0.2 for i in x], chan["margin_pct"], width=0.4,
             label="Gross margin %", color="#9d7bff")
    ax4.set_xticks(list(x), chan.index)
    ax4.set_title("Channel mix: revenue and margin", color="white", fontsize=12, loc="left")
    ax4.tick_params(colors="#9db2cc", labelsize=9)
    ax4b.tick_params(colors="#9d7bff", labelsize=9)
    for s in list(ax4.spines.values()) + list(ax4b.spines.values()):
        s.set_color("#33475f")
    ax4.set_facecolor("#0f1b2d")
    ax4.grid(alpha=0.2, axis="y", color="#33475f")
    h1, l1 = ax4.get_legend_handles_labels()
    h2, l2 = ax4b.get_legend_handles_labels()
    ax4.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8,
               facecolor="#1c2f4a", labelcolor="white", framealpha=0.9)

    fig.text(0.99, 0.01, "Author: Mahesh M - synthetic demo data",
             ha="right", color="#5b7290", fontsize=8)
    for ext in ("png", "svg"):
        fig.savefig(ROOT / f"dashboard.{ext}", dpi=140, facecolor=fig.get_facecolor(),
                    bbox_inches="tight")
    plt.close(fig)


def write_summary(df: pd.DataFrame, kpis: dict, definitions: dict) -> None:
    lines = [
        "# KPI summary (synthetic data)",
        "",
        "Computed by `scripts/build_dashboard.py` from `data/orders.csv`,",
        "using the definitions in `metrics/metrics.yml`.",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for name in [
        "net_revenue", "gross_profit", "gross_margin_pct", "total_orders",
        "avg_order_value", "on_time_ship_pct", "return_rate_pct",
    ]:
        lines.append(f"| {definitions[name]['label']} | {fmt(name, kpis[name], definitions)} |")
    lines += [
        "",
        "## On-time ship % by region",
        "",
        "| Region | On-time % |",
        "|---|---|",
    ]
    ot = df.groupby("region")["on_time"].mean().sort_values(ascending=False) * 100
    for region, value in ot.items():
        lines.append(f"| {region} | {value:.1f}% |")
    lines += [
        "",
        "## Net revenue by channel",
        "",
        "| Channel | Net revenue | Gross margin % |",
        "|---|---|---|",
    ]
    chan = df.groupby("channel").agg(net=("net_revenue", "sum"), gp=("gross_profit", "sum"))
    for channel, row in chan.iterrows():
        lines.append(
            f"| {channel} | ${row['net']:,.0f} | {100 * row['gp'] / row['net']:.1f}% |"
        )
    (ROOT / "kpi_summary.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    definitions = {
        m["name"]: m for m in yaml.safe_load(METRICS.read_text())["metrics"]
    }
    df = load_orders()
    kpis = compute_kpis(df)
    render_dashboard(df, kpis, definitions)
    write_summary(df, kpis, definitions)
    print("KPIs:")
    for name, value in kpis.items():
        print(f"  {name}: {fmt(name, value, definitions)}")
    print("wrote dashboard.png, dashboard.svg and kpi_summary.md")


if __name__ == "__main__":
    main()
