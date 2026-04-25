import os
import csv
import argparse

def clean_csv(file_path, start_row, end_row):
    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path}. Are you in the right folder?")
        return

    # Read all the current data
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))

    total_original = len(rows)
    
    # We use 1-based indexing so it perfectly matches what you see in Excel!
    cleaned_rows = [row for idx, row in enumerate(rows, start=1) 
                    if not (start_row <= idx <= end_row)]

    # Write the surviving rows back to the file
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(cleaned_rows)

    print(f"\nSuccess! Deleted rows {start_row} through {end_row}.")
    print(f"Original row count: {total_original}")
    print(f"New row count: {len(cleaned_rows)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Surgically delete rows from your results CSV.")
    parser.add_argument("--start", type=int, required=True, help="First Excel row to delete (e.g., 2)")
    parser.add_argument("--end", type=int, required=True, help="Last Excel row to delete (e.g., 901)")
    
    args = parser.parse_args()
    
    # Automatically point to your output file
    csv_path = os.path.join("Output", "final_results.csv")
    clean_csv(csv_path, args.start, args.end)