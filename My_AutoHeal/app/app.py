import os, time, sys, json, pathlib

DATA_DIR = pathlib.Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
HEARTBEAT = DATA_DIR / "heartbeat.txt"
CONFIG = DATA_DIR / "config.json"

def load_config():
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text())
        except Exception:
            pass
    return {"repaired": False}

def main():
    fault = os.getenv("FAULT", "crash")  # "crash" | "hang" | "none"
    crash_tick = int(os.getenv("CRASH_TICK", "5"))
    hang_tick  = int(os.getenv("HANG_TICK", "5"))
    cfg = load_config()
    repaired = bool(cfg.get("repaired", False))
    print(f"[app] start repaired={repaired} fault={fault}", flush=True)

    for i in range(1, 10**6):
        HEARTBEAT.write_text(str(time.time()))
        print(f"[app] tick {i}", flush=True)
        time.sleep(1)

        # Only fault if not yet repaired
        if not repaired:
            if fault == "crash" and i == crash_tick:
                raise RuntimeError("simulated crash")
            if fault == "hang" and i == hang_tick:
                print("[app] simulating hang (heartbeat stops)", flush=True)
                while True:
                    time.sleep(3600)

if __name__ == "__main__":
    main()
