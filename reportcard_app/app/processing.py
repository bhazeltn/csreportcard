import pandas as pd
import numpy as np
import os
import openpyxl
import re
import json
from app import app, db
from app.models import Session, Skater

# --- Helper Functions ---

def normalize_name(name):
    """Converts a name to a simple, standardized format for reliable matching."""
    if not isinstance(name, str): return ""
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    return name

def load_mapping_df(filename):
    """Loads a mapping CSV from the data/mapping directory."""
    path = os.path.join(app.root_path, '..', 'data', 'mapping', filename)
    return pd.read_csv(path)

def transform_ribbon_name(ribbon):
    """Standardizes ribbon names to match the mapping files (e.g., 'CanSkate 1 - Agility' -> 'Agility 1')."""
    if not isinstance(ribbon, str): return ""
    ribbon = ribbon.replace("Pre-CanSkate", "PreCanSkate")
    match = re.match(r"CanSkate (\d+) - (.*)", ribbon.strip())
    if match:
        # Swaps 'CanSkate X - Y' to 'Y X'
        return f"{match.group(2).strip()} {match.group(1).strip()}"
    return ribbon.strip()

# --- Report Identification and Initial Loading ---

def identify_report_type(file_path):
    """Identifies the report type by inspecting the content of the first worksheet."""
    try:
        df = pd.read_excel(file_path, header=None, sheet_name=0, nrows=5)
        first_row_values = [str(v).strip().lower() for v in df.iloc[0].values]
        if 'first name' in first_row_values and 'last name' in first_row_values:
            app.logger.info(f"Identified {os.path.basename(file_path)} as Achievements report.")
            return 'Achievements'
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

# --- Data Validation and Confirmation Page Logic ---

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
        achievements_df = pd.read_excel(achievements_path)
        achievements_df['Skater Name'] = achievements_df['First Name'] + ' ' + achievements_df['Last Name']
        achievements_df['Normalized Name'] = achievements_df['Skater Name'].apply(normalize_name)
        
        evaluations_df = get_skater_list_from_evaluations(evaluations_path)

        date_cols = achievements_df.drop(columns=['First Name', 'Last Name', 'Skater Name', 'Normalized Name'], errors='ignore')
        latest_date = pd.to_datetime(date_cols.stack(), errors='coerce').max()
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
        app.logger.error(f"Error during data processing: {e}", exc_info=True)
        return {'success': False, 'message': 'An error occurred while processing the Excel files.'}

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

# --- Core Data Processing and Database Saving ---

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
    
    achievements_path = upload1_path if identify_report_type(upload1_path) == 'Achievements' else file2_path
    evaluations_path = upload2_path if identify_report_type(upload1_path) == 'Achievements' else file1_path

    try:
        # 1. Load Achievements Data
        achievements_df = pd.read_excel(achievements_path)
        achievements_df['Skater Name'] = achievements_df['First Name'] + ' ' + achievements_df['Last Name']
        achievements_df['Normalized Name'] = achievements_df['Skater Name'].apply(normalize_name)
        achievements_df = achievements_df.drop(columns=['First Name', 'Last Name', 'Skater Name'])
        
        # 2. Load and Transform Evaluations Data
        evals_df = load_and_transform_evaluations(evaluations_path)

        # 3. Merge Transformed Data
        merged_df = pd.merge(evals_df, achievements_df, on='Normalized Name', how='left')

        # 4. Save to Database
        new_session = Session(name=session_name, club_name=club_name, report_date=report_date)
        db.session.add(new_session)
        db.session.commit()

        for index, row in merged_df.iterrows():
            skater_data_dict = row.to_dict()
            
            final_data = {}
            for key, value in skater_data_dict.items():
                if pd.isna(value) or value is None:
                    continue
                if isinstance(value, (bool, np.bool_)):
                    final_data[key] = bool(value)
                elif isinstance(value, pd.Timestamp):
                    final_data[key] = value.strftime('%Y-%m-%d')
                else:
                    final_data[key] = value

            skater = Skater(
                name=final_data.get('Skater Name'),
                group_name=final_data.get('Group Name'),
                session_id=new_session.id,
                skater_data=json.dumps(final_data)
            )
            db.session.add(skater)

        db.session.commit()
        app.logger.info(f"Successfully saved {len(merged_df)} skaters for session '{session_name}' to the database.")
        return True

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error during database import: {e}", exc_info=True)
        return False

def load_and_transform_evaluations(file_path):
    """Loads, transforms, and consolidates the evaluations data from the Excel file."""
    xls = pd.ExcelFile(file_path)
    all_skater_data = []
    group_pattern = re.compile(r'--\s*(.*)')

    for sheet_name in xls.sheet_names:
        if not any(keyword in sheet_name.lower() for keyword in ['canskate', 'pre-canskate']):
            continue
        
        match = group_pattern.search(sheet_name)
        group_name = match.group(1).strip() if match else 'Unknown Group'
        
        header_df = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=3)
        ribbon_names_raw = header_df.iloc[1, 1:].ffill()
        skill_names = header_df.iloc[2, 1:]
        
        column_names = [f"{transform_ribbon_name(ribbon)} - {str(skill).strip()}" for ribbon, skill in zip(ribbon_names_raw, skill_names)]

        sheet_df = pd.read_excel(xls, sheet_name=sheet_name, header=None, skiprows=3)
        sheet_df.columns = ['Skater Name'] + column_names
        sheet_df = sheet_df.dropna(subset=['Skater Name'])
        sheet_df = sheet_df[~sheet_df['Skater Name'].astype(str).str.startswith('*')]

        sheet_df['Group Name'] = group_name
        sheet_df['Normalized Name'] = sheet_df['Skater Name'].apply(normalize_name)
        
        for col in column_names:
            sheet_df[col] = sheet_df[col].astype(str).str.contains('✓', na=False)

        all_skater_data.append(sheet_df)

    if not all_skater_data:
        return pd.DataFrame()

    combined_df = pd.concat(all_skater_data, ignore_index=True)
    
    id_cols = ['Skater Name', 'Group Name', 'Normalized Name']
    skill_cols = [col for col in combined_df.columns if col not in id_cols]

    agg_dict = {col: 'any' for col in skill_cols}
    agg_dict.update({col: 'first' for col in id_cols})

    final_df = combined_df.groupby('Normalized Name').agg(agg_dict).reset_index(drop=True)

    return process_skill_variations(final_df)


def process_skill_variations(df):
    """Consolidates skill variations into single skills, preserving all other data."""
    skill_map_df = load_mapping_df('skill_names.csv')
    
    # Start with the identifying columns
    final_cols = ['Skater Name', 'Group Name', 'Normalized Name']
    
    # Group the mapping file by the target 'Mapped Skill Name'
    grouped_skills = skill_map_df.groupby('Mapped Skill Name')

    for mapped_skill, group in grouped_skills:
        original_skills = group['Skill Names'].tolist()
        existing_skills = [s for s in original_skills if s in df.columns]

        if not existing_skills:
            continue

        # If it's a single skill (1 of 1), just ensure the column is kept
        if len(existing_skills) == 1:
            final_cols.append(existing_skills[0])
            continue
        
        # If it's a multi-variation skill, calculate the new consolidated column
        try:
            variations_needed = int(group['Variations Required'].iloc[0].split(' of ')[0])
            df[mapped_skill] = df[existing_skills].sum(axis=1) >= variations_needed
            final_cols.append(mapped_skill)
        except (ValueError, IndexError):
            continue

    # Return a new DataFrame with only the desired final columns
    # Use set to remove duplicates and then convert back to list to preserve order
    final_cols = list(dict.fromkeys(final_cols))
    return df[final_cols]
