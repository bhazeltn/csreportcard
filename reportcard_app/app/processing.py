import pandas as pd
import numpy as np
import os
import openpyxl
import re
import json
from datetime import datetime
from app import app, db
from app.models import Session, Skater

# --- Helper Functions ---

def normalize_name(name):
    """Correctly capitalizes and normalizes a skater's name."""
    if not isinstance(name, str): return "", ""
    # Capitalize each part of a multi-word or hyphenated name
    capitalized_name = ' '.join(word.capitalize() for word in '-'.join([part.capitalize() for part in name.split('-')]).split(' '))
    
    normalized = capitalized_name.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[^a-z0-9\s-]', '', normalized)
    return capitalized_name, normalized

def load_mapping_df(filename):
    """Loads a mapping CSV from the data/mapping directory."""
    path = os.path.join(app.root_path, '..', 'data', 'mapping', filename)
    return pd.read_csv(path)

def transform_ribbon_name(ribbon):
    """Standardizes ribbon names to match the mapping files."""
    if not isinstance(ribbon, str): return ""
    ribbon = ribbon.replace("Pre-CanSkate", "PreCanSkate")
    match = re.match(r"CanSkate (\d+) - (.*)", ribbon.strip())
    if match:
        return f"{match.group(2).strip()} {match.group(1).strip()}"
    return ribbon.strip()

# --- Report Identification and Initial Loading ---

def identify_report_type(file_path):
    """Identifies the report type by inspecting the content of the first worksheet."""
    try:
        df = pd.read_excel(file_path, header=None, sheet_name=0, nrows=5)
        first_row_values = [str(v).strip().lower() for v in df.iloc[0].values]
        if 'first name' in first_row_values and 'last name' in first_row_values:
            return 'Achievements'
        if any(isinstance(cell, str) and 'coaches:' in cell.lower() for cell in df.iloc[1].values):
            return 'Evaluations'
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
        achievements_df['Skater Name_temp'] = achievements_df['First Name'] + ' ' + achievements_df['Last Name']
        _, achievements_df['Normalized Name'] = zip(*achievements_df['Skater Name_temp'].apply(normalize_name))
        
        evaluations_df = get_skater_list_from_evaluations(evaluations_path)

        date_cols = achievements_df.drop(columns=['First Name', 'Last Name', 'Skater Name_temp', 'Normalized Name'], errors='ignore')
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
    _, eval_df['Normalized Name'] = zip(*eval_df['Skater Name'].apply(normalize_name))
    return eval_df

# --- Core Data Processing and Database Saving ---

def process_and_save_to_db(session_path, session_name, club_name, report_date, replace=False):
    """Processes the validated files and saves the session and skater data to the database."""
    existing_session = Session.query.filter_by(name=session_name).first()
    if existing_session:
        if replace:
            db.session.delete(existing_session)
            db.session.commit()
        else:
            return False, None

    upload1_path = os.path.join(session_path, 'upload1.xlsx')
    upload2_path = os.path.join(session_path, 'upload2.xlsx')
    
    achievements_path = upload1_path if identify_report_type(upload1_path) == 'Achievements' else file2_path
    evaluations_path = upload2_path if identify_report_type(upload1_path) == 'Achievements' else file1_path

    try:
        achievements_df = pd.read_excel(achievements_path)
        achievements_df['Skater Name_temp'] = achievements_df['First Name'] + ' ' + achievements_df['Last Name']
        achievements_df['Skater Name'], achievements_df['Normalized Name'] = zip(*achievements_df['Skater Name_temp'].apply(normalize_name))
        
        achievements_df = achievements_df.drop(columns=['First Name', 'Last Name', 'Skater Name_temp'])
        
        achievements_df.columns = [re.sub(r'Stage (\d+) CanSkate', r'Stage \1', col) for col in achievements_df.columns]

        evals_df = load_and_transform_evaluations(evaluations_path)
        merged_df = pd.merge(evals_df, achievements_df, on='Normalized Name', how='left', suffixes=('', '_ach'))
        
        merged_df['Skater Name'] = merged_df['Skater Name'].fillna(merged_df['Skater Name_ach'])
        merged_df = merged_df.drop(columns=['Skater Name_ach'], errors='ignore')

        merged_df = autofix_achievement_dates(merged_df)
        merged_df = generate_badge_dates(merged_df)
        merged_df = automate_pcs_recommendation(merged_df, report_date)
        validation_results = validate_missing_ribbons(merged_df, report_date)

        new_session = Session(
            name=session_name, 
            club_name=club_name, 
            report_date=report_date,
            validation_results=json.dumps(validation_results)
        )
        db.session.add(new_session)
        db.session.commit()

        for index, row in merged_df.iterrows():
            skater_data_dict = row.to_dict()
            final_data = {k: v for k, v in skater_data_dict.items() if pd.notna(v)}
            
            skater = Skater(
                name=final_data.get('Skater Name'),
                group_name=final_data.get('Group Name'),
                birthdate=pd.to_datetime(final_data.get('Birthdate')).strftime('%Y-%m-%d') if pd.notna(final_data.get('Birthdate')) else None,
                generates_pcs_report=final_data.get('generates_pcs_report', False),
                generates_cs_report=final_data.get('generates_cs_report', False),
                session_id=new_session.id,
                skater_data=json.dumps(final_data, default=str),
                suggested_recommendation=final_data.get('Recommendation'),
                suggested_recommendation_reason=final_data.get('Recommendation Reason')
            )
            db.session.add(skater)

        db.session.commit()
        return True, new_session.id

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error during database import: {e}", exc_info=True)
        return False, None

def load_and_transform_evaluations(file_path):
    """Loads, transforms, and consolidates the evaluations data from the Excel file."""
    xls = pd.ExcelFile(file_path)
    all_skater_data = []
    group_pattern = re.compile(r'--\s*(.*)')

    for sheet_name in xls.sheet_names:
        is_pcs_sheet = 'pre-canskate' in sheet_name.lower()
        is_cs_sheet = 'canskate' in sheet_name.lower()
        if not is_pcs_sheet and not is_cs_sheet:
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

        sheet_df['Skater Name'], sheet_df['Normalized Name'] = zip(*sheet_df['Skater Name'].apply(normalize_name))
        
        sheet_df['generates_pcs_report'] = is_pcs_sheet
        sheet_df['generates_cs_report'] = is_cs_sheet
        
        for col in column_names:
            sheet_df[col] = sheet_df[col].astype(str).str.contains('✓', na=False)

        all_skater_data.append(sheet_df)

    if not all_skater_data:
        return pd.DataFrame()

    combined_df = pd.concat(all_skater_data, ignore_index=True)
    
    id_cols = ['Skater Name', 'Group Name', 'Normalized Name']
    skill_cols = [col for col in combined_df.columns if col not in id_cols and col not in ['generates_pcs_report', 'generates_cs_report']]

    agg_dict = {col: 'any' for col in skill_cols}
    agg_dict.update({
        'generates_pcs_report': 'any',
        'generates_cs_report': 'any',
        'Skater Name': 'first',
        'Group Name': 'first',
        'Normalized Name': 'first'
    })

    final_df = combined_df.groupby('Normalized Name').agg(agg_dict).reset_index(drop=True)

    return process_skill_variations(final_df)


def process_skill_variations(df):
    """Consolidates skill variations into single skills, preserving all other data."""
    skill_map_df = load_mapping_df('skill_names.csv')
    
    final_df = df.copy()
    cols_to_drop = []
    
    grouped_skills = skill_map_df.groupby('Mapped Skill Name')

    for mapped_skill, group in grouped_skills:
        original_skills = group['Skill Names'].tolist()
        existing_skills = [s for s in original_skills if s in final_df.columns]

        if not existing_skills or len(existing_skills) <= 1:
            continue
        
        try:
            variations_needed = int(group['Variations Required'].iloc[0].split(' of ')[0])
            final_df[mapped_skill] = final_df[existing_skills].sum(axis=1) >= variations_needed
            cols_to_drop.extend(existing_skills)
        except (ValueError, IndexError):
            continue

    final_df.drop(columns=cols_to_drop, inplace=True, errors='ignore')
    return final_df

# --- Validation and Autofix Functions ---

def autofix_achievement_dates(df):
    """Corrects any chronological errors in achievement dates for each skater."""
    for index, skater in df.iterrows():
        for category in ['Agility', 'Balance', 'Control']:
            dates = {}
            for stage in range(1, 7):
                col_name = f"CanSkate {stage} - {category}"
                if col_name in skater and pd.notna(skater[col_name]):
                    dates[stage] = pd.to_datetime(skater[col_name])
            
            for stage in range(6, 1, -1):
                if stage in dates and (stage - 1) in dates:
                    if dates[stage - 1] > dates[stage]:
                        df.loc[index, f"CanSkate {stage - 1} - {category}"] = dates[stage]
    return df

def generate_badge_dates(df):
    """Generates badge dates for skaters who have completed all three ribbons for a stage."""
    for stage in range(1, 7):
        badge_col = f"Stage {stage}"
        agility_col = f"CanSkate {stage} - Agility"
        balance_col = f"CanSkate {stage} - Balance"
        control_col = f"CanSkate {stage} - Control"

        if all(col in df.columns for col in [agility_col, balance_col, control_col]):
            completed_all_ribbons = df[[agility_col, balance_col, control_col]].notna().all(axis=1)
            
            if completed_all_ribbons.any():
                latest_dates = df.loc[completed_all_ribbons, [agility_col, balance_col, control_col]].max(axis=1)
                df.loc[completed_all_ribbons, badge_col] = latest_dates
    return df

def automate_pcs_recommendation(df, report_date):
    """Automates the recommendation for PreCanSkate skaters based on age and progress."""
    df['Recommendation'] = None
    df['Recommendation Reason'] = None
    pcs_skaters_mask = df['generates_pcs_report'] == True
    
    for index, skater in df[pcs_skaters_mask].iterrows():
        birthdate = pd.to_datetime(skater.get('Birthdate'))
        if pd.isna(birthdate):
            continue
            
        age = (datetime.strptime(report_date, '%Y-%m-%d') - birthdate).days / 365.25
        
        passed_pcs4 = pd.notna(skater.get('Pre-CanSkate 4'))
        passed_pcs2 = pd.notna(skater.get('Pre-CanSkate 2'))
        
        recommendation = "Remain in PreCanSkate"
        reason = "Default recommendation."

        if age >= 4.8:
            recommendation = "Move to CanSkate"
            reason = f"Age ({age:.1f}) is >= 4.8"
        elif age >= 4.3 and passed_pcs2:
            recommendation = "Move to CanSkate"
            reason = f"Age ({age:.1f}) is >= 4.3 and PCS 2 is passed"
        elif passed_pcs4:
            recommendation = "Move to CanSkate"
            reason = "PCS 4 is passed"
            
        df.loc[index, 'Recommendation'] = recommendation
        df.loc[index, 'Recommendation Reason'] = reason
        
    return df

def validate_missing_ribbons(df, report_date):
    """Validates which skaters have earned a ribbon but do not have an achievement date."""
    ribbon_reqs = load_mapping_df('ribbons.csv')
    missing_ribbons = []

    for index, req in ribbon_reqs.iterrows():
        ribbon_name = req['Ribbon']
        elements_needed = req['Skills Required']

        elements_for_ribbon = [col for col in df.columns if isinstance(col, str) and col.startswith(ribbon_name)]
        if not elements_for_ribbon: continue

        df['elements_passed_count'] = df[elements_for_ribbon].sum(axis=1)
        earned_ribbon = df[df['elements_passed_count'] >= elements_needed]

        for i, skater in earned_ribbon.iterrows():
            parts = ribbon_name.split(' ')
            category, stage = parts[0], int(parts[1])
            achievement_col_name = f"CanSkate {stage} - {category}"
            
            if achievement_col_name in df.columns and pd.isna(skater.get(achievement_col_name)):
                suggested_date = report_date
                for next_stage in range(stage + 1, 7):
                    next_col = f"CanSkate {next_stage} - {category}"
                    if next_col in skater and pd.notna(skater[next_col]):
                        suggested_date = skater[next_col]
                        break

                missing_ribbons.append({
                    'Skater Name': skater['Skater Name'],
                    'Ribbon': ribbon_name,
                    'Skills Passed': int(skater['elements_passed_count']),
                    'Skills Required': int(elements_needed),
                    'Suggested Date': pd.to_datetime(suggested_date).strftime('%Y-%m-%d')
                })
    return missing_ribbons

def rerun_validation(session_id):
    """Fetches all skater data for a session, re-runs validation, and updates the session."""
    session = Session.query.get(session_id)
    if not session: return

    skaters = session.skaters
    skater_data_list = [json.loads(s.skater_data) for s in skaters]
    df = pd.DataFrame(skater_data_list)

    df = autofix_achievement_dates(df)
    df = generate_badge_dates(df)
    validation_results = validate_missing_ribbons(df, session.report_date)
    session.validation_results = json.dumps(validation_results)
    db.session.commit()
