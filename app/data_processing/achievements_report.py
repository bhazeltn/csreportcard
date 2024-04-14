import pandas as pd
import re

def process_achievements(file_path):
    """ Import the achievement report, clean the data, and pass it back for futher processing

    Args:
        file_path (str): The path to the Excel file.
    
    Returns:
        pandas.DataFrame: The cleaned and prepared data.
    """
    try:
        data = load_achievements_data(file_path)
        data = clean_achievements_data(data)
        # Further processing or saving results
        return data
    except Exception as e:
        print(f"Error processing achievements data: {e}")
        return None


def load_achievements_data(file_path):
    """Load data from the Achievements Report Excel file.
    
    Args:
        file_path (str): The path to the Excel file.
    
    Returns:
        pandas.DataFrame: The loaded data.
    """
    try:
        # Load the Excel file into a DataFrame
        data = pd.read_excel(file_path)
        return data
    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")
        return None

def clean_achievements_data(df):
    """ Function to clean the Achievements DataFrame using the helper functions
    
    Args:
        df (pandas.DataFrame): The achievements DataFrame
        
    Returns: 
        pandas.DataFrame: The cleaned data.
    """
    clean_date_dtypes(df)
    clean_column_names(df)
    create_stage_5(df)
    merge_name(df)
    return df

def clean_date_dtypes(df):
    """Update the Achievements DataFrame so all the date columns have the correct datatype

    Args:
        df (pandas.DataFrame): The achievements DataFrame
        
    Returns: 
        pandas.DataFrame: The cleaned data.
    """
    all_columns = df.columns
    columns_to_convert = [col for col in all_columns if col not in ['First Name', 'Last Name']]
    df[columns_to_convert] = df[columns_to_convert].apply(pd.to_datetime)
    return df

def clean_column_names(df):
    """Give the columns names that will be easier to reference in the future.

    Args:
        df (pandas.DataFrame): The DataFrame with unclean column names.

    Returns:
        pandas.DataFrame: The DataFrame with cleaned column names.
    """
    
    # Uniformly format 'CanSkate' across all column names
    df.columns = df.columns.str.replace('Canskate', 'CanSkate', flags=re.IGNORECASE)
    
    df.columns = df.columns.str.replace('CanSkate :: ', '')

    # Correctly handle "Stage 5/6 CanSkate" to "Stage 6 CanSkate"
    df.columns = [re.sub(r'Stage\s+5/6\s+CanSkate', 'Stage 6 CanSkate', col) for col in df.columns]

    # Remove 'CanSkate' from columns formatted as 'Stage # CanSkate'
    df.columns = [re.sub(r'Stage (\d+) CanSkate', r'Stage \1', col) for col in df.columns]
    
    # Format Agility, Balance, and Control columns
    df.columns = [re.sub(r'CanSkate (\d+) - Agility', r'Agility \1', col) for col in df.columns]
    df.columns = [re.sub(r'CanSkate (\d+) - Balance', r'Balance \1', col) for col in df.columns]
    df.columns = [re.sub(r'CanSkate (\d+) - Control', r'Control \1', col) for col in df.columns]

    return df

def create_stage_5(df):
    """ Created a Stage 5 column and uses the Agility, Balance, and Control ribbons to determine
    if the stage is complete
    
    Args:
        df (pandas.DataFrame): The achievements DataFrame
        
    Returns: 
        pandas.DataFrame: The cleaned data.
    """
    # Define the column names for Stage 5 tasks
    agility_5_col = 'Agility 5'
    balance_5_col = 'Balance 5'
    control_5_col = 'Control 5'

    # Create a new column for Stage 5, initialize with NaT (Not a Time)
    df['Stage 5'] = pd.NaT

    # Check if all tasks for Stage 5 are completed (not null)
    stage_5_completed = df[[agility_5_col, balance_5_col, control_5_col]].notna().all(axis=1)

    # Where all tasks are completed, find the newest date from the task columns
    df.loc[stage_5_completed, 'Stage 5'] = df.loc[stage_5_completed, [agility_5_col, balance_5_col, control_5_col]].max(axis=1)

    return df

def merge_name(df):
    """ Makes Skater Name from First Name and Last Name to match the Evaluations Report

    Args:
        df (pandas.DataFrame): The achievements DataFrame
        
    Returns: 
        pandas.DataFrame: The cleaned data.
    """
    # Merge First Name and Last Name into Skater Name
    df['Skater Name'] = df['First Name'] + ' ' + df['Last Name']

    df.drop(['First Name', 'Last Name'], axis=1, inplace=True)
    
    skater_names = df.pop('Skater Name')
    df.insert(0, 'Skater Name', skater_names)
    
    return df