from app import app, db
from app.models import Session, Skater
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
import json
import secrets
from datetime import date
from collections import defaultdict
from app.processing import validate_and_load_data, process_and_save_to_db, rerun_validation

@app.route('/')
def dashboard():
    """Displays the main dashboard with a list of all sessions."""
    sessions = Session.query.order_by(Session.report_date.desc()).all()
    return render_template('dashboard.html', sessions=sessions)

@app.route('/upload', methods=['GET', 'POST'])
def upload_files():
    """Handles the file upload form."""
    if request.method == 'POST':
        session_name = request.form.get('session_name')
        club_name = request.form.get('club_name')
        report_date = request.form.get('report_date')
        achievements_file = request.files.get('achievements_file')
        evaluations_file = request.files.get('evaluations_file')

        if not all([session_name, club_name, report_date, achievements_file, evaluations_file]):
            flash('All fields and files are required.', 'error')
            return redirect(request.url)

        secure_session_name = secure_filename(f"{report_date}_{session_name}")
        session_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_session_name)
        os.makedirs(session_path, exist_ok=True)

        achievements_file.save(os.path.join(session_path, "upload1.xlsx"))
        evaluations_file.save(os.path.join(session_path, "upload2.xlsx"))
        
        validation_results = validate_and_load_data(session_path, session_name)
        
        if validation_results['success']:
            existing_session = Session.query.filter_by(name=session_name).first()
            validation_results['session_exists'] = bool(existing_session)

            session['confirmation_data'] = validation_results
            session['form_data'] = {'club_name': club_name, 'report_date': report_date}
            return redirect(url_for('confirm_session'))
        else:
            flash(f"Validation Error: {validation_results['message']}", 'error')
            return redirect(url_for('upload_files'))

    today_date = date.today().strftime('%Y-%m-%d')
    return render_template('upload.html', today_date=today_date)

@app.route('/confirm', methods=['GET', 'POST'])
def confirm_session():
    confirmation_data = session.get('confirmation_data')
    form_data = session.get('form_data')
    if not confirmation_data or not form_data:
        flash('Session data not found. Please start over.', 'error')
        return redirect(url_for('upload_files'))

    if request.method == 'POST':
        replace_existing = request.form.get('replace') == 'true'
        session_name = confirmation_data['form_session_name']
        
        success, new_session_id = process_and_save_to_db(
            session_path=confirmation_data['session_path'],
            session_name=session_name,
            club_name=form_data['club_name'],
            report_date=form_data['report_date'],
            replace=replace_existing
        )
        
        session.pop('confirmation_data', None)
        session.pop('form_data', None)
        
        if success:
            flash('Session data has been successfully saved and processed.', 'success')
            return redirect(url_for('validation_results', session_id=new_session_id)) 
        else:
            flash('An error occurred while saving the data.', 'error')
            return redirect(url_for('upload_files'))

    return render_template('confirm.html', data=confirmation_data)

@app.route('/session/<int:session_id>/validation')
def validation_results(session_id):
    session_obj = Session.query.get_or_404(session_id)
    results = json.loads(session_obj.validation_results) if session_obj.validation_results else []
    return render_template('validation_results.html', session=session_obj, results=results)

@app.route('/autofix_achievement', methods=['POST'])
def autofix_achievement():
    session_id = request.form.get('session_id')
    skater_name = request.form.get('skater_name')
    ribbon_name = request.form.get('ribbon_name')
    suggested_date = request.form.get('suggested_date')

    skater = Skater.query.filter_by(session_id=session_id, name=skater_name).first()
    if skater:
        skater_data = json.loads(skater.skater_data)
        
        parts = ribbon_name.split(' ')
        achievement_col_name = f"CanSkate {parts[1]} - {parts[0]}"
        
        skater_data[achievement_col_name] = suggested_date
        skater.skater_data = json.dumps(skater_data)
        db.session.commit()
        
        rerun_validation(session_id)
        flash(f"Achievement for {skater_name} has been auto-fixed.", 'success')
    else:
        flash("Could not find the specified skater to apply the fix.", 'error')

    return redirect(url_for('validation_results', session_id=session_id))

@app.route('/session/<int:session_id>')
def session_detail(session_id):
    """Displays the details of a session, with skaters grouped by their on-ice group."""
    session_obj = Session.query.get_or_404(session_id)
    skaters = session_obj.skaters
    
    skaters_by_group = defaultdict(list)
    for skater in skaters:
        skaters_by_group[skater.group_name].append(skater)
        
    return render_template('session_detail.html', session=session_obj, skaters_by_group=skaters_by_group)

@app.route('/skater/<int:skater_id>/report')
def skater_report_card(skater_id):
    """Displays a basic HTML version of a skater's CanSkate report card."""
    skater = Skater.query.get_or_404(skater_id)
    skater_data = json.loads(skater.skater_data)
    return render_template('skater_report_card.html', skater=skater, data=skater_data)

@app.route('/skater/<int:skater_id>/pcs_report')
def pcs_report_card(skater_id):
    """Displays the custom HTML PreCanSkate report card."""
    skater = Skater.query.get_or_404(skater_id)
    skater_data = json.loads(skater.skater_data)
    session_obj = skater.session
    return render_template('pcs_report_card.html', skater=skater, data=skater_data, session=session_obj)

@app.route('/generate_magic_link', methods=['POST'])
def generate_magic_link():
    """Generates a unique token for a group of skaters."""
    session_id = request.form.get('session_id')
    group_name = request.form.get('group_name')
    
    token = secrets.token_urlsafe(16)
    
    skaters = Skater.query.filter_by(session_id=session_id, group_name=group_name).all()
    for skater in skaters:
        skater.assigned_coach_token = token
    db.session.commit()
    
    flash(f"Magic link generated for group: {group_name}", "success")
    return redirect(url_for('session_detail', session_id=session_id))

@app.route('/coach/<token>', methods=['GET', 'POST'])
def coach_view(token):
    """Displays the coach's view for entering comments."""
    skaters = Skater.query.filter_by(assigned_coach_token=token).order_by(Skater.name).all()
    if not skaters:
        return "Invalid or expired link.", 404

    if request.method == 'POST':
        coach_name = request.form.get('coach_name')
        for skater in skaters:
            skater.coach_name = coach_name
            skater.coach_comments = request.form.get(f'comments_{skater.id}')
            if skater.coach_comments and skater.coach_comments.strip() != '':
                skater.comment_status = 'Pending'
            else:
                skater.comment_status = None
        db.session.commit()
        flash("Comments have been saved and are pending review.", "success")
        return redirect(url_for('coach_view', token=token))

    skaters_with_data = []
    for s in skaters:
        skaters_with_data.append({
            'id': s.id,
            'name': s.name,
            'coach_name': s.coach_name,
            'coach_comments': s.coach_comments,
            'comment_status': s.comment_status,
            'data': json.loads(s.skater_data)
        })

    session_name = skaters[0].session.name
    group_name = skaters[0].group_name
    club_name = skaters[0].session.club_name
    
    return render_template('coach_view.html', skaters=skaters_with_data, session_name=session_name, group_name=group_name, club_name=club_name)

@app.route('/skater/<int:skater_id>/review', methods=['GET', 'POST'])
def review_comment(skater_id):
    """Handles the admin's review, edit, and approval of a comment."""
    skater = Skater.query.get_or_404(skater_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        revised_comment = request.form.get('revised_comment')
        
        skater.coach_comments = revised_comment
        
        if action == 'Approve':
            skater.comment_status = 'Approved'
            flash(f"Comment for {skater.name} has been approved.", "success")
        elif action == 'Reject':
            skater.comment_status = 'Rejected'
            flash(f"Comment for {skater.name} has been rejected. The coach will be able to revise it.", "info")
            
        db.session.commit()
        return redirect(url_for('session_detail', session_id=skater.session_id))

    skater_data = json.loads(skater.skater_data)
    return render_template('review_comment.html', skater=skater, data=skater_data)
