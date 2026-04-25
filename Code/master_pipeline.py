import os
import re
import csv
import json
import argparse
import subprocess
import pandas as pd
import boto3
import time 
from dotenv import load_dotenv # <-- NEW IMPORT

# --- LOAD SECURE API KEY ---
load_dotenv() # This looks for the .env file and loads your secrets
aws_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")

if not aws_token:
    raise ValueError("CRITICAL SECURITY ERROR: AWS_BEARER_TOKEN_BEDROCK is missing from the .env file!")

os.environ["AWS_BEARER_TOKEN_BEDROCK"] = aws_token
# ---------------------------

# ---------------------------------------------------------
# 1. RUBRIC PARSER
# ---------------------------------------------------------
def parse_rubric_stats(rubric_text):
    approaches = {}
    current_approach = "Global"
    approaches[current_approach] = {"max_marks": 0, "steps": 0}

    for line in rubric_text.split('\n'):
        match = re.search(r'(Solution|Approach)\s*\d+', line, re.IGNORECASE)
        if match:
            current_approach = match.group(0).strip()
            approaches[current_approach] = {"max_marks": 0, "steps": 0}
        
        mark_match = re.search(r'\[(\d+)\s*marks?\]', line, re.IGNORECASE)
        if mark_match:
            approaches[current_approach]["max_marks"] += int(mark_match.group(1))
            approaches[current_approach]["steps"] += 1

    return approaches

def fuzzy_match_approach(ai_approach, parsed_approaches):
    for key in parsed_approaches.keys():
        if key.lower() in ai_approach.lower(): return key
    return "Global"

# ---------------------------------------------------------
# 2. SYNTAX CHECKER
# ---------------------------------------------------------
def check_syntax(code_filepath: str):
    try:
        abs_path = os.path.abspath(code_filepath)
        result = subprocess.run(
            ["javac", abs_path], 
            capture_output=True, 
            text=True, 
            timeout=10 
        )
        return result.stderr.strip() if result.stderr else "Compilation Successful."
    except subprocess.TimeoutExpired:
        return "Compiler Error: Process Timed Out."
    except Exception as e:
        return f"Compiler Error: {str(e)}"

# ---------------------------------------------------------
# 3. HUMAN SCORE MATCHER
# ---------------------------------------------------------
def get_human_score(human_df, prob_name, sub_file):
    if human_df is None: return "N/A", "N/A"
    
    clean_prob_folder = prob_name.replace('_', ' ').strip().lower()

    if "palindrome linked list" in clean_prob_folder:
        clean_prob_folder = "palindrom linked list"
    
    clean_sub = sub_file.replace('.java', '').strip().lower()
    if "compilation" in clean_sub: clean_sub = "compilation_error"
    if "tle" in clean_sub: clean_sub = "tle"

    human_df['CleanProb'] = human_df['Problem'].str.strip().str.lower()
    human_df['CleanSub'] = human_df['Submission'].str.strip().str.lower()

    match = human_df[(human_df['CleanProb'] == clean_prob_folder) & 
                     (human_df['CleanSub'] == clean_sub)]
    
    if match.empty:
        match = human_df[human_df['CleanProb'].str.contains(clean_prob_folder[:15]) & 
                         (human_df['CleanSub'] == clean_sub)]

    if match.empty: return "N/A", "N/A"
    
    raw_score_str = str(match.iloc[0]['Total Marks'])
    if pd.isna(raw_score_str) or '/' not in raw_score_str: return raw_score_str, "N/A"

    try:
        parts = raw_score_str.split('/')
        human_raw = float(parts[0])
        human_max = float(parts[1])
        human_norm = min((human_raw / human_max) * 10, 10.0) if human_max > 0 else 0
        return raw_score_str, round(human_norm, 2)
    except:
        return raw_score_str, "N/A"

# ---------------------------------------------------------
# 4. THE MASTER EVALUATOR ENGINE 
# ---------------------------------------------------------
class MasterEvaluator:
    def __init__(self, mock_mode=False):
        self.mock_mode = mock_mode
        self.logs_dir = "Logs"
        os.makedirs(self.logs_dir, exist_ok=True)

        if not mock_mode:
            self.client = boto3.client("bedrock-runtime", region_name="us-east-1")
            self.model_id = "arn:aws:bedrock:us-east-1:390847198516:inference-profile/global.anthropic.claude-sonnet-4-6"
            
        self.prompt_strict = '''You are a strict, expert university professor grading a Data Structures and Algorithms submission.
Your job is to evaluate the logical correctness of the student's code based EXACTLY on the provided rubric.

CRITICAL INSTRUCTIONS:
1. Read the code carefully. Does the code ACTUALLY implement the approach?
2. Identify which "Solution" from the rubric the student attempted.
3. Grade each step of that specific solution. 
4. IF THE CODE DOES NOT MATCH THE STEP, GIVE A 0. Be extremely strict.
5. Ignore syntax errors, but penalize logic errors.

CRITICAL: Do not write any analysis, thoughts, or markdown. 
Start your response with {{ and end it with }}. Any text outside the JSON block will break the system.

Return ONLY a valid JSON object in this EXACT format:
{{
    "chosen_approach": "Solution 1",
    "marks": {{
        "Step 1 text...": 0,
        "Step 2 text...": 1
    }}
}}

Question: {question}
Rubric: {rubric}
Code Submission: {code}
Compiler Response: {compiler}
'''

        # NEW PROMPT FOR PRESENTATION RESPONSES
        self.prompt_verbose = '''You are a strict, expert university professor grading a Data Structures and Algorithms submission.
Your job is to evaluate the logical correctness of the student's code based EXACTLY on the provided rubric.

1. Write a detailed, step-by-step analysis explaining EXACTLY how you are grading this code against the rubric. Point out specific logic errors or correct implementations.
2. After your analysis, you MUST provide the final grading in a valid JSON object.

Return your final JSON object at the very bottom in this EXACT format:
{{
    "chosen_approach": "Solution 1",
    "marks": {{
        "Step 1 text...": 0,
        "Step 2 text...": 1
    }}
}}

Question: {question}
Rubric: {rubric}
Code Submission: {code}
Compiler Response: {compiler}
'''

    def extract_json(self, text):
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
                return json.loads(json_str)
            return json.loads(text)
        except Exception as e:
            print(f"!!! JSON Parse Fail. Raw text start: {text[:50]}...")
            raise ValueError(f"Could not parse JSON")

    def evaluate(self, prob_id, rubric_type, sub_file, question, rubric_text, code_filepath, force_run=False, save_responses=False):
        log_file = os.path.join(self.logs_dir, f"{prob_id}_{rubric_type}_{sub_file.replace('.java', '')}.json")

        if not force_run and os.path.exists(log_file):
            print(f"   -> Found cached log for {sub_file}. Skipping API...")
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)["llm_response"]

        if self.mock_mode:
            return {"chosen_approach": "Solution 1 (Mock)", "marks": {"mock step 1": 2}}

        compiler_response = check_syntax(code_filepath)
        with open(code_filepath, "r", encoding="utf-8") as f:
            code = f.read()

        # Select the correct prompt based on the user's terminal flag
        active_prompt = self.prompt_verbose if save_responses else self.prompt_strict
        prompt = active_prompt.format(question=question, rubric=rubric_text, code=code, compiler=compiler_response)
        
        try:
            print(f"   -> Pinging AWS Bedrock for {sub_file}...")
            native_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                "max_tokens": 4096,
                "temperature": 0
            }
            
            response = self.client.invoke_model(modelId=self.model_id, body=json.dumps(native_request))
            model_response = json.loads(response["body"].read())
            response_text = model_response["content"][0]["text"]
            
            # --- NEW: SAVE RAW RESPONSE IF FLAG IS ACTIVE ---
            if save_responses:
                raw_dir = "LLM_Detailed_Responses"
                os.makedirs(raw_dir, exist_ok=True)
                raw_file = os.path.join(raw_dir, f"{prob_id}_{rubric_type}_{sub_file.replace('.java', '')}.txt")
                with open(raw_file, 'w', encoding='utf-8') as rf:
                    rf.write(f"Problem: {prob_id}\nRubric: {rubric_type}\nSubmission: {sub_file}\n")
                    rf.write("=========================================\n")
                    rf.write("            LLM FULL RESPONSE            \n")
                    rf.write("=========================================\n\n")
                    rf.write(response_text)
            # -------------------------------------------------

            response_json = self.extract_json(response_text)
            
            log_data = {
                "prompt_readable": prompt.split('\n'), 
                "llm_response": response_json
            }

            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=4)

            return response_json

        except Exception as e:
            print(f"LLM Error on {code_filepath}: {e}")
            return None

# ---------------------------------------------------------
# 5. PIPELINE CONTROLLER
# ---------------------------------------------------------
def run_pipeline(args):
    output_file = os.path.join("Output", "final_results.csv")
    os.makedirs("Output", exist_ok=True)
    
    human_df = None
    if os.path.exists("combined_human_scores.csv"):
        human_df = pd.read_csv("combined_human_scores.csv")

    evaluator = MasterEvaluator(mock_mode=args.mock)
    
    problems_dir = os.path.join("Data", "Problems")
    problems_list = sorted(os.listdir(problems_dir))

    for problem_folder in problems_list:
        parts = problem_folder.split('_', 1)
        prob_id = parts[0]
        prob_name = parts[1] if len(parts) > 1 else "Unknown"

        if args.problem and args.problem != prob_id: continue
        if args.start_prob and prob_id < args.start_prob: continue
        if args.end_prob and prob_id > args.end_prob: continue

        print(f"\n--- Evaluating Problem: {prob_id} - {prob_name} ---")
        prob_path = os.path.join(problems_dir, problem_folder)
        with open(os.path.join(prob_path, "problem.txt"), 'r', encoding='utf-8') as f:
            question_text = f.read()

        submissions_path = os.path.join(prob_path, "submissions")
        
        for sub_file in os.listdir(submissions_path):
            if not sub_file.endswith(".java"): continue
            if args.student and sub_file != args.student: continue
            
            all_results = []
            
            for rubric_type in sorted(os.listdir("Rubrics")):
                if args.rubric and args.rubric not in rubric_type: continue
                
                rubric_file = os.path.join("Rubrics", rubric_type, f"{prob_id}_rubric.txt")
                if not os.path.exists(rubric_file): continue
                
                with open(rubric_file, 'r', encoding='utf-8') as f:
                    rubric_text = f.read()
                rubric_stats = parse_rubric_stats(rubric_text)

                ai_result = evaluator.evaluate(
                    prob_id, rubric_type, sub_file, question_text, rubric_text, 
                    os.path.join(submissions_path, sub_file), args.force, args.save_responses
                )
                
                if ai_result is None:
                    print(f"Warning: AWS Bedrock returned None for {sub_file}. Assigning 0 marks.")
                    total_marks = 0
                    approach_name = "Unknown"
                else:
                    total_marks = sum(ai_result.get("marks", {}).values())
                    approach_name = ai_result.get("chosen_approach", "Unknown")
                
                matched_key = fuzzy_match_approach(approach_name, rubric_stats)
                stats = rubric_stats.get(matched_key, {"max_marks": 10, "steps": 0})
                max_marks = stats["max_marks"]

                ai_norm = min((total_marks / max_marks) * 10, 10.0) if max_marks > 0 else 0
                human_raw, human_norm = get_human_score(human_df, prob_name, sub_file)
                all_results.append({
                    "Problem ID": prob_id,
                    "Problem Name": prob_name,
                    "Submission ID": sub_file,
                    "Rubric ID": rubric_type,
                    "Sub Rubric ID (Approach)": approach_name,
                    "AI Total Marks": total_marks,
                    "AI Max Marks": max_marks,
                    "AI Normalized (Out of 10)": round(ai_norm, 2),
                    "Human Raw Score": human_raw,
                    "Human Normalized (Out of 10)": human_norm,
                    "Total Rubric Steps": stats["steps"]
                })

            if all_results:
                new_df = pd.DataFrame(all_results)
                if os.path.exists(output_file):
                    old_df = pd.read_csv(output_file)
                    final_df = pd.concat([old_df, new_df]).drop_duplicates(
                        subset=['Problem ID', 'Submission ID', 'Rubric ID'], keep='last'
                    )
                    final_df.to_csv(output_file, index=False)
                else:
                    new_df.to_csv(output_file, index=False)

            if not args.mock:
                print(f"--- Finished student {sub_file}. Taking a 1s breather for AWS... ---")
                time.sleep(1)

    print(f"\nPipeline complete! All results are safe in {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master ML Grading Pipeline")
    parser.add_argument("--run_all", action="store_true", help="Run the entire dataset")
    parser.add_argument("--mock", action="store_true", help="Run without API key for testing")
    parser.add_argument("--force", action="store_true", help="Ignore logs and force a new API call")
    parser.add_argument("--problem", type=str, help="Specific problem ID (e.g., P01)")
    parser.add_argument("--start_prob", type=str, help="Range start (e.g., P03)")
    parser.add_argument("--end_prob", type=str, help="Range end (e.g., P06)")
    parser.add_argument("--rubric", type=str, help="Filter by rubric type")
    parser.add_argument("--student", type=str, help="Filter by student file")
    
    # NEW ARGUMENT FOR DETAILED RESPONSES
    parser.add_argument("--save_responses", action="store_true", help="Allow AI to explain its logic and save the full text")
    
    args = parser.parse_args()
    
    if not any([args.run_all, args.problem, args.start_prob]):
        print("Please specify a run criterion. Example: python Code/master_pipeline.py --mock --run_all")
    else:
        run_pipeline(args)