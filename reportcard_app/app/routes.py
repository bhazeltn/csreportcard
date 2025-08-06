from app import app, db
from app.models import Session
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
from app.processing import validate_and_load_data, process_and_save_to_db

@app.route('/', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        session_name = request.form.get('session_name')
        club_name = request.form.get('club_name')
        report_date = request.form.get('report_date')
        achievements_file = request.files.get('achievements_file')
        evaluations_file = request.files.get('evaluations_file')

        if not all([session_name, club_name, report_date, achievements_file, evaluations_file]):
            flash('All fields and files are required.', 'error')
            return redirect(request.url)

        # Secure the session name for use in the directory path
        secure_session_name = secure_filename(f"{report_date}_{session_name}")
        session_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_session_name)
        os.makedirs(session_path, exist_ok=True)

        # Save the files with generic names for consistent processing
        achievements_file.save(os.path.join(session_path, "upload1.xlsx"))
        evaluations_file.save(os.path.join(session_path, "upload2.xlsx"))
        
        validation_results = validate_and_load_data(session_path, session_name)
        
        if validation_results['success']:
            # Check if session already exists in the database
            existing_session = Session.query.filter_by(name=session_name).first()
            validation_results['session_exists'] = bool(existing_session)

            session['confirmation_data'] = validation_results
            session['form_data'] = {'club_name': club_name, 'report_date': report_date}
            return redirect(url_for('confirm_session'))
        else:
            flash(f"Validation Error: {validation_results['message']}", 'error')
            return redirect(url_for('upload_files'))

    return render_template('index.html')

@app.route('/confirm', methods=['GET', 'POST'])
def confirm_session():
    confirmation_data = session.get('confirmation_data')
    form_data = session.get('form_data')
    if not confirmation_data or not form_data:
        flash('Session data not found. Please start over.', 'error')
        return redirect(url_for('upload_files'))

    if request.method == 'POST':
        # Check if the user confirmed to replace the data
        replace_existing = request.form.get('replace') == 'true'
        session_name = confirmation_data['form_session_name']
        
        success = process_and_save_to_db(
            session_path=confirmation_data['session_path'],
            session_name=session_name,
            club_name=form_data['club_name'],
            report_date=form_data['report_date'],
            replace=replace_existing
        )
        
        # Clear the session data regardless of outcome
        session.pop('confirmation_data', None)
        session.pop('form_data', None)
        
        if success:
            flash('Session data has been successfully saved and processed.', 'success')
            return redirect(url_for('upload_files')) 
        else:
            flash('An error occurred while saving the data. The session name may already exist.', 'error')
            return redirect(url_for('upload_files'))

    return render_template('confirm.html', data=confirmation_data)
