from reactpy import component, html, use_state
import requests
import json

@component
def AIRecipeMaker():
    ingredients, set_ingredients = use_state("")
    health_level, set_health_level = use_state("balanced")
    servings, set_servings = use_state("2")
    recipe_html, set_recipe_html = use_state("")

    def handle_generate_recipe(event):
        set_recipe_html("")  # clear previous
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5-coder:7b",
                    "prompt": (
                        f"Create a recipe using these ingredients: {ingredients}. "
                        f"Make it the following health level: {health_level}. "
                        f"Portion it for {servings} people. "
                        "Assume the user also has common ingredients like sugar, salt, and flour. "
                        "Add nutrition information at the end, including calories, protein, carbs, and fat, both per serving and per 100g. "
                        "Format the recipe as HTML with CLEAR headings (<strong> them) and lists. Make sure it looks good on a web page. "
                        "Use H2 for the recipe title, H3 for the ingredients (bullet points), and H4 for the instructions. "
                        "Do NOT use Markdown at all. NO ### or * or _ or any other Markdown formatting."
                    )
                },
                stream=True,
                timeout=60
            )
            if response.status_code == 200:
                full_html = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode("utf-8"))
                        full_html += data.get("response", "")
                set_recipe_html(full_html or "<p>(no content)</p>")
            else:
                set_recipe_html(
                    f"<p style='color:red'>Error: AI model returned {response.status_code}</p>"
                )
        except Exception as e:
            set_recipe_html(f"<p style='color:red'>Exception: {e}</p>")

    def render_output():
        if not recipe_html.strip():
            return html.i({"style": {"color": "#888"}}, "No recipe generated yet.")
        return html.div({
            "dangerouslySetInnerHTML": {"__html": recipe_html},
            "key": hash(recipe_html)
        })

    style = """
    .recipe-maker {
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 2rem;
        margin: 2rem auto;
        max-width: 600px;
        font-family: Arial, sans-serif;
    }
    .form-group {
        margin-bottom: 1.5rem;
    }
    label {
        display: block;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    input[type="text"], select {
        width: 100%;
        padding: 0.5rem;
        border-radius: 4px;
        border: 1px solid #ccc;
        font-size: 1rem;
    }
    input[type="number"] {
        width: 4rem;
        padding: 0.5rem;
        border-radius: 4px;
        border: 1px solid #ccc;
        font-size: 1rem;
        text-align: center;
        margin-left: 0.5rem;
    }
    .generate-btn {
        background-color: #6200ea;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 4px;
        font-size: 1rem;
        cursor: pointer;
        margin-bottom: 1.5rem;
    }
    .generate-btn:hover {
        background-color: #3700b3;
    }
    .recipe-output {
        margin-top: 2rem;
        background: #f4f4f9;
        border-radius: 6px;
        padding: 1rem;
    }
    .pdf-btn {
        background-color: #03a9f4;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-size: 0.9rem;
        cursor: pointer;
        margin-top: 1rem;
    }
    .pdf-btn:hover {
        background-color: #0288d1;
    }
    """

    return html.div(
        {},
        html.style(style),
        html.div(
            {"className": "recipe-maker"},
            html.h2("AI Recipe Maker"),
            # Ingredients
            html.div(
                {"className": "form-group"},
                html.label({"for": "ingredients"}, "What ingredients do you have?"),
                html.input({
                    "id": "ingredients",
                    "type": "text",
                    "value": ingredients,
                    "placeholder": "e.g. chicken, tomatoes, cheese",
                    "onInput": lambda e: set_ingredients(e["target"]["value"])
                }),
            ),
            # Health level
            html.div(
                {"className": "form-group"},
                html.label({"for": "health-level"}, "Health Level:"),
                html.select({
                    "id": "health-level",
                    "value": health_level,
                    "onChange": lambda e: set_health_level(e["target"]["value"])
                },
                    html.option({"value": "balanced"}, "Balanced"),
                    html.option({"value": "healthy"}, "Healthy"),
                    html.option({"value": "indulgent"}, "Indulgent"),
                ),
            ),
            # Servings
            html.div(
                {"className": "form-group"},
                html.label({"for": "servings"}, "Servings:"),
                html.input({
                    "id": "servings",
                    "type": "number",
                    "min": "1",
                    "value": servings,
                    "onInput": lambda e: set_servings(e["target"]["value"])
                }),
                html.span({"style": {"marginLeft": "0.5rem"}}, "people")
            ),
            # Generate button
            html.button(
                {"className": "generate-btn", "onClick": handle_generate_recipe},
                "Generate Recipe"
            ),
            # Output + Save as PDF
            html.div(
                {"className": "recipe-output"},
                html.h3("Generated Recipe:"),
                render_output(),
                # Browser‑side PDF link—no Python event needed
                html.a(
                    {
                        "className": "pdf-btn",
                        "href": "javascript:window.print()"
                    },
                    "Save as PDF"
                )
            )
        )
    )
