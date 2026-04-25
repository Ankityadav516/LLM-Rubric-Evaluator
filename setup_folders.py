import os

# The exact folder structure for our research pipeline
folders = [
    "Data/Problems",
    "Rubrics/Type_1_Original",
    "Rubrics/Type_2_Agnostic",
    "Rubrics/Type_3_Degraded_10",
    "Rubrics/Type_4_Degraded_30",
    "Rubrics/Type_5_Error_10",
    "Rubrics/Type_6_Error_30",
    "Code",
    "Output"
]

print("Building Master Workspace...")

for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f" -> Created: {folder}")

print("\nSuccess! Workspace is ready for data.")