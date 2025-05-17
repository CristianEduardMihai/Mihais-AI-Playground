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
        set_recipe_html("")  # Clear previous output
        try:
            prompt = (
                "Please output a recipe in Markdown using this template:\n\n"
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
                "*Note: Nutritional values are approximate and AI generated.*\n\n"
                "## Alergens\n"
                "- allergen 1\n"
                "- allergen 2\n\n"
                "\n\n"
                f"Use these ingredients: {ingredients}\n"
                "Assume the user also has common ingredients like sugar, salt, and flour.\n"
                "Explain the recipe in detail, including cooking times and methods, do not cheap down on words.\n"
                "You don't have to use all the ingredients.\n\n"
                f"Health level: {health_level}\n"
                f"Servings: {servings}\n\n"
                "Fill in each section accordingly, using bullet lists and numbered steps exactly as above. "
            )

            response = requests.post(
                "https://ai.hackclub.com/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a helpful chef AI. "
                                "Output ONLY the recipe in Markdown format, with no extra comments, explanations, or preamble. "
                                "Do not include any text outside the Markdown recipe. "
                                "Follow the provided template exactly."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=60
            )
            if response.status_code != 200:
                raise RuntimeError(f"AI model returned {response.status_code}")

            data = response.json()
            md = data["choices"][0]["message"]["content"]

            html_content = markdown.markdown(md, extensions=["tables"])
            set_recipe_html(f"<div class='markdown-body'>{html_content}</div>")

        except Exception as e:
            set_recipe_html(f"<p style='color:red'>Error: {e}</p>")


    return html.div(
        {},
        # External CSS and background
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/ai_recipe_maker.css"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")
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
                    "onChange": lambda e: set_ingredients(e["target"]["value"])
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
                    "onChange": lambda e: set_servings(e["target"]["value"])
                }),
                html.span({"style": {"marginLeft": "0.5rem"}}, "people")
            ),
            # Generate button
            html.button(
                {"className": "btn btn-primary", "onClick": handle_generate_recipe},
                "Generate Recipe"
            ),
            # Output + Save as PDF
            html.div(
                {"className": "recipe-output"},
                html.h3("Generated Recipe:"),
                (
                    html.i({"style": {"color": "#888"}}, "No recipe generated yet.")
                    if not recipe_html.strip()
                    else html.div({
                        "dangerouslySetInnerHTML": {"__html": recipe_html},
                        "key": hash(recipe_html)
                    })
                ),
                html.a(
                    {"className": "btn btn-secondary", "href": "javascript:window.print()"},
                    "Save as PDF"
                )
            )
        )
    )