import pandas as pd

def validate_achievements(evaluations_df, achievements_df):
    ribbons = missing_ribbons(evaluations_df, achievements_df)
    badges = missing_achievements(achievements_df)
    
    return ribbons, badges

def missing_ribbons(evaluations_df, achievements_df):
    # Extract ribbon names from evaluations_df
    ribbon_names = set(col.split(' - ')[0] for col in evaluations_df.columns if '-' in col)
    
    missing_achievements = []

    # Loop through each skater in evaluations_df
    for index, row in evaluations_df.iterrows():
        skater_name = row['Skater Name']
        for ribbon in ribbon_names:
            # Filter columns for the current ribbon
            ribbon_skills = [col for col in evaluations_df.columns if col.startswith(ribbon)]
            # Check if all skills for this ribbon are marked True
            if all(row[skill] for skill in ribbon_skills):
                # Check the corresponding date in achievements_df
                if pd.isna(achievements_df.loc[achievements_df['Skater Name'] == skater_name, ribbon].iloc[0]):
                    missing_achievements.append({
                        'Skater Name': skater_name,
                        'Ribbon': ribbon,
                        'Issue': 'All skills completed, but no achievement date recorded'
                    })

    return pd.DataFrame(missing_achievements)

def missing_achievements(df, stages=[1, 2, 3, 4, 6]):
    """Identifies skaters who have completed all tasks for a stage but do not have a recorded achievement date.
    
    Args:
        df (pandas.DataFrame): DataFrame containing skater achievements data.
        stages (list, optional): List of stages to check. Defaults to [1, 2, 3, 4, 6].

    Returns:
        pandas.DataFrame: DataFrame listing skaters with missing stage credits.
    """
    missing_credits_list = []

    for i in stages:
        agility_col = f'Agility {i}'
        balance_col = f'Balance {i}'
        control_col = f'Control {i}'
        stage_col = f'Stage {i}'
        # Criteria for completed tasks and missing stage credit
        task_completed = df[[agility_col, balance_col, control_col]].notna().all(axis=1)
        no_credit = df[stage_col].isna()

        # Detect missing credits
        missing_credits = df[task_completed & no_credit]
        for index, row in missing_credits.iterrows():
            skater_info = {
                'Skater Name': row['Skater Name'],
                'Stage': i,
                'Details': f"Completed all tasks for Stage {i} but no stage recorded."
            }
            missing_credits_list.append(skater_info)

    return pd.DataFrame(missing_credits_list)

def load_skill_requirements(file_path):
    skill_df = pd.read_csv(file_path)
    
    # Splitting the 'Variations Required' into two separate columns
    variations_split = skill_df['Variations Required'].str.split(' of ', expand=True)
    
    # Handle missing or malformed entries before conversion
    variations_split[0] = pd.to_numeric(variations_split[0], errors='coerce')
    variations_split[1] = pd.to_numeric(variations_split[1], errors='coerce')
    
    # Fill NaN values with a default value or handle them according to your requirements
    variations_split[0] = variations_split[0].fillna(0)  # Example: setting defaults to 0
    variations_split[1] = variations_split[1].fillna(1)  # Assuming at least one variation exists as default

    skill_df['Variations Needed'] = variations_split[0].astype(int)
    skill_df['Total Variations'] = variations_split[1].astype(int)
    
    # Filter out all 1 variation skills
    skill_df = skill_df[~((skill_df['Variations Needed'] == 1) & (skill_df['Total Variations'] == 1))]
    
    return skill_df

def verify_mapped_skills(evaluations_df, skill_df):
    # Adding new mapped skills with initial false values
    for skill in skill_df['Mapped Skill Name'].unique():
        evaluations_df[skill] = False

    # Iterate over each mapped skill and determine if it should be marked as complete
    for _, row in skill_df.iterrows():
        mapped_skill = row['Mapped Skill Name']
        original_skills = skill_df[
            skill_df['Mapped Skill Name'] == mapped_skill
        ]['Skill Names']

        required_variations = row['Variations Needed']
        total_variations = row['Total Variations']

        # Aggregate the results for each mapped skill based on original skills
        for index, eval_row in evaluations_df.iterrows():
            completed_count = sum(eval_row[skill] for skill in original_skills if skill in evaluations_df.columns)
            # Check if the number of completed variations meets the required number
            if completed_count >= required_variations:
                evaluations_df.at[index, mapped_skill] = True

    # Remove the original skill columns
    original_skills_to_remove = skill_df['Skill Names'].unique()
    evaluations_df = evaluations_df.drop(columns=[col for col in original_skills_to_remove if col in evaluations_df.columns])

    return evaluations_df