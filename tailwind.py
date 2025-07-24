from pytailwind import Tailwind
from pathlib import Path
from typing import List, Dict, Any

def generate_tailwind_css():
    """
    Generates Tailwind CSS classes based on the provided configuration.
    """
    tailwind = Tailwind()


    # go through every html file and combine all content
    html_files = Path("assets/html").rglob("*.html")
    combined_content = ""
    for html_file in html_files:
        with open(html_file, 'r', encoding='utf-8') as file:
            combined_content += file.read() + "\n"
    
    # generate tailwind css classes

    tailwind_css = tailwind.generate(combined_content)

    # write the tailwind css to a file
    output_path = Path("assets/css/tailwind.css")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(tailwind_css)