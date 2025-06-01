import os
import json
import matplotlib.pyplot as plt
import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.feature import NaturalEarthFeature
from geopy.geocoders import Nominatim
from pyproj import Geod

# ───────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION: set Cartopy data directory and force-download of NE assets
# ───────────────────────────────────────────────────────────────────────────────

CARTOPY_DATA_DIR =   "../server-assets/persistent/cartopy"
AIRPORT_CACHE_FILE = "../server-assets/persistent/airport_cache.json"

# Ensure the directories exist
os.makedirs(CARTOPY_DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(AIRPORT_CACHE_FILE), exist_ok=True)

# Point Cartopy to use this directory
cartopy.config["data_dir"] = CARTOPY_DATA_DIR

# Force-download of Natural Earth features at multiple resolutions (so that
# on the first run, all required shapefiles are pulled into CARTOPY_DATA_DIR).
# We instantiate features for 'land', 'ocean', and 'coastline' at
# 110m, 50m, and 10m resolutions.
for scale in ("110m", "50m", "10m"):
    _ = NaturalEarthFeature("physical", "land", scale)
    _ = NaturalEarthFeature("physical", "ocean", scale)
    _ = NaturalEarthFeature("physical", "coastline", scale)

# ───────────────────────────────────────────────────────────────────────────────
#  AIRPORT COORDINATE CACHING
# ───────────────────────────────────────────────────────────────────────────────

def get_airport_coordinates(iata_code, cache_file=AIRPORT_CACHE_FILE):
    """
    Returns (longitude, latitude) for the given IATA code. First checks a local
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

    # Otherwise, geocode via Nominatim
    geolocator = Nominatim(headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"})
    location = geolocator.geocode(f"{iata_code} Airport")
    if not location:
        raise ValueError(f"Airport '{iata_code}' not found by Nominatim.")

    lon, lat = location.longitude, location.latitude
    cache[iata_code] = [lon, lat]

    # Write back the updated cache
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2)

    return (lon, lat)

# ───────────────────────────────────────────────────────────────────────────────
#  MAIN FUNCTION: create_clean_route_map
# ───────────────────────────────────────────────────────────────────────────────

def create_clean_route_map(
    airport_codes,
    output_file="flight_route.png",
    extra_margin=0.2
):
    """
    Draws great-circle flight routes between a sequence of IATA airport codes,
    with control over how much “extra” map area to show around those routes.

    Parameters
    ----------
    airport_codes : list of str
        A list of IATA codes (e.g., ["OTP", "JFK", "LAX", "SFO"]). Routes are drawn
        in the given order: OTP→JFK, JFK→LAX, LAX→SFO, etc.

    output_file : str
        Filename for the saved PNG (transparent background, bbox_inches="tight").

    extra_margin : float
        Fractional padding around the minimal bounding box of all route points
        (and airports). For example, extra_margin=0.2 adds 20% of the lon/lat
        range on each side. Use 0.0 to show exactly the bounding box, or larger
        values for more “breathing room.” Defaults to 0.2.
    """
    # 1) Look up (lon, lat) for each IATA code (with caching)
    coords = []
    for code in airport_codes:
        try:
            lon_lat = get_airport_coordinates(code)
        except ValueError as e:
            print(f"Error looking up {code}: {e}")
            raise
        coords.append(lon_lat)

    # 2) Prepare lists to collect every plotted point’s lon/lat
    all_lons = []
    all_lats = []
    for lon, lat in coords:
        all_lons.append(lon)
        all_lats.append(lat)

    # 3) Initialize pyproj.Geod for great-circle calculations (WGS84 ellipsoid)
    geod = Geod(ellps="WGS84")

    # 4) Create a PlateCarree figure (we’ll set extent manually later)
    fig = plt.figure(figsize=(16, 12), facecolor="none")
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    # 5) Remove the default map frame/spines
    ax.spines["geo"].set_visible(False)

    # 6) Draw minimal land/ocean/coastline features for context
    ax.add_feature(cfeature.LAND, facecolor="#f0f0f0", zorder=0)
    ax.add_feature(cfeature.OCEAN, facecolor="#d0e5ff", zorder=0)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.7, zorder=0)

    # 7) Prepare a simple color palette for multiple segments
    colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3"]

    # 8) For each consecutive airport pair, compute & plot the great-circle arc + arrow
    for i in range(len(coords) - 1):
        start_lon, start_lat = coords[i]
        end_lon, end_lat = coords[i + 1]

        # 8a) Generate intermediate points along the geodesic:
        #     geod.npts(lon1, lat1, lon2, lat2, npts) returns a list of (lon, lat) tuples.
        npts = 100
        intermediate = geod.npts(start_lon, start_lat, end_lon, end_lat, npts)

        # Build lists of lons/lats including both endpoints
        lons = [start_lon] + [pt[0] for pt in intermediate] + [end_lon]
        lats = [start_lat] + [pt[1] for pt in intermediate] + [end_lat]

        # Add these to the “all_lons/all_lats” for bounding-box calculation
        all_lons.extend(lons)
        all_lats.extend(lats)

        # 8b) Plot the curved flight path (great-circle)
        ax.plot(
            lons,
            lats,
            color=colors[i % len(colors)],
            linewidth=3,
            transform=ccrs.Geodetic(),
            zorder=2,
        )

        # 8c) Place a small arrow at the midpoint of that arc
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
                pad=0.5,                    # smaller padding
                edgecolor="none",
                boxstyle="round,pad=0.2",   # tight round box
            ),
            zorder=5,
        )

    # 10) Compute the bounding box of all points (with extra margin)
    min_lon = min(all_lons)
    max_lon = max(all_lons)
    min_lat = min(all_lats)
    max_lat = max(all_lats)

    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat

    # Expand by extra_margin fraction on each side
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

    # 11) Save as a transparent PNG without extra whitespace
    plt.savefig(output_file, transparent=True, bbox_inches="tight", pad_inches=0, dpi=200)
    plt.close()
    print(f"Clean map saved to {output_file}")


# ───────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ───────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Example usage: draw OTP → JFK → LAX → SFO with 20% extra padding around routes
    create_clean_route_map(
        ["OTP", "JFK", "LAX", "SFO", "YYZ", "VKO", "OTP"],
        "flight_route.png",
        extra_margin=0.2
    )
