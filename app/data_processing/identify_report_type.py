import os
import openpyxl

def identify_report_type(file_path):
    """Identify the type of report based on worksheet names.

    Args:
        file_path (str): The path to the Excel file.

    Returns:
        str: The identified report type ('Achievements Report', 'Evaluation Printouts', or 'Unknown Report Type').
    """ 
    try:
        workbook = openpyxl.load_workbook(file_path)
        worksheet_names = workbook.sheetnames

        # Check for Achievements Report
        for sheet_name in worksheet_names:
            if 'Skaters - Completed Achievem...' in sheet_name:
                return 'Achievements Report'

        # Check for Evaluation Printouts
        for tab_name in ['CanSkate - Agility', 'CanSkate - Balance', 'CanSkate - Control', 'Pre-CanSkate']:
            if tab_name in worksheet_names:
                return 'Evaluation Printouts'

        # If neither type is found, classify as unknown
        return 'Unknown Report Type'
    except Exception as e:
        print(f"Error identifying report type for {file_path}: {e}")
        return 'Unknown Report Type'

def process_files_in_directory(directory_path):
    """Process all Excel files in the given directory.

    Args:
        directory_path (str): The path to the directory containing the Excel files.

    Returns:
        None
    """
    for filename in os.listdir(directory_path):
        if filename.endswith('.xlsx'):  # Process only Excel files
            file_path = os.path.join(directory_path, filename)
            report_type = identify_report_type(file_path)
            print(f"{filename}: {report_type}")