from reactpy import component, html

@component
def Home():
    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/home.css"}),
        html.header(
            html.h1("Mihai's AI Playground"),
            html.p("Explore fun and useful AI-powered tools!")
        ),
        html.main(
            html.section(
                {"id": "learning"},
                html.h2({"class": "section-title"}, "Learning 📚"),
                html.div(
                    {"class": "card"},
                    html.h3("AI Language Buddy 🌍"),
                    html.p("Practice your target language with an AI buddy!"),
                    html.a({"class": "btn-gradient", "href": "/learning/language-buddy"}, "Go to AI Language Buddy")
                ),
                html.div(
                    {"class": "card"},
                    html.h3("AI Spell Check 📝"),
                    html.p("Correct your writing, tone and much more."),
                    html.a({"class": "btn-gradient", "href": "/qol/spell-check"}, "Go to AI Spell Check")
                ),
                html.div(
                    {"class": "card"},
                    html.h3("AI Translator 🌎"),
                    html.p("Translate text between multiple languages."),
                    html.a({"class": "btn-gradient", "href": "/qol/translator"}, "Go to AI Translator")
                ),
                html.div(
                    {"class": "card"},
                    html.h3("AI Text Summarizer 📚"),
                    html.p("Summarize long texts into concise summaries."),
                    html.a({"class": "btn-gradient", "href": "/qol/text-summarizer"}, "Go to AI Text Summarizer")
                )
            ),
            html.section(
                {"id": "health"},
                html.h2({"class": "section-title"}, "Health 🥗"),
                html.div(
                    {"class": "card"},
                    html.h3("AI Recipe Maker 🍳"),
                    html.p("Input your ingredients and let AI suggest recipes. Customize how healthy the recipes should be!"),
                    html.a({"class": "btn-gradient", "href": "/health/recipe-maker"}, "Go to AI Recipe Maker")
                ),
                html.div(
                    {"class": "card"},
                    html.h3("AI Calorie Tracker 🔢"),
                    html.p("Track your daily calorie intake with the help of AI."),
                    html.a({"class": "btn-gradient", "href": "/health/calorie-tracker"}, "Go to AI Calorie Tracker")
                ),
            ),
            html.section(
                {"id": "quality-of-life"},
                html.h2({"class": "section-title"}, "Quality of Life ✨"),
                html.div(
                    {"class": "card"},
                    html.h3("AI PC Part Picker 🖥️"),
                    html.p("Get AI-generated recommendations for PC parts based on your preferences."),
                    html.a({"class": "btn-gradient", "href": "/qol/pc-part-picker"}, "Go to AI PC Part Picker")
                )
            ),
            html.section(
                {"id": "fun"},
                html.h2({"class": "section-title"}, "Fun 🤖"),
                html.div(
                    {"class": "card"},
                    html.h3("Bot Vs Bot AI Roast Battle 🔥"),
                    html.p("Watch two AI bots engage in a hilarious roast battle!"),
                    html.a({"class": "btn-gradient", "href": "/fun/roast-battle"}, "Go to AI Roast Battle")
                ),
                html.div(
                    {"class": "card"},
                    html.h3("AI Personality Quiz 🎭"),
                    html.p("Answer fun questions and get a playful AI-generated personality analysis!"),
                    html.a({"class": "btn-gradient", "href": "/fun/personality-quiz"}, "Go to AI Personality Quiz")
                ),
                html.div(
                    {"class": "card"},
                    html.h3("Reddit-like Storyteller 📖"),
                    html.p("Generate stories in the style of your favorite subreddits."),
                    html.a({"class": "btn-gradient", "href": "/fun/reddit-like-storyteller"}, "Go to AI Storyteller")
                )
            ),
        ),
        html.footer(
            html.p("© 2025 Mihai's AI Playground")
        )
    )
