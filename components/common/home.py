from reactpy import component, html, use_state
import random
import threading
import time

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
    search_box, set_search_box = use_state("")
    tab, set_tab = use_state("learning")
    tab_clicked, set_tab_clicked = use_state(False)
    info_open, set_info_open = use_state(None)  # Track which info box is open
    search_btn_clicked, set_search_btn_clicked = use_state(False)

    # Module data for easier filtering
    modules = {
        "learning": [
            {"title": "Language Buddy 🌍", "desc": "Practice your target language with an AI buddy!", "href": "/learning/language-buddy", "history": "One of the earliest modules, Language Buddy started as a simple chat wrapper for the AI. Over time, it evolved to provide more interactive and helpful feedback, reflecting the project's shift from just wrapping AI to integrating it as a true backend. This module showcases the project's original vision: making AI accessible in a fun way."},
            {"title": "Spell Check 📝", "desc": "Correct your writing, tone and much more.", "href": "/learning/spell-check", "history": "Spell Check is one of the earliest module, and does only basic correction. It benefited from early UI/UX improvements."},
            {"title": "Translator 🌎", "desc": "Translate text between multiple languages.", "href": "/learning/translator", "history": "The Translator module was added soon after Language Buddy, leveraging AI for text translation. It was improved with better text input handling and mobile support, and was part of the batch of modules that made the site useful for practical tasks."},
            {"title": "Text Summarizer 📚", "desc": "Summarize long texts into concise summaries.", "href": "/learning/text-summarizer", "history": "Text Summarizer was introduced as the project matured, reflecting a growing focus on productivity tools. It benefited from the improved backend and UI."},
        ],
        "health": [
            {"title": "Recipe Maker 🍳", "desc": "Input your ingredients and let AI suggest recipes. Customize how healthy the recipes should be!", "href": "/health/recipe-maker", "history": "Recipe Maker was the first module. It got a polished UI and mobile support. It was also a testbed for integrating more complex AI output into the frontend, and inspired later modules to do more with the AI's responses."},
        ],
        "tools": [
            {"title": "PC Part Picker 🖥️", "desc": "Get AI-generated recommendations for PC parts based on your preferences.", "href": "/tools/pc-part-picker", "history": "PC Part Picker was a milestone: it marked the project's move from simple text output to structured, actionable results. It was one of the first modules to use AI as a backend for generating complex, user-specific content."},
            {"title": "Color Palette Picker 🎨", "desc": "Generate color palettes for your projects with AI.", "href": "/tools/color-picker", "history": "Color Palette Picker is a turning point in the project. Here, AI output was first visualized directly in the UI (as color boxes), not just as text. This set the stage for all future modules to integrate AI results more deeply into the frontend."},
            {"title": "Interview Prep Assistant 🎤", "desc": "Prepare for your next job interview with AI-generated questions and tips.", "href": "/tools/interview-prep", "history": "Interview Prep Assistant was built as the project matured, benefiting from improved prompt engineering and UI/UX. It reflects the project's focus on practical, real-world tools powered by AI."},
            {"title": "HTML5 Portfolio Builder 🖼️", "desc": "Create a beautiful HTML5 portfolio to showcase your work, with AI assistance.", "href": "/tools/html5-portfolio-builder", "history": "Portfolio Builder started as a simple form, but quickly evolved to use AI for content generation. It was a showcase for integrating AI with persistent user data and advanced UI features."},
            {"title": "Task Organizer 📅", "desc": "Organize your tasks and calendars with AI assistance.", "href": "/tools/task-organizer", "history": "Task Organizer is the most complex module to date, featuring calendar integration and persistent storage. Its development spanned many commits, including major bugfixes, timezone handling, and UI/UX improvements. It represents the project's evolution into a true productivity platform, not just a collection of AI demos."},
        ],
        "fun": [
            {"title": "Bot Vs Bot Roast Battle 🔥", "desc": "Watch two AI bots engage in a hilarious roast battle!", "href": "/fun/roast-battle", "history": "Roast Battle was an early experiment in making AI fun and interactive. It was improved with more realistic arguments, better timing, and a mobile-friendly UI. It helped shape the playful side of the project."},
            {"title": "Personality Quiz 🎭", "desc": "Answer fun questions and get a playful AI-generated personality analysis!", "href": "/fun/personality-quiz", "history": "Personality Quiz was part of a batch of modules added after a major code reorganization. It benefited from improved backend structure and was one of the first to use AI for playful, personalized content."},
            {"title": "Reddit-like Storyteller 📖", "desc": "Generate stories in the style of your favorite subreddits.", "href": "/fun/reddit-like-storyteller", "history": "Reddit-like Storyteller was added alongside other fun modules, and was the first to use TTS (text-to-speech) for AI-generated stories. It reflects the project's technical growth and creative ambition."},
            {"title": "Character Chat 🤖", "desc": "Chat with your favorite cartoon characters!", "href": "/fun/character-chat", "history": "Character Chat was inspired by the addition of character images and a focus on playful, engaging AI. It was part of a wave of UI/UX improvements and new features."},
            {"title": "Coder Profile 🧑‍💻", "desc": "Upload your code and get a playful coder personality analysis!", "href": "/fun/coder-profile", "history": "Coder Profile was a later addition, showing the project's ability to analyze and respond to user-uploaded content. It highlights the platform's flexibility and the growing complexity of its AI integrations."},
        ]
    }
    categories = [
        ("learning", "Learning 📚"),
        ("health", "Health 🥗"),
        ("tools", "Tools ✨"),
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

    def handle_search(e=None):
        set_search(search_box)
        set_search_btn_clicked(True)
        def clear():
            time.sleep(0.45)
            set_search_btn_clicked(False)
        threading.Thread(target=clear, daemon=True).start()

    def handle_input_blur(e):
        val = e["target"]["value"]
        set_search_box(val)
        set_search(val)

    def handle_input_keydown(e):
        if e.get("key") == "Enter":
            val = e["target"]["value"]
            set_search_box(val)
            set_search(val)

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

    def info_icon(module_id, history):
        return html.span(
            {"className": "home-info-icon",
             "tabIndex": 0,
             "onMouseEnter": lambda e: set_info_open(module_id),
             "onMouseLeave": lambda e: set_info_open(None),
             "onFocus": lambda e: set_info_open(module_id),
             "onBlur": lambda e: set_info_open(None),
             "onClick": lambda e: set_info_open(module_id if info_open != module_id else None)
            },
            "ℹ️",
            info_open == module_id and html.div({"class": "home-info-tooltip"}, history) or None
        )

    def filtered_cards():
        cards = []
        if search.strip():
            for cat, mods in modules.items():
                grad_key = "dianas" if cat == "fun" else cat
                for idx, m in enumerate(mods):
                    module_id = f"{cat}-{idx}"
                    if search.lower() in m["title"].lower() or search.lower() in m["desc"].lower():
                        button_text = random.choice(button_variations)
                        btn_style = {"background": tab_gradients[grad_key]["button"]}
                        cards.append(
                            html.div({"class": "card", "style": {"position": "relative"}},
                                html.h3(
                                    {},
                                    m["title"],
                                    info_icon(module_id, m.get("history", ""))
                                ),
                                html.p(m["desc"]),
                                html.a({"class": "btn-gradient", "href": m["href"], "style": btn_style}, button_text)
                            )
                        )
            if not cards:
                cards.append(html.p({"style": {"color": "#888", "marginTop": "2rem"}}, "No modules found."))
            return cards
        for idx, m in enumerate(modules[tab]):
            module_id = f"{tab}-{idx}"
            button_text = random.choice(button_variations)
            grad_key = "dianas" if tab == "fun" else tab
            btn_style = {"background": tab_gradients[grad_key]["button"]}
            cards.append(
                html.div({"class": "card", "style": {"position": "relative"}},
                    html.h3(
                        {},
                        m["title"],
                        info_icon(module_id, m.get("history", ""))
                    ),
                    html.p(m["desc"]),
                    html.a({"class": "btn-gradient", "href": m["href"], "style": btn_style}, button_text)
                )
            )
        return cards

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.div(get_bg_style()),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/home.css?v={CACHE_SUFFIX}"}),
        html.header(
            html.h1("Mihai's AI Playground"),
            html.p("Explore fun and useful AI-powered tools!")
        ),
        html.div(
            {"class": "home-search-tabs"},
            html.div(
                {"class": "home-search-row"},
                html.input({
                    "type": "text",
                    "placeholder": "Search modules...",
                    "value": search_box,
                    "onBlur": handle_input_blur,
                    "onKeyDown": handle_input_keydown,
                    "className": "home-search-bar",
                }),
                html.button({
                    "type": "button",
                    "onClick": handle_search,
                    "className": f"btn-gradient home-search-btn{' clicked' if search_btn_clicked else ''}",
                    "tabIndex": 0,
                    "aria-label": "Search"
                }, "\U0001F50D")  # Eyeglass emoji
            ),
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