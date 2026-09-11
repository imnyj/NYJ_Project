with open('/home/imnyj/.gemini/antigravity-cli/brain/bff0f4a2-6bd4-4508-ae14-d560f3f05914/writer_instructions.md', 'r') as f:
    content = f.read()
start = content.find("```latex\n") + 9
end = content.find("```", start)
bib_str = content[start:end]
with open('bib_extracted.txt', 'w') as f:
    f.write(bib_str)
