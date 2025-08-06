import pandas as pd
import os
import openpyxl
import re
from app import app

def normalize_name(name):
    """Converts a name to a simple, standardized format for reliable matching."""
    if not isinstance(name, str):
        return ""
    # Lowercase, remove extra whitespace, and non-alphanumeric chars except hyphens
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name) # Collapse multiple spaces
    name = re.sub(r'[^a-z0-9\s-]', '', name) # Keep only letters, numbers, spaces, hyphens
    return name

def identify_report_type(file_path):
    """
    Identifies the report type by checking for specific worksheet names.
    Returns 'Achievements', 'Evaluations', or 'Unknown'.
    """
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet_names = workbook.sheetnames

        # Check for Achievements Report (case-insensitive)
        if any('skaters - completed achievem' in s.lower() for s in sheet_names):
            return 'Achievements'

        # Check for Evaluation Printouts (case-insensitive)
        eval_keywords = ['canskate - agility', 'canskate - balance', 'canskate - control', 'pre-canskate']
        for s_name in sheet_names:
            if any(keyword in s_name.lower() for keyword in eval_keywords):
                return 'Evaluations'
            
        return 'Unknown'
    except Exception as e:
        app.logger.error(f"Could not identify report type for {file_path}: {e}")
        return 'Unknown'

def get_session_name_from_evaluations(file_path):
    """
    Extracts the session name from the first cell of the first worksheet
    in the Evaluations report.
    """
    try:
        df = pd.read_excel(file_path, header=None, sheet_name=0)
        session_name = df.iloc[0, 0].strip()
        return session_name
    except Exception as e:
        app.logger.error(f"Could not extract session name from {file_path}: {e}")
        return None

def are_sessions_compatible(form_name, eval_name):
    """
    Performs a flexible comparison to see if the session names are a likely match.
    """
    if not form_name or not eval_name:
        return False

    # Pre-process strings to separate letters from numbers (e.g., "cs2a" -> "cs 2a")
    form_name_processed = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', form_name)
    eval_name_processed = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', eval_name)

    # Normalize both strings: lowercase, keep only letters and numbers
    norm_form = set(re.findall(r'\w+', form_name_processed.lower()))
    norm_eval = set(re.findall(r'\w+', eval_name_processed.lower()))

    # Treat 'cs' and 'canskate' as the same
    if 'cs' in norm_form:
        norm_form.discard('cs')
        norm_form.add('canskate')

    intersection = norm_form.intersection(norm_eval)
    
    # Lower the threshold to 50% for a more flexible match
    match_percentage = (len(intersection) / len(norm_form)) if len(norm_form) > 0 else 0
    app.logger.info(f"Session name match score: {match_percentage:.2f}")
    
    return match_percentage > 0.5

def load_and_clean_achievements(file_path):
    """Loads, cleans, and normalizes the achievements data."""
    df = pd.read_excel(file_path)
    # Combine first and last name into a single 'Skater Name' column
    df['Skater Name'] = df['First Name'] + ' ' + df['Last Name']
    # Apply normalization to the new 'Skater Name' column
    df['Normalized Name'] = df['Skater Name'].apply(normalize_name)
    df = df.drop(columns=['First Name', 'Last Name'])
    
    # Convert all possible date columns to datetime, coercing errors
    for col in df.columns:
        if col not in ['Skater Name', 'Normalized Name']:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def load_and_clean_evaluations(file_path):
    """Loads, cleans, and normalizes the multi-sheet evaluations data."""
    xls = pd.ExcelFile(file_path)
    all_skaters = set()

    for sheet_name in xls.sheet_names:
        if any(keyword in sheet_name.lower() for keyword in ['canskate', 'pre-canskate']):
            # Read just the first column to get skater names
            skater_col = pd.read_excel(xls, sheet_name=sheet_name, header=None, usecols=[0], skiprows=2).squeeze("columns")
            # Clean up names and add to our set
            cleaned_skaters = skater_col.dropna().astype(str)
            all_skaters.update(cleaned_skaters)
            
    # Filter out footer text that might be read as a name
    all_skaters = {name for name in all_skaters if not name.startswith('*')}
    
    # Create a DataFrame for easy normalization
    eval_df = pd.DataFrame(list(all_skaters), columns=['Skater Name'])
    eval_df['Normalized Name'] = eval_df['Skater Name'].apply(normalize_name)
    return eval_df

def validate_and_load_data(session_path, form_session_name):
    """
    Main function to validate and process the uploaded reports.
    Returns a dictionary with validation results and data.
    """
    app.logger.info(f"Starting validation for session: {form_session_name}")
    
    file1_path = os.path.join(session_path, 'upload1.xlsx')
    file2_path = os.path.join(session_path, 'upload2.xlsx')

    file1_type = identify_report_type(file1_path)
    file2_type = identify_report_type(file2_path)

    if {file1_type, file2_type} != {'Achievements', 'Evaluations'}:
        return {'success': False, 'message': "Upload failed. Please ensure you upload one Achievements and one Evaluations report."}

    achievements_path = file1_path if file1_type == 'Achievements' else file2_path
    evaluations_path = file2_path if file1_type == 'Achievements' else file1_path
    
    eval_session_name = get_session_name_from_evaluations(evaluations_path)
    
    if not are_sessions_compatible(form_session_name, eval_session_name):
        msg = f"Session name mismatch. Form said '{form_session_name}', but file seems to be for '{eval_session_name}'."
        return {'success': False, 'message': msg}

    try:
        achievements_df = load_and_clean_achievements(achievements_path)
        evaluations_df = load_and_clean_evaluations(evaluations_path)

        # 1. Get latest achievement date
        latest_date = achievements_df.select_dtypes(include=['datetime64']).max().max()
        latest_achievement_date = latest_date.strftime('%Y-%m-%d') if pd.notna(latest_date) else 'N/A'

        # 2. Check for skater match using normalized names
        ach_skaters_normalized = set(achievements_df['Normalized Name'])
        eval_skaters_normalized = set(evaluations_df['Normalized Name'])
        
        common_skaters = ach_skaters_normalized.intersection(eval_skaters_normalized)
        
        denominator = max(len(ach_skaters_normalized), len(eval_skaters_normalized))
        match_percentage = len(common_skaters) / denominator * 100 if denominator > 0 else 0

        app.logger.info(f"Skater match: {match_percentage:.2f}%")
        if match_percentage < 80:
             msg = f"Low skater match between files ({match_percentage:.0f}%). Please check if they are for the same session."
             return {'success': False, 'message': msg}
        
        return {
            'success': True,
            'form_session_name': form_session_name,
            'eval_session_name': eval_session_name,
            'skater_count': len(evaluations_df),
            'latest_achievement_date': latest_achievement_date,
            'skater_match_percentage': f"{match_percentage:.0f}%",
            'session_path': session_path
        }

    except Exception as e:
        app.logger.error(f"Error during data processing: {e}")
        return {'success': False, 'message': 'An error occurred while processing the Excel files.'}
