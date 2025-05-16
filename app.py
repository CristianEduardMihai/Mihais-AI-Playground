from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from reactpy.backend.fastapi import configure, Options

from components.health.ai_recipe_maker import AIRecipeMaker
# 4 future
# from components.health.calorie_tracker import CalorieTracker
# from components.health.fun.roast_battle import RoastBattle

app = FastAPI()

# Mount your static assets and pages
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/home.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())

# === ReactPy component routes ===

# AI Recipe Maker at /health/recipe_maker
configure(
    app,
    AIRecipeMaker,
    Options(url_prefix="/health/recipe_maker"),
)

# for future
# configure(app, CalorieTracker, Options(url_prefix="/health/calorie_tracker"))
# configure(app, RoastBattle,  Options(url_prefix="/health/fun/roast-battle"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
