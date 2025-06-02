from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from reactpy.backend.fastapi import configure, Options
from reactpy import html
from contextlib import asynccontextmanager
import os
import time
import asyncio
import re
import requests
from components.common.router import RootRouter
import components.common.calendar_db as calendar_db
from components.common.config import CACHE_SUFFIX, set_CACHE_SUFFIX

DEBUG_MODE = False  # Set to True to enable verbose debug output

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG] [app.py]", *args, **kwargs)

debug_print("app.py loaded, DEBUG_MODE is", DEBUG_MODE)

# ─── Cleanup Config ─────────────────────────────────────────────
MAX_AGE_SECONDS = 60 * 60  # 1 hour
CLEANUP_INTERVAL = 60 * 60  # 1 hour

def cleanup_temp_files():
    temp_dirs = [
        "static/assets/tts_temp",
        "static/assets/flight_routes_temp"
    ]
    MAX_AGE_SECONDS = 60 * 60  # 1 hour
    removed_total = 0
    for dir_path in temp_dirs:
        if os.path.exists(dir_path):
            now = time.time()
            removed = 0
            for f in os.listdir(dir_path):
                fpath = os.path.join(dir_path, f)
                if os.path.isfile(fpath) and (f.endswith('.wav') or f.endswith('.png')):
                    try:
                        if now - os.path.getmtime(fpath) > MAX_AGE_SECONDS:
                            os.remove(fpath)
                            removed += 1
                    except Exception:
                        pass
            if removed:
                print(f"Cleaned up {removed} old temp files in {dir_path}.")
            removed_total += removed
        else:
            print(f"{dir_path} does not exist, no cleanup needed.")
    return removed_total

async def periodic_cleanup():
    while True:
        cleanup_temp_files()
        await asyncio.sleep(CLEANUP_INTERVAL)

# ─── Lifespan for FastAPI Startup/Shutdown ─────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    debug_print("Starting FastAPI lifespan...")
    asyncio.create_task(periodic_cleanup())
    yield
    debug_print("Shutting down FastAPI lifespan...")

# ─── FastAPI App ────────────────────────────────────────────────────
app = FastAPI(lifespan=lifespan)

# ─── Middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def add_user_agent_header(request: Request, call_next):
    debug_print("Incoming request:", request.method, request.url)
    response = await call_next(request)
    debug_print("Outgoing response status:", response.status_code)
    response.headers["user-agent"] = "SlackID U08RP1Z64EN"
    return response

# ─── Static Files ───────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ─── Calendar Endpoint ──────────────────────────────────────────────
@app.get("/calendars/{user_id}")
def get_calendar(user_id: str, request: Request):
    import os
    debug_print("app.py calendar_db imported from", os.path.abspath(calendar_db.__file__))
    debug_print(f"/calendars/{{user_id}} endpoint called with user_id={user_id}")
    debug_print(f"Request path: {request.url.path}")
    debug_print(f"Request headers: {dict(request.headers)}")
    ics = calendar_db.get_calendar(user_id)
    if not ics:
        debug_print(f"No calendar found for user_id={user_id}")
        return Response(content="No calendar found.", status_code=404, media_type="text/plain")
    debug_print(f"Returning calendar for user_id={user_id}, ICS length: {len(ics)}")
    debug_print(f"ICS content (first 200 chars):\n{ics[:200]}")
    return Response(content=ics, media_type="text/calendar")

# ─── ReactPy Configuration ──────────────────────────────────────────
configure(
    app, RootRouter,
    options=Options(
        head=html.head(
            html.title("Mihai's AI Playground"),
            html.link({"rel": "icon", "type": "image/png", "href": f"/static/favicon.ico?v={CACHE_SUFFIX}"}),
            html.link({"rel": "apple-touch-icon", "href": f"/apple-touch-icon.png?v={CACHE_SUFFIX}"})
        )
    )
)

# ─── Favicon Routes ─────────────────────────────────────────────────
@app.get("/favicon.ico")
def favicon(): return FileResponse("static/favicon.ico")
@app.get("/apple-touch-icon.png")
def apple_icon(): return FileResponse("static/favicon_io/apple-touch-icon.png")
@app.get("/android-chrome-192x192.png")
def android_192(): return FileResponse("static/favicon_io/android-chrome-192x192.png")
@app.get("/android-chrome-512x512.png")
def android_512(): return FileResponse("static/favicon_io/android-chrome-512x512.png")
@app.get("/favicon-16x16.png")
def favicon_16(): return FileResponse("static/favicon_io/favicon-16x16.png")
@app.get("/favicon-32x32.png")
def favicon_32(): return FileResponse("static/favicon_io/favicon-32x32.png")
@app.get("/site.webmanifest")
def site_manifest(): return FileResponse("static/favicon_io/site.webmanifest")

# ─── GitHub Actions Run Number ───────────────────────────────────────
GITHUB_ACTIONS_URL = "https://github.com/CristianEduardMihai/Mihais-AI-Playground/actions"
def fetch_CACHE_SUFFIX():
    try:
        resp = requests.get(GITHUB_ACTIONS_URL, timeout=5) # Using requests because it's okay to block, making sure the action URL is fetched before the app starts
        if resp.ok:
            match = re.search(r"/actions/runs/(\d+)", resp.text)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None

# Set the global config variable at startup
run_number = fetch_CACHE_SUFFIX()
print("Fetched GitHub Actions run number:", run_number)
if not run_number:
    run_number = str(int(time.time()))
set_CACHE_SUFFIX(run_number)

# ─── Local Dev Entrypoint ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8084, reload=True)
