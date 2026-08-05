from database import db
import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    conversions = db.relationship('ConversionLog', backref='user', lazy=True)

class ConversionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    file_type = db.Column(db.String(20), nullable=False)
    conversion_type = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
