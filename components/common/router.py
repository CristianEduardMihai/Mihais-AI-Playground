from reactpy import component
from reactpy_router import browser_router, route
from components.common.home import Home
from components.learning.language_buddy import LanguageBuddy
from components.health.recipe_maker import RecipeMaker
from components.learning.spell_check import SpellCheck
from components.learning.translator import Translator
from components.learning.text_summarizer import TextSummarizer
from components.tools.pc_part_picker import PCPartPicker
from components.tools.color_picker import AIColorPicker
from components.tools.interview_prep import InterviewPrep
from components.tools.HTML5_portfolio_builder import HTML5PortfolioBuilder
from components.tools.task_organizer import TaskOrganizer
from components.tools.trip_planner import TripPlanner
from components.fun.roast_battle import BotVsBotRoastBattle
from components.fun.personality_quiz import PersonalityQuiz
from components.fun.reddit_like_storyteller import RedditLikeStoryteller
from components.fun.character_chat import CharacterChat
from components.fun.playlist_maker import PlaylistMaker
from components.fun.coder_profile import CoderProfile
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
        route("/tools/pc-part-picker", PCPartPicker()),
        route("/tools/color-picker", AIColorPicker()),
        route("/tools/interview-prep", InterviewPrep()),
        route("/tools/html5-portfolio-builder", HTML5PortfolioBuilder()),
        route("/tools/task-organizer", TaskOrganizer()),
        route("/tools/trip-planner", TripPlanner()),
        route("/fun/roast-battle", BotVsBotRoastBattle()),
        route("/fun/personality-quiz", PersonalityQuiz()),
        route("/fun/reddit-like-storyteller", RedditLikeStoryteller()),
        route("/fun/character-chat", CharacterChat()),
        route("/fun/playlist-maker", PlaylistMaker()),
        route("/fun/coder-profile", CoderProfile()),
        route("{404:any}", NotFound())
    )