import pandas as pd

def validate_achievements(evaluations_df, achievements_df, ribbon_requirements_df):
    ribbons = missing_ribbons(evaluations_df, ribbon_requirements_df, achievements_df)
    badges = missing_achievements(achievements_df)
    
    return ribbons, badges

def missing_ribbons(evaluations_df, ribbon_requirements_df, achievements_df):
    missing_ribbons_list = []
    
    # Iterate over each ribbon requirement
    for index, requirement in ribbon_requirements_df.iterrows():
        ribbon_name = requirement['Ribbon']
        required_skills = requirement['Skills Required']
        
        # Filter evaluations_df for columns that match the ribbon name
        related_skills = [col for col in evaluations_df.columns if ribbon_name in col]
        
        for idx, skater in evaluations_df.iterrows():
            skater_name = skater['Skater Name']
            # Sum the True values for related skills
            completed_skills = skater[related_skills].sum()
            
            # Check if the number of completed skills meets the requirement
            if completed_skills >= required_skills:
                # Check if the achievement date is NOT recorded in achievements_df
                achievement_recorded = not pd.isna(
                    achievements_df.loc[achievements_df['Skater Name'] == skater_name, ribbon_name].iloc[0]
                )
                
                if not achievement_recorded:
                    missing_ribbons_list.append({
                        'Skater Name': skater_name,
                        'Ribbon': ribbon_name,
                        'Completed Skills': completed_skills,
                        'Required Skills': required_skills,
                        'Status': 'Achievement missing in records'
                    })
                
    return pd.DataFrame(missing_ribbons_list)

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

def load_ribbon_requirements(csv_path):
    return pd.read_csv(csv_path)