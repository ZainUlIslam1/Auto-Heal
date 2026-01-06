import os
import re
import csv
import matplotlib.pyplot as plt

# Scenario keywords as they appear in the logs, mapped to nice labels
SCENARIOS = {
    "LOGIN": "Login & Profile",
    "E-COMMERCE": "E-commerce",
    "BLOG": "Blog",
    "DASHBOARD": "Dashboard",
    "CONTACT": "Contact",
}


def detect_scenario(line: str):
    """
    Given a log line that contains 'SCENARIO', identify which of the
    known scenario names it belongs to, based on keyword matching.
    """
    for key, label in SCENARIOS.items():
        if key in line:
            return label
    return None


def parse_healing_metrics(log_path: str, method_name: str) -> dict:
    """
    Parse a log file and collect healing metrics per scenario for a given method.

    We look for lines like:
        --- SCENARIO 1: LOGIN (index.html) ---
        [Performance] Method=Standard, Time=0.0192s, Attempts=3, Success=True

    Returns a dict:
        {
          "Login & Profile": {
              "events_total": int,
              "events_success": int,
              "times": [float, float, ...]
          },
          ...
        }
    """
    # Initialise empty counters for each scenario
    metrics = {
        label: {"events_total": 0, "events_success": 0, "times": []}
        for label in SCENARIOS.values()
    }

    if not os.path.exists(log_path):
        print(f"[WARN] Log file not found: {log_path}")
        return metrics

    current_scenario = None

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            # Detect which scenario we are currently in
            if "SCENARIO" in line:
                sc = detect_scenario(line)
                if sc:
                    current_scenario = sc

            # Only consider performance lines for this method
            if "[Performance]" in line and f"Method={method_name}" in line:
                if not current_scenario:
                    continue

                # Example: "[Performance] Method=Standard, Time=0.0196s, Attempts=3, Success=True"
                time_match = re.search(r"Time=([\d.]+)s", line)
                success_match = re.search(r"Success=(\w+)", line)

                if not (time_match and success_match):
                    continue

                t = float(time_match.group(1))
                success_flag = success_match.group(1).lower() == "true"

                m = metrics[current_scenario]
                m["events_total"] += 1
                if success_flag:
                    m["events_success"] += 1
                m["times"].append(t)

    return metrics


def compute_rates_and_times(std_metrics: dict, lev_metrics: dict) -> dict:
    """
    Build a combined data structure with success rates and average times
    for Baseline, Standard, and Levenshtein, per scenario.
    """
    combined = {}

    for label in SCENARIOS.values():
        std = std_metrics[label]
        lev = lev_metrics[label]

        # Baseline: no healing
        baseline_rate = 0.0
        baseline_time = 0.0

        # Standard (rule-based)
        if std["events_total"] > 0:
            std_rate = std["events_success"] / std["events_total"] * 100.0
            std_time = sum(std["times"]) / len(std["times"])
        else:
            std_rate = 0.0
            std_time = 0.0

        # Levenshtein
        if lev["events_total"] > 0:
            lev_rate = lev["events_success"] / lev["events_total"] * 100.0
            lev_time = sum(lev["times"]) / len(lev["times"])
        else:
            lev_rate = 0.0
            lev_time = 0.0

        combined[label] = {
            "Baseline": {
                "success_rate": baseline_rate,
                "avg_time": baseline_time,
            },
            "Standard": {
                "success_rate": std_rate,
                "avg_time": std_time,
            },
            "Levenshtein": {
                "success_rate": lev_rate,
                "avg_time": lev_time,
            },
        }

    return combined


def save_csv(combined: dict, out_csv: str) -> None:
    """
    Save all scenario metrics to a CSV file for the dissertation appendix.
    """
    fieldnames = [
        "Scenario",
        "Method",
        "SuccessRatePercent",
        "AverageHealingTimeSeconds",
    ]

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for scenario, methods in combined.items():
            for method_name, vals in methods.items():
                writer.writerow(
                    {
                        "Scenario": scenario,
                        "Method": method_name,
                        "SuccessRatePercent": f"{vals['success_rate']:.1f}",
                        "AverageHealingTimeSeconds": f"{vals['avg_time']:.4f}",
                    }
                )

    print(f"[INFO] CSV written to {out_csv}")


def make_per_scenario_charts(combined: dict, outdir: str) -> None:
    """
    For each scenario, create two charts:
      - *_success.png  (Baseline vs Standard vs Levenshtein)
      - *_time.png     (same methods, average healing time)
    Bars are always drawn, even if value is 0.0.
    """
    os.makedirs(outdir, exist_ok=True)

    for scenario, methods in combined.items():
        labels = ["Baseline", "Standard", "Levenshtein"]
        success_vals = [methods[m]["success_rate"] for m in labels]
        time_vals = [methods[m]["avg_time"] for m in labels]

        # --- Success chart ---
        plt.figure(figsize=(5, 4))
        bars = plt.bar(labels, success_vals)
        plt.ylim(0, 110)
        plt.ylabel("Healing success rate (%)")
        plt.title(f"Success rate by method\nScenario: {scenario}")

        # Show values on top of bars, including 0.0%
        for bar, v in zip(bars, success_vals):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                v + 2,
                f"{v:.1f}%",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        plt.tight_layout()
        filename_success = scenario.replace(" ", "_").lower() + "_success.png"
        plt.savefig(os.path.join(outdir, filename_success))
        plt.close()

        # --- Time chart ---
        plt.figure(figsize=(5, 4))
        bars = plt.bar(labels, time_vals)
        plt.ylabel("Average healing time (s)")
        plt.title(f"Healing time by method\nScenario: {scenario}")

        for bar, v in zip(bars, time_vals):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                v + 0.001,
                f"{v:.4f}s",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        plt.tight_layout()
        filename_time = scenario.replace(" ", "_").lower() + "_time.png"
        plt.savefig(os.path.join(outdir, filename_time))
        plt.close()


def make_combined_charts(combined: dict, outdir: str) -> None:
    """
    Create two combined charts across all scenarios:
      - all_scenarios_success.png
      - all_scenarios_time.png
    """
    os.makedirs(outdir, exist_ok=True)

    scenarios = list(combined.keys())
    x = range(len(scenarios))
    width = 0.25

    # Success values
    baseline_rates = [combined[s]["Baseline"]["success_rate"] for s in scenarios]
    std_rates = [combined[s]["Standard"]["success_rate"] for s in scenarios]
    lev_rates = [combined[s]["Levenshtein"]["success_rate"] for s in scenarios]

    plt.figure(figsize=(9, 4))
    plt.bar([i - width for i in x], baseline_rates, width, label="Baseline")
    plt.bar(list(x), std_rates, width, label="Standard")
    plt.bar([i + width for i in x], lev_rates, width, label="Levenshtein")
    plt.xticks(list(x), scenarios, rotation=20, ha="right")
    plt.ylabel("Healing success rate (%)")
    plt.title("Success rate by scenario and method")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "all_scenarios_success.png"))
    plt.close()

    # Time values
    baseline_times = [combined[s]["Baseline"]["avg_time"] for s in scenarios]
    std_times = [combined[s]["Standard"]["avg_time"] for s in scenarios]
    lev_times = [combined[s]["Levenshtein"]["avg_time"] for s in scenarios]

    plt.figure(figsize=(9, 4))
    plt.bar([i - width for i in x], baseline_times, width, label="Baseline")
    plt.bar(list(x), std_times, width, label="Standard")
    plt.bar([i + width for i in x], lev_times, width, label="Levenshtein")
    plt.xticks(list(x), scenarios, rotation=20, ha="right")
    plt.ylabel("Average healing time (s)")
    plt.title("Average healing time by scenario and method")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "all_scenarios_time.png"))
    plt.close()


def main():
    log_dir = "logs"
    auto_log = os.path.join(log_dir, "auto_heal.log")
    lev_log = os.path.join(log_dir, "levenshtein.log")

    print("[INFO] Parsing Standard (AutoHealingDriver) metrics...")
    std_metrics = parse_healing_metrics(auto_log, "Standard")

    print("[INFO] Parsing Levenshtein metrics...")
    lev_metrics = parse_healing_metrics(lev_log, "Levenshtein")

    combined = compute_rates_and_times(std_metrics, lev_metrics)

    outdir = "scenario_graphs"
    os.makedirs(outdir, exist_ok=True)

    # Save CSV table with all values
    csv_path = os.path.join(outdir, "scenario_metrics.csv")
    save_csv(combined, csv_path)

    # Per-scenario charts
    print(f"[INFO] Generating per-scenario charts into {outdir}/ ...")
    make_per_scenario_charts(combined, outdir)

    # Combined charts
    print("[INFO] Generating combined charts...")
    make_combined_charts(combined, outdir)

    print("[INFO] Done.")


if __name__ == "__main__":
    main()
