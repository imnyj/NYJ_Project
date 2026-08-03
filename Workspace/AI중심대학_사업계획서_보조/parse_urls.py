import glob
from bs4 import BeautifulSoup
import re

files = [
    "/home/imnyj/.gemini/antigravity-cli/brain/1c053628-e908-435e-b62b-bcf020ae8d11/.system_generated/steps/215/content.md",
    "/home/imnyj/.gemini/antigravity-cli/brain/1c053628-e908-435e-b62b-bcf020ae8d11/.system_generated/steps/216/content.md",
    "/home/imnyj/.gemini/antigravity-cli/brain/1c053628-e908-435e-b62b-bcf020ae8d11/.system_generated/steps/221/content.md",
    "/home/imnyj/.gemini/antigravity-cli/brain/1c053628-e908-435e-b62b-bcf020ae8d11/.system_generated/steps/222/content.md",
    "/home/imnyj/.gemini/antigravity-cli/brain/1c053628-e908-435e-b62b-bcf020ae8d11/.system_generated/steps/226/content.md",
]

with open("articles_summary.txt", "w", encoding="utf-8") as out:
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as file:
                content = file.read()
                soup = BeautifulSoup(content, 'html.parser')
                
                # find board body
                view_node = soup.find(class_=re.compile('board_txt|board_view_con|board_body'))
                if view_node:
                    for s in view_node(['script', 'style']):
                        s.extract()
                    body = view_node.get_text(separator='\n', strip=True)
                else:
                    body = "No Content"
                    
                out.write(f"--- FILE: {f} ---\n")
                out.write(f"CONTENT:\n{body}\n\n")
        except Exception as e:
            out.write(f"Error reading {f}: {e}\n")
