"""
Inventory service — lab checkout leaf.

Healthy path: O(1) dict lookup in WAREHOUSE_SKU_INDEX.

Code-level SLOWDOWN (see scripts/break_inventory_slow_code.sh): lookup walks a
long unsorted WAREHOUSE_LEDGER and runs a leftover per-row checksum — classic
perf regression (HTTP 200, elevated response time). Not a fault-flag sleep.
"""
import logging
import os
import threading
import time

from flask import Flask

app = Flask("inventory")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("inventory")

WAREHOUSE_SKU_INDEX = {
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    "MACBOOK-PRO-14": 100,
}

# --- SCENARIO_MODE markers (break/heal scripts swap HEALTHY / MONITORING_DARK / AVAILABILITY_DOWN) ---
SCENARIO_MODE = "HEALTHY"
# --- end SCENARIO_MODE ---

if SCENARIO_MODE == "MONITORING_DARK":
    # Best-effort code-only telemetry suppression for lab reruns.
    # Applied before request handling so instrumentation can read env on boot.
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["DT_DISABLE"] = "true"
elif SCENARIO_MODE == "AVAILABILITY_DOWN":
    # Code-induced hard outage: process exits shortly after boot.
    def _exit_soon():
        time.sleep(2)
        os._exit(1)

    threading.Thread(target=_exit_soon, name="lab-avail-down", daemon=True).start()


# --- LOOKUP_ impl markers (break/heal scripts swap between FAST and SLOW) ---
def lookup_stock_in_warehouse(sku: str = "MACBOOK-PRO-14") -> dict:
    """FAST: O(1) index lookup."""
    qty = WAREHOUSE_SKU_INDEX[sku]
    return {"stock": qty, "sku": sku}


# --- end LOOKUP_ ---

# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
# IDLE: no background CPU burn (RESOURCE_CONTENTION lab off).
# --- end RESOURCE_BURN ---


@app.route("/inventory")
def inventory():
    return lookup_stock_in_warehouse("MACBOOK-PRO-14")


app.run(host="0.0.0.0", port=8082, threaded=True)
