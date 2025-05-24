from reactpy import component, html, use_state

@component
def Home():
    search, set_search = use_state("")
    tab, set_tab = use_state("learning")

    # Module data for easier filtering
    modules = {
        "learning": [
            {"title": "AI Language Buddy 🌍", "desc": "Practice your target language with an AI buddy!", "href": "/learning/language-buddy"},
            {"title": "AI Spell Check 📝", "desc": "Correct your writing, tone and much more.", "href": "/learning/spell-check"},
            {"title": "AI Translator 🌎", "desc": "Translate text between multiple languages.", "href": "/learning/translator"},
            {"title": "AI Text Summarizer 📚", "desc": "Summarize long texts into concise summaries.", "href": "/learning/text-summarizer"},
        ],
        "health": [
            {"title": "AI Recipe Maker 🍳", "desc": "Input your ingredients and let AI suggest recipes. Customize how healthy the recipes should be!", "href": "/health/recipe-maker"},
            {"title": "AI Calorie Tracker 🔢", "desc": "Track your daily calorie intake with the help of AI.", "href": "/health/calorie-tracker"},
        ],
        "tools": [
            {"title": "AI PC Part Picker 🖥️", "desc": "Get AI-generated recommendations for PC parts based on your preferences.", "href": "/tools/pc-part-picker"},
            {"title": "AI Color Palette Picker 🎨", "desc": "Generate color palettes for your projects with AI.", "href": "/tools/color-picker"},
        ],
        "fun": [
            {"title": "Bot Vs Bot AI Roast Battle 🔥", "desc": "Watch two AI bots engage in a hilarious roast battle!", "href": "/fun/roast-battle"},
            {"title": "AI Personality Quiz 🎭", "desc": "Answer fun questions and get a playful AI-generated personality analysis!", "href": "/fun/personality-quiz"},
            {"title": "Reddit-like Storyteller 📖", "desc": "Generate stories in the style of your favorite subreddits.", "href": "/fun/reddit-like-storyteller"},
            {"title": "Character Chat 🤖", "desc": "Chat with your favorite cartoon characters!", "href": "/fun/character-chat"},
        ]
    }
    categories = [
        ("learning", "Learning 📚"),
        ("health", "Health 🥗"),
        ("tools", "QOL Tools ✨"),
        ("fun", "Fun 🤖")
    ]

    def filtered_cards():
        cards = []
        # If search is active, search all modules in all categories
        if search.strip():
            for cat, mods in modules.items():
                for m in mods:
                    if search.lower() in m["title"].lower() or search.lower() in m["desc"].lower():
                        cards.append(
                            html.div({"class": "card"},
                                html.h3(m["title"]),
                                html.p(m["desc"]),
                                html.a({"class": "btn-gradient", "href": m["href"]}, f"Go to {m['title'].split(' ')[0]}")
                            )
                        )
            if not cards:
                cards.append(html.p({"style": {"color": "#888", "marginTop": "2rem"}}, "No modules found."))
            return cards
        # Otherwise, show modules for the selected tab
        for m in modules[tab]:
            cards.append(
                html.div({"class": "card"},
                    html.h3(m["title"]),
                    html.p(m["desc"]),
                    html.a({"class": "btn-gradient", "href": m["href"]}, f"Go to {m['title'].split(' ')[0]}")
                )
            )
        return cards

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/home.css"}),
        html.header(
            html.h1("Mihai's AI Playground"),
            html.p("Explore fun and useful AI-powered tools!")
        ),
        html.div(
            {"class": "home-search-tabs"},
            html.input({
                "type": "text",
                "placeholder": "Search modules...",
                "value": search,
                "onInput": lambda e: set_search(e["target"]["value"]),
                "className": "home-search-bar"
            }),
            html.div(
                {"class": "home-tabs"},
                *[
                    html.button({
                        "className": f"home-tab-btn{' active' if tab == cat[0] else ''}",
                        "onClick": lambda e, c=cat[0]: set_tab(c)
                    }, cat[1])
                    for cat in categories
                ]
            )
        ),
        html.main(
            html.section(
                {"id": tab},
                html.h2({"class": "section-title"}, dict(categories)[tab]),
                *filtered_cards()
            )
        ),
        html.footer(
            html.p("© 2025 Mihai's AI Playground")
        )
    )
