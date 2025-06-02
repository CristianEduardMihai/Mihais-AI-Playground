from reactpy import component, html, use_state
import asyncio
import aiohttp
import markdown
import os
import json
import re
from components.common import generate_flightroute

DEBUG_MODE = True  # Set to True to enable debug logging

def debug_log(*args):
    if DEBUG_MODE:
        print("[TripPlanner DEBUG]", *args)

@component
def TripPlanner():
    # State for user trip preferences
    prefs, set_prefs = use_state({
        "departure_city": "",   # e.g. Bucharest
        "departure_country": "", # e.g. Romania
        "month": "",            # e.g. October
        "climate": "",           # e.g. warm, mild, hot, cold
        "duration": "",         # e.g. 5 days
        "budget": "",           # e.g. 1000 EUR per person
        "people": 1,
        "interests": "",        # e.g. beach, wine, hiking, culture
        "goal": "",             # e.g. relax on the beach, visit famous wine regions, city break, explore nature
    })
    ai_loading, set_ai_loading = use_state(False)
    ai_error, set_ai_error = use_state("")
    ai_result, set_ai_result = use_state("")
    route_img_url, set_route_img_url = use_state("")
    suggested_route, set_suggested_route = use_state([])

    def handle_input(field, value):
        debug_log(f"Input change: {field} = {value}")
        set_prefs(lambda prev: {**prev, field: value})

    async def call_ai_trip_plan():
        debug_log("call_ai_trip_plan: started")
        set_ai_loading(True)
        set_ai_error("")
        set_ai_result("")
        set_route_img_url("")
        set_suggested_route([])
        debug_log("User prefs:", prefs)
        prompt = f"""
        You are a travel assistant. Given the user's preferences below, suggest the best destination(s) and a sample itinerary.
        Your job is to pick the best destination(s) for the user, not just plan a trip to a given city.
        For each destination, find the most popular airport (do not ask the user for IATA codes, use your own knowledge or search).
        Suggest a realistic flight route (as a list of IATA codes, but infer them yourself from the cities/countries).
        Use the fast-flights library to check for real-world direct/cheap routes if possible.
        Output JSON with: destination_city, destination_country, route (list of IATA codes), daily_plan (list of day summaries), and a short explanation of why you chose this destination.
        User preferences: {json.dumps(prefs, ensure_ascii=False)}
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
                            {"role": "system", "content": "You are a helpful travel planner."},
                            {"role": "user", "content": prompt}
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
            # Remove code block wrappers (```json ... ``` or ``` ... ```)
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
                debug_log("Extracted JSON string:", json_str)
                result = json.loads(json_str)
            else:
                raise ValueError("No JSON object found in AI response")
            debug_log("Parsed AI result:", result)
            set_ai_result(result)
            set_suggested_route(result.get("route", []))
            # Generate flight route image if route is present
            if result.get("route"):
                debug_log("Generating route image for:", result["route"])
                await generate_route_image(result["route"])
        except Exception as e:
            debug_log("Exception in call_ai_trip_plan:", e)
            set_ai_error(f"AI error: {e}")
        set_ai_loading(False)
        debug_log("call_ai_trip_plan: finished")

    async def generate_route_image(route):
        filename = f"/static/assets/flight_route_{os.getpid()}.png"
        debug_log(f"generate_route_image: filename={filename}, route={route}")
        try:
            await generate_flightroute.create_clean_route_map(route, f".{filename}", extra_margin=0.2)
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
    return html.div(
        {},
        html.link({"rel": "stylesheet", "href": f"/static/css/tools/trip_planner.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "navbar"}, html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")),
        html.div({"className": "trip-planner"},
            html.h2("AI Trip Planner"),
            html.div({"className": "form-group"},
                html.input({
                    "type": "text", "placeholder": "Your departure city (e.g. Bucharest)",
                    "value": prefs["departure_city"],
                    "onBlur": lambda e: handle_input("departure_city", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "Your country (optional)",
                    "value": prefs["departure_country"],
                    "onBlur": lambda e: handle_input("departure_country", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "When do you want to go? (e.g. October)",
                    "value": prefs["month"],
                    "onBlur": lambda e: handle_input("month", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "Preferred climate (e.g. warm, mild, hot, cold)",
                    "value": prefs["climate"],
                    "onBlur": lambda e: handle_input("climate", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "Trip duration (e.g. 5 days)",
                    "value": prefs["duration"],
                    "onBlur": lambda e: handle_input("duration", e["target"]["value"])
                }),
                html.input({
                    "type": "text", "placeholder": "Budget (e.g. 1000 EUR per person)",
                    "value": prefs["budget"],
                    "onBlur": lambda e: handle_input("budget", e["target"]["value"])
                }),
                html.input({
                    "type": "number", "placeholder": "Number of people", "min": 1,
                    "value": prefs["people"],
                    "onBlur": lambda e: handle_input("people", int(e["target"]["value"]))
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
            html.button({"className": "btn btn-gradient", "onClick": handle_submit, "disabled": ai_loading},
                "Suggest Trip" if not ai_loading else "Planning..."
            ),
            ai_error and html.div({"className": "error-message"}, ai_error) or None,
            ai_result and html.div({"className": "interview-output"},
                html.h3(f"Destination: {ai_result.get('destination','')}") if isinstance(ai_result, dict) else None,
                html.ul({}, *[
                    html.li({}, day) for day in (ai_result.get("daily_plan", []) if isinstance(ai_result, dict) else [])
                ]),
                html.p({}, ai_result.get("explanation", "")) if isinstance(ai_result, dict) else None,
            ) or None,
            route_img_url and html.div({"style": {"marginTop": "2em"}},
                html.h4("Flight Route"),
                html.img({"src": route_img_url, "style": {"maxWidth": "100%", "borderRadius": "8px", "boxShadow": "0 2px 8px #8883"}})
            ) or None
        )
    )
