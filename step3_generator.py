import os
import random
import re

# Pro Move: Deterministic seed for reproducible research
random.seed(42)

# Directories
in_dir = "Rubrics/Type_1_Original"
t2_dir = "Rubrics/Type_2_Agnostic"
t3_dir = "Rubrics/Type_3_Degraded_10"
t4_dir = "Rubrics/Type_4_Degraded_30"
t5_dir = "Rubrics/Type_5_Error_10"
t6_dir = "Rubrics/Type_6_Error_30"

# The Master QA Rubric Text
qa_rubric_content = """Question Agnostic Evaluation Rubric
1. Logical Correctness [4 marks]: Does the code fulfill the core objective without failing on standard test cases?
2. Time & Space Efficiency [2 marks]: Is the chosen algorithm optimal, or does it use unnecessary nested loops or extra memory?
3. Edge Case Handling [2 marks]: Does the code safely handle null inputs, empty arrays, or extreme boundary values?
4. Code Compilability & Syntax [1 mark]: Does the code compile cleanly without syntax errors?
5. Readability & Structure [1 mark]: Are variables named meaningfully and is the logic easy to follow?
"""

# Process every original rubric
for filename in os.listdir(in_dir):
    if not filename.endswith(".txt"): continue
    
    # -----------------------------------------
    # 1. AUTO-GENERATE QA RUBRIC (TYPE 2)
    # -----------------------------------------
    with open(os.path.join(t2_dir, filename), 'w', encoding='utf-8') as f:
        f.write(qa_rubric_content)
    
    # -----------------------------------------
    # 2. PROCESS ORIGINAL FOR DEGRADATION
    # -----------------------------------------
    filepath = os.path.join(in_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Isolate steps by "Approach" or "Solution"
    approaches = []
    current_approach = []
    
    for i, line in enumerate(lines):
        # Look for headers like "Solution 1:" or "Approach 2"
        if re.search(r'(Solution|Approach)\s*\d+', line, re.IGNORECASE):
            if current_approach:
                approaches.append(current_approach)
                current_approach = []
        
        # If it's a step, add its index to the current approach
        if '[' in line and 'mark' in line.lower():
            current_approach.append(i)
            
    if current_approach:
        approaches.append(current_approach)

    # Calculate drops for EACH approach independently
    to_drop_10 = set()
    to_drop_30 = set()
    
    for step_indices in approaches:
        total_steps = len(step_indices)
        if total_steps == 0: continue
        
        # Apply the hard percentage ceilings per approach
        count_10 = round(total_steps * 0.10)
        if count_10 == 0 and (1 / total_steps) <= 0.30:
            count_10 = 1
            
        count_30 = round(total_steps * 0.30)
        if count_30 <= count_10:
            desired_30 = count_10 + 1
            if (desired_30 / total_steps) <= 0.50:
                count_30 = desired_30
            else:
                count_30 = count_10 
                
        if count_30 == 0 and (1 / total_steps) <= 0.50:
            count_30 = 1

        # Add the randomly selected drops to the master set
        to_drop_10.update(random.sample(step_indices, count_10))
        to_drop_30.update(random.sample(step_indices, count_30))

    # -----------------------------------------
    # GENERATE TYPE 3 & 4 (DEGRADATION)
    # -----------------------------------------
    with open(os.path.join(t3_dir, filename), 'w', encoding='utf-8') as f:
        f.writelines([line for i, line in enumerate(lines) if i not in to_drop_10])
        
    with open(os.path.join(t4_dir, filename), 'w', encoding='utf-8') as f:
        f.writelines([line for i, line in enumerate(lines) if i not in to_drop_30])

    # -----------------------------------------
    # GENERATE TYPE 5 & 6 (COPY FOR MANUAL EDITING)
    # -----------------------------------------
    with open(os.path.join(t5_dir, filename), 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    with open(os.path.join(t6_dir, filename), 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"Processed: {filename} (Approaches Found: {len(approaches)} | Total Steps Dropped - 10%: {len(to_drop_10)}, 30%: {len(to_drop_30)})")

print("\nSuccess! Phase 2 is completely finished. QA generated, and approaches degraded independently.")