from reactpy import component, html, use_state
import asyncio
import aiohttp
import json
import datetime
import re
import random
from components.common import generate_flightroute

# ───────────────────────────────────────────────────────────────────────────────
#  DEBUG LOGGER
# ───────────────────────────────────────────────────────────────────────────────

try:
    from components.common.config import DEBUG_MODE, REACTPY_DEBUG_MODE
    if REACTPY_DEBUG_MODE:
        import reactpy
        reactpy.config.REACTPY_DEBUG_MODE.current = True
        print("[trip_planner.py DEBUG] REACTPY_DEBUG_MODE imported from config.py, using value:", REACTPY_DEBUG_MODE)
    if DEBUG_MODE:
        print("[trip_planner.py DEBUG] DEBUG_MODE imported from config.py, using value:", DEBUG_MODE)
except ImportError:
    DEBUG_MODE = False
    print("Warning: DEBUG_MODE not imported from config.py, using default value False.")

def debug_log(*args):
    if DEBUG_MODE:
        print("[trip_planner.py DEBUG]", *args)

@component
def TripPlanner():
    # State for user trip preferences
    prefs, set_prefs = use_state({
        "departure_city": "",   # e.g. Bucharest
        "month": "",            # e.g. October
        "climate": "",           # e.g. warm, mild, hot, cold
        "duration": "",         # e.g. 5 days
        "budget": "",           # e.g. 1000 EUR per person
        "people": "",
        "interests": "",        # e.g. beach, wine, hiking, culture
        "goal": "",             # e.g. relax on the beach, visit famous wine regions, city break, explore nature
    })
    ai_loading, set_ai_loading = use_state(False)
    ai_error, set_ai_error = use_state("")
    ai_result, set_ai_result = use_state("")
    route_img_url, set_route_img_url = use_state("")
    suggested_route, set_suggested_route = use_state([])
    # Modal state for details popup
    details_modal, set_details_modal = use_state({"open": False, "label": "", "details": ""})
    # Modal state for route image popup
    route_img_modal, set_route_img_modal = use_state({"open": False})

    def handle_input(field, value):
        debug_log(f"Input change: {field} = {value}")
        set_prefs(lambda prev: {**prev, field: value})

    async def call_ai_trip_plan(retry_count=0):
        debug_log("call_ai_trip_plan: started, retry_count=", retry_count)
        set_ai_loading(True)
        set_ai_error("")
        set_ai_result("")
        set_route_img_url("")
        set_suggested_route([])
        debug_log("User prefs:", prefs)
        # Always provide the current date to the AI
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        debug_log("Current date: schedule-block", current_date)
        prompt = """
        You are a travel assistant. Given the user's preferences below, suggest the best destination(s) and a sample itinerary.
        Your job is to pick the best destination(s) for the user, not just plan a trip to a given city.
        For each destination, find the most popular airport (do not ask the user for IATA codes, use your own knowledge. Make sure they're right.).
        Suggest a realistic flight route (as a list of IATA codes, but infer them yourself from the cities/countries).
        Use the fast-flights library to check for real-world direct/cheap routes if possible.
        Output your answer as a JSON object in the following format (do not include any text outside the code block):

        {
          "destination_city": "",
          "destination_country": "",
          "route": ["IATA1", "IATA2", ...],
          "daily_plan": [
            {
              "label": "Day 1-3",
              "title": "Tokyo Arrival & Exploration",
              "activities": [
                "Arrive in Tokyo",
                "Visit Senso-ji Temple",
                "Explore Akihabara",
                "Try local ramen shops"
              ],
              "details": "Expand on the activities above, providing more context, tips, and price estimates for each activity. Show price estimates in the currency entered by the user in the budget field, or default to USD if not specified. Format as a readable paragraph or bullet list."
            },
            {
              "label": "Day 4-7",
              "title": "Kyoto Temples & Culture",
              "activities": [
                "Take bullet train to Kyoto",
                "Tour Fushimi Inari Shrine",
                "Walk the Philosopher's Path",
                "Enjoy a traditional tea ceremony"
              ],
              "details": "Expand on the activities above, providing more context, tips, and price estimates for each activity. Show price estimates in the currency entered by the user in the budget field, or default to USD if not specified. Format as a readable paragraph or bullet list."
            },
            ...
          ],
          "explanation": ""
        }

        IMPORTANT:
        - For trips longer than 7 days, group days into ranges (e.g. 'Day 1-5', 'Day 6-10') in the label field, but always keep the label on a single line (no newlines).
        - For long trips (10+ days), provide at least one daily_plan entry per 2-3 days, so a 20-day trip should have at least 7-10 daily_plan entries.
        - Each daily_plan entry must have a 'label' (e.g. 'Day 1-3'), a short 'title' summarizing the main theme or highlight, an 'activities' array of short, capitalized phrases (one per activity), and a 'details' field as described above.
        - Do NOT use newlines or line breaks in the label or title fields.
        - Make the daily_plan as detailed as possible, with plenty of activities and variety.
        - Write the explanation field in the second person (use 'you', 'your', 'yours').
        - If you suggest the user to fly to a city/region in the daily_plan, always include the corresponding airport's IATA code in the route list, in the correct order.
        - Do not use just capital letters for the activities, use proper capitalization (e.g. 'Visit Senso-ji Temple', not 'VISIT SENSO-JI TEMPLE').
        - If a budget is absurd (ex: 1000 EUR for a 2-week trip), suggest a more realistic budget based on the destination and activities.
        - If some fields are empty, take a guess based on the other fields. For example, if the user doesn't specify climate but mentions beach, assume warm or tropical climate. Tell them to the user in the explanation or details field.
        """
        debug_log("AI prompt:", prompt)
        try:
            async with aiohttp.ClientSession() as session:
                debug_log("Opening aiohttp session...")
                async with session.post(
                    "https://ai.hackclub.com/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": f"Current date(YYY-MM-DD): {current_date}\nUser preferences: {json.dumps(prefs, ensure_ascii=False)}"}
                        ]
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    debug_log(f"AI endpoint response status: {resp.status}")
                    raw_json = await resp.json()
                    debug_log("AI raw response:", raw_json)
                    ai_raw = raw_json["choices"][0]["message"]["content"]
            ai_clean = ai_raw.strip()
            debug_log("AI cleaned response (pre-strip):", ai_clean)
            # Remove code block wrappers (```json ... ``` or ``` ... ```
            if ai_clean.startswith("```json"):
                ai_clean = ai_clean[7:]
            if ai_clean.startswith("```"):
                ai_clean = ai_clean.lstrip("`\n ")
            if ai_clean.endswith("```"):
                ai_clean = ai_clean.rstrip("`\n ")
            if ai_clean.startswith("json"):
                ai_clean = ai_clean[4:].lstrip("\n ")
            ai_clean = ai_clean.strip()
            debug_log("AI cleaned response (post-strip):", ai_clean)
            # Extract the first JSON object from the string
            match = re.search(r"\{[\s\S]*\}", ai_clean)
            if match:
                json_str = match.group(0)
                # Remove illegal trailing commas before ] or }
                json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
                # Fix invalid backslash escapes (e.g. \, \t, etc) by replacing single backslashes not part of \\ or \", with \\.
                # This will make the string safe for json.loads
                def fix_invalid_escapes(s):
                    # Replace single backslashes not followed by \\, ", /, b, f, n, r, t, u
                    return re.sub(r'(?<!\\)\\(?![\\"/bfnrtu])', r'\\\\', s)
                json_str = fix_invalid_escapes(json_str)
                try:
                    result = json.loads(json_str)
                except Exception as e:
                    debug_log("JSON decode error after trailing comma and escape fix:", e)
                    raise
            else:
                raise ValueError("No JSON object found in AI response")
            debug_log("Parsed AI result:", result)
            set_ai_result(result)
            set_suggested_route(result.get("route", []))
            # Generate flight route image if route is present
            if result.get("route"):
                debug_log("Generating route image for:", result["route"])
                try:
                    await generate_route_image(result["route"])
                except Exception as e:
                    debug_log("Exception in generate_route_image (retry logic):", e)
                    # If the error is about airport not found, retry up to 3 times
                    if ("airport" in str(e).lower() and "not found" in str(e).lower() and retry_count < 2):
                        set_ai_error(f"Flight route image error: {e} (retrying...)")
                        await call_ai_trip_plan(retry_count=retry_count+1)
                        return
                    else:
                        set_ai_error(f"Flight route image error: {e}")
        except Exception as e:
            debug_log("Exception in call_ai_trip_plan:", e)
            # If the error is about airport not found, retry up to 3 times
            if ("airport" in str(e).lower() and "not found" in str(e).lower() and retry_count < 2):
                set_ai_error(f"AI error: {e} (retrying...)")
                await call_ai_trip_plan(retry_count=retry_count+1)
                return
            else:
                set_ai_error(f"AI error: {e}")
        set_ai_loading(False)
        debug_log("call_ai_trip_plan: finished")

    async def generate_route_image(route):
        # Use route IATA codes for filename
        if route and isinstance(route, list) and len(route) > 0:
            route_codes = '-'.join([str(code) for code in route])
            filename = f"/static/assets/flight_routes_temp/route_{route_codes}.png"
        else:
            filename = f"/static/assets/flight_routes_temp/route_UNKNOWN.png"
        try:
            if route and isinstance(route, list) and len(route) > 0:
                route = route + [route[0]]
            debug_log(f"generate_route_image: filename={filename}, route={route}")
            await generate_flightroute.create_clean_route_map(route, f".{filename}", extra_lon_margin=0.30, extra_lat_margin=0.70, npts=50)
            set_route_img_url(filename)
            debug_log(f"Route image generated and set: {filename}")
        except Exception as e:
            debug_log("Exception in generate_route_image:", e)
            set_ai_error(f"Flight route image error: {e}")

    def handle_submit(_):
        debug_log("handle_submit: user clicked Suggest Trip")
        asyncio.create_task(call_ai_trip_plan())

    # UI
    from components.common.config import CACHE_SUFFIX
    # Color palette and emoji list for schedule blocks
    COLORS = [
        "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33", "#a65628", "#f781bf", "#999999", "#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02",
    ]
    EMOJIS = [
        "🗓️", "✈️", "🌍", "🏖️", "🏙️", "🧳", "🎒", "🚗", "🚆", "🚢", "🏞️", "🌄", "🏰", "🎡", "🍽️", "🎉", "🗺️", "📸", "🏝️", "🏔️", "🌆"
    ]

    # For each render, shuffle colors and emojis for randomness
    shuffled_colors = COLORS[:]
    shuffled_emojis = EMOJIS[:]
    random.shuffle(shuffled_colors)
    random.shuffle(shuffled_emojis)

    return html.div(
        {},
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/tools/trip_planner.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "global-home-btn-row"}, html.a({"href": "/", "className": "global-home-btn"}, "🏠 Home")),
        html.div({"className": "trip-planner"},
            html.h2("AI Trip Planner"),
            html.div({"className": "form-group"},
                html.input({
                    "type": "text", "placeholder": "Departure city* (e.g. Bucharest)",
                    "value": prefs["departure_city"],
                    "onBlur": lambda e: handle_input("departure_city", e["target"]["value"]),
                    "required": True
                }),
                html.input({
                    "type": "text", "placeholder": "When?*",
                    "value": prefs["month"],
                    "onBlur": lambda e: handle_input("month", e["target"]["value"]),
                    "required": True
                }),
                html.input({
                    "type": "text", "placeholder": "Preferred climate (e.g. warm, mild, hot, cold)",
                    "value": prefs["climate"],
                    "onBlur": lambda e: handle_input("climate", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "Trip duration",
                    "value": prefs["duration"],
                    "onBlur": lambda e: handle_input("duration", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "Budget (e.g. 1000 EUR per person)",
                    "value": prefs["budget"],
                    "onBlur": lambda e: handle_input("budget", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "Number of people",
                    "value": prefs["people"],
                    "onBlur": lambda e: handle_input("people", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "Interests (e.g. beach, wine, hiking, culture)",
                    "value": prefs["interests"],
                    "onBlur": lambda e: handle_input("interests", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "What is your main goal for this trip? (e.g. relax on the beach, visit famous wine regions, city break, explore nature)",
                    "value": prefs["goal"],
                    "onBlur": lambda e: handle_input("goal", e["target"]["value"])
                }),
            ),
            html.button({
                "className": f"btn btn-gradient{' btn-disabled' if ai_loading or not prefs['departure_city'] or not prefs['month'] else ''}",
                "onClick": handle_submit,
                "disabled": ai_loading or not prefs["departure_city"] or not prefs["month"]
            },
                "Suggest Trip" if not ai_loading else "Planning..."
            ),
            ai_error and html.div({"className": "error-message"}, ai_error) or None,
            ai_result and html.div({"className": "schedule-list"},
                html.div({"className": "schedule-tip"}, "Tip: Click any day block/flight route for more details!"),
                *[
                    (lambda day=day, i=i: html.div({
                        "className": "schedule-block schedule-task",
                        "key": f"day-{i}",
                        "style": {"borderLeft": f"6px solid {shuffled_colors[i % len(shuffled_colors)]}"},
                        "onClick": lambda e, day=day, i=i: (
                            debug_log(f"Modal open for day index {i}, label={day.get('label')}, details={day.get('details')}, activities={day.get('activities')}"),
                            set_details_modal({
                                "open": True,
                                "label": day.get("label") or f"Day {i+1}",
                                "details": day.get("details") if day.get("details") not in (None, "", [], {}) else (
                                    f"Activities: {', '.join(day.get('activities', []))}" if day.get('activities') else "No details available."
                                )
                            })
                        )[1]
                    },
                        html.div({"className": "block-header"},
                            html.span({"className": "block-icon task"}, shuffled_emojis[i % len(shuffled_emojis)]),
                            html.span({"className": "block-type"}, day.get("label", f"Day {i+1}")),
                            html.span({"className": "block-title"}, day.get("title", ""))
                        ),
                        html.ul({},
                            *[html.li({}, activity) for activity in day.get("activities", [])]
                        )
                    ))()
                    for i, day in enumerate(ai_result.get("daily_plan", []) if isinstance(ai_result, dict) else [])
                ]
            ) or None,
            # Modal popup for details
            details_modal["open"] and html.div({"className": "modal-overlay"},
                html.div({"className": "modal-content"},
                    html.button({"onClick": lambda e: set_details_modal({"open": False, "label": "", "details": ""}), "className": "modal-close-btn"}, "×"),
                    html.h3({}, "Detailed View"),
                    html.div({"className": "modal-details"}, details_modal["details"])
                )
            ) or None,
            ai_result and ai_result.get("explanation") and html.div({"className": "explanation-block"},
                html.b("Why this trip?"), html.br(), ai_result["explanation"]
            ) or None,
            route_img_url and html.div({"className": "route-image-block"},
                html.h4("Flight Route"),
                html.img({
                    "src": route_img_url,
                    "className": "route-image",
                    "style": {"cursor": "pointer"},
                    "onClick": lambda e: set_route_img_modal({"open": True})
                })
            ) or None,
            # Modal popup for route image fullscreen
            route_img_modal["open"] and html.div({"className": "modal-overlay", "onClick": lambda e: set_route_img_modal({"open": False})},
                html.div({"className": "route-image-modal-content", "onClick": lambda e: (e.stop_propagation() if hasattr(e, 'stop_propagation') else None)},
                    html.img({
                        "src": route_img_url,
                        "className": "route-image-modal-img"
                    }),
                    html.button({
                        "onClick": lambda e: set_route_img_modal({"open": False}),
                        "className": "route-image-modal-close"
                    }, "×")
                )
            ) or None
        )
    )
