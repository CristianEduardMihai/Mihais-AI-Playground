from reactpy import component, html, use_state
import requests
import markdown
import os
import json
import datetime
import re

DATA_PATH = "static/assets/pc_parts"

DEBUG_MODE = False

# Load all relevant datasets into a dict for easy lookup
def load_json(filename):
    try:
        if DEBUG_MODE:
            print(f"[DEBUG] Loading dataset: {filename}")
        with open(os.path.join(DATA_PATH, filename), "r") as f:
            data = json.load(f)
            if DEBUG_MODE:
                print(f"[DEBUG] Loaded {len(data)} items from {filename}")
            return data
    except Exception as e:
        if DEBUG_MODE:
            print(f"[DEBUG] Failed to load {filename}: {e}")
        return []

def find_best_match(name, dataset):
    if DEBUG_MODE:
        print(f"[DEBUG] Matching part: '{name}' in dataset of size {len(dataset)}")
    # Try exact match, then case-insensitive, then partial
    for item in dataset:
        if item.get("name", "").lower() == name.lower():
            return item
    for item in dataset:
        if name.lower() in item.get("name", "").lower():
            return item
    return None

def smart_find_best_match(name, dataset):
    """
    Try to match using brand and model keywords, not just the full string.
    E.g., if AI outputs 'nvidia' and '3060', match 'GeForce RTX 3060'.
    """
    if not name or not dataset:
        return None
    name = name.lower()
    # Split on space, dash, etc. to get tokens
    tokens = re.split(r"[\s\-_/]+", name)
    tokens = [t for t in tokens if t]
    # Try to match all tokens in the item name (case-insensitive)
    for item in dataset:
        item_name = item.get("name", "").lower()
        if all(token in item_name for token in tokens):
            return item
    # Try to match any token in the item name
    for item in dataset:
        item_name = item.get("name", "").lower()
        if any(token in item_name for token in tokens):
            return item
    # Fallback to partial match
    for item in dataset:
        if name in item.get("name", "").lower():
            return item
    return None

@component
def PCPartPicker():
    from reactpy import use_effect
    currency_list, set_currency_list = use_state([])
    currency, set_currency = use_state("eur")
    exchange_rates, set_exchange_rates = use_state({})
    budget, set_budget = use_state(1000)
    use_case, set_use_case = use_state("Gaming")
    perf_level, set_perf_level = use_state("Medium")
    noise_pref, set_noise_pref = use_state("Doesn't matter")
    size_pref, set_size_pref = use_state("Standard/Mid Tower")
    brand_pref, set_brand_pref = use_state("")
    wifi_pref, set_wifi_pref = use_state("Doesn't matter")
    upgrade_pref, set_upgrade_pref = use_state("Somewhat important")
    games, set_games = use_state("")
    result_md, set_result_md = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")
    parts_loading, set_parts_loading = use_state(True)
    datasets, set_datasets = use_state({
        "cpu": [], "gpu": [], "motherboard": [], "ram": [], "storage": [], "psu": [], "case": []
    })

    # Load datasets only once on mount
    def load_all():
        if DEBUG_MODE:
            print("[DEBUG] Loading all datasets...")
        ds = {
            "cpu": load_json("cpu.json"),
            "gpu": load_json("video-card.json"),
            "motherboard": load_json("motherboard.json"),
            "ram": load_json("memory.json"),
            "storage": load_json("internal-hard-drive.json"),
            "psu": load_json("power-supply.json"),
            "case": load_json("case.json"),
        }
        if DEBUG_MODE:
            print("[DEBUG] All datasets loaded.")
        return ds

    def load_datasets_once():
        set_parts_loading(True)
        ds = load_all()
        set_datasets(ds)
        set_parts_loading(False)
    use_effect(load_datasets_once, [])

    # Novice-friendly dropdowns
    def dropdown(label, value, set_value, options, explanation, id_):
        return html.div(
            {"className": "form-group"},
            html.label({"for": id_}, f"{label}: "),
            html.span({"className": "explanation"}, explanation),
            html.select(
                {
                    "id": id_,
                    "value": value,
                    "onChange": lambda e: set_value(e["target"]["value"])
                },
                *[html.option({"value": o}, o) for o in options]
            )
        )

    # Text input for preferred brands
    def brand_textbox(label, value, set_value, explanation, id_):
        return html.div(
            {"className": "form-group"},
            html.label({"for": id_}, f"{label}: "),
            html.span({"className": "explanation"}, explanation),
            html.input({
                "type": "text",
                "id": id_,
                "value": value,
                "onChange": lambda e: set_value(e["target"]["value"]),
                "placeholder": "e.g. Intel, NVIDIA, Corsair"
            })
        )

    # Text input for games
    def games_textbox(label, value, set_value, explanation, id_):
        return html.div(
            {"className": "form-group"},
            html.label({"for": id_}, f"{label}: "),
            html.span({"className": "explanation"}, explanation),
            html.input({
                "type": "text",
                "id": id_,
                "value": value,
                "onChange": lambda e: set_value(e["target"]["value"]),
                "placeholder": "e.g. Cyberpunk 2077, Fortnite, Valorant"
            })
        )

    # AI system prompt
    SYSTEM_PROMPT = (
        "You are a helpful PC building assistant for complete beginners. "
        "Given the user's preferences, recommend a compatible set of PC parts. "
        "Respond in the following JSON format (no markdown, no extra text):\n"
        "{\n"
        "  'cpu': 'CPU Name',\n"
        "  'gpu': 'GPU Name',\n"
        "  'motherboard': 'Motherboard Name',\n"
        "  'ram': 'RAM Name',\n"
        "  'storage': 'Storage Name',\n"
        "  'psu': 'PSU Name',\n"
        "  'case': 'Case Name'\n"
        "}\n"
        "Choose only one for each.\n"
        "If you don't know, guess a reasonable part from 2024.\n"
        "Do not explain, just output the JSON."
    )

    def debug(msg):
        if DEBUG_MODE:
            print(msg)

    def handle_submit(event):
        if loading:
            debug("[DEBUG] Submit ignored: already loading.")
            return  # Prevent double-clicks
        set_loading(True)
        set_result_md("")
        set_error("")
        # Convert user budget to EUR for AI
        budget_eur = convert_to_eur(budget, currency)
        # --- Check for impossible config before AI call ---
        impossible_msg = is_impossible_config(budget_eur, use_case, perf_level)
        if impossible_msg:
            set_error(impossible_msg)
            set_loading(False)
            return
        brand_pref_str = brand_pref.strip() if brand_pref.strip() else "Doesn't matter"
        games_str = games.strip() if games.strip() else "(not specified)"
        user_prefs = (
            f"Budget: {int(budget_eur)} EUR\n"
            f"Use case: {use_case}\n"
            f"Performance: {perf_level}\n"
            f"Noise: {noise_pref}\n"
            f"Size: {size_pref}\n"
            f"Preferred Brands: {brand_pref_str}\n"
            f"Wi-Fi/Bluetooth: {wifi_pref}\n"
            f"Upgradeability: {upgrade_pref}\n"
            f"Games: {games_str}\n"
        )
        debug(f"[PCPartPicker] {datetime.datetime.now().isoformat()}\nUser preferences (AI gets EUR):\n{user_prefs}")
        ai_response = None
        tries = 0
        max_tries = 6
        last_missing = None
        debug(f"[DEBUG] Entering AI build loop (max_tries={max_tries})")
        while tries < max_tries:
            tries += 1
            debug(f"[DEBUG] AI request attempt {tries} (last_missing={last_missing})")
            prompt = SYSTEM_PROMPT + "\nUser preferences:\n" + user_prefs
            if last_missing:
                dataset_snippet = datasets.get(last_missing, [])[:3]
                for item in dataset_snippet:
                    if "price" in item and item.get("price") is not None:
                        item["price_eur"] = round(convert_to_eur(item["price"], "usd"), 2)
                snippet_str = json.dumps(dataset_snippet, ensure_ascii=False)
                prompt += (f"\nLast time, the part '{last_missing}' could not be found in the dataset. "
                           f"Please suggest a different, more common or compatible {last_missing}. "
                           f"Here is a snippet of the {last_missing} database (prices in EUR):\n{snippet_str}\n")
            debug(f"[DEBUG] Prompt sent to AI (length={len(prompt)}):\n{prompt}")
            try:
                response = requests.post(
                    "https://ai.hackclub.com/chat/completions",
                    json={
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prefs}
                        ],
                        "max_tokens": 400
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=60
                )
                debug(f"[DEBUG] AI response: {response}")
                debug(f"[DEBUG] AI response headers: {response.headers}")
                debug(f"[DEBUG] AI HTTP status: {response.status_code}")
                raw_json = response.json()
                debug(f"[DEBUG] Raw response JSON: {raw_json}")
                if response.status_code == 200:
                    text = raw_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                    debug(f"[PCPartPicker][AI raw response]:\n{text}")
                    if not text.strip():
                        debug("[DEBUG] AI response text is empty!")
                        set_error("AI returned an empty response. Try again.")
                        break
                    # Use non-greedy regex with DOTALL to extract the first JSON object
                    matches = list(re.finditer(r"\{.*?\}", text, re.DOTALL))
                    debug(f"[DEBUG] Regex matches found: {len(matches)}")
                    if len(matches) > 1:
                        debug(f"[DEBUG] Warning: Multiple JSON objects found in AI response. Using the first one.")
                    match = matches[0] if matches else None
                    debug(f"[DEBUG] Regex match: {match}")
                    if not match:
                        debug("[DEBUG] No JSON object found in AI response.")
                        set_error("AI did not return a JSON object. Try again.")
                        with open("ai_debug.log", "a") as f:
                            f.write(f"\n[NO JSON] {datetime.datetime.now().isoformat()}\nPrompt:\n{prompt}\nAI raw text:\n{text}\n\n")
                        break
                    json_str = match.group(0)
                    debug(f"[DEBUG] Extracted JSON string (to be parsed):\n{json_str}")
                    try:
                        data = json.loads(json_str.replace("'", '"'))
                        debug(f"[DEBUG] Parsed JSON: {data}")
                    except Exception as e:
                        debug(f"[DEBUG] JSON parse error: {e}")
                        debug(f"[DEBUG] Problematic string: {json_str}")
                        with open("ai_debug.log", "a") as f:
                            f.write(f"\n[JSON ERROR] {datetime.datetime.now().isoformat()}\nPrompt:\n{prompt}\nAI raw text:\n{text}\nExtracted JSON string:\n{json_str}\nError: {e}\n\n")
                        set_error(f"AI JSON parse error: {e}")
                        break
                    build = {}
                    missing = None
                    for part, name in data.items():
                        debug(f"[DEBUG] Matching {part}: {name}")
                        match = smart_find_best_match(name, datasets.get(part, []))
                        if not match:
                            match = find_best_match(name, datasets.get(part, []))
                        if match:
                            debug(f"[DEBUG] Found match for {part}: {match.get('name')}")
                            build[part] = match
                        else:
                            debug(f"[DEBUG] No match for {part}: {name}")
                            missing = part
                            break
                    if not missing:
                        debug("[DEBUG] All parts matched. Rendering markdown.")
                        # Calculate total price in EUR, USD, and user currency
                        total_eur = 0.0
                        total_usd = 0.0
                        total_user = 0.0
                        for part, info in build.items():
                            if info.get('price'):
                                price_eur = round(convert_to_eur(info['price'], 'usd'), 2)
                                price_user = round(convert_from_eur(price_eur, currency), 2)
                                price_usd = info['price']
                                total_eur += price_eur
                                total_usd += price_usd
                                total_user += price_user
                        md = f"# Your PC Build\n\n"
                        for part, info in build.items():
                            md += f"**{part.upper()}**: {info.get('name', 'Unknown')}\n"
                            if info.get('price'):
                                price_eur = round(convert_to_eur(info['price'], 'usd'), 2)
                                price_user = round(convert_from_eur(price_eur, currency), 2)
                                md += f"- Price: {price_user} {currency.upper()} (original: ${info['price']} USD, €{price_eur} EUR)\n"
                            if info.get('brand'):
                                md += f"- Brand: {info['brand']}\n"
                            if info.get('specs'):
                                md += f"- Specs: {info['specs']}\n"
                            md += "\n"
                        md += f"**Total Price:** {round(total_user,2)} {currency.upper()} (original: ${round(total_usd,2)} USD, €{round(total_eur,2)} EUR)\n\n"
                        md += "---\n"
                        md += "## Tips & Recommendations\n"
                        md += (
                            "- Double-check compatibility before buying.\n"
                            "- Prices and availability may have changed since 2024.\n"
                            "- If you want to upgrade, consider increasing your budget or performance level.\n"
                        )
                        set_result_md(md)
                        # --- Query AI again for expert analysis ---
                        try:
                            build_summary = ", ".join([f"{part}: {info.get('name','Unknown')}" for part, info in build.items()])
                            analysis_prompt = (
                                "You are a PC building expert. Given a build, "
                                "provide a short analysis of potential bottlenecks, system balance, upgrade advice, and any expert opinions. State everything is according to you, an AI, not any bottlenech calculators and so on."
                                "Be concise and helpful."
                            )
                            analysis_response = requests.post(
                                "https://ai.hackclub.com/chat/completions",
                                json={
                                    "messages": [
                                        {"role": "system", "content": analysis_prompt},
                                        {"role": "user", "content": build_summary}
                                    ],
                                    "max_tokens": 250
                                },
                                headers={"Content-Type": "application/json"},
                                timeout=40
                            )
                            analysis_json = analysis_response.json()
                            analysis_text = analysis_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                            if analysis_text:
                                set_result_md(lambda prev: prev + "\n---\n## Expert Analysis\n" + analysis_text.strip())
                        except Exception as e:
                            debug(f"[DEBUG] Error during expert analysis AI call: {e}")
                        # --- Query AI again for game performance estimates ---
                        try:
                            build_summary = ", ".join([f"{part}: {info.get('name','Unknown')}" for part, info in build.items()])
                            games_list = games.strip() if games.strip() else None
                            if games_list:
                                perf_prompt = (
                                    "You are a PC gaming expert. Given a build, "
                                    "estimate how games would run on it."
                                    "For each game, estimate the expected settings (e.g., low/medium/high/ultra), resolution, and FPS. "
                                    "If a game is not in your knowledge base, say so. "
                                    "Add a disclaimer that these are AI-generated estimates and may not be accurate."
                                )
                                perf_response = requests.post(
                                    "https://ai.hackclub.com/chat/completions",
                                    json={
                                        "messages": [
                                            {"role": "system", "content": perf_prompt},
                                            {"role": "user", "content": f"Given this build: {build_summary}, and these games: {games_list}, estimate how they would run on this PC."}
                                        ],
                                        "max_tokens": 300
                                    },
                                    headers={"Content-Type": "application/json"},
                                    timeout=40
                                )
                                perf_json = perf_response.json()
                                perf_text = perf_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                                if perf_text:
                                    # Ensure each '- ' is on its own line for Markdown
                                    perf_text_md = re.sub(r'(?<!\n)- ', '\n- ', perf_text)
                                    set_result_md(lambda prev: prev + "\n---\n## Game Performance Estimates\n" + perf_text_md.strip())
                        except Exception as e:
                            debug(f"[DEBUG] Error during game performance AI call: {e}")
                        set_loading(False)
                        debug("[DEBUG] Done. Build and analysis shown to user.")
                        return
                    else:
                        last_missing = missing
                        debug(f"[DEBUG] Will retry for missing part: {missing}")
                        continue
                else:
                    debug(f"[DEBUG] AI HTTP error: {response.status_code}")
                    set_error(f"Error: {response.status_code}")
                    break
            except Exception as e:
                debug(f"[DEBUG] Exception during AI call: {e}")
                debug(e.__traceback__)
                debug(e.__cause__)
                set_error(f"Error: {e}")
                break
        if not result_md:
            debug("[DEBUG] Could not find a compatible build after several tries.")
            set_result_md("Could not find a compatible build after several tries. Please adjust your preferences and try again.")
        set_loading(False)

    # Fetch currency list on mount
    def fetch_currencies():
        try:
            with open("static/assets/currencies.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                # data is a dict: code -> name (with flag)
                currency_options = sorted([(k, v) for k, v in data.items()], key=lambda x: x[1].lower())
                set_currency_list(currency_options)
        except Exception as e:
            set_currency_list([("eur", "Euro"), ("usd", "US Dollar")])
    use_effect(fetch_currencies, [])

    # Fetch exchange rates on mount and when currency changes
    def fetch_exchange_rates():
        try:
            resp = requests.get("https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                rates = data.get("eur", {})
                set_exchange_rates(rates)
                if DEBUG_MODE:
                    print(f"[DEBUG] Fetched exchange rates")
            else:
                set_exchange_rates({"usd": 1.09, "eur": 1.0})
        except Exception as e:
            set_exchange_rates({"usd": 1.09, "eur": 1.0})
    use_effect(fetch_exchange_rates, [])

    # Budget input with currency dropdown
    def budget_input():
        def handle_budget_change(e):
            val = e["target"]["value"]
            try:
                set_budget(int(val) if val.strip() else 0)
            except Exception:
                set_budget(0)
        return html.div(
            {"className": "form-group"},
            html.label({"for": "budget"}, "Budget:"),
            html.input({
                "type": "number",
                "id": "budget",
                "min": 1,
                "value": budget,
                "onChange": handle_budget_change
            }),
            html.select({
                "id": "currency",
                "value": currency,
                "onChange": lambda e: set_currency(e["target"]["value"])
            }, *[
                html.option({"value": code}, f"{code.upper()} - {name}") for code, name in currency_list
            ])
        )

    # Currency conversion utility
    def convert_to_eur(amount, from_currency):
        if from_currency == "eur" or not exchange_rates:
            return amount
        rate = exchange_rates.get(from_currency, None)
        if rate is None:
            if DEBUG_MODE:
                print(f"[DEBUG] No exchange rate for {from_currency}, returning original amount.")
            return amount
        converted = amount / rate
        if DEBUG_MODE:
            print(f"[DEBUG] Converted {amount} {from_currency.upper()} to {converted:.2f} EUR (rate: {rate})")
        return converted

    def convert_from_eur(amount_eur, to_currency):
        if to_currency == "eur" or not exchange_rates:
            return amount_eur
        rate = exchange_rates.get(to_currency, None)
        if rate is None:
            if DEBUG_MODE:
                print(f"[DEBUG] No exchange rate for {to_currency}, returning EUR amount.")
            return amount_eur
        converted = amount_eur * rate
        if DEBUG_MODE:
            print(f"[DEBUG] Converted {amount_eur} EUR to {converted:.2f} {to_currency.upper()} (rate: {rate})")
        return converted

    # --- Helper: Check for impossible config ---
    def is_impossible_config(budget_eur, use_case, perf_level):
        if use_case == "Gaming" and budget_eur < 400:
            return "A gaming PC is not possible below 400 EUR. Please increase your budget or choose a different use case."
        if perf_level == "Ultra" and budget_eur < 800:
            return "Ultra performance builds are not possible below 800 EUR. Please increase your budget or select a lower performance level."
        if perf_level == "High" and budget_eur < 600:
            return "High performance builds are not possible below 600 EUR. Please increase your budget or select a lower performance level."
        return None

    # --- Helper: Get allowed options for dropdowns based on budget ---
    def allowed_perf_options(budget_eur):
        opts = ["Low", "Medium", "High", "Ultra"]
        # Ultra: 800+, High: 600+, Medium: 350+, Low: always
        if budget_eur < 800 and "Ultra" in opts:
            opts.remove("Ultra")
        if budget_eur < 600 and "High" in opts:
            opts.remove("High")
        if budget_eur < 350 and "Medium" in opts:
            opts.remove("Medium")
        return opts

    def allowed_use_case_options(budget_eur):
        opts = ["Gaming", "Content Creation", "Streaming", "Office/School", "General Use"]
        # Gaming: 400+, Content Creation: 500+, Streaming: 500+, Office/School: always, General Use: always
        if budget_eur < 400 and "Gaming" in opts:
            opts.remove("Gaming")
        if budget_eur < 500 and "Content Creation" in opts:
            opts.remove("Content Creation")
        if budget_eur < 500 and "Streaming" in opts:
            opts.remove("Streaming")
        return opts

    # Handle form submission
    def handle_submit(event):
        if loading:
            debug("[DEBUG] Submit ignored: already loading.")
            return  # Prevent double-clicks
        set_loading(True)
        set_result_md("")
        set_error("")
        # Convert user budget to EUR for AI
        budget_eur = convert_to_eur(budget, currency)
        # --- Check for impossible config before AI call ---
        impossible_msg = is_impossible_config(budget_eur, use_case, perf_level)
        if impossible_msg:
            set_error(impossible_msg)
            set_loading(False)
            return
        brand_pref_str = brand_pref.strip() if brand_pref.strip() else "Doesn't matter"
        games_str = games.strip() if games.strip() else "(not specified)"
        user_prefs = (
            f"Budget: {int(budget_eur)} EUR\n"
            f"Use case: {use_case}\n"
            f"Performance: {perf_level}\n"
            f"Noise: {noise_pref}\n"
            f"Size: {size_pref}\n"
            f"Preferred Brands: {brand_pref_str}\n"
            f"Wi-Fi/Bluetooth: {wifi_pref}\n"
            f"Upgradeability: {upgrade_pref}\n"
            f"Games: {games_str}\n"
        )
        debug(f"[PCPartPicker] {datetime.datetime.now().isoformat()}\nUser preferences (AI gets EUR):\n{user_prefs}")
        ai_response = None
        tries = 0
        max_tries = 6
        last_missing = None
        debug(f"[DEBUG] Entering AI build loop (max_tries={max_tries})")
        while tries < max_tries:
            tries += 1
            debug(f"[DEBUG] AI request attempt {tries} (last_missing={last_missing})")
            prompt = SYSTEM_PROMPT + "\nUser preferences:\n" + user_prefs
            if last_missing:
                dataset_snippet = datasets.get(last_missing, [])[:3]
                for item in dataset_snippet:
                    if "price" in item and item.get("price") is not None:
                        item["price_eur"] = round(convert_to_eur(item["price"], "usd"), 2)
                snippet_str = json.dumps(dataset_snippet, ensure_ascii=False)
                prompt += (f"\nLast time, the part '{last_missing}' could not be found in the dataset. "
                           f"Please suggest a different, more common or compatible {last_missing}. "
                           f"Here is a snippet of the {last_missing} database (prices in EUR):\n{snippet_str}\n")
            debug(f"[DEBUG] Prompt sent to AI (length={len(prompt)}):\n{prompt}")
            try:
                response = requests.post(
                    "https://ai.hackclub.com/chat/completions",
                    json={
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prefs}
                        ],
                        "max_tokens": 400
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=60
                )
                debug(f"[DEBUG] AI response: {response}")
                debug(f"[DEBUG] AI response headers: {response.headers}")
                debug(f"[DEBUG] AI HTTP status: {response.status_code}")
                raw_json = response.json()
                debug(f"[DEBUG] Raw response JSON: {raw_json}")
                if response.status_code == 200:
                    text = raw_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                    debug(f"[PCPartPicker][AI raw response]:\n{text}")
                    if not text.strip():
                        debug("[DEBUG] AI response text is empty!")
                        set_error("AI returned an empty response. Try again.")
                        break
                    # Use non-greedy regex with DOTALL to extract the first JSON object
                    matches = list(re.finditer(r"\{.*?\}", text, re.DOTALL))
                    debug(f"[DEBUG] Regex matches found: {len(matches)}")
                    if len(matches) > 1:
                        debug(f"[DEBUG] Warning: Multiple JSON objects found in AI response. Using the first one.")
                    match = matches[0] if matches else None
                    debug(f"[DEBUG] Regex match: {match}")
                    if not match:
                        debug("[DEBUG] No JSON object found in AI response.")
                        set_error("AI did not return a JSON object. Try again.")
                        with open("ai_debug.log", "a") as f:
                            f.write(f"\n[NO JSON] {datetime.datetime.now().isoformat()}\nPrompt:\n{prompt}\nAI raw text:\n{text}\n\n")
                        break
                    json_str = match.group(0)
                    debug(f"[DEBUG] Extracted JSON string (to be parsed):\n{json_str}")
                    try:
                        data = json.loads(json_str.replace("'", '"'))
                        debug(f"[DEBUG] Parsed JSON: {data}")
                    except Exception as e:
                        debug(f"[DEBUG] JSON parse error: {e}")
                        debug(f"[DEBUG] Problematic string: {json_str}")
                        with open("ai_debug.log", "a") as f:
                            f.write(f"\n[JSON ERROR] {datetime.datetime.now().isoformat()}\nPrompt:\n{prompt}\nAI raw text:\n{text}\nExtracted JSON string:\n{json_str}\nError: {e}\n\n")
                        set_error(f"AI JSON parse error: {e}")
                        break
                    build = {}
                    missing = None
                    for part, name in data.items():
                        debug(f"[DEBUG] Matching {part}: {name}")
                        match = smart_find_best_match(name, datasets.get(part, []))
                        if not match:
                            match = find_best_match(name, datasets.get(part, []))
                        if match:
                            debug(f"[DEBUG] Found match for {part}: {match.get('name')}")
                            build[part] = match
                        else:
                            debug(f"[DEBUG] No match for {part}: {name}")
                            missing = part
                            break
                    if not missing:
                        debug("[DEBUG] All parts matched. Rendering markdown.")
                        # Calculate total price in EUR, USD, and user currency
                        total_eur = 0.0
                        total_usd = 0.0
                        total_user = 0.0
                        for part, info in build.items():
                            if info.get('price'):
                                price_eur = round(convert_to_eur(info['price'], 'usd'), 2)
                                price_user = round(convert_from_eur(price_eur, currency), 2)
                                price_usd = info['price']
                                total_eur += price_eur
                                total_usd += price_usd
                                total_user += price_user
                        md = f"# Your PC Build\n\n"
                        for part, info in build.items():
                            md += f"**{part.upper()}**: {info.get('name', 'Unknown')}\n"
                            if info.get('price'):
                                price_eur = round(convert_to_eur(info['price'], 'usd'), 2)
                                price_user = round(convert_from_eur(price_eur, currency), 2)
                                md += f"- Price: {price_user} {currency.upper()} (original: ${info['price']} USD, €{price_eur} EUR)\n"
                            if info.get('brand'):
                                md += f"- Brand: {info['brand']}\n"
                            if info.get('specs'):
                                md += f"- Specs: {info['specs']}\n"
                            md += "\n"
                        md += f"**Total Price:** {round(total_user,2)} {currency.upper()} (original: ${round(total_usd,2)} USD, €{round(total_eur,2)} EUR)\n\n"
                        md += "---\n"
                        md += "## Tips & Recommendations\n"
                        md += (
                            "- Double-check compatibility before buying.\n"
                            "- Prices and availability may have changed since 2024.\n"
                            "- If you want to upgrade, consider increasing your budget or performance level.\n"
                        )
                        set_result_md(md)
                        # --- Query AI again for expert analysis ---
                        try:
                            build_summary = ", ".join([f"{part}: {info.get('name','Unknown')}" for part, info in build.items()])
                            analysis_prompt = (
                                "You are a PC building expert. Given a build, "
                                "provide a short analysis of potential bottlenecks, system balance, and any expert opinions (e.g., bottleneck calculator, upgrade advice). "
                                "Be concise and helpful."
                            )
                            analysis_response = requests.post(
                                "https://ai.hackclub.com/chat/completions",
                                json={
                                    "messages": [
                                        {"role": "system", "content": analysis_prompt},
                                        {"role": "user", "content": build_summary}
                                    ],
                                    "max_tokens": 250
                                },
                                headers={"Content-Type": "application/json"},
                                timeout=40
                            )
                            analysis_json = analysis_response.json()
                            analysis_text = analysis_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                            if analysis_text:
                                set_result_md(lambda prev: prev + "\n---\n## Expert Analysis\n" + analysis_text.strip())
                        except Exception as e:
                            debug(f"[DEBUG] Error during expert analysis AI call: {e}")
                        # --- Query AI again for game performance estimates ---
                        try:
                            build_summary = ", ".join([f"{part}: {info.get('name','Unknown')}" for part, info in build.items()])
                            games_list = games.strip() if games.strip() else None
                            if games_list:
                                perf_prompt = (
                                    "You are a PC gaming expert. Given a build, "
                                    "estimate how games would run on it. "
                                    "For each game, estimate the expected settings (e.g., low/medium/high/ultra), resolution, and FPS. "
                                    "If a game is not in your knowledge base, say so. "
                                    "Add a disclaimer that these are AI-generated estimates and may not be accurate."
                                )
                                perf_response = requests.post(
                                    "https://ai.hackclub.com/chat/completions",
                                    json={
                                        "messages": [
                                            {"role": "system", "content": perf_prompt},
                                            {"role": "user", "content": f"Build: {build_summary}, Games: {games_list}."}
                                        ],
                                        "max_tokens": 300
                                    },
                                    headers={"Content-Type": "application/json"},
                                    timeout=40
                                )
                                perf_json = perf_response.json()
                                perf_text = perf_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                                if perf_text:
                                    # Ensure each '- ' is on its own line for Markdown
                                    perf_text_md = re.sub(r'(?<!\n)- ', '\n- ', perf_text)
                                    set_result_md(lambda prev: prev + "\n---\n## Game Performance Estimates\n" + perf_text_md.strip())
                        except Exception as e:
                            debug(f"[DEBUG] Error during game performance AI call: {e}")
                        set_loading(False)
                        debug("[DEBUG] Done. Build and analysis shown to user.")
                        return
                    else:
                        last_missing = missing
                        debug(f"[DEBUG] Will retry for missing part: {missing}")
                        continue
                else:
                    debug(f"[DEBUG] AI HTTP error: {response.status_code}")
                    set_error(f"Error: {response.status_code}")
                    break
            except Exception as e:
                debug(f"[DEBUG] Exception during AI call: {e}")
                debug(e.__traceback__)
                debug(e.__cause__)
                set_error(f"Error: {e}")
                break
        if not result_md:
            debug("[DEBUG] Could not find a compatible build after several tries.")
            set_result_md("Could not find a compatible build after several tries. Please adjust your preferences and try again.")
        set_loading(False)

    # Budget input with currency dropdown
    def budget_input():
        def handle_budget_change(e):
            val = e["target"]["value"]
            try:
                set_budget(int(val) if val.strip() else 0)
            except Exception:
                set_budget(0)
        return html.div(
            {"className": "form-group"},
            html.label({"for": "budget"}, "Budget:"),
            html.input({
                "type": "number",
                "id": "budget",
                "min": 1,
                "value": budget,
                "onChange": handle_budget_change
            }),
            html.select({
                "id": "currency",
                "value": currency,
                "onChange": lambda e: set_currency(e["target"]["value"])
            }, *[
                html.option({"value": code}, f"{code.upper()} - {name}") for code, name in currency_list
            ])
        )

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/pc_part_picker.css"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")
        ),
        html.div(
            {"className": "recipe-maker"},
            html.div(
                {"className": "pcpp-inputs"},
                html.h2("AI PC Part Picker"),
                html.p(
                    {"className": "disclaimer"},
                    "⚠️ Disclaimer:",
                    "Due to live API costs, we are using an older dataset from 2024;",
                    "The generation may take a while, give it a few seconds.",
                ),
                (
                    html.div(
                        {"className": "loading-spinner"},
                        html.span({"className": "spinner"}, "⏳"),
                        "Loading PC part options..."
                    ) if parts_loading else None
                ),
                budget_input() if not parts_loading else None,
                dropdown("Use Case", use_case, set_use_case, allowed_use_case_options(convert_to_eur(budget, currency)), "What will you use the PC for?", "use_case") if not parts_loading else None,
                dropdown("Performance", perf_level, set_perf_level, allowed_perf_options(convert_to_eur(budget, currency)), "How powerful do you want it?", "perf_level") if not parts_loading else None,
                dropdown("Noise Preference", noise_pref, set_noise_pref, ["Doesn't matter", "Quiet as possible", "Silent"], "Do you care about fan noise?", "noise_pref") if not parts_loading else None,
                dropdown("Size Preference", size_pref, set_size_pref, ["Standard/Mid Tower", "Small Form Factor", "Doesn't matter"], "How big should the PC be?", "size_pref") if not parts_loading else None,
                brand_textbox("Preferred Brands", brand_pref, set_brand_pref, "Type your preferred brands, separated by commas (optional)", "brand_pref") if not parts_loading else None,
                (games_textbox("Games you want to play", games, set_games, "List the games you want to play (comma separated)", "games") if not parts_loading and use_case == "Gaming" else None),
                dropdown("Wi-Fi/Bluetooth", wifi_pref, set_wifi_pref, ["Doesn't matter", "Yes", "No"], "Do you need built-in Wi-Fi/Bluetooth?", "wifi_pref") if not parts_loading else None,
                dropdown("Upgradeability", upgrade_pref, set_upgrade_pref, ["Important", "Somewhat important", "Not important"], "How important is future upgradeability?", "upgrade_pref") if not parts_loading else None,
                html.button(
                    {
                        "className": f"btn btn-gradient{' btn-disabled' if loading or parts_loading else ''}",
                        "onClick": handle_submit,
                        "disabled": loading or parts_loading
                    },
                    "Get Recommendations" if not loading else "Generating..."
                ),
            ),
            # --- Output on the right (desktop), below on mobile ---
            html.div(
                {"className": "pcpp-output"},
                html.div(
                    {"className": "recipe-output"},
                    html.h3("Recommended Build:"),
                    (
                        html.i({"className": "no-recommendations"}, "No recommendations yet.")
                        if not result_md.strip() and not error else
                        html.div({
                            "dangerouslySetInnerHTML": {"__html": markdown.markdown(result_md)},
                            "key": hash(result_md)
                        })
                    ),
                    (
                        html.p({"className": "error-message"}, error) if error else None
                    )
                )
            )
        )
    )