import os
import pandas as pd
from app.data_processing.identify_report_type import identify_report_type
from app.data_processing.achievements_report import process_achievements
from app.data_processing.evaluations_report import process_evaluations
from app.data_processing.validations import validate_achievements, load_skill_requirements, verify_mapped_skills

def process_reports(directory_path):
    """Process all files in the given directory."""
    for filename in os.listdir(directory_path):
        if filename.endswith('.xlsx'):  # Process only Excel files
            file_path = os.path.join(directory_path, filename)
            report_type = identify_report_type(file_path)
            if report_type == 'Achievements Report':
                achievements_df = process_achievements(file_path)
                print("Achievements Processed")
            elif report_type == 'Evaluation Printouts':
                evaluations_df = process_evaluations(file_path)
                skills_df = load_skill_requirements("/home/bradley/development/csreportcard/skill_names.csv")
                evaluations_df = verify_mapped_skills(evaluations_df, skills_df)
                print("Evaluations Processed")
            else:
                print(f"Unknown report type for {filename}")
    missing_ribbons, missing_badges = validate_achievements(evaluations_df, achievements_df)
    
    #print (missing_ribbons)
    #print (missing_badges)
    
    #print ("achievements_df")
    #for column in achievements_df.columns:
    #    print(column)
    print("evaluations_df")
    evaluations_df.to_csv('./test.csv')
    for column in evaluations_df.columns:
        print(column)
    
    
    

directory_path = '/home/bradley/development/csreportcard/data/uploads'
process_reports(directory_path)


