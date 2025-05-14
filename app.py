from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from reactpy.backend.fastapi import configure
from components.health.ai_recipe_maker import AIRecipeMaker

app = FastAPI()

# WIll mount the static directory to serve static files, as the home page does not require dynamic rendering
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the static HTML for the home page
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/home.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)

# Configure ReactPy components as routes
configure(app, {"/health/recipe_maker": AIRecipeMaker})