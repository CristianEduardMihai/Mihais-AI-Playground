from reactpy import component
from reactpy_router import browser_router, route
from components.common.home import Home
from components.learning.language_buddy import LanguageBuddy
from components.health.recipe_maker import RecipeMaker
from components.learning.spell_check import SpellCheck
from components.learning.translator import Translator
from components.learning.text_summarizer import TextSummarizer
from components.qol.pc_part_picker import PCPartPicker
from components.qol.color_picker import AIColorPicker
from components.fun.roast_battle import BotVsBotRoastBattle
from components.fun.personality_quiz import PersonalityQuiz
from components.fun.reddit_like_storyteller import RedditLikeStoryteller
from components.common.not_found import NotFound

@component
def RootRouter():
    return browser_router(
        route("/", Home()),
        route("/learning/language-buddy", LanguageBuddy()),
        route("/health/recipe-maker", RecipeMaker()),
        route("/learning/spell-check", SpellCheck()),
        route("/learning/translator", Translator()),
        route("/learning/text-summarizer", TextSummarizer()),
        route("/qol/pc-part-picker", PCPartPicker()),
        route("/qol/color-picker", AIColorPicker()),
        route("/fun/roast-battle", BotVsBotRoastBattle()),
        route("/fun/personality-quiz", PersonalityQuiz()),
        route("/fun/reddit-like-storyteller", RedditLikeStoryteller()),
        route("{404:any}", NotFound())
    )