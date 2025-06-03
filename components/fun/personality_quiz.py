from reactpy import component, html, use_state
import asyncio
import aiohttp
import markdown

@component
def PersonalityQuiz():
    # --- state ---
    name, set_name = use_state("")
    age, set_age = use_state("")
    gender, set_gender = use_state("")
    mood, set_mood = use_state("")
    color, set_color = use_state("")
    animal, set_animal = use_state("")
    hobby, set_hobby = use_state("")
    social, set_social = use_state("")
    risk, set_risk = use_state("Medium")
    result_md, set_result_md = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")

    # --- handlers ---
    def handle_submit(_event=None):
        set_loading(True)
        set_result_md("")
        set_error("")
        import threading
        def run_async():
            async def do_request():
                prompt = (
                    "You are a playful personality analyst. "
                    "Write a playful, friendly personality analysis in Markdown. "
                    "Use bullet lists for strengths/quirks. Add a fun summary at the end. "
                    "Format all lists with newlines before each bullet. "
                    "Add fun emojis, but don't overdo it. "
                    "Use second person perspective (you, your). "
                    "IMPORTANT: Do not directly repeat the information provided in the user's answers. "
                    "Instead, derive personality traits and insights that might be suggested by their preferences. "
                    "Be creative and interpretive rather than literal. Avoid sentences like 'Your love for [hobby] shows that...' "
                    "Make connections that aren't obvious and provide a unique, insightful analysis. "
                    "Keep responses playful and upbeat, focusing on positive traits."
                )
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://ai.hackclub.com/chat/completions",
                            json={
                                "messages": [
                                    {"role": "system", "content": prompt},
                                    {"role": "user", "content": (
                                        f"User Personality Quiz:\n"
                                        f"Name: {name}\n"
                                        f"Age: {age}\n"
                                        f"Gender: {gender}\n"
                                        f"Mood: {mood}\n"
                                        f"Favorite Color: {color}\n"
                                        f"Favorite Animal: {animal}\n"
                                        f"Hobby: {hobby}\n"
                                        f"Social Level: {social}\n"
                                        f"Risk Tolerance: {risk}\n"
                                    )},
                                ],
                                "max_tokens": 350
                            },
                            headers={"Content-Type": "application/json"},
                            timeout=aiohttp.ClientTimeout(total=40)
                        ) as resp:
                            resp.raise_for_status()
                            data = await resp.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if text:
                        text = text.replace("\n*", "\n\n*").replace("\n-", "\n\n-")
                    set_result_md(text)
                except Exception as e:
                    set_error(f"Error: {e}")
                finally:
                    set_loading(False)
            asyncio.run(do_request())
        threading.Thread(target=run_async, daemon=True).start()

    # --- render ---
    from components.common.config import CACHE_SUFFIX
    return html.div(
        {"className": "personality-quiz"},
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/fun/personality_quiz.css?v={CACHE_SUFFIX}"}),
        html.div({"className": "background-gradient-blur"}),
        html.nav({"className": "global-home-btn-row"}, html.a({"href": "/", "className": "global-home-btn"}, "🏠 Home")),
        html.div(
            {"className": "form"},
            html.h2({"style": {"textAlign": "center", "color": "purple"}}, "AI Personality Quiz"),
            html.p({"className": "desc"}, "Answer a few fun questions and get your playful AI-generated personality analysis!"),

            # name
            html.div({"className": "form-group"},
                html.label({"htmlFor": "name"}, "Your Name"),
                html.input({
                    "id": "name", "type": "text", "value": name,
                    "placeholder": "e.g. Alex",
                    "onBlur": lambda e: set_name(e["target"]["value"])
                }),
            ),
            # age
            html.div({"className": "form-group"},
                html.label({"htmlFor": "age"}, "Age"),
                html.input({
                    "id": "age", "type": "text", "value": age,
                    "placeholder": "e.g. 21",
                    "onBlur": lambda e: set_age(e["target"]["value"])
                }),
            ),
            # gender
            html.div({"className": "form-group"},
                html.label({"htmlFor": "gender"}, "Gender"),
                html.select({
                    "id": "gender", "value": gender,
                    "onChange": lambda e: set_gender(e["target"]["value"])
                },
                    html.option({"value": ""}, "Select..."),
                    html.option({"value": "Male"}, "Male"),
                    html.option({"value": "Female"}, "Female"),
                    html.option({"value": "Non-binary"}, "Non-binary"),
                    html.option({"value": "Other"}, "Other"),
                    html.option({"value": "Prefer not to say"}, "Prefer not to say"),
                ),
            ),
            # mood
            html.div({"className": "form-group"},
                html.label({"htmlFor": "mood"}, "How are you feeling today?"),
                html.input({
                    "id": "mood", "type": "text", "value": mood,
                    "placeholder": "e.g. Excited, sleepy, etc.",
                    "onBlur": lambda e: set_mood(e["target"]["value"])
                }),
            ),
            # color
            html.div({"className": "form-group"},
                html.label({"htmlFor": "color"}, "Favorite Color"),
                html.input({
                    "id": "color", "type": "text", "value": color,
                    "placeholder": "e.g. Blue",
                    "onBlur": lambda e: set_color(e["target"]["value"])
                }),
            ),
            # animal
            html.div({"className": "form-group"},
                html.label({"htmlFor": "animal"}, "Favorite Animal"),
                html.input({
                    "id": "animal", "type": "text", "value": animal,
                    "placeholder": "e.g. Cat",
                    "onBlur": lambda e: set_animal(e["target"]["value"])
                }),
            ),
            # hobby
            html.div({"className": "form-group"},
                html.label({"htmlFor": "hobby"}, "A hobby you enjoy"),
                html.input({
                    "id": "hobby", "type": "text", "value": hobby,
                    "placeholder": "e.g. Painting, gaming",
                    "onBlur": lambda e: set_hobby(e["target"]["value"])
                }),
            ),
            # social
            html.div({"className": "form-group"},
                html.label({"htmlFor": "social"}, "How social are you?"),
                html.select({
                    "id": "social", "value": social,
                    "onChange": lambda e: set_social(e["target"]["value"])
                },
                    html.option({"value": ""}, "Select..."),
                    html.option({"value": "Introvert"}, "Introvert"),
                    html.option({"value": "Ambivert"}, "Ambivert"),
                    html.option({"value": "Extrovert"}, "Extrovert"),
                ),
            ),
            # risk
            html.div({"className": "form-group"},
                html.label({"htmlFor": "risk"}, "Risk Tolerance"),
                html.select({
                    "id": "risk", "value": risk,
                    "onChange": lambda e: set_risk(e["target"]["value"])
                },
                    html.option({"value": "Low"}, "Low"),
                    html.option({"value": "Medium"}, "Medium"),
                    html.option({"value": "High"}, "High"),
                ),
            ),

            # the submit button
            html.button(
                {
                    "className": "btn btn-gradient",
                    "onClick": handle_submit,
                    "disabled": loading
                },
                "Get My Personality Analysis" if not loading else "Loading..."
            ),
        ),

        # results
        html.div(
            {"className": "quiz-output"},
            html.h3("Your Personality Analysis:"),
            html.i({"style": {"color": "#888"}}, "No analysis yet.") if not result_md.strip() else
            html.div({
                "dangerouslySetInnerHTML": {"__html": markdown.markdown(result_md)},
                "key": hash(result_md)
            }),
            html.div({"style": {"color": "red"}}, error) if error else None
        )
    )