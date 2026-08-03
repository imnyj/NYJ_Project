import sys
import re

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 check_citations.py <file>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    
    with open(filepath, 'r') as f:
        content = f.read()
        
    # Check for empty cite blocks like \cite{}
    empty_cites = re.findall(r'\\cite\{\s*\}', content)
    if empty_cites:
        print(f"Error: Empty \\cite{{}} found in {filepath}")
        sys.exit(1)
        
    # Check for broken citations like [?]
    if '[?]' in content:
        print(f"Error: Broken citation [?] found in {filepath}")
        sys.exit(1)
        
    print(f"Citations in {filepath} look OK.")
    sys.exit(0)

if __name__ == '__main__':
    main()
