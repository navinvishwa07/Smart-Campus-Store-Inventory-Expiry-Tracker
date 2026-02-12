
import re
import os

app_js_path = 'frontend/app.js'

with open(app_js_path, 'r') as f:
    content = f.read()

# Regex to find function definitions
# Matches: function name( or async function name(
# Assumes function names are valid identifiers
func_pattern = re.compile(r'^(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(', re.MULTILINE)

matches = func_pattern.findall(content)
unique_funcs = sorted(list(set(matches)))

# Existing exports
existing_exports = re.findall(r'window\.([a-zA-Z0-9_]+)\s*=', content)

# Check for const/let defined functions if any (unlikely in this codebase but good to check)
# Skipping for now as code uses function declarations mostly.

to_append = []
for func in unique_funcs:
    if func not in existing_exports and func != 'init': # init might be generic, but let's include it
        to_append.append(f"window.{func} = {func};")

if to_append:
    with open(app_js_path, 'a') as f:
        f.write("\n// Auto-exposed functions for HTML event handlers\n")
        f.write("\n".join(to_append))
        f.write("\n")

print(f"Exposed {len(to_append)} functions.")
print("\n".join(to_append))
