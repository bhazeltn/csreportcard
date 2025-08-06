import pandas as pd
import os
import openpyxl
import re
import json
from app import app, db
from app.models import Session, Skater

def normalize_name(name):
    """Converts a name to a simple, standardized format for reliable matching."""
    if not isinstance(name, str): return ""
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    return name

def identify_report_type(file_path):
    """
    Identifies the report type by inspecting the content of the first worksheet.
    This check is case-insensitive and more robust.
    """
    try:
        df = pd.read_excel(file_path, header=None, sheet_name=0, nrows=5)

        # Check for Achievements Report (case-insensitive)
        first_row_values = [str(v).strip().lower() for v in df.iloc[0].values]
        if 'first name' in first_row_values and 'last name' in first_row_values:
            app.logger.info(f"Identified {os.path.basename(file_path)} as Achievements report.")
            return 'Achievements'

        # Check for Evaluations Report (case-insensitive)
        if any(isinstance(cell, str) and 'coaches:' in cell.lower() for cell in df.iloc[1].values):
            app.logger.info(f"Identified {os.path.basename(file_path)} as Evaluations report.")
            return 'Evaluations'

        app.logger.warning(f"Could not identify report type for {file_path}.")
        return 'Unknown'
    except Exception as e:
        app.logger.error(f"Could not read or identify report type for {file_path}: {e}")
        return 'Unknown'

def get_session_name_from_evaluations(file_path):
    """Extracts the session name from the Evaluations report."""
    try:
        df = pd.read_excel(file_path, header=None, sheet_name=0)
        return df.iloc[0, 0].strip()
    except Exception: return None

def are_sessions_compatible(form_name, eval_name):
    """Performs a flexible comparison of session names."""
    if not form_name or not eval_name: return False
    form_processed = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', form_name)
    eval_processed = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', eval_name)
    norm_form = set(re.findall(r'\w+', form_processed.lower()))
    norm_eval = set(re.findall(r'\w+', eval_processed.lower()))
    if 'cs' in norm_form:
        norm_form.discard('cs')
        norm_form.add('canskate')
    intersection = norm_form.intersection(norm_eval)
    match_score = (len(intersection) / len(norm_form)) if len(norm_form) > 0 else 0
    return match_score > 0.5

def load_and_clean_achievements(file_path):
    """Loads, cleans, and normalizes the achievements data."""
    df = pd.read_excel(file_path)
    df['Skater Name'] = df['First Name'] + ' ' + df['Last Name']
    df['Normalized Name'] = df['Skater Name'].apply(normalize_name)
    df = df.drop(columns=['First Name', 'Last Name'])
    for col in df.columns:
        if col not in ['Skater Name', 'Normalized Name']:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def get_skater_list_from_evaluations(file_path):
    """Loads just the skater names from the evaluations report for validation."""
    xls = pd.ExcelFile(file_path)
    all_skaters = set()
    for sheet_name in xls.sheet_names:
        if any(keyword in sheet_name.lower() for keyword in ['canskate', 'pre-canskate']):
            skater_col = pd.read_excel(xls, sheet_name=sheet_name, header=None, usecols=[0], skiprows=2).squeeze("columns")
            cleaned_skaters = skater_col.dropna().astype(str)
            all_skaters.update(cleaned_skaters)
    all_skaters = {name for name in all_skaters if not name.startswith('*')}
    eval_df = pd.DataFrame(list(all_skaters), columns=['Skater Name'])
    eval_df['Normalized Name'] = eval_df['Skater Name'].apply(normalize_name)
    return eval_df

def load_full_evaluations_data(file_path):
    """Loads and cleans the FULL multi-sheet evaluations data, returning a complete DataFrame."""
    xls = pd.ExcelFile(file_path)
    skater_data = {}
    group_pattern = re.compile(r'--\s*(.*)')

    for sheet_name in xls.sheet_names:
        if any(keyword in sheet_name.lower() for keyword in ['canskate', 'pre-canskate']):
            match = group_pattern.search(sheet_name)
            group_name = match.group(1).strip() if match else 'Unknown Group'
            
            sheet_df = pd.read_excel(xls, sheet_name=sheet_name, header=[0, 1], skiprows=1, index_col=0)
            sheet_df.index.name = 'Skater Name'
            sheet_df.columns.names = ['Category', 'Skill']
            
            clean_cols = [(str(cat).replace('\n', ' ').strip(), str(skill).replace('\n', ' ').strip()) for cat, skill in sheet_df.columns]
            sheet_df.columns = pd.MultiIndex.from_tuples(clean_cols)
            
            sheet_df.columns = sheet_df.columns.to_frame().ffill()[0].to_list()
            sheet_df.columns = [f"{col[0]} - {col[1]}" for col in sheet_df.columns]

            for skater_name, row in sheet_df.iterrows():
                if skater_name.startswith('*'): continue
                
                normalized_skater_name = normalize_name(skater_name)
                if normalized_skater_name not in skater_data:
                    skater_data[normalized_skater_name] = {'Skater Name': skater_name, 'Group Name': group_name}

                for skill_name, value in row.items():
                    if isinstance(value, str) and '✓' in value:
                        skater_data[normalized_skater_name][skill_name] = True

    final_df = pd.DataFrame.from_dict(skater_data, orient='index')
    final_df.index.name = 'Normalized Name'
    return final_df.fillna(False)

def validate_and_load_data(session_path, form_session_name):
    """Validates uploaded files and returns data for the confirmation page."""
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
        evaluations_df = get_skater_list_from_evaluations(evaluations_path)

        latest_date = achievements_df.select_dtypes(include=['datetime64']).max().max()
        latest_achievement_date = latest_date.strftime('%Y-%m-%d') if pd.notna(latest_date) else 'N/A'

        ach_skaters_normalized = set(achievements_df['Normalized Name'])
        eval_skaters_normalized = set(evaluations_df['Normalized Name'])
        
        common_skaters = ach_skaters_normalized.intersection(eval_skaters_normalized)
        
        denominator = max(len(ach_skaters_normalized), len(eval_skaters_normalized))
        match_percentage = len(common_skaters) / denominator * 100 if denominator > 0 else 0

        if match_percentage < 80:
             msg = f"Low skater match between files ({match_percentage:.0f}%). Please check if they are for the same session."
             return {'success': False, 'message': msg}
        
        return {
            'success': True, 'form_session_name': form_session_name, 'eval_session_name': eval_session_name,
            'skater_count': len(evaluations_df), 'latest_achievement_date': latest_achievement_date,
            'skater_match_percentage': f"{match_percentage:.0f}%", 'session_path': session_path
        }
    except Exception as e:
        app.logger.error(f"Error during data processing: {e}")
        return {'success': False, 'message': 'An error occurred while processing the Excel files.'}

def process_and_save_to_db(session_path, session_name, club_name, report_date, replace=False):
    """Processes the validated files and saves the session and skater data to the database."""
    app.logger.info(f"Final processing and DB import for session: {session_name}")
    
    existing_session = Session.query.filter_by(name=session_name).first()
    if existing_session:
        if replace:
            app.logger.warning(f"Session '{session_name}' exists. Deleting old data.")
            db.session.delete(existing_session)
            db.session.commit()
        else:
            app.logger.error(f"Session '{session_name}' already exists.")
            return False

    upload1_path = os.path.join(session_path, 'upload1.xlsx')
    upload2_path = os.path.join(session_path, 'upload2.xlsx')
    
    achievements_path = upload1_path if identify_report_type(upload1_path) == 'Achievements' else upload2_path
    evaluations_path = upload2_path if identify_report_type(upload1_path) == 'Achievements' else upload1_path

    try:
        evals_full_df = load_full_evaluations_data(evaluations_path) 
        achievements_df = load_and_clean_achievements(achievements_path)

        merged_df = pd.merge(evals_full_df.reset_index(), achievements_df.drop(columns=['Skater Name']), on='Normalized Name', how='left')

        new_session = Session(name=session_name, club_name=club_name, report_date=report_date)
        db.session.add(new_session)
        db.session.commit()

        for index, row in merged_df.iterrows():
            skater_data_dict = row.to_dict()
            
            for key, value in skater_data_dict.items():
                if isinstance(value, pd.Timestamp):
                    skater_data_dict[key] = value.strftime('%Y-%m-%d')
                elif pd.isna(value):
                    skater_data_dict[key] = None
                elif value is True:
                    skater_data_dict[key] = '✓'
            
            skater_data_json = json.dumps(skater_data_dict)

            skater = Skater(
                name=skater_data_dict.get('Skater Name', index), # Use original name
                group_name=skater_data_dict.get('Group Name'),
                session_id=new_session.id,
                skater_data=skater_data_json
            )
            db.session.add(skater)

        db.session.commit()
        app.logger.info(f"Successfully saved {len(merged_df)} skaters for session '{session_name}' to the database.")
        return True

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error during database import: {e}")
        return False
