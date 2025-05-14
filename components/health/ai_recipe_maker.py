from reactpy import component, html, use_state
import requests

@component
def AIRecipeMaker():
    # State variables for ingredients, health level, and the generated recipe
    ingredients, set_ingredients = use_state("")
    health_level, set_health_level = use_state("balanced")
    recipe, set_recipe = use_state("")

    # Function to handle recipe generation
    def handle_generate_recipe(event):
        # Call the AI model via Ollama
        response = requests.post(
            "http://localhost:11434/api/generate",  # Ollama's default endpoint
            json={
                "model": "llama3.2",
                "prompt": f"Create a {health_level} recipe using these ingredients: {ingredients}. Format the recipe in Markdown."
            }
        )
        if response.status_code == 200:
            set_recipe(response.json().get("text", "Failed to generate recipe."))
        else:
            set_recipe("Error: Unable to connect to the AI model.")

    # Return the ReactPy component structure
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
        ),
    )