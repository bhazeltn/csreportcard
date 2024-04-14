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