from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os

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
            evaluations_file.save(os.path.join('/home/bradley/development/csreportcard/data/uploads', filename1))
            assessments_file.save(os.path.join('/home/bradley/development/csreportcard/data/uploads', filename2))
            return redirect(url_for('main.upload_success'))

    return render_template('index.html')

@main.route('/upload_success')
def upload_success():
    return "Files successfully uploaded!"
