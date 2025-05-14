from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import List
import openai
import os
from dotenv import load_dotenv
import uvicorn

load_dotenv()

app = FastAPI()

# Configure CORS
"""
origins = ["https://willbuylater.xyz"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
"""
# Allow all origins for development purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OpenAI API key not found. Set OPENAI_API_KEY in your environment.")

# Models for request validation
class RoastRequest(BaseModel):
    prompt: str

class RecipeRequest(BaseModel):
    ingredients: List[str]

class CaloriesRequest(BaseModel):
    food: str

# Helper function to call OpenAI API
async def generate_openai_response(prompt: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

# POST /roast endpoint
@app.post("/roast")
async def roast(request: RoastRequest):
    try:
        prompt = f"Roast this: {request.prompt}"
        response = await generate_openai_response(prompt)
        return {"response": response}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST /recipe endpoint
@app.post("/recipe")
async def recipe(request: RecipeRequest):
    try:
        prompt = f"Create a recipe using these ingredients: {', '.join(request.ingredients)}"
        response = await generate_openai_response(prompt)
        return {"response": response}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST /calories endpoint
@app.post("/calories")
async def calories(request: CaloriesRequest):
    try:
        prompt = f"Estimate the calories in this food: {request.food}"
        response = await generate_openai_response(prompt)
        return {"response": response}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the server using uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)