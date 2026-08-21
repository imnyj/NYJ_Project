import os
file_path = '/home/imnyj/.gemini/antigravity-cli/brain/8130db3b-367f-452c-bbe0-02bd3f253a09/walkthrough.md'
with open(file_path, 'r') as f:
    text = f.read()

text = text.replace('/home/imnyj/papers/paper4/paper/data/plots/', '/home/imnyj/.gemini/antigravity-cli/brain/8130db3b-367f-452c-bbe0-02bd3f253a09/')

with open(file_path, 'w') as f:
    f.write(text)
print("Updated walkthrough.md paths")
