from app import app
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os

# We will rename the main processing function to be more descriptive
from app.processing import validate_and_load_data

@app.route('/', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        # --- Get Session Data from Form ---
        session_name = request.form.get('session_name')
        club_name = request.form.get('club_name')
        report_date = request.form.get('report_date')
        achievements_file = request.files.get('achievements_file')
        evaluations_file = request.files.get('evaluations_file')

        # --- Basic Validation ---
        if not all([session_name, club_name, report_date, achievements_file, evaluations_file]):
            flash('All fields and files are required.', 'error')
            return redirect(request.url)

        # --- Save Files Temporarily ---
        # Create a unique folder for this upload attempt
        session_folder_name = secure_filename(f"{report_date}_{session_name}")
        session_path = os.path.join(app.config['UPLOAD_FOLDER'], session_folder_name)
        os.makedirs(session_path, exist_ok=True)

        # We save with temporary names first, as we don't know which is which yet.
        file1_path = os.path.join(session_path, "upload1.xlsx")
        file2_path = os.path.join(session_path, "upload2.xlsx")
        achievements_file.save(file1_path)
        evaluations_file.save(file2_path)
        
        # --- Validate the files and get data for the confirmation page ---
        validation_results = validate_and_load_data(session_path, session_name)
        
        if validation_results['success']:
            # Store results in the user's session to use after confirmation
            session['confirmation_data'] = validation_results
            session['form_data'] = {'club_name': club_name, 'report_date': report_date}
            return redirect(url_for('confirm_session'))
        else:
            flash(f"Validation Error: {validation_results['message']}", 'error')
            return redirect(url_for('upload_files'))

    return render_template('index.html')

@app.route('/confirm', methods=['GET', 'POST'])
def confirm_session():
    # Retrieve the validated data from the session
    confirmation_data = session.get('confirmation_data')
    if not confirmation_data:
        # If there's no data, the user shouldn't be here. Redirect them.
        return redirect(url_for('upload_files'))

    if request.method == 'POST':
        # User has clicked the "Confirm & Process Data" button
        app.logger.info(f"User confirmed session: {confirmation_data['form_session_name']}")
        
        # --- THIS IS WHERE WE WILL ADD DATABASE LOGIC ---
        # For now, we just clear the session data and flash a success message
        
        session.pop('confirmation_data', None)
        session.pop('form_data', None)
        
        flash('Session confirmed! Data is now being processed and saved.', 'success')
        # In the future, this will redirect to the admin dashboard for the new session
        return redirect(url_for('upload_files')) 

    # If it's a GET request, show the confirmation page with the validated data
    return render_template('confirm.html', data=confirmation_data)
