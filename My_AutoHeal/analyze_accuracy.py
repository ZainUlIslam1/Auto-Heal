import re
import os
import glob
import matplotlib.pyplot as plt

def parse_log_file(filepath):
    metrics = {
        "Standard": {"times": [], "attempts": [], "success": 0, "total": 0},
        "Levenshtein": {"times": [], "scanned": [], "success": 0, "total": 0}
    }
    
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return metrics

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if "[Performance]" in line:
                # Example: [Performance] Method=Standard, Time=0.0152s, Attempts=4, Success=True
                # Example: [Performance] Method=Levenshtein, Time=0.123s, Scanned=50, Success=True
                
                method_match = re.search(r"Method=(\w+)", line)
                time_match = re.search(r"Time=([\d\.]+)s", line)
                success_match = re.search(r"Success=(\w+)", line)
                
                if not (method_match and time_match and success_match):
                    continue
                    
                method = method_match.group(1)
                duration = float(time_match.group(1))
                success = success_match.group(1) == "True"
                
                if method == "Standard":
                    attempts_match = re.search(r"Attempts=(\d+)", line)
                    attempts = int(attempts_match.group(1)) if attempts_match else 0
                    
                    metrics["Standard"]["times"].append(duration)
                    metrics["Standard"]["attempts"].append(attempts)
                    metrics["Standard"]["total"] += 1
                    if success: metrics["Standard"]["success"] += 1

                elif method == "Levenshtein":
                    scanned_match = re.search(r"Scanned=(\d+)", line)
                    scanned = int(scanned_match.group(1)) if scanned_match else 0
                    
                    metrics["Levenshtein"]["times"].append(duration)
                    metrics["Levenshtein"]["scanned"].append(scanned)
                    metrics["Levenshtein"]["total"] += 1
                    if success: metrics["Levenshtein"]["success"] += 1
                    
    return metrics

def print_report(metrics):
    print("\n" + "="*50)
    print("       AUTO-HEAL PERFORMANCE ANALYSIS REPORT       ")
    print("="*50)
    
    # --- Standard ---
    std = metrics["Standard"]
    std_avg_time = 0
    std_success_rate = 0
    if std["total"] > 0:
        std_avg_time = sum(std["times"]) / std["total"]
        avg_attempts = sum(std["attempts"]) / std["total"]
        std_success_rate = (std["success"] / std["total"]) * 100
        
        print("\n[ STANDARD RULE-BASED HEALING ]")
        print(f"  Total Heals Attempted: {std['total']}")
        print(f"  Success Rate:          {std_success_rate:.1f}%")
        print(f"  Avg Resolution Time:   {std_avg_time:.4f}s")
        print(f"  Avg Fallback Strategies: {avg_attempts:.1f}")
    else:
        print("\n[ STANDARD RULE-BASED HEALING ]")
        print("  No data found.")

    # --- Levenshtein ---
    lev = metrics["Levenshtein"]
    lev_avg_time = 0
    lev_success_rate = 0
    if lev["total"] > 0:
        lev_avg_time = sum(lev["times"]) / lev["total"]
        avg_scanned = sum(lev["scanned"]) / lev["total"]
        lev_success_rate = (lev["success"] / lev["total"]) * 100
        
        print("\n[ LEVENSHTEIN FUZZY HEALING ]")
        print(f"  Total Heals Attempted: {lev['total']}")
        print(f"  Success Rate:          {lev_success_rate:.1f}%")
        print(f"  Avg Resolution Time:   {lev_avg_time:.4f}s")
        print(f"  Avg Elements Scanned:  {avg_scanned:.1f}")
    else:
        print("\n[ LEVENSHTEIN FUZZY HEALING ]")
        print("  No data found.")
        
    print("\n" + "="*50 + "\n")
    return std_avg_time, std_success_rate, lev_avg_time, lev_success_rate

def generate_graphs(std_time, std_rate, lev_time, lev_rate):
    methods = ['Standard', 'Levenshtein']
    times = [std_time, lev_time]
    rates = [std_rate, lev_rate]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

    # Time Chart
    ax1.bar(methods, times, color=['blue', 'orange'])
    ax1.set_title('Average Healing Time (s)')
    ax1.set_ylabel('Time (seconds)')
    for i, v in enumerate(times):
        ax1.text(i, v, f"{v:.4f}s", ha='center', va='bottom')

    # Success Rate Chart
    ax2.bar(methods, rates, color=['green', 'purple'])
    ax2.set_title('Success Rate (%)')
    ax2.set_ylabel('Percentage')
    ax2.set_ylim(0, 110)
    for i, v in enumerate(rates):
        ax2.text(i, v, f"{v:.1f}%", ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig('accuracy_graphs.png')
    print("Graphs saved to accuracy_graphs.png")

def main():
    log_files = glob.glob("logs/*.log")
    combined_metrics = {
        "Standard": {"times": [], "attempts": [], "success": 0, "total": 0},
        "Levenshtein": {"times": [], "scanned": [], "success": 0, "total": 0}
    }
    
    for log_file in log_files:
        print(f"Parsing {log_file}...")
        file_metrics = parse_log_file(log_file)
        
        # Merge
        for method in ["Standard", "Levenshtein"]:
            combined_metrics[method]["times"].extend(file_metrics[method]["times"])
            if method == "Standard":
                combined_metrics[method]["attempts"].extend(file_metrics[method]["attempts"])
            elif method == "Levenshtein":
                combined_metrics[method]["scanned"].extend(file_metrics[method]["scanned"])
            
            combined_metrics[method]["success"] += file_metrics[method]["success"]
            combined_metrics[method]["total"] += file_metrics[method]["total"]

    std_time, std_rate, lev_time, lev_rate = print_report(combined_metrics)
    generate_graphs(std_time, std_rate, lev_time, lev_rate)

if __name__ == "__main__":
    main()
