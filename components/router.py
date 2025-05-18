from reactpy import component, html
from reactpy_router import browser_router, route
from components.home import Home
from components.health.recipe_maker import RecipeMaker
from components.qol.spell_check import SpellCheck
from components.qol.translator import Translator
from components.qol.text_summarizer import TextSummarizer
from components.fun.roast_battle import BotVsBotRoastBattle
from components.common.not_found import NotFound

@component
def RootRouter():
    return browser_router(
        route("/", Home()),
        route("/health/recipe-maker", RecipeMaker()),
        route("/qol/spell-check", SpellCheck()),
        route("/qol/translator", Translator()),
        route("/qol/text-summarizer", TextSummarizer()),
        route("/fun/roast-battle", BotVsBotRoastBattle()),
        route("{404:any}", NotFound())
    )
