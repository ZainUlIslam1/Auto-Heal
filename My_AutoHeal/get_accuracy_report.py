
import os
import json

def calculate_accuracy(log_file):
    if not os.path.exists(log_file):
        return {"error": "Log file not found"}
    
    successes = 0
    failures = 0
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            lower = line.lower()
            # Counting generic success message found in both drivers
            if "healing successful" in lower:
                successes += 1
            # Counting generic failure message found in both drivers
            if "could not heal locator" in lower:
                failures += 1
                
    total = successes + failures
    accuracy = 0.0
    if total > 0:
        accuracy = (successes / total) * 100
        
    return {
        "successes": successes,
        "failures": failures,
        "total": total,
        "accuracy": accuracy
    }

def main():
    print("--- Auto-Heal Accuracy Report ---\n")
    
    # 1. Standard Driver
    std_stats = calculate_accuracy("logs/auto_heal.log")
    if "error" in std_stats:
        print(f"Standard Driver (logs/auto_heal.log): {std_stats['error']}")
    else:
        print(f"Standard Driver (test.py):")
        print(f"  Accuracy: {std_stats['accuracy']:.2f}%")
        print(f"  Successes: {std_stats['successes']}")
        print(f"  Failures:  {std_stats['failures']}")
        print(f"  Total Attempts: {std_stats['total']}")
        
    print("-" * 30)
    
    # 2. Levenshtein Driver
    lev_stats = calculate_accuracy("logs/levenshtein.log")
    if "error" in lev_stats:
        print(f"Levenshtein Driver (logs/levenshtein.log): {lev_stats['error']}")
    else:
        print(f"Levenshtein Driver (levenshtein.py):")
        print(f"  Accuracy: {lev_stats['accuracy']:.2f}%")
        print(f"  Successes: {lev_stats['successes']}")
        print(f"  Failures:  {lev_stats['failures']}")
        print(f"  Total Attempts: {lev_stats['total']}")

if __name__ == "__main__":
    main()
