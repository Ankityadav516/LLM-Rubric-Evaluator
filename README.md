# LLM Rubric Quality Evaluator

**Course:** Undergraduate Project (CS496) | Indian Institute of Technology Kanpur  
**Professor:** Prof. Subhajit Roy  

## Project Overview
High-quality, step-by-step rubrics improve an LLM's grading accuracy. This project explores the reverse question: **Can LLMs be used to evaluate the quality of the grading rubric itself?** By systematically injecting deficiencies (abstractness, incompleteness, and logical incorrectness) into a gold-standard Question-Specific (QS) rubric, this pipeline measures the resulting deviation in AI grading accuracy compared to a human baseline. The magnitude of this deviation acts as a detection signal for rubric flaws.

## Dataset
* Sourced from the ACM research dataset (*Rubric is ALL You Need*).
* Evaluated **25 DSA problems** (Java).
* Assessed multiple submission types per problem (Correct, Compilation Error, TLE, Logically Incorrect).
* **Total Evaluations Generated:** 1,050 JSON logs.

## Repository Structure
* `/Code/` - Core execution engine (`master_pipeline.py`) and data cleaning scripts.
* `/Data/` - The raw DSA problems and student Java submissions.
* `/Rubrics/` - The 7 systematic rubric variations tested (QS Baseline, Abstract, Incomplete, Incorrect).
* `/Logs/` - 1,050 raw JSON outputs from the LLM.
* `/LLM_Detailed_Responses/` - Verbose Chain-of-Thought logs used for qualitative analysis.
* `/Output/` - The final aggregated CSV results and visualization plots.
* `setup_folders.py`, `step2_extract.py`, etc. - Data preprocessing pipeline.

## Architecture & Execution
The evaluation engine is powered by **Claude-Sonnet-4-6** via AWS Bedrock. To ensure deterministic, repeatable logic, the model `temperature` is strictly set to `0`. 

### Dependencies
Create a `.env` file in the root directory containing your AWS token: `AWS_BEARER_TOKEN_BEDROCK=your_token_here`.
```bash
pip install pandas matplotlib seaborn boto3 python-dotenv