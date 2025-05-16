from reactpy import component, html, use_state
import requests
import json

@component
def AIRecipeMaker():
    ingredients, set_ingredients = use_state("")
    health_level, set_health_level = use_state("balanced")
    recipe, set_recipe = use_state("")

    def handle_generate_recipe(event):
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": f"Create a {health_level} recipe using these ingredients: {ingredients}. Format the recipe in Markdown."
                },
                stream=True
            )
            if response.status_code == 200:
                recipe_text = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        # Ollama streams with "response" or "text" field
                        recipe_text += data.get("response", data.get("text", ""))
                set_recipe(recipe_text if recipe_text else "Failed to generate recipe.")
            else:
                set_recipe("Error: Unable to connect to the AI model.")
        except Exception as e:
            set_recipe(f"Exception: {e}")

    return html.div(
        {"className": "recipe-maker"},
        html.h2("AI Recipe Maker"),
        html.div(
            {"className": "form-group"},
            html.label({"for": "ingredients"}, "Ingredients (comma-separated):"),
            html.input(
                {
                    "id": "ingredients",
                    "type": "text",
                    "value": ingredients,
                    "onInput": lambda event: set_ingredients(event["target"]["value"]),
                }
            ),
        ),
        html.div(
            {"className": "form-group"},
            html.label({"for": "health-level"}, "Health Level:"),
            html.select(
                {
                    "id": "health-level",
                    "value": health_level,
                    "onChange": lambda event: set_health_level(event["target"]["value"]),
                },
                html.option({"value": "balanced"}, "Balanced"),
                html.option({"value": "healthy"}, "Healthy"),
                html.option({"value": "indulgent"}, "Indulgent"),
            ),
        ),
        html.button(
            {"className": "generate-btn", "onClick": handle_generate_recipe},
            "Generate Recipe"
        ),
        html.div(
            {"className": "recipe-output"},
            html.h3("Generated Recipe:"),
            html.pre(recipe),
        )
    )