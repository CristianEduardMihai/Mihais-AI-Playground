import asyncio
import aiohttp
import subprocess
import os

async def ask_ai(prompt, user_input):
    system_prompt = (
        "You are a helpful business mentor AI. "
        "Guide the user through a business idea as a single, complex Mermaid flowchart. "
        "Output ONLY the Mermaid diagram code, with no markdown, no code blocks, and no explanations or instructions. "
        "Do not include ``` or any markdown formatting. Just output the raw Mermaid code. "
        "The diagram should be as detailed as possible, showing all major steps and decisions."
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://ai.hackclub.com/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            },
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"AI model returned {response.status}")
            data = await response.json()
    return data["choices"][0]["message"]["content"]

def render_mermaid(mermaid_code, filename="business_idea.png"):
    mmd_file = "business_idea.mmd"
    with open(mmd_file, "w", encoding="utf-8") as f:
        f.write(mermaid_code)
    try:
        subprocess.run(["mmdc", "-i", mmd_file, "-o", filename])
        print(f"Diagram saved as {filename}")
        if os.name == "nt":
            os.startfile(filename)
    except Exception as e:
        print(f"Error rendering Mermaid diagram: {e}")

def main():
    print("Welcome to the AI Business Guide!")
    capital = input("What is your starting capital (EUR)? ")
    skills = input("What are your main skills? (comma separated) ")
    user_input = f"I have a starting capital of {capital} EUR. I know how to do {skills}. Suggest a business idea and output a complex Mermaid flowchart for the whole process, not just the first step. Output only the Mermaid code, no markdown or code blocks."
    loop = asyncio.get_event_loop()
    mermaid_code = loop.run_until_complete(ask_ai("", user_input))
    print("\nAI Mermaid Code (copy below for .mmd):\n")
    print(mermaid_code)
    # Always render as PNG
    render_mermaid(mermaid_code, filename="business_idea.png")

if __name__ == "__main__":
    main()
