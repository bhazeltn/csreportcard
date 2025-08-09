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
    birthdate = db.Column(db.String(20), nullable=True)
    
    generates_pcs_report = db.Column(db.Boolean, default=False)
    generates_cs_report = db.Column(db.Boolean, default=False)

    skater_data = db.Column(db.Text, nullable=False)
    
    coach_name = db.Column(db.String(150), nullable=True)
    coach_comments = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.String(50), nullable=True)
    suggested_recommendation = db.Column(db.String(50), nullable=True)
    suggested_recommendation_reason = db.Column(db.String(255), nullable=True) # New field
    assigned_coach_token = db.Column(db.String(100), nullable=True)
    
    comment_status = db.Column(db.String(20), nullable=True)
