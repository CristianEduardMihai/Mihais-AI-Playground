from reactpy import component, html, use_state
import asyncio
import aiohttp
import markdown
import threading
import datetime
from components.common.config import CACHE_SUFFIX

# ───────────────────────────────────────────────────────────────────────────────
#  DEBUG LOGGER
# ───────────────────────────────────────────────────────────────────────────────

try:
    from components.common.config import DEBUG_MODE, REACTPY_DEBUG_MODE
    if REACTPY_DEBUG_MODE:
        import reactpy
        reactpy.config.REACTPY_DEBUG_MODE.current = True
        print("[workout_planner.py DEBUG] REACTPY_DEBUG_MODE imported from config.py, using value:", REACTPY_DEBUG_MODE)
    if DEBUG_MODE:
        print("[workout_planner.py DEBUG] DEBUG_MODE imported from config.py, using value:", DEBUG_MODE)
except ImportError:
    DEBUG_MODE = False
    print("Warning: DEBUG_MODE not imported from config.py, using default value False.")

def debug_log(*args):
    if DEBUG_MODE:
        print("[workout_planner.py DEBUG]", *args)

@component
def WorkoutPlanner():
    weight, set_weight = use_state("")
    target_weight, set_target_weight = use_state("")
    sex, set_sex = use_state("male")
    age, set_age = use_state("")
    height, set_height = use_state("")
    target_date, set_target_date = use_state("")
    fat_mass, set_fat_mass = use_state("")
    muscle_mass, set_muscle_mass = use_state("")
    result_html, set_result_html = use_state("")
    error, set_error = use_state("")
    loading, set_loading = use_state(False)
    show_flow, set_show_flow = use_state(False)

    def handle_submit(event):
        set_loading(True)
        set_result_html("")
        set_error("")
        debug_log("Form submitted")
        def run_async():
            async def do_request():
                try:
                    debug_log("Preparing AI prompt and user input")
                    prompt = (
                        "You are a professional fitness and nutrition assistant AI. "
                        "Your goal is to help the user safely and effectively reach their target body weight. "
                        "Use the user's provided data (current weight, target weight, biological sex, age, height, target date, and optional fat and muscle mass) "
                        "to generate a customized fitness and nutrition plan.\n\n"

                        "Format the output in clean, readable Markdown only. Do not include any introductions, explanations, or formatting syntax explanations.\n\n"

                        "### Output format:\n"
                        "# Daily Caloric Intake\n"
                        "- Total kcal/day (clearly state it)\n\n"
                        "# Macronutrient Targets\n"
                        "- Carbs: __ g/day\n"
                        "- Protein: __ g/day\n"
                        "- Fat: __ g/day\n\n"

                        "# Weekly Workout Plan\n"
                        "- List each day with:\n"
                        "  - Workout type\n"
                        "  - Suggested intensity (e.g. low, moderate, high)\n"
                        "  - Estimated duration (minutes)\n"
                        "  - Optional notes for beginners or advanced users\n\n"

                        "# Nutrition Guidelines\n"
                        "- Bullet points with specific dietary strategies and practical tips\n"
                        "- Emphasize consistency, hydration, and whole foods\n\n"

                        "# Progress Monitoring\n"
                        "- Weekly weight check\n"
                        "- Bi-weekly body measurements\n"
                        "- Monthly photos or fitness assessments\n\n"

                        "# Motivation & Sustainability\n"
                        "- Encouraging reminders and tips to stay on track\n"
                        "- Ideas to adjust the plan if life gets busy or motivation drops\n\n"

                        "## Notes:\n"
                        "- Use body composition to personalize caloric and protein needs if available.\n"
                        "- Recommend a gradual weight change pace unless the goal is short-term and realistic.\n"
                        "- Never expose calculations or formulas.\n"
                        "- Ensure tone is friendly, motivating, and actionable."
                    )
                    user_input = (
                        f"Current weight: {weight} kg\n"
                        f"Target weight: {target_weight} kg\n"
                        f"Sex: {sex}\n"
                        f"Age: {age}\n"
                        f"Height: {height} cm\n"
                        f"Target date (MM/DD/YYYY): {target_date}\n"
                        f"Current date: {datetime.datetime.now().strftime('%m/%d/%Y')}\n"
                    )
                    if fat_mass or muscle_mass:
                        user_input += f"Fat mass: {fat_mass} kg\nMuscle mass: {muscle_mass} kg\n"
                    debug_log("Prompt:", prompt)
                    debug_log("User input:", user_input)
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://ai.hackclub.com/chat/completions",
                            headers={"Content-Type": "application/json"},
                            json={
                                "messages": [
                                    {"role": "system", "content": prompt},
                                    {"role": "user", "content": user_input}
                                ]
                            },
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            debug_log("AI response status:", response.status)
                            if response.status != 200:
                                raise RuntimeError(f"AI model returned {response.status}")
                            data = await response.json()
                    md = data["choices"][0]["message"]["content"]
                    debug_log("AI raw output:", md)
                    set_result_html(f"<div class='markdown-body'>{markdown.markdown(md)}</div>")
                except Exception as e:
                    debug_log("Error in do_request:", e)
                    set_error(f"Error: {e}")
                finally:
                    set_loading(False)
            asyncio.run(do_request())
        threading.Thread(target=run_async, daemon=True).start()

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/health/workout_planner.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "global-home-btn-row"}, html.a({"href": "/", "className": "global-home-btn"}, "🏠 Home")),
        html.div({"className": "workout-planner"},
            html.h2("AI Workout Planner"),
            html.form({"className": "workout-form"},
                html.div({"className": "workout-form-group"},
                    html.label({"for": "weight"}, "Current Weight (kg):"),
                    html.input({"id": "weight", "type": "number", "min": "1", "value": weight, "onBlur": lambda e: set_weight(e["target"]["value"]), "required": True})
                ),
                html.div({"className": "workout-form-group"},
                    html.label({"for": "target_weight"}, "Target Weight (kg):"),
                    html.input({"id": "target_weight", "type": "number", "min": "1", "value": target_weight, "onBlur": lambda e: set_target_weight(e["target"]["value"]), "required": True})
                ),
                html.div({"className": "workout-form-group-dropdown"},
                    html.label({"for": "sex"}, "Sex:"),
                    html.select({"id": "sex", "className": "sex-select", "value": sex, "onChange": lambda e: set_sex(e["target"]["value"]), "required": True},
                        html.option({"value": "male"}, "Male"),
                        html.option({"value": "female"}, "Female"),
                        html.option({"value": "other"}, "Other")
                    )
                ),
                html.div({"className": "workout-form-group"},
                    html.label({"for": "age"}, "Age (years):"),
                    html.input({"id": "age", "type": "number", "min": "1", "value": age, "onBlur": lambda e: set_age(e["target"]["value"]), "required": True})
                ),
                html.div({"className": "workout-form-group"},
                    html.label({"for": "height"}, "Height (cm):"),
                    html.input({"id": "height", "type": "number", "min": "50", "value": height, "onBlur": lambda e: set_height(e["target"]["value"]), "required": True})
                ),
                html.div({"className": "workout-form-group"},
                    html.label({"for": "target_date"}, "Target Date:"),
                    html.input({"id": "target_date", "type": "date", "value": target_date, "onBlur": lambda e: set_target_date(e["target"]["value"]), "required": True})
                ),
                html.div({"className": "workout-form-group"},
                    html.label({}, "Body Composition (optional):"),
                    html.input({"type": "number", "min": "0", "placeholder": "Fat mass (kg)", "value": fat_mass, "onBlur": lambda e: set_fat_mass(e["target"]["value"])}),
                    html.input({"type": "number", "min": "0", "placeholder": "Muscle mass (kg)", "value": muscle_mass, "onBlur": lambda e: set_muscle_mass(e["target"]["value"])}),
                ),
                html.button({"type": "button", "className": f"btn-workout-gradient{' disabled' if loading else ''}", "onClick": handle_submit, "disabled": loading},
                    "Generating..." if loading else "Generate Plan"
                ),
            ),
            error and html.div({"style": {"color": "#f357a8", "marginTop": "1em"}}, error),
            result_html and html.div({"className": "workout-output", "dangerouslySetInnerHTML": {"__html": result_html}}),
        )
    )