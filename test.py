import pandas as pd

def preview_worksheet(file_path, sheet_name):
    """Load and preview the first few rows of a specific worksheet."""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        return df.head()
    except Exception as e:
        print(f"Error loading worksheet: {e}")
        return None

# Specify the file path and worksheet name
file_path = '/home/bradley/development/csreportcard/data/uploads/EvaluationPrintouts-Wednesday4_45-5_30pmCanSkate(Stage1-6)JantoApr2024-2024-04-13 (1).xlsx'
sheet_name = 'Pre-CanSkate'

# Try loading and previewing the Pre-CanSkate worksheet again
preview_df = preview_worksheet(file_path, sheet_name)
print(preview_df)

