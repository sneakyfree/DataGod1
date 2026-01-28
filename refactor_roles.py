import re
import os

file_path = 'api/src/api_v2.py'

with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
skip_next = False

# Regex to capture roles from @has_role(["admin", "user"])
# Expects: @has_role(["admin"]) or @has_role(["admin", "user"])
role_pattern = re.compile(r'@has_role\(\[(.*?)\]\)')

for i, line in enumerate(lines):
    if skip_next:
        skip_next = False
        continue

    # Check if current line is @has_role
    match = role_pattern.search(line)
    if match:
        roles_str = match.group(1) # e.g. "admin", "user"
        
        # Check previous line (it's already in new_lines, last element)
        if new_lines and ('@app.' in new_lines[-1] or '@router.' in new_lines[-1]):
            prev_line = new_lines.pop()
            stripped_prev = prev_line.rstrip()
            
            # If previous line ends with ), remove it and append dependency
            if stripped_prev.endswith(')'):
                new_prev = stripped_prev[:-1] + f', dependencies=[Depends(RoleChecker([{roles_str}]))])\n'
                new_lines.append(new_prev)
                # Skip current line (do not add @has_role)
                continue
            else:
                # Previous line might be multiline or ending differently
                print(f"Warning at line {i}: Previous line format unexpected: {stripped_prev}")
                new_lines.append(prev_line)
                new_lines.append(line)
        else:
            print(f"Warning at line {i}: @has_role not preceded by @app decorator")
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(file_path, 'w') as f:
    f.writelines(new_lines)

print("Refactoring complete.")
