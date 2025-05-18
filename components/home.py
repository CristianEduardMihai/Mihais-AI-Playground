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
                {"id": "health"},
                html.h2({"class": "section-title"}, "Health"),
                html.div(
                    {"class": "card"},
                    html.h3("AI Recipe Maker"),
                    html.p("Input your ingredients and let AI suggest recipes. Customize how healthy the recipes should be!"),
                    html.a({"class": "btn-gradient", "href": "/health/recipe_maker"}, "Go to AI Recipe Maker")
                ),
                html.div(
                    {"class": "card"},
                    html.h3("AI Calorie Tracker"),
                    html.p("Track your daily calorie intake with the help of AI."),
                    html.a({"class": "btn-gradient", "href": "/health/calorie-tracker"}, "Go to AI Calorie Tracker")
                ),
            ),
            html.section(
                {"id": "quality-of-life"},
                html.h2({"class": "section-title"}, "Quality of Life"),
                html.div(
                    {"class": "card"},
                    html.h3("AI Spell Check"),
                    html.p("Correct your writing, tone and much more."),
                    html.a({"class": "btn-gradient", "href": "/fun/spell-check"}, "Go to AI Spell Check")
                ),
            ),
            html.section(
                {"id": "fun"},
                html.h2({"class": "section-title"}, "Fun"),
                html.div(
                    {"class": "card"},
                    html.h3("Bot Vs Bot AI Roast Battle"),
                    html.p("Watch two AI bots engage in a hilarious roast battle!"),
                    html.a({"class": "btn-gradient", "href": "/fun/roast-battle"}, "Go to AI Roast Battle")
                ),
            ),
        ),
        html.footer(
            html.p("© 2025 Mihai's AI Playground")
        )
    )
