from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
db = SQLAlchemy()

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_admin = db.Column(db.Boolean, default=False)
    username = db.Column(db.String(200), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    age = db.Column(db.Integer, nullable=True)
    interest = db.Column(db.String(200), nullable=True)
    leave_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        role = 'Admin' if self.is_admin else 'User'
        return f'<{role} {str(self.id).zfill(3)} - {self.username}>'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    username = db.Column(db.String(200))
    number = db.Column(db.Integer)
    memo = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    stamp_missing = db.Column(db.Boolean, default=False)