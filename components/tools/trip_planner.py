from reactpy import component, html, use_state
import asyncio
import aiohttp
import json
import datetime
import re
import random
import os
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

async def generate_pdf_server_side(trip_data, route_img_path=None):
    """Generate PDF on server side and return the file path"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        
        temp_dir = "./static/assets/pdf_temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        random_id = random.randint(100000, 999999)
        filename = f"Trip-{random_id}.pdf"
        filepath = os.path.join(temp_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=10,
            alignment=TA_CENTER
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 11
        normal_style.spaceAfter = 6
        
        content = []
        
        # Title
        content.append(Paragraph("AI Trip Plan", title_style))
        content.append(Spacer(1, 12))

        # Subtitle
        content.append(Paragraph('<a href="https://mihais-ai-playground.xyz/">https://mihais-ai-playground.xyz/</a>', subtitle_style))
        content.append(Spacer(1, 20))
        
        # Destination info
        if trip_data.get('destination_city') and trip_data.get('destination_country'):
            content.append(Paragraph(f"<b>Destination:</b> {trip_data['destination_city']}, {trip_data['destination_country']}", normal_style))
        
        # Flight route
        if trip_data.get('route') and isinstance(trip_data['route'], list):
            route_text = " → ".join(trip_data['route'])
            content.append(Paragraph(f"<b>Flight Route:</b> {route_text}", normal_style))
        
        content.append(Spacer(1, 20))
        
        # Explanation
        if trip_data.get('explanation'):
            content.append(Paragraph("Why this trip?", heading_style))
            content.append(Paragraph(trip_data['explanation'], normal_style))
            content.append(Spacer(1, 20))
        
        # Daily plan
        if trip_data.get('daily_plan') and isinstance(trip_data['daily_plan'], list):
            content.append(Paragraph("Daily Itinerary", heading_style))
            
            for i, day in enumerate(trip_data['daily_plan']):
                # Day header
                day_label = day.get('label', f'Day {i+1}')
                day_title = day.get('title', '')
                header_text = f"{day_label}: {day_title}" if day_title else day_label
                content.append(Paragraph(f"<b>{header_text}</b>", heading_style))
                
                # Activities
                if day.get('activities') and isinstance(day['activities'], list):
                    content.append(Paragraph("<b>Activities:</b>", normal_style))
                    for activity in day['activities']:
                        content.append(Paragraph(f"• {activity}", normal_style))
                
                # Details
                if day.get('details'):
                    content.append(Paragraph("<b>Details:</b>", normal_style))
                    content.append(Paragraph(day['details'], normal_style))
                
                content.append(Spacer(1, 15))
        
        # Add flight route image if available
        if route_img_path and os.path.exists(f".{route_img_path}"):
            try:
                content.append(PageBreak())
                content.append(Paragraph("Flight Route Map", heading_style))
                content.append(Spacer(1, 12))
                from reportlab.lib.utils import ImageReader
                img_path = f".{route_img_path}"
                img_reader = ImageReader(img_path)
                orig_width, orig_height = img_reader.getSize()
                max_width, max_height = 500, 300
                aspect = orig_width / orig_height
                if orig_width > max_width or orig_height > max_height:
                    if (max_width / aspect) <= max_height:
                        draw_width = max_width
                        draw_height = max_width / aspect
                    else:
                        draw_width = max_height * aspect
                        draw_height = max_height
                else:
                    draw_width = orig_width
                    draw_height = orig_height
                img = Image(img_path, width=draw_width, height=draw_height)
                content.append(img)
                debug_log(f"Added flight route image to PDF: {route_img_path} (scaled to {draw_width}x{draw_height})")
            except Exception as img_e:
                debug_log(f"Could not add image to PDF: {img_e}")
        
        # Build PDF
        doc.build(content)
        
        debug_log(f"PDF generated successfully: {filepath}")
        return f"/static/assets/pdf_temp/{filename}"
        
    except ImportError as e:
        debug_log(f"PDF generation failed - missing reportlab: {e}")
        return None
    except Exception as e:
        debug_log(f"PDF generation failed: {e}")
        return None

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
    # PDF download state
    pdf_loading, set_pdf_loading = use_state(False)
    pdf_error, set_pdf_error = use_state("")
    pdf_download_url, set_pdf_download_url = use_state("")
    # Route image loading state
    route_img_loading, set_route_img_loading = use_state(False)

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
        - VERY IMPORTANT: Suggest common layovers if you know the flight is not direct. For example, if the user wants to fly from Bucharest to San Francisco, suggest a layover in London or Frankfurt, and add those airports to the route list. Do this both for the outbound and return flights.
        - Always add the departure airport at the end of the route list, even if it's the same as the first airport. This makes it a round trip. Also suggest common layovers on the way back.
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
            # Remove code block wrappers (
            if ai_clean.startswith("json"):
                ai_clean = ai_clean[7:]
            if ai_clean.startswith(""):
                ai_clean = ai_clean.lstrip("\n ")
            if ai_clean.endswith(" "):
                ai_clean = ai_clean.rstrip("\n ")
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
        set_route_img_loading(True)
        try:
            # Use route IATA codes for filename
            if route and isinstance(route, list) and len(route) > 0:
                route_codes = '-'.join([str(code) for code in route])
                filename = f"/static/assets/flight_routes_temp/route_{route_codes}.png"
            else:
                filename = f"/static/assets/flight_routes_temp/route_UNKNOWN.png"
            # Check if file already exists
            abs_path = f".{filename}"
            if os.path.exists(abs_path):
                set_route_img_url(filename)
                debug_log(f"Route image already exists, serving: {filename}")
                return
            
            # Add the departure airport at the end of the route
            #if route and isinstance(route, list) and len(route) > 0:
            #    route = route + [route[0]]
            debug_log(f"generate_route_image: filename={filename}, route={route}")
            await generate_flightroute.create_clean_route_map(route, abs_path, extra_lon_margin=0.30, extra_lat_margin=0.70, npts=50)
            set_route_img_url(filename)
            debug_log(f"Route image generated and set: {filename}")
        except Exception as e:
            debug_log("Exception in generate_route_image:", e)
            set_ai_error(f"Flight route image error: {e}")
        finally:
            set_route_img_loading(False)

    def handle_submit(_):
        debug_log("handle_submit: user clicked Suggest Trip")
        asyncio.create_task(call_ai_trip_plan())

    async def handle_pdf_download(_):
        debug_log("handle_pdf_download: user clicked Download PDF")
        if not (ai_result and isinstance(ai_result, dict) and ai_result.get("daily_plan")):
            set_pdf_error("No trip data available to generate PDF")
            return
        
        set_pdf_loading(True)
        set_pdf_error("")
        
        try:
            pdf_path = await generate_pdf_server_side(ai_result, route_img_url)
            if pdf_path:
                # Create download link and trigger download
                debug_log(f"PDF generated at: {pdf_path}")
                set_pdf_download_url(pdf_path)
            else:
                set_pdf_error("Failed to generate PDF. Make sure reportlab is installed.")
        except Exception as e:
            debug_log(f"PDF download error: {e}")
            set_pdf_error(f"PDF generation failed: {e}")
        finally:
            set_pdf_loading(False)

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

    def download_pdf_btn():
        if not (ai_result and isinstance(ai_result, dict) and ai_result.get("daily_plan")):
            return None
        
        def trigger_pdf(_):
            debug_log("Download Trip as PDF button clicked")
            asyncio.create_task(handle_pdf_download(_))
        
        return html.div({},
            html.button({
                "className": f"btn btn-navy{' btn-disabled' if pdf_loading else ''}",
                "onClick": trigger_pdf,
                "disabled": pdf_loading
            }, "Generating PDF..." if pdf_loading else "Download Trip as PDF"),
            pdf_error and html.div({"className": "error-message", "style": {"marginTop": "10px"}}, pdf_error) or None
        )

    def pdf_download_script():
        """Inject JavaScript to trigger PDF download when URL is set"""
        if not pdf_download_url:
            return None
        
        script_content = f"""
        // Create a temporary download link and click it
        var link = document.createElement('a');
        link.href = '{pdf_download_url}';
        link.download = 'trip_plan.pdf';
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Clear the download URL after triggering
        setTimeout(function() {{
            var input = document.getElementById('pdf-download-clear');
            if (input) {{
                input.value = 'clear';
                input.dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
        }}, 100);
        """
        
        return html.script({
            "key": f"pdf-download-{pdf_download_url}",  # Unique key to force re-injection
            "type": "text/javascript"
        }, script_content)

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.input({
            "type": "hidden", 
            "id": "pdf-download-clear", 
            "value": "", 
            "onInput": lambda e: set_pdf_download_url("") if e["target"]["value"] == "clear" else None
        }),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/tools/trip_planner.css?v={CACHE_SUFFIX}"}),
        pdf_download_script(),
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
            # Show loading message while route image is being generated
            route_img_loading and html.div({"className": "route-image-loading"}, "Loading flight route...") or None,
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
            ) or None,
            ai_result and download_pdf_btn(),
        )
    )
