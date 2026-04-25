import pandas as pd
import os
import re

# 1. Load the CSV
csv_file = 'extracted_data.csv'

if not os.path.exists(csv_file):
    print(f"Error: {csv_file} not found! Please move it into this folder.")
    exit()

print("Loading data from CSV...")
df = pd.read_csv(csv_file)

# Columns containing the student submissions
submission_cols = ['correct_1', 'correct_2', 'correct_3', 'TLE', 'wrong', 'compilation_error']

for index, row in df.iterrows():
    # Get problem number and sanitize the name (replace spaces with underscores)
    prob_num = str(row['number']).zfill(2) # Turns 1 into 01
    raw_name = str(row['name'])
    clean_name = re.sub(r'[^A-Za-z0-9]+', '_', raw_name).strip('_')
    
    folder_name = f"P{prob_num}_{clean_name}"
    prob_dir = os.path.join("Data", "Problems", folder_name)
    sub_dir = os.path.join(prob_dir, "submissions")
    
    # Create the directories
    os.makedirs(sub_dir, exist_ok=True)
    
    # 2. Write problem.txt and solution.txt
    with open(os.path.join(prob_dir, "problem.txt"), "w", encoding="utf-8") as f:
        f.write(str(row['question']))
        
    with open(os.path.join(prob_dir, "solution.txt"), "w", encoding="utf-8") as f:
        f.write(str(row['solution']))
        
    # 3. Write the 6 submissions
    # Note: Saving as .java because the javac compiler check requires .java files!
    for col in submission_cols:
        if pd.notna(row[col]):
            code_content = str(row[col])
            with open(os.path.join(sub_dir, f"{col}.java"), "w", encoding="utf-8") as f:
                f.write(code_content)
                
    # 4. Write the Original Rubric to Type_1 folder
    rubric_path = os.path.join("Rubrics", "Type_1_Original", f"P{prob_num}_rubric.txt")
    with open(rubric_path, "w", encoding="utf-8") as f:
        f.write(str(row['rubric']))
        
    print(f"Extracted: {folder_name} (Problem, Solution, Submissions, Rubric)")

print("\nSuccess! All 25 problems and rubrics have been extracted and organized.")