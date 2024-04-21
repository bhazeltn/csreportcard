from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, current_app
from werkzeug.utils import secure_filename
from app.data_processing import identify_report_type, process_achievements, process_evaluations, validate_achievements, load_ribbon_requirements
from app.report_generation import create_report_cards
import os
import shutil
import pandas as pd

main = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        evaluations_file = request.files['evaluations_file']
        assessments_file = request.files['assessments_file']

        # Check if files are present
        if evaluations_file.filename == '' or assessments_file.filename == '':
            return render_template('index.html', message="Both files are required.")

        if evaluations_file and assessments_file:
            filename1 = secure_filename(evaluations_file.filename)
            filename2 = secure_filename(assessments_file.filename)
            evaluations_file_path = os.path.join('/home/bradley/development/csreportcard/data/uploads', filename1)
            assessments_file_path = os.path.join('/home/bradley/development/csreportcard/data/uploads', filename2)
            evaluations_file.save(evaluations_file_path)
            assessments_file.save(assessments_file_path)

            # Redirect to processing and validation step
            return redirect(url_for('main.process_files'))

    return render_template('index.html')

@main.route('/process_files')
def process_files():
    directory_path = '/home/bradley/development/csreportcard/data/uploads'
    achievements_df, evaluations_df = None, None

    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        report_type = identify_report_type(file_path)

        if report_type == 'Achievements Report':
            achievements_df = process_achievements(file_path)
        elif report_type == 'Evaluation Printouts':
            evaluations_df = process_evaluations(file_path, "/home/bradley/development/csreportcard/data/mapping/skill_names.csv")

    if achievements_df is not None and evaluations_df is not None:
        # Save dataframes for later use in generating report cards
        achievements_df.to_csv('/home/bradley/development/csreportcard/data/achievements.csv', index=False)
        evaluations_df.to_csv('/home/bradley/development/csreportcard/data/evaluations.csv', index=False)

        # Load ribbon requirements and validate achievements
        ribbon_requirement_df = load_ribbon_requirements("/home/bradley/development/csreportcard/data/mapping/ribbons.csv")
        missing_ribbons, missing_badges = validate_achievements(evaluations_df, achievements_df, ribbon_requirement_df)

        # Render template with results and link to generate report cards
        return render_template('results.html', missing_ribbons=missing_ribbons, missing_badges=missing_badges, can_generate=True)
    else:
        return render_template('index.html', message="Error processing files, please ensure the correct files are uploaded.")

@main.route('/generate_report_cards')
def generate_report_cards():
    # Read DataFrames from CSV
    evaluations_df = pd.read_csv('/home/bradley/development/csreportcard/data/evaluations.csv')
    achievements_df = pd.read_csv('/home/bradley/development/csreportcard/data/achievements.csv')

    # Define the path to your PDF template and the output directory for report cards
    template_path = '/home/bradley/development/csreportcard/app/report_generation/templates/pdf/Report_Card_ENG.pdf'
    output_directory = '/home/bradley/development/csreportcard/data/output'
    individual_directory = os.path.join(output_directory, 'individual')

    # Ensure the output directories exist and are empty
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    if not os.path.exists(individual_directory):
        print ("directory error")
        os.makedirs(individual_directory)
    
    # Clear existing report cards
    #clear_directory(output_directory)
    #clear_directory(individual_directory)
    current_app.logger.info("about to generate report cards")
    # Call the function to generate report cards
    create_report_cards(evaluations_df, achievements_df, template_path, output_directory)

    # Redirect to the process completion page which shows links to the generated report cards
    return redirect(url_for('main.process_completion'))

@main.route('/process_completion')
def process_completion():
    directory = '/home/bradley/development/csreportcard/data/output'
    individual_directory = '/home/bradley/development/csreportcard/data/output/individual'
    all_files = os.listdir(individual_directory)
    individual_files = sorted([f for f in all_files if f.endswith('.pdf') and not f.startswith('merged')])
    
    all_files = os.listdir(directory)
    merged_files = [f for f in all_files if f.startswith('report')]

    merged_file = merged_files[0] if merged_files else None

    return render_template('process_completion.html', individual_files=individual_files, merged_file=merged_file)

@main.route('/downloads/merged/<filename>')
def download_merged(filename):
    directory = '/home/bradley/development/csreportcard/data/output'
    return send_from_directory(directory, filename, as_attachment=True)

@main.route('/downloads/individual/<filename>')
def download_individual(filename):
    directory = '/home/bradley/development/csreportcard/data/output/individual'
    return send_from_directory(directory, filename, as_attachment=True)

def clear_directory(directory_path):
    """Remove all files in the specified directory."""
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')
