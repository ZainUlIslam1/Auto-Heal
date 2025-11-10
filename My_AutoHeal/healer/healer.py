import subprocess, time, json, pathlib, csv, os
from datetime import datetime

PROJECT = pathlib.Path("/project").resolve()
DATA = pathlib.Path("/data")
DATA.mkdir(exist_ok=True)
HEARTBEAT = DATA / "heartbeat.txt"
CONFIG = DATA / "config.json"
LOG = PROJECT / "results.csv"
DATA_HOST_PATH = os.getenv("DATA_HOST_PATH")  # host path to /data


# This is the app image name defined in docker-compose.yml (services.app.image)
APP_IMAGE = os.getenv("APP_IMAGE", "autoheal-demo:latest")
CONTAINER_NAME = "my_autoheal"

HANG_TIMEOUT = int(os.getenv("HANG_TIMEOUT", "8"))   # seconds without heartbeat -> hang
SLA_SEC = int(os.getenv("SLA_SEC", "20"))            # heal within this after detection

from datetime import datetime, UTC
def now(): return datetime.now(UTC).isoformat()

def docker(*args, check=True, capture_output=True, text=True):
    # capture_output=True keeps compose logs clean; see result.returncode/stdout if needed
    return subprocess.run(["docker", *args], check=check, capture_output=capture_output, text=text)
print("[healer] starting trials…", flush=True)


def is_running():
    try:
        out = docker("inspect", "-f", "{{.State.Running}}", CONTAINER_NAME, capture_output=True).stdout.strip()
        return out.lower() == "true"
    except subprocess.CalledProcessError:
        return False

def start_app(fault: str):
    # create (or recreate) the app container for this trial
    docker("rm", "-f", CONTAINER_NAME, check=False)
    docker(
        "run","-d",
        "--name", CONTAINER_NAME,
        "--restart=always",
        "-e", f"FAULT={fault}",
        "-v", f"{DATA_HOST_PATH}:/data",   # same named volume as compose
        APP_IMAGE
    )

def append_log(row):
    new_file = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["trial_id","fault","event","ts_utc","elapsed_s"])
        w.writerow(row)

def write_fix():
    CONFIG.write_text(json.dumps({"repaired": True}))

def monitor_trial(trial_id: str, fault: str):
    # reset shared state
    HEARTBEAT.write_text(str(time.time()))
    CONFIG.write_text(json.dumps({"repaired": False}))
    append_log([trial_id, fault, "start", now(), 0.0])

    start = time.time()
    detected_at = None
    last_hb = time.time()

    while True:
        # heartbeat freshness
        try:
            hb_val = float(HEARTBEAT.read_text())
            if hb_val != last_hb:
                last_hb = hb_val
        except Exception:
            pass

        running = is_running()

        # detect crash
        if not running and detected_at is None:
            detected_at = time.time()
            append_log([trial_id, fault, "detected_crash", now(), round(detected_at - start, 3)])
            write_fix()  # so next auto-restart comes back healthy
            append_log([trial_id, fault, "fix_applied", now(), round(time.time() - start, 3)])
            # docker restart policy will auto-restart container

        # detect hang
        if running and (time.time() - last_hb > HANG_TIMEOUT) and detected_at is None:
            detected_at = time.time()
            append_log([trial_id, fault, "detected_hang", now(), round(detected_at - start, 3)])
            write_fix()
            append_log([trial_id, fault, "fix_applied", now(), round(time.time() - start, 3)])
            docker("restart", CONTAINER_NAME)
            append_log([trial_id, fault, "forced_restart", now(), round(time.time() - start, 3)])

        # success criteria: after detection, heartbeat resumes and stays fresh
        if detected_at is not None:
            if time.time() - detected_at > SLA_SEC:
                append_log([trial_id, fault, "timeout_after_detection", now(), round(time.time() - start, 3)])
                docker("rm","-f", CONTAINER_NAME, check=False)
                break
            if running and time.time() - last_hb < 2:
                append_log([trial_id, fault, "healed", now(), round(time.time() - start, 3)])
                docker("rm","-f", CONTAINER_NAME, check=False)
                break

        time.sleep(0.5)

def score():
    rows = list(csv.DictReader(open(LOG, newline="")))
    from collections import defaultdict
    by_trial = defaultdict(list)
    for r in rows: by_trial[r["trial_id"]].append(r)

    TP=FP=FN=TN=0
    det_lat=[]; rec_lat=[]; sla_hits=0; faults=0
    for tid, events in by_trial.items():
        fault = events[0]["fault"]
        detected = next((e for e in events if e["event"].startswith("detected_")), None)
        healed   = next((e for e in events if e["event"]=="healed"), None)
        timeout  = next((e for e in events if e["event"]=="timeout_after_detection"), None)
        if fault in ("crash","hang"):
            faults += 1
            if detected and healed:
                TP += 1
                d = float(detected["elapsed_s"]); h = float(healed["elapsed_s"])
                det_lat.append(d); rec_lat.append(h - d)
                if (h - d) <= SLA_SEC: sla_hits += 1
            else:
                FN += 1
        else:
            if detected: FP += 1
            else: TN += 1

    precision = TP / (TP + FP) if (TP+FP) else 1.0
    recall    = TP / (TP + FN) if (TP+FN) else 1.0
    success   = TP / faults if faults else 1.0
    mttd      = sum(det_lat)/len(det_lat) if det_lat else 0
    mttr      = sum(rec_lat)/len(rec_lat) if rec_lat else 0
    sla_rate  = sla_hits / (TP if TP else 1)

    print("")
    print("=== ACCURACY SUMMARY ===")
    print(f"TP={TP} FP={FP} FN={FN} TN={TN}")
    print(f"Success rate: {success:.2f}")
    print(f"Precision:    {precision:.2f}")
    print(f"Recall:       {recall:.2f}")
    print(f"MTTD (s):     {mttd:.2f}")
    print(f"MTTR (s):     {mttr:.2f}")
    print(f"SLA hit rate: {sla_rate:.2f}")
    print("========================")

def main():
    # clean old log
    try: LOG.unlink()
    except FileNotFoundError: pass

    # define trials
    trials = [
        ("crash_1","crash"),
        ("crash_2","crash"),
        ("hang_1","hang"),
        ("hang_2","hang"),
        ("none_1","none"),
        ("none_2","none"),
    ]

    print("[healer] starting trials…")
    for tid, fault in trials:
        print(f"[healer] trial={tid} fault={fault}")
        start_app(fault=fault)
        try:
            monitor_trial(trial_id=tid, fault=fault)
        finally:
            subprocess.run(["docker","rm","-f", CONTAINER_NAME], check=False)
        time.sleep(2)

    print("[healer] trials complete. results.csv written.")
    score()  # print summary at the end

if __name__ == "__main__":
    main()
