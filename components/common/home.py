from reactpy import component, html, use_state
import random

button_variations = [
    "✨ Take me there!",
    "🚀 Blast off!",
    "🎮 Let's play!",
    "🔮 Discover the magic",
    "⚡ Try it now",
    "🌟 Beam me up!",
    "🎯 Jump right in",
    "🎪 Join the fun",
    "🧠 Feed my brain",
    "🌈 Start exploring",
    "🏄‍♂️ Dive in",
    "🏃‍♀️ Let's go!",
    "🎁 Unwrap this",
    "🛸 Teleport me",
    "🔥 Fire it up!",
    "🦄 Show me magic",
    "🎭 Experience it",
    "🚂 All aboard!",
    "👾 Game on!",
    "🧪 Experiment now",
    "🌊 Make waves",
    "🎢 Let's ride!",
    "🎯 Hit the target"
]

@component
def Home():
    search, set_search = use_state("")
    tab, set_tab = use_state("learning")
    tab_clicked, set_tab_clicked = use_state(False)

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
            {"title": "AI Interview Prep Assistant 🎤", "desc": "Prepare for your next job interview with AI-generated questions and tips.", "href": "/tools/interview-prep"},
        ],
        "fun": [
            {"title": "Bot Vs Bot AI Roast Battle 🔥", "desc": "Watch two AI bots engage in a hilarious roast battle!", "href": "/fun/roast-battle"},
            {"title": "AI Personality Quiz 🎭", "desc": "Answer fun questions and get a playful AI-generated personality analysis!", "href": "/fun/personality-quiz"},
            {"title": "Reddit-like Storyteller 📖", "desc": "Generate stories in the style of your favorite subreddits.", "href": "/fun/reddit-like-storyteller"},
            {"title": "Character Chat 🤖", "desc": "Chat with your favorite cartoon characters!", "href": "/fun/character-chat"},
            {"title": "AI Coder Profile 🧑‍💻", "desc": "Upload your code and get a playful coder personality analysis!", "href": "/fun/coder-profile"},
        ]
    }
    categories = [
        ("learning", "Learning 📚"),
        ("health", "Health 🥗"),
        ("tools", "QOL Tools ✨"),
        ("fun", "Fun 🤖")
    ]

    # Dynamic gradients for each tab/category
    tab_gradients = {
        "learning": {
            # Main background: blue and light purple
            "background": "radial-gradient(circle at 20% 30%, #3a8dde 0%, transparent 60%), "
                           "radial-gradient(circle at 80% 70%, #b388ff 0%, transparent 60%), "
                           "linear-gradient(120deg, #3a8dde 0%, #b388ff 100%)",
            "button": "linear-gradient(90deg, #b388ff 0%, #3a8dde 100%)"
        },
        "health": {
            # Main background: green and yellow
            "background": "radial-gradient(circle at 20% 30%, #30ba40 0%, transparent 60%), "
                           "radial-gradient(circle at 80% 70%, #e1fc56 0%, transparent 60%), "
                           "linear-gradient(120deg, #30ba40 0%, #e1fc56 100%)",
            "button": "linear-gradient(90deg, #e1fc56 0%, #30ba40 100%)"
        },
        "tools": {
            # Main background: red and orange
            "background": "radial-gradient(circle at 20% 30%, #ab0a0a 0%, transparent 60%), "
                           "radial-gradient(circle at 80% 70%, #e06441 0%, transparent 60%), "
                           "linear-gradient(120deg, #ab0a0a 0%, #e06441 100%)",
            "button": "linear-gradient(90deg, #e06441 0%, #ab0a0a 100%)"
        },
        "dianas": {
            # Main background: pink and purple
            "background": "radial-gradient(circle at 20% 30%, #f357a8 0%, transparent 60%), "
                           "radial-gradient(circle at 80% 70%, #7b2ff2 0%, transparent 60%), "
                           "linear-gradient(120deg, #f357a8 0%, #7b2ff2 100%)",
            "button": "linear-gradient(90deg, #f357a8 0%, #7b2ff2 100%)"
        },
        # Default: fallback to Diana's colors :D
        "default": {
            "background": "radial-gradient(circle at 20% 30%, #f357a8 0%, transparent 60%), "
                           "radial-gradient(circle at 80% 70%, #7b2ff2 0%, transparent 60%), "
                           "linear-gradient(120deg, #f357a8 0%, #7b2ff2 100%)",
            "button": "linear-gradient(90deg, #f357a8 0%, #7b2ff2 100%)"
        }
    }

    def handle_tab_click(cat_key):
        set_tab(cat_key)
        set_tab_clicked(True)

    def get_bg_style():
        if not tab_clicked:
            # Show Diana's (pink) gradient until a tab is clicked
            grad = tab_gradients["dianas"]['background']
        else:
            grad = tab_gradients.get(tab, tab_gradients["default"])['background']
        return {
            "className": "background-gradient-blur",
            "style": {"background": grad}
        }

    def get_tab_btn_style(cat_key):
        grad = tab_gradients.get(cat_key, tab_gradients["default"])['button']
        return {
            "className": f"home-tab-btn{' active' if tab == cat_key else ''}",
            "style": {"background": grad}  # Only override background
        }

    def filtered_cards():
        cards = []
        # If search is active, search all modules in all categories
        if search.strip():
            for cat, mods in modules.items():
                # Use 'dianas' gradient for the 'fun' tab, otherwise use the tab's own gradient
                grad_key = "dianas" if cat == "fun" else cat
                for m in mods:
                    if search.lower() in m["title"].lower() or search.lower() in m["desc"].lower():
                        button_text = random.choice(button_variations)
                        btn_style = {"background": tab_gradients[grad_key]["button"]}
                        cards.append(
                            html.div({"class": "card"},
                                html.h3(m["title"]),
                                html.p(m["desc"]),
                                html.a({"class": "btn-gradient", "href": m["href"], "style": btn_style}, button_text)
                            )
                        )
            if not cards:
                cards.append(html.p({"style": {"color": "#888", "marginTop": "2rem"}}, "No modules found."))
            return cards
        # Otherwise, show modules for the selected tab
        for m in modules[tab]:
            button_text = random.choice(button_variations)
            # Use 'dianas' gradient for the 'fun' tab, otherwise use the tab's own gradient
            grad_key = "dianas" if tab == "fun" else tab
            btn_style = {"background": tab_gradients[grad_key]["button"]}
            cards.append(
                html.div({"class": "card"},
                    html.h3(m["title"]),
                    html.p(m["desc"]),
                    html.a({"class": "btn-gradient", "href": m["href"], "style": btn_style}, button_text)
                )
            )
        return cards

    return html.div(
        {},
        html.div(get_bg_style()),
        html.link({"rel": "stylesheet", "href": "/static/css/common/home.css"}),
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
                    html.button(
                        dict(get_tab_btn_style(cat[0]),
                             onClick=(lambda e, c=cat[0]: handle_tab_click(c))),
                        cat[1]
                    ) for cat in categories
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
            html.p([
                html.a({"href": "https://www.youtube.com/watch?v=2uC171f46Cg", "target": "_blank", "style": {"color": "#f357a8", "textDecoration": "underline"}}, "Thanks for being with us here on CNN :)")
            ])
        )
    )
