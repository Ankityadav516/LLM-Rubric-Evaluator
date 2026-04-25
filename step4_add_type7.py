import os

t7_dir = "Rubrics/Type_7_Agnostic_Simple"
os.makedirs(t7_dir, exist_ok=True)

# The Simple Agnostic Rubric Text 
simple_rubric_content = """Simple Agnostic Evaluation Rubric
1. Core Functionality [5 marks]: Does the logic solve the primary objective of the problem without major flaws?
2. Efficiency & Cleanliness [5 marks]: Is the code reasonably optimal, readable, and free of massive syntax errors?
"""

# Get all problem IDs from Type 1 to copy the naming convention
in_dir = "Rubrics/Type_1_Original"

for filename in os.listdir(in_dir):
    if not filename.endswith(".txt"): continue
    
    with open(os.path.join(t7_dir, filename), 'w', encoding='utf-8') as f:
        f.write(simple_rubric_content)

print(f"Success! Generated Simple Agnostic Rubrics in {t7_dir}")