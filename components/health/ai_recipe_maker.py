from reactpy import component, html, use_state
import requests
import json
import markdown 

@component
def AIRecipeMaker():
    ingredients, set_ingredients = use_state("")
    health_level, set_health_level = use_state("balanced")
    servings, set_servings = use_state("2")
    recipe_html, set_recipe_html = use_state("")

    def handle_generate_recipe(event):
        # Clear previous output
        set_recipe_html("")
        try:
            # Stream in Markdown from LLM
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": (
                        "Please output a recipe in Markdown using this template:\n\n"
                        "```\n"
                        "# Recipe Title\n\n"
                        "## Ingredients\n"
                        "- ingredient 1\n"
                        "- ingredient 2\n\n"
                        "## Instructions\n"
                        "1. Step one\n"
                        "2. Step two\n\n"
                        "## Nutrition (per serving / per 100g)\n"
                        "| Nutrient     | per serving | per 100g |\n"
                        "|--------------|-------------|----------|\n"
                        "| Calories     |             |          |\n"
                        "| Protein      |             |          |\n"
                        "| Carbs        |             |          |\n"
                        "| Fat          |             |          |\n"
                        "*Note: Nutritional values are approximate and AI generated.*\n"
                        "## Alergens\n"
                        "- allergen 1\n"
                        "- allergen 2\n\n"
                        "```\n\n"
                        f"Use these ingredients: {ingredients}\n"
                        "Assume the user also has common ingredients like sugar, salt, and flour.\n"
                        "You don't have to use all the ingredients.\n\n"
                        f"Health level: {health_level}\n"
                        f"Servings: {servings}\n\n"
                        "—\n\n"
                        "Fill in each section accordingly, using bullet lists and numbered steps exactly as above. "
                    )
                },
                stream=True,
                timeout=60
            )
            if response.status_code != 200:
                raise RuntimeError(f"AI model returned {response.status_code}")

            # Accumulate Markdown
            md = ""
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    md += chunk.get("response", chunk.get("text", ""))

            # Convert Markdown → HTML (enable tables)
            html_content = markdown.markdown(md, extensions=["tables"])

            # Wrap in a container to scope styles if needed
            set_recipe_html(f"<div class='markdown-body'>{html_content}</div>")

        except Exception as e:
            set_recipe_html(f"<p style='color:red'>Error: {e}</p>")

    def render_output():
        if not recipe_html.strip():
            return html.i({"style": {"color": "#888"}}, "No recipe generated yet.")
        return html.div({
            "dangerouslySetInnerHTML": {"__html": recipe_html},
            "key": hash(recipe_html)
        })

    return html.div(
        {},
        # External CSS
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/ai_recipe_maker.css"}),
        html.link({"rel": "icon", "href": "/static/favicon.ico", "type": "image/x-icon"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "home-btn"}, "🏠 Home")
        ),
        html.div(
            {"className": "recipe-maker"},
            html.h2("AI Recipe Maker"),
            # Ingredients
            html.div(
                {"className": "form-group"},
                html.label({"for": "ingredients"}, "Ingredients:"),
                html.input({
                    "id": "ingredients", "type": "text", "value": ingredients,
                    "placeholder": "e.g. chicken, tomatoes, cheese",
                    "onInput": lambda e: set_ingredients(e["target"]["value"])
                }),
            ),
            # Health level
            html.div(
                {"className": "form-group"},
                html.label({"for": "health-level"}, "Health Level:"),
                html.select({
                    "id": "health-level", "value": health_level,
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
                    "id": "servings", "type": "number", "min": "1", "value": servings,
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
                html.a(
                    {"className": "pdf-btn", "href": "javascript:window.print()"},
                    "Save as PDF"
                )
            )
        )
    )
