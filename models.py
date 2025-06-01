from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date

db = SQLAlchemy()

class Account(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    def __repr__(self):
        return f'<Account {self.username}>'

class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(200), unique=True, nullable=False)
    join_date  = db.Column(db.DateTime, default=datetime.utcnow)
    age        = db.Column(db.Integer, nullable=True)
    interest   = db.Column(db.String(200), nullable=True)
    # User 1명 ↔ Attendance 여러 개 (백엔드에서 join)
    attendances = db.relationship(
        'Attendance',
        backref='user',
        cascade='all, delete-orphan'
    )
    is_admin   = db.Column(db.Boolean, default=False)  # 운영진 표시용
    
    def __repr__(self):
        return f'<User {str(self.id).zfill(3)} - {self.username}>'

class Attendance(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date          = db.Column(db.Date, default=date.today, nullable=False)
    status        = db.Column(db.String(20), nullable=False)  # 'attended' 또는 'late'
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow)
    stamp_missing = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f'<Attendance {self.user.name} {self.date} {self.status}>'