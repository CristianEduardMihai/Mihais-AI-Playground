import json
import time
import requests
import os

INPUT_FILE = "airports.json" # https://github.com/jbrooksuk/JSON-Airports/blob/master/airports.json
OUTPUT_FILE = "../../server-assets/persistent/airport_cache.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Load airport list and extract IATA codes
def load_iata_codes(filename):
    with open(filename, "r", encoding="utf-8") as f:
        airports = json.load(f)
    return [a["iata"] for a in airports if a.get("iata")]  # Only non-empty IATA

def fetch_airport_info(iata):
    # Query Nominatim for the airport location
    params = {
        "q": f"{iata} airport",
        "format": "json",
        "limit": 1,
        "extratags": 1,
        "namedetails": 1,
    }
    headers = {"User-Agent": "airport-cache-script/1.0"}
    resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    results = resp.json()
    if results:
        r = results[0]
        return {
            "iata": iata,
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "display_name": r.get("display_name", ""),
            "osm_id": r.get("osm_id", None),
        }
    return None

def load_existing_cache(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    return {}

def main():
    iata_codes = load_iata_codes(INPUT_FILE)
    cache = load_existing_cache(OUTPUT_FILE)
    uncached = [iata for iata in iata_codes if iata not in cache]
    print(f"Total airports: {len(iata_codes)}, Already cached: {len(cache)}, To fetch: {len(uncached)}")
    for chunk_start in range(0, len(uncached), 10):
        chunk = uncached[chunk_start:chunk_start+10]
        for i, iata in enumerate(chunk):
            print(f"[{chunk_start+i+1}/{len(uncached)}] Fetching {iata}...")
            try:
                info = fetch_airport_info(iata)
                if info:
                    # Store as [lon, lat] for generate_flightroute compatibility
                    cache[iata] = [info["lon"], info["lat"]]
                    print(f"  -> {info['lat']}, {info['lon']}")
                else:
                    print("  -> Not found")
            except Exception as e:
                print(f"  -> Error: {e}")
            time.sleep(1)
        # Write after each chunk
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        print(f"Wrote {len(cache)} airports to {OUTPUT_FILE}")
    print(f"Done. Cached {len(cache)} airports to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
