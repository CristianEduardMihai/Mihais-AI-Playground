import subprocess
import os

# npm install -g @mermaid-js/mermaid-cli

MERMAID_CODE = '''
stateDiagram-v2
    [*] --> Still
    Still --> [*]

    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
'''

MMD_FILE = "diagram.mmd"
PNG_FILE = "diagram.png"

# Write Mermaid code to .mmd file
with open(MMD_FILE, "w", encoding="utf-8") as f:
    f.write(MERMAID_CODE)

# Call Mermaid CLI to generate PNG
try:
    subprocess.run(["mmdc.cmd", "-i", MMD_FILE, "-o", PNG_FILE], check=True)   # .CMD FOR WINDOWS TESTING
    print(f"PNG generated: {PNG_FILE}")
    # Optionally open the PNG file (Windows only)
    os.startfile(PNG_FILE)
except subprocess.CalledProcessError as e:
    print(f"Error running mmdc: {e}")