from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from reactpy.backend.fastapi import configure

from components.router import RootRouter

app = FastAPI()

# Middleware to set User-Agent header
@app.middleware("http")
async def add_user_agent_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["user-agent"] = "SlackID U08RP1Z64EN"
    return response

# Mount your static assets
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount the SPA router at root
configure(app, RootRouter)

# Apple icons and favicons at root for iOS/browser compatibility
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
