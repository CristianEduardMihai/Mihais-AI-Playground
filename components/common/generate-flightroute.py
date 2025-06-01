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

# ───────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION: set Cartopy data directory and force-download of NE assets
# ───────────────────────────────────────────────────────────────────────────────

CARTOPY_DATA_DIR =   "../../server-assets/persistent/cartopy"
AIRPORT_CACHE_FILE = "../../server-assets/persistent/airport_cache.json"

# Ensure the directories exist
os.makedirs(CARTOPY_DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(AIRPORT_CACHE_FILE), exist_ok=True)

# Point Cartopy to use this directory
cartopy.config["data_dir"] = CARTOPY_DATA_DIR

# Force-download of Natural Earth features at multiple resolutions (so that
# on the first run, all required shapefiles are pulled into CARTOPY_DATA_DIR).
for scale in ("110m", "50m", "10m"):
    _ = NaturalEarthFeature("physical", "land", scale)
    _ = NaturalEarthFeature("physical", "ocean", scale)
    _ = NaturalEarthFeature("physical", "coastline", scale)

# ───────────────────────────────────────────────────────────────────────────────
#  ASYNC AIRPORT COORDINATE CACHING
# ───────────────────────────────────────────────────────────────────────────────

async def async_get_airport_coordinates(iata_code, cache_file=AIRPORT_CACHE_FILE, session=None):
    """
    Async version: Returns (longitude, latitude) for the given IATA code. Checks local
    JSON cache; if not found, queries Nominatim and stores the result in cache.
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
        return (lon, lat)

    # Otherwise, geocode via Nominatim (async)
    url = f"https://nominatim.openstreetmap.org/search?q={iata_code}+Airport&format=json&limit=1"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"}
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True
    async with session.get(url, headers=headers) as resp:
        data = await resp.json()
    if close_session:
        await session.close()
    if not data:
        raise ValueError(f"Airport '{iata_code}' not found by Nominatim.")
    lon, lat = float(data[0]["lon"]), float(data[0]["lat"])
    cache[iata_code] = [lon, lat]
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2)
    return (lon, lat)

async def async_get_all_airport_coordinates(airport_codes, cache_file=AIRPORT_CACHE_FILE):
    """Async batch lookup for a list of IATA codes."""
    async with aiohttp.ClientSession() as session:
        tasks = [async_get_airport_coordinates(code, cache_file, session) for code in airport_codes]
        return await asyncio.gather(*tasks)

# ───────────────────────────────────────────────────────────────────────────────
#  MAIN FUNCTION: create_clean_route_map (async version)
# ───────────────────────────────────────────────────────────────────────────────

async def create_clean_route_map(
    airport_codes,
    output_file="flight_route.png",
    extra_margin=0.2,
    npts=50
):
    """
    Async version. Draws great-circle flight routes between a sequence of IATA airport codes.
    """
    coords = await async_get_all_airport_coordinates(airport_codes)
    all_lons = []
    all_lats = []
    for lon, lat in coords:
        all_lons.append(lon)
        all_lats.append(lat)
    geod = Geod(ellps="WGS84")
    fig = plt.figure(figsize=(16, 12), facecolor="none")
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.spines["geo"].set_visible(False)
    ax.add_feature(cfeature.LAND, facecolor="#f0f0f0", zorder=0)
    ax.add_feature(cfeature.OCEAN, facecolor="#d0e5ff", zorder=0)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.7, zorder=0)
    colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3"]
    for i in range(len(coords) - 1):
        start_lon, start_lat = coords[i]
        end_lon, end_lat = coords[i + 1]
        intermediate = geod.npts(start_lon, start_lat, end_lon, end_lat, npts)
        lons = [start_lon] + [pt[0] for pt in intermediate] + [end_lon]
        lats = [start_lat] + [pt[1] for pt in intermediate] + [end_lat]
        all_lons.extend(lons)
        all_lats.extend(lats)
        ax.plot(
            lons,
            lats,
            color=colors[i % len(colors)],
            linewidth=3,
            transform=ccrs.Geodetic(),
            zorder=2,
        )
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
            lon + 1.5,
            lat,
            airport_codes[i],
            fontsize=11,
            weight="bold",
            transform=ccrs.Geodetic(),
            bbox=dict(
                facecolor="white",
                alpha=0.8,
                pad=0.5,
                edgecolor="none",
                boxstyle="round,pad=0.2",
            ),
            zorder=5,
        )
    min_lon = min(all_lons)
    max_lon = max(all_lons)
    min_lat = min(all_lats)
    max_lat = max(all_lats)
    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat
    pad_lon = lon_range * extra_margin
    pad_lat = lat_range * extra_margin
    lon_min_display = max(min_lon - pad_lon, -180)
    lon_max_display = min(max_lon + pad_lon, 180)
    lat_min_display = max(min_lat - pad_lat, -90)
    lat_max_display = min(max_lat + pad_lat, 90)
    ax.set_extent(
        [lon_min_display, lon_max_display, lat_min_display, lat_max_display],
        crs=ccrs.PlateCarree()
    )
    plt.savefig(output_file, transparent=True, bbox_inches="tight", pad_inches=0, dpi=200)
    plt.close()
    print(f"Clean map saved to {output_file}")

# ───────────────────────────────────────────────────────────────────────────────
#  IMPORTABLE ENTRY POINT
# ───────────────────────────────────────────────────────────────────────────────

async def main():
    await create_clean_route_map(
        ["OTP", "JFK", "LAX", "SFO", "YYZ", "VKO", "OTP"],
        "flight_route.png",
        extra_margin=0.2
    )

if __name__ == "__main__":
    asyncio.run(main())
