# /// script
# dependencies = [
#     "matplotlib",
# ]
# ///
import argparse
import csv
import os
from collections import defaultdict
from typing import TypedDict

import matplotlib.pyplot as plt

# Color mapping logic
WIREUP_COLOR = "#007ACC"
OTHER_COLOR = "#cccccc"
PROJECT_ALIASES = {"FastAPI": "FastAPI Depends"}
PROJECT_ALIASES["Injector (+fastapi-injector) †"] = "Injector †"


class ChartItem(TypedDict):
    name: str
    rps: float


def load_data(csv_path: str) -> dict[str, list[ChartItem]]:
    """Loads CSV data and returns a dict grouped by test type."""
    data_by_test: defaultdict[str, list[ChartItem]] = defaultdict(list)

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            project_name = PROJECT_ALIASES.get(row["project"], row["project"])
            data_by_test[row["test"]].append({"name": project_name, "rps": float(row["rps"])})

    # Sort each group by RPS descending
    for test in data_by_test:
        data_by_test[test].sort(key=lambda x: x["rps"], reverse=True)

    return data_by_test


def create_chart(title: str, data: list[ChartItem], filename: str, text_color: str = "black") -> None:
    if not data:
        return

    plt.figure(figsize=(10, len(data) * 0.4))  # Reduced height multiplier

    # Set text colors
    plt.rcParams["text.color"] = text_color
    plt.rcParams["axes.labelcolor"] = text_color
    plt.rcParams["xtick.color"] = text_color
    plt.rcParams["ytick.color"] = text_color

    ax = plt.gca()
    names = [item["name"] for item in data]
    rps_values = [item["rps"] for item in data]

    # Highlight logic: If "Wireup" is in the display name
    colors = [WIREUP_COLOR if "wireup" in item["name"].lower() else OTHER_COLOR for item in data]

    bars = ax.barh(names, rps_values, color=colors, height=0.6)  # Slightly thinner bars

    # Make "Manual Wiring (No DI)" visually distinct: outline + diagonal hatch.
    for bar, item in zip(bars, data, strict=False):
        if item["name"].lower().startswith("globals"):
            outline = "#cecece" if text_color == "black" else "#cecece"
            bar.set_facecolor("none")
            bar.set_edgecolor(outline)
            bar.set_linewidth(1.5)
            # bar.set_linestyle((0, (3, 2)))
            bar.set_hatch("//")

    plt.title(title, color=text_color, pad=10)  # Less padding
    ax.invert_yaxis()  # Best on top

    # Remove borders
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Remove x-axis
    ax.set_xticks([])
    ax.set_xticklabels([])
    ax.tick_params(axis="y", colors=text_color, length=0)

    max_rps = max(rps_values) if rps_values else 1
    label_pad = max_rps * 0.01
    ax.set_xlim(0, max_rps + label_pad * 8)

    # Add value labels
    for bar, item in zip(bars, data, strict=False):
        width = bar.get_width()
        is_wireup = "wireup" in item["name"].lower()

        # Position label outside the bar (to the right).
        ax.text(
            width + label_pad,
            bar.get_y() + bar.get_height() / 2,
            f"{int(width):,}",
            va="center",
            ha="left",
            color=WIREUP_COLOR if is_wireup else text_color,
            fontweight="bold" if is_wireup else "normal",
            clip_on=False,
        )

    plt.tight_layout()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(os.path.dirname(script_dir), "docs", "pages", "img")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, filename)
    plt.savefig(output_path, transparent=True, bbox_inches="tight")
    print(f"Saved {output_path}")
    plt.close()


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_csv_path = os.path.join(os.path.dirname(script_dir), "benchmarks", "benchmark_results.csv")

    parser = argparse.ArgumentParser(description="Generate benchmark charts from CSV")
    parser.add_argument("input", type=str, nargs="?", default=default_csv_path, help="Input CSV file path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        return

    data_by_test = load_data(args.input)

    for test_type, results in data_by_test.items():
        title = "Requests per Second - Higher is Better"

        # Light mode
        create_chart(
            title,
            results,
            f"benchmarks_{test_type}_light.svg",
            "black",
        )

        # Dark mode
        create_chart(
            title,
            results,
            f"benchmarks_{test_type}_dark.svg",
            "#e0e0e0",
        )


if __name__ == "__main__":
    main()
