from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from reactpy.backend.fastapi import configure, Options
from reactpy import html
import os
import time
import asyncio

from components.common.router import RootRouter

app = FastAPI()

# Middleware to set User-Agent header
@app.middleware("http")
async def add_user_agent_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["user-agent"] = "SlackID U08RP1Z64EN"
    return response

# Mount your static assets
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure the ReactPy app
configure(
    app, RootRouter,
    options=Options(
        head=html.head(
            html.title("Mihai's AI Playground"),
            html.link({"rel": "icon", "type": "image/png", "href": "/static/favicon.ico"}),
            html.link({"rel": "apple-touch-icon", "href": "/apple-touch-icon.png"})
        )
    )
)

# Clean up old tts files in static/assets/tts_temp (max age: 1 hour)
dir_path = "static/assets/tts_temp"
MAX_AGE_SECONDS = 60 * 60  # 1 hour
CLEANUP_INTERVAL = 60 * 60  # 1 hour

def cleanup_old_wavs():
    if os.path.exists(dir_path):
        now = time.time()
        removed = 0
        for f in os.listdir(dir_path):
            fpath = os.path.join(dir_path, f)
            if os.path.isfile(fpath) and f.endswith('.wav'):
                try:
                    if now - os.path.getmtime(fpath) > MAX_AGE_SECONDS:
                        os.remove(fpath)
                        removed += 1
                except Exception:
                    pass
        if removed:
            print(f"Cleaned up {removed} old .wav files in {dir_path}.")
    else:
        print(f"{dir_path} does not exist, no cleanup needed.")

async def periodic_cleanup():
    while True:
        cleanup_old_wavs()
        await asyncio.sleep(CLEANUP_INTERVAL)

@app.on_event("startup")
async def start_periodic_cleanup():
    asyncio.create_task(periodic_cleanup())

# Icons and favicons at root for iOS/browser compatibility
@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/apple-touch-icon.png")
def apple_icon():
    return FileResponse("static/favicon_io/apple-touch-icon.png")

@app.get("/android-chrome-192x192.png")
def android_192():
    return FileResponse("static/favicon_io/android-chrome-192x192.png")

@app.get("/android-chrome-512x512.png")
def android_512():
    return FileResponse("static/favicon_io/android-chrome-512x512.png")

@app.get("/favicon-16x16.png")
def favicon_16():
    return FileResponse("static/favicon_io/favicon-16x16.png")

@app.get("/favicon-32x32.png")
def favicon_32():
    return FileResponse("static/favicon_io/favicon-32x32.png")

@app.get("/site.webmanifest")
def site_manifest():
    return FileResponse("static/favicon_io/site.webmanifest")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8084, reload=True)
