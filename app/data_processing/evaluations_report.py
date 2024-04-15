import re
import pandas as pd

def process_evaluations(evaluations_file_path, skills_file_path):
    try:
        data = compile_evaluations(evaluations_file_path)
        data = convert_evaluations_to_boolean(data)
        skills = load_skill_requirements(skills_file_path)
        data = verify_mapped_skills(data, skills)
        # Additional transformations or checks
        return data
    except Exception as e:
        print(f"Error processing evaluations data: {e}")
        return None

def clean_skill_name(skill):
    # Remove newlines and extra spaces
    cleaned_skill = skill.strip().replace("\n", " ")

    # If the skill starts with "Speed Drill", truncate after the drill number
    speed_drill_match = re.match(r"(Speed Drill #[1-3])(:.*)?", cleaned_skill)
    if speed_drill_match:
        return speed_drill_match.group(1)  # Return only "Speed Drill #X"
    
    return cleaned_skill


def transform_ribbon_name(ribbon):
    # Use regex to swap places between "CanSkate" number and the ribbon type
    # Adjust the formatting for "Pre-CanSkate" first
    ribbon = ribbon.replace("Pre-CanSkate", "PreCanSkate")
    match = re.match(r"CanSkate (\d+) - (.*)", ribbon.strip())
    if match:
        return f"{match.group(2)} {match.group(1)}"
    return ribbon  # Return original if no match just as a safeguard

def load_transform_sheet(file_path, sheet_name):
    # Load the worksheet, skipping the first row which contains session information
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, skiprows=1)

    # Drop the last two rows if necessary
    df = df.iloc[:-2]

    # Clear out the "Coaches" label which is not needed
    df.iloc[0, 0] = None

    # Reading ribbon names from the first row after "Skater Name"
    ribbons = df.iloc[0, 1:].ffill()

    # Skill names from the second row
    skills = df.iloc[1, 1:]

    # Combine ribbon and skill names for column names, skip 'Skater Name'
    column_names = ['Skater Name'] + [f'{transform_ribbon_name(ribbon)} - {clean_skill_name(skill)}' for ribbon, skill in zip(ribbons, skills)]

    # Set column names
    df.columns = column_names

    # Drop the rows used for headers
    df = df.drop(index=[0, 1])

    return df
    
    
def compile_evaluations(file_path):
    """Load all sheets and compile them into a single DataFrame by merging on 'Skater Name'."""
    xls = pd.ExcelFile(file_path)
    combined_df = None  # Initialize to None

    for sheet_name in xls.sheet_names:
        df = load_transform_sheet(file_path, sheet_name)

        if combined_df is None:
            combined_df = df  # First DataFrame to initialize combined_df
        else:
            # Merge the current DataFrame with the combined DataFrame on 'Skater Name'
            combined_df = pd.merge(combined_df, df, on='Skater Name', how='outer', suffixes=('', '_dup'))
            
    return combined_df

def convert_evaluations_to_boolean(df):
    """ Replaces the checkmarks with TRUE and empty cells with FALSE to prepare for the report card

    Args:
        df (pandas.DataFrame): The achievements DataFrame
        
    Returns: 
        pandas.DataFrame: The cleaned data.
    """
    df = df.replace({'✓': True, '✓*>': True})

    # Replace all NaN (including None, np.nan) values with False
    df = df.fillna(False)
    
    return df

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