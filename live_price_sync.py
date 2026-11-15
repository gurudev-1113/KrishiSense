"""
Live Price Sync Module for KrishiSense
---------------------------------------
Fetches real-time daily mandi/APMC prices from the official Indian Government
Open Data Platform (Data.gov.in - Directorate of Marketing & Inspection / Agmarknet).
Normalizes prices for target commodities and updates SQLite prices.db.
"""

import os
import sqlite3
import json
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
DB_PATH = os.path.join(os.path.dirname(__file__), "prices.db")

COMMODITY_MAPPING = {
    "arecanut": "Arecanut",
    "betelnut": "Arecanut",
    "supari": "Arecanut",
    "banana": "Banana",
    "black pepper": "Black Pepper",
    "pepper": "Black Pepper",
    "cashew": "Cashew",
    "coconut": "Coconut"
}

TARGET_MARKETS = [
    "Bantwal", "Belthangady", "Mangalore", "Moodbidri",
    "Puttur", "Sullia", "Uppinangady"
]

def normalize_commodity(name):
    if not name:
        return None
    name_lower = name.lower()
    for key, normalized in COMMODITY_MAPPING.items():
        if key in name_lower:
            return normalized
    return None

def normalize_market(name):
    if not name:
        return None
    for m in TARGET_MARKETS:
        if m.lower() in name.lower():
            return m
    # Clean suffix like " APMC", " Market"
    clean = name.replace(" APMC", "").replace(" Market", "").strip()
    return clean

def fetch_live_mandi_data(api_key=None):
    """Query data.gov.in for Karnataka daily mandi records"""
    key = api_key or os.environ.get("DATAGOV_API_KEY")
    if not key:
        return {"success": False, "error": "No DATAGOV_API_KEY configured."}

    url = (
        f"https://api.data.gov.in/resource/{API_RESOURCE_ID}"
        f"?api-key={key}&format=json&filters[state]=Karnataka&limit=500"
    )

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KrishiSense/2.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
            records = data.get("records", [])
            return {"success": True, "records": records, "total": data.get("total", len(records))}
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP Error {e.code}: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def sync_live_prices(api_key=None):
    """
    Fetches live data and upserts into prices.db.
    Also ensures local Dakshina Kannada markets receive up-to-date benchmarks.
    """
    res = fetch_live_mandi_data(api_key)
    if not res.get("success"):
        return res

    raw_records = res.get("records", [])
    if not raw_records:
        return {
            "success": True,
            "message": "No Karnataka records found in the current live bulletin.",
            "records_updated": 0
        }

    matched_by_crop = {}
    parsed_entries = []

    for r in raw_records:
        norm_crop = normalize_commodity(r.get("commodity"))
        if not norm_crop:
            continue

        raw_market = r.get("market", "")
        norm_mkt = normalize_market(raw_market)
        
        # Parse date (API format is DD/MM/YYYY)
        raw_date = r.get("arrival_date", "")
        try:
            dt = datetime.strptime(raw_date, "%d/%m/%Y")
            iso_date = dt.strftime("%Y-%m-%d")
        except Exception:
            dt = datetime.today()
            iso_date = dt.strftime("%Y-%m-%d")

        try:
            modal_price = float(r.get("modal_price", 0) or 0)
            min_price = float(r.get("min_price", 0) or modal_price)
            max_price = float(r.get("max_price", 0) or modal_price)
        except (ValueError, TypeError):
            continue

        if modal_price <= 0:
            continue

        entry = {
            "date": iso_date,
            "state": "Karnataka",
            "district": r.get("district", "Dakshina Kannada"),
            "market": norm_mkt,
            "commodity": norm_crop,
            "variety": r.get("variety", "Local") or "Local",
            "arrival_qty": 50,  # default estimated mandi lot
            "rainfall_mm": 0.0,
            "month": dt.month,
            "festival_flag": 0,
            "min_price": int(min_price),
            "max_price": int(max_price),
            "modal_price": int(modal_price),
            "source": "Agmarknet Live API",
            "month_name": dt.strftime("%B")
        }
        parsed_entries.append(entry)

        matched_by_crop.setdefault(norm_crop, []).append(entry)

    if not parsed_entries:
        return {
            "success": True,
            "message": "No price updates found for target commodities (Arecanut, Banana, Coconut, Pepper, Cashew).",
            "records_updated": 0
        }

    # If Dakshina Kannada specific markets aren't directly reporting today,
    # generate benchmark entries for standard DK markets based on state averages for that commodity
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    inserted_count = 0

    try:
        # First, insert exact parsed entries
        for entry in parsed_entries:
            cur.execute("""
                DELETE FROM prices 
                WHERE Date = ? AND Market = ? AND Commodity = ?
            """, (entry["date"], entry["market"], entry["commodity"]))

            cur.execute("""
                INSERT INTO prices (
                    Date, State, District, Market, Commodity, Variety,
                    Arrival_Qty, Rainfall_mm, Month, Festival_Flag,
                    Min_Price, Max_Price, Modal_Price, Source, Month_Name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry["date"], entry["state"], entry["district"], entry["market"],
                entry["commodity"], entry["variety"], entry["arrival_qty"],
                entry["rainfall_mm"], entry["month"], entry["festival_flag"],
                entry["min_price"], entry["max_price"], entry["modal_price"],
                entry["source"], entry["month_name"]
            ))
            inserted_count += 1

        # Second: Ensure the primary 7 Dakshina Kannada markets have current day entries
        # for available commodities by using regional weighted averages if not specifically reported
        for crop, entries in matched_by_crop.items():
            avg_modal = int(sum(e["modal_price"] for e in entries) / len(entries))
            avg_min = int(sum(e["min_price"] for e in entries) / len(entries))
            avg_max = int(sum(e["max_price"] for e in entries) / len(entries))
            ref_date = entries[0]["date"]
            ref_month = entries[0]["month"]
            ref_month_name = entries[0]["month_name"]

            for target_mkt in TARGET_MARKETS:
                # Check if this target market was already directly inserted
                cur.execute("""
                    SELECT COUNT(*) FROM prices 
                    WHERE Date = ? AND Market = ? AND Commodity = ?
                """, (ref_date, target_mkt, crop))
                already_exists = cur.fetchone()[0] > 0

                if not already_exists:
                    cur.execute("""
                        INSERT INTO prices (
                            Date, State, District, Market, Commodity, Variety,
                            Arrival_Qty, Rainfall_mm, Month, Festival_Flag,
                            Min_Price, Max_Price, Modal_Price, Source, Month_Name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ref_date, "Karnataka", "Dakshina Kannada", target_mkt,
                        crop, "Local", 50, 0.0, ref_month, 0,
                        avg_min, avg_max, avg_modal, "Agmarknet Live Benchmark", ref_month_name
                    ))
                    inserted_count += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "success": True,
        "records_updated": inserted_count,
        "latest_date": parsed_entries[0]["date"] if parsed_entries else None,
        "crops_updated": list(matched_by_crop.keys()),
        "message": f"Successfully synced {inserted_count} live mandi records for {len(matched_by_crop)} crops."
    }

_last_sync_timestamp = 0
_sync_lock = threading.Lock()

def auto_sync_if_needed(max_age_hours=3):
    """
    Checks if today's mandi data is present or if data is older than max_age_hours.
    If sync is needed, performs it automatically without user intervention.
    Thread-safe and falls back gracefully.
    """
    global _last_sync_timestamp
    now = time.time()
    today_str = datetime.today().strftime("%Y-%m-%d")

    # If synced recently within max_age_hours, use current data
    if (now - _last_sync_timestamp) < (max_age_hours * 3600):
        return {"status": "fresh"}

    # Check database for today's date
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT MAX(Date) FROM prices").fetchone()
        conn.close()
        max_date = row[0] if row else ""
        if max_date >= today_str and (now - _last_sync_timestamp) < (6 * 3600):
            _last_sync_timestamp = now
            return {"status": "up_to_date", "latest_date": max_date}
    except Exception as e:
        print(f"[live_price_sync] DB check error: {e}")

    # Needs sync
    acquired = _sync_lock.acquire(blocking=False)
    if not acquired:
        return {"status": "in_progress"}

    try:
        print("🌾 [AutoSync] Triggering live price update from Data.gov.in...")
        res = sync_live_prices()
        _last_sync_timestamp = time.time()
        print(f"🌾 [AutoSync] {res.get('message', res)}")
        return res
    except Exception as e:
        print(f"⚠️ [AutoSync] Auto-sync failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        _sync_lock.release()

if __name__ == "__main__":
    print("Testing live price sync with Data.gov.in...")
    result = sync_live_prices()
    print("Result:", json.dumps(result, indent=2))
