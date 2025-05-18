from reactpy import component, html
from reactpy_router import browser_router, route
from components.home import Home
from components.health.recipe_maker import AIRecipeMaker
from components.fun.roast_battle import BotVsBotRoastBattle

@component
def RootRouter():
    return browser_router(
        route("/", Home()),
        route("/health/recipe_maker", AIRecipeMaker()),
        route("/fun/roast-battle", BotVsBotRoastBattle()),
        route("{404:any}", html.h1({"style": {"textAlign": "center", "marginTop": "3rem"}}, "Missing Link 🔗‍💥")),
    )
