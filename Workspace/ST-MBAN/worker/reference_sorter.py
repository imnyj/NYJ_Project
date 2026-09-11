import os
import sys
import re
import time
import shutil

# Import lock_manager and audit_logger from core
sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

def strip_empty_lines(lines):
    # Strip leading empty lines
    start = 0
    while start < len(lines) and lines[start].strip() == '':
        start += 1
    # Strip trailing empty lines
    end = len(lines)
    while end > start and lines[end - 1].strip() == '':
        end -= 1
    return lines[start:end]

def main():
    tex_path = "/home/imnyj/papers/paper1/paper/draft/main.tex"
    agent_id = "reference_sorter"
    
    lm = LockManager()
    logger = AuditLogger()
    
    # 1. Acquire Lock
    print("Acquiring lock for main.tex...")
    if not lm.acquire(tex_path, agent_id):
        print("Failed to acquire lock. Exiting.")
        sys.exit(1)
        
    try:
        # 2. Backup File (with timestamp)
        backup_dir = "/home/imnyj/papers/paper1/paper/draft/backup"
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = int(time.time())
        backup_path = os.path.join(backup_dir, f"main.tex.{timestamp}.bak")
        shutil.copy2(tex_path, backup_path)
        print(f"Backup created at {backup_path}")
        
        # 3. Read main.tex
        with open(tex_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Clean up formatting anomalies (literal \n before \end{thebibliography})
        content = content.replace('\\n\\end{thebibliography}', '\\end{thebibliography}')
            
        # 4. Split content into body, bibliography, and tail
        bib_start_match = re.search(r'\\begin\{thebibliography\}\{\d+\}', content)
        if not bib_start_match:
            print("Could not find \\begin{thebibliography}{...} in main.tex")
            sys.exit(1)
            
        bib_start_idx = bib_start_match.start()
        body_text = content[:bib_start_idx]
        
        bib_rest = content[bib_start_idx:]
        bib_end_match = re.search(r'\\end\{thebibliography\}', bib_rest)
        if not bib_end_match:
            print("Could not find \\end{thebibliography} in main.tex")
            sys.exit(1)
            
        bib_end_idx = bib_end_match.start()
        bib_content = bib_rest[:bib_end_idx + len('\\end{thebibliography}')]
        tail_text = bib_rest[bib_end_idx + len('\\end{thebibliography}'):]
        
        # 5. Scan body_text for \cite{...}
        cite_pattern = re.compile(r'\\cite\s*\{([^}]+)\}')
        citations = cite_pattern.findall(body_text)
        
        appeared_keys = []
        for cit in citations:
            keys = [k.strip() for k in cit.split(',')]
            for k in keys:
                if k and k not in appeared_keys:
                    appeared_keys.append(k)
                        
        print(f"Appeared keys (in order of appearance, count={len(appeared_keys)}): {appeared_keys}")
        
        # Build mapping for appeared keys
        old_to_new = {}
        for idx, old_k in enumerate(appeared_keys):
            old_to_new[old_k] = idx + 1
            
        print("Mapping created successfully. Verification:")
        for k in sorted(old_to_new.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            print(f"  {k} -> {old_to_new[k]}")
            
        # 6. Replace \cite in body_text
        def replace_cite(match):
            content_str = match.group(1)
            keys = [k.strip() for k in content_str.split(',')]
            new_keys = []
            for k in keys:
                if k in old_to_new:
                    new_keys.append(str(old_to_new[k]))
                else:
                    new_keys.append(k)
            return f"\\cite{{{','.join(new_keys)}}}"
            
        updated_body_text = cite_pattern.sub(replace_cite, body_text)
        
        # 7. Parse bibliography
        bib_lines = bib_content.splitlines()
        header_lines = []
        bibitem_dict = {}
        current_key = None
        in_header = True
        
        for line in bib_lines:
            line_stripped = line.strip()
            if line_stripped.startswith(r'\bibitem'):
                in_header = False
                match = re.match(r'\\bibitem\s*\{([^}]+)\}', line_stripped)
                if match:
                    key_str = match.group(1).strip()
                    current_key = key_str
                    bibitem_dict[current_key] = []
                else:
                    current_key = None
            elif line_stripped == r'\end{thebibliography}':
                current_key = None
            else:
                if in_header:
                    if r'\begin{thebibliography}' in line:
                        line = f"\\begin{{thebibliography}}{{{len(appeared_keys)}}}"
                    header_lines.append(line)
                elif current_key is not None:
                    # Skip category comment lines like %% **********
                    if line_stripped.startswith('%%') and '***' in line_stripped:
                        continue
                    bibitem_dict[current_key].append(line)
                    
        # 8. Rebuild bibliography
        new_bib_lines = []
        new_bib_lines.extend(header_lines)
        
        new_to_old = {v: k for k, v in old_to_new.items()}
        
        for new_key in range(1, len(appeared_keys) + 1):
            old_key = new_to_old[new_key]
            # Write \bibitem{new_key}
            new_bib_lines.append(f"\\bibitem{{{new_key}}}")
            # Write the content
            content_lines = strip_empty_lines(bibitem_dict.get(old_key, []))
            new_bib_lines.extend(content_lines)
            # Add an empty line between bibitems
            new_bib_lines.append("")
            
        new_bib_lines.append(r"\end{thebibliography}")
        
        # 9. Merge and Write back
        final_content = updated_body_text + '\n'.join(new_bib_lines) + '\n' + tail_text
        
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        print("main.tex updated successfully.")
        
        # Calculate removed count
        total_old_references = len(bibitem_dict)
        removed_count = total_old_references - len(appeared_keys)
        
        # 10. Audit Log
        logger.log_action(agent_id, "MODIFY", tex_path, f"Sorted references by order of appearance, purged {removed_count} unused references, and updated cite keys.")
        
        # 11. Write progress file
        progress_path = "/home/imnyj/Workspace/paper1/worker/reference_sort_progress.md"
        progress_dir = os.path.dirname(progress_path)
        os.makedirs(progress_dir, exist_ok=True)
        
        with open(progress_path, 'w', encoding='utf-8') as f:
            f.write("# Reference Sorter Progress Report (Final Run)\n\n")
            f.write(f"- **Date/Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Agent**: `{agent_id}`\n")
            f.write("- **Status**: Completed final run successfully\n")
            f.write(f"- **Backup file**: `{backup_path}`\n")
            f.write(f"- **Total Cited References**: {len(appeared_keys)}\n")
            f.write(f"- **Removed Unused References**: {removed_count} (originally {total_old_references} total)\n\n")
            f.write("## Reference Mapping (Old Key -> New Key)\n\n")
            f.write("| Old Key | New Key | Cited in Body | First Appearance Order |\n")
            f.write("|---|---|---|---|\n")
            for old_k in appeared_keys:
                f.write(f"| {old_k} | {old_to_new[old_k]} | Yes | {old_to_new[old_k]} |\n")
                
        print(f"Progress report written to {progress_path}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Release lock
        print("Releasing lock...")
        lm.release(tex_path, agent_id)
        print("Lock released.")

if __name__ == "__main__":
    main()
