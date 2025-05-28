from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_admin = db.Column(db.Boolean, default=False)
    username = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
