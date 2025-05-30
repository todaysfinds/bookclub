from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
db = SQLAlchemy()

class Account(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    def __repr__(self):
        return f'<Account {self.username}>'

class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(200), nullable=False)
    join_date  = db.Column(db.DateTime, default=datetime.utcnow)
    age        = db.Column(db.Integer, nullable=True)
    interest   = db.Column(db.String(200), nullable=True)
    leave_date = db.Column(db.DateTime, nullable=True)
    is_admin   = db.Column(db.Boolean, default=False)  # 운영진 표시용
    def __repr__(self):
        return f'<User {str(self.id).zfill(3)} - {self.username}>'

class Attendance(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username      = db.Column(db.String(200))   # 백업용
    number        = db.Column(db.Integer)       # 복사된 user.id
    memo          = db.Column(db.Text, nullable=True)
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow)
    stamp_missing = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f'<Attend {self.id} by {self.username}>'