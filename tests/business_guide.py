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
        "The diagram should be as detailed as possible, showing all major steps and decisions. "
        "When outputting Mermaid code, use only valid Mermaid syntax for the requested diagram type. "
        "For graph edges, use the format `A -->|label| B`, with no extra characters like `>`, `<`, or `?>`. "
        "For decision nodes, use curly braces with only the label inside, e.g., `B{Can I make saleable products?}`. "
        "Do not use `?>` or `|>` in any part of the diagram. "
        "Prefer a vertical layout by using 'graph TD' or 'flowchart TD' instead of 'graph LR'. "
        "Refer to the official Mermaid flowchart syntax: https://mermaid.js.org/syntax/flowchart.html "
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
        # Increase scale for higher resolution PNG
        subprocess.run(["mmdc.cmd", "-i", mmd_file, "-o", filename, "-s", "3"], check=True)
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
    max_retries = 2
    attempt = 0
    while attempt <= max_retries:
        mermaid_code = loop.run_until_complete(ask_ai("", user_input))
        print(f"\nAI Mermaid Code (attempt {attempt+1}):\n")
        print(mermaid_code)
        try:
            render_mermaid(mermaid_code, filename="business_idea.png")
            break  # Success
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            attempt += 1
            if attempt > max_retries:
                print("All attempts to generate a valid Mermaid diagram failed.")
                return
            print("Retrying with the same input...\n")

if __name__ == "__main__":
    main()
