import sys, json, re, ast
from pprint import pprint

# Read input from stdin
data = sys.stdin.read()

data = data.replace('\\n', "\n")
data = data.replace('\t', "\n")
data = ast.literal_eval(data)
pprint(data)

# # Clean up the data
# data = data.strip("()")  # Remove outer parentheses
# data = data.replace('"{', "{")  # Remove outer parentheses
# data = data.replace(
#     """}",
# )""",
#     "}",
# )

# data = data.replace("\\\\n", "\\n")  # Replace \\n with \n
# data = data.replace("\\n", "\n")  # Replace \\n with \n
# data = data.replace('\\"', '"')  # Replace escaped quotes
# data = re.sub(r"\\s+", " ", data)  # Remove extra whitespace

# # Parse JSON and pretty-print
# try:
#     # print("data", data)
#     parsed_data = json.loads(data)
#     print(json.dumps(parsed_data))
# except json.JSONDecodeError as e:
#     print("Error parsing JSON:", e)
