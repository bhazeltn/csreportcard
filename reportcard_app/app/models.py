from app import db

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    report_date = db.Column(db.String(20), nullable=False)
    club_name = db.Column(db.String(100), nullable=False)
    skaters = db.relationship('Skater', backref='session', lazy=True, cascade="all, delete-orphan")

class Skater(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    
    # --- ADD THIS LINE ---
    group_name = db.Column(db.String(50), nullable=True)
    # --------------------

    # Store all evaluation and achievement data as a single JSON string
    skater_data = db.Column(db.Text, nullable=False)
    
    # Fields for coach collaboration
    coach_comments = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.String(50), nullable=True)
    assigned_coach_token = db.Column(db.String(100), nullable=True)
