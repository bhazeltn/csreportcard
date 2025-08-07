from app import db

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    report_date = db.Column(db.String(20), nullable=False)
    club_name = db.Column(db.String(100), nullable=False)
    skaters = db.relationship('Skater', backref='session', lazy=True, cascade="all, delete-orphan")
    validation_results = db.Column(db.Text, nullable=True)

class Skater(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    
    group_name = db.Column(db.String(50), nullable=True)

    skater_data = db.Column(db.Text, nullable=False)
    
    # Fields for coach collaboration
    coach_name = db.Column(db.String(150), nullable=True) # New field
    coach_comments = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.String(50), nullable=True)
    assigned_coach_token = db.Column(db.String(100), nullable=True)
    
    comment_status = db.Column(db.String(20), nullable=True)
