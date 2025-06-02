#!/usr/bin/env python3
import os
import json
import asyncio
import aiohttp
import matplotlib.pyplot as plt
import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.feature import NaturalEarthFeature
from pyproj import Geod
from pathlib import Path

# ───────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION: set Cartopy data directory and force-download of NE assets
# ───────────────────────────────────────────────────────────────────────────────

# Use project-root-relative paths for assets
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CARTOPY_DATA_DIR = BASE_DIR / "server-assets" / "persistent" / "cartopy"
AIRPORT_CACHE_FILE = BASE_DIR / "server-assets" / "persistent" / "airport_cache.json"
OUTPUT_DIR = BASE_DIR / "static" / "assets" / "flight_routes_temp"

# Ensure the directories exist
os.makedirs(CARTOPY_DATA_DIR, exist_ok=True)
os.makedirs(AIRPORT_CACHE_FILE.parent, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Point Cartopy to use this directory
cartopy.config["data_dir"] = str(CARTOPY_DATA_DIR)

# Force-download of Natural Earth features at multiple resolutions
for scale in ("110m", "50m", "10m"):
    _ = NaturalEarthFeature("physical", "land", scale)
    _ = NaturalEarthFeature("physical", "ocean", scale)
    _ = NaturalEarthFeature("physical", "coastline", scale)

# ───────────────────────────────────────────────────────────────────────────────
#  DEBUG LOGGER
# ───────────────────────────────────────────────────────────────────────────────

DEBUG_MODE = False

def debug_log(*args):
    if DEBUG_MODE:
        print("[generate_flightroute DEBUG]", *args)

# ───────────────────────────────────────────────────────────────────────────────
#  ASYNC AIRPORT COORDINATE CACHING
# ───────────────────────────────────────────────────────────────────────────────

async def async_get_airport_coordinates(
    iata_code,
    cache_file=AIRPORT_CACHE_FILE,
    session=None,
    max_retries=5,
    initial_delay=2
):
    """
    Async version: Returns (longitude, latitude) for the given IATA code. Checks local
    JSON cache; if not found, queries Nominatim and stores the result in cache.
    Retries with exponential backoff on 403 errors.
    """
    # Load existing cache (or create an empty dict if file does not exist)
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    # If already cached, return it
    if iata_code in cache:
        lon, lat = cache[iata_code]
        debug_log(f"Cache hit for {iata_code}: ({lon}, {lat})")
        return (lon, lat)

    # Otherwise, query Nominatim
    url = f"https://nominatim.openstreetmap.org/search?q={iata_code}+Airport&format=json&limit=1"
    headers = {"User-Agent": "mihais-ai-playground/hackatron-demo"}
    debug_log(f"Requesting {url}")
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    retries = 0
    delay = initial_delay
    while retries < max_retries:
        async with session.get(url, headers=headers) as resp:
            debug_log(f"Nominatim status: {resp.status}")
            if resp.status == 403:
                if retries < max_retries - 1:
                    debug_log(f"403 Forbidden; retrying after {delay} seconds...")
                    await asyncio.sleep(delay)
                    retries += 1
                    delay *= 2
                    continue
                else:
                    raise Exception(f"Nominatim 403 Forbidden for {iata_code}")
            data = await resp.json()

        if close_session:
            await session.close()

        if not data:
            raise ValueError(f"Airport '{iata_code}' not found by Nominatim.")
        lon, lat = float(data[0]["lon"]), float(data[0]["lat"])
        cache[iata_code] = [lon, lat]
        with open(cache_file, "w") as f:
            json.dump(cache, f, indent=2)
        debug_log(f"Cached {iata_code}: ({lon}, {lat})")
        return (lon, lat)

    raise Exception(f"Nominatim 403 Forbidden for {iata_code} after {max_retries} retries.")

async def async_get_all_airport_coordinates(
    airport_codes,
    cache_file=AIRPORT_CACHE_FILE
):
    """Async batch lookup for a list of IATA codes."""
    async with aiohttp.ClientSession() as session:
        tasks = [
            async_get_airport_coordinates(code, cache_file, session)
            for code in airport_codes
        ]
        return await asyncio.gather(*tasks)

# ───────────────────────────────────────────────────────────────────────────────
#  MAIN FUNCTION: create_clean_route_map (async version)
# ───────────────────────────────────────────────────────────────────────────────

async def create_clean_route_map(
    airport_codes,
    output_file="flight_route.png",
    extra_lon_margin=0.2,
    extra_lat_margin=0.1,
    npts=50
):
    """
    Async version: Draws great-circle flight routes between a sequence of IATA codes.

    Parameters
    ----------
    airport_codes : list of str
        List of IATA codes (e.g., ["OTP", "JFK", "LAX", "SFO"]).
    output_file : str
        Filename for the saved PNG (transparent background, bbox_inches="tight").
    extra_lon_margin : float
        Fractional padding in longitude around the minimal bounding box. E.g., 0.2 → 20%.
    extra_lat_margin : float
        Fractional padding in latitude around the minimal bounding box. E.g., 0.1 → 10%.
    npts : int
        Number of intermediate points for each great-circle segment.
    """
    # 1) Broadcast async fetch of all airport coordinates (with caching)
    coords = await async_get_all_airport_coordinates(airport_codes)

    # 2) Collect all lons/lats seen (airports + intermediate points)
    all_lons = []
    all_lats = []
    for lon, lat in coords:
        all_lons.append(lon)
        all_lats.append(lat)

    # 3) Initialize pyproj.Geod for great-circle calculations (WGS84 ellipsoid)
    geod = Geod(ellps="WGS84")

    # 4) Create a PlateCarree figure (we will set extent manually)
    fig = plt.figure(figsize=(16, 12), facecolor="none")
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    # 5) Remove the default map frame/spines
    ax.spines["geo"].set_visible(False)

    # 6) Draw minimal land/ocean/coastline features for context
    ax.add_feature(cfeature.LAND, facecolor="#f0f0f0", zorder=0)
    ax.add_feature(cfeature.OCEAN, facecolor="#d0e5ff", zorder=0)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.7, zorder=0)

    # 7) Prepare a color palette for multiple segments (highly differentiated)
    colors = [
        "#e41a1c",
        "#377eb8",
        "#4daf4a",
        "#984ea3",
        "#ff7f00",
        "#ffff33",
        "#a65628",
        "#f781bf",
        "#999999",
        "#1b9e77",
        "#d95f02",
        "#7570b3",
        "#e7298a",
        "#66a61e",
        "#e6ab02",
    ]

    # 8) For each consecutive airport pair, compute & plot the great-circle arc + arrow
    for i in range(len(coords) - 1):
        start_lon, start_lat = coords[i]
        end_lon, end_lat = coords[i + 1]

        # 8a) Generate intermediate points along the geodesic
        intermediate = geod.npts(start_lon, start_lat, end_lon, end_lat, npts)

        # Build lists of lons/lats including both endpoints
        lons = [start_lon] + [pt[0] for pt in intermediate] + [end_lon]
        lats = [start_lat] + [pt[1] for pt in intermediate] + [end_lat]

        # 8b) Add these to the “all_lons/all_lats” for bounding-box calculations
        all_lons.extend(lons)
        all_lats.extend(lats)

        # 8c) Plot the curved flight path (great-circle)
        ax.plot(
            lons,
            lats,
            color=colors[i % len(colors)],
            linewidth=3,
            transform=ccrs.Geodetic(),
            zorder=2,
        )

        # 8d) Place a small arrow at the midpoint of that arc
        mid_idx = len(lons) // 2
        arrow_lon, arrow_lat = lons[mid_idx], lats[mid_idx]
        next_idx = min(mid_idx + 1, len(lons) - 1)
        target_lon, target_lat = lons[next_idx], lats[next_idx]

        ax.annotate(
            "",
            xy=(target_lon, target_lat),
            xytext=(arrow_lon, arrow_lat),
            arrowprops=dict(
                arrowstyle="->",
                color=colors[i % len(colors)],
                lw=2,
                mutation_scale=15,
            ),
            transform=ccrs.Geodetic(),
            zorder=3,
        )

    # 9) Plot each airport as a marker + a tight white label bubble
    for i, (lon, lat) in enumerate(coords):
        ax.plot(
            lon,
            lat,
            marker="o",
            markersize=8,
            color=colors[i % len(colors)],
            markeredgecolor="black",
            markeredgewidth=1,
            transform=ccrs.Geodetic(),
            zorder=4,
        )
        ax.text(
            lon + 1.5,  # shift text slightly east so it doesn’t overlap the dot
            lat,
            airport_codes[i],
            fontsize=11,
            weight="bold",
            transform=ccrs.Geodetic(),
            bbox=dict(
                facecolor="white",
                alpha=0.8,
                pad=0.5,                 # smaller padding
                edgecolor="none",
                boxstyle="round,pad=0.2",  # tight round box
            ),
            zorder=5,
        )

    # 10) Compute the bounding box of all points (with separate lon/lat margins)
    min_lon = min(all_lons)
    max_lon = max(all_lons)
    min_lat = min(all_lats)
    max_lat = max(all_lats)

    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat

    # Expand by lon/lat margins on each side
    pad_lon = lon_range * extra_lon_margin
    pad_lat = lat_range * extra_lat_margin

    lon_min_display = max(min_lon - pad_lon, -180)
    lon_max_display = min(max_lon + pad_lon, 180)
    lat_min_display = max(min_lat - pad_lat, -90)
    lat_max_display = min(max_lat + pad_lat, 90)

    ax.set_extent(
        [lon_min_display, lon_max_display, lat_min_display, lat_max_display],
        crs=ccrs.PlateCarree()
    )

    # 11) Save as a transparent PNG without extra whitespace
    plt.savefig(output_file, transparent=True, bbox_inches="tight", pad_inches=0, dpi=200)
    plt.close()
    print(f"Clean map saved to {output_file}")

# ───────────────────────────────────────────────────────────────────────────────
#  IMPORTABLE ENTRY POINT
# ───────────────────────────────────────────────────────────────────────────────

# Sample usage for testing:

async def main():
    await create_clean_route_map(
        ["OTP", "BCN", "JFK", "LAX", "SFO", "SEA", "YVR", "YYZ", "MIA"],
        output_file="flight_route_bigger5.png",
        extra_lon_margin=0.30,   # 30% padding in longitude (WIDTH)
        extra_lat_margin=0.70,   # 70% padding in latitude (HEIGHT)
        npts=50
    )

if __name__ == "__main__":
    asyncio.run(main())
