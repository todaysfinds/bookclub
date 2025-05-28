# Flask는 웹 서버, DB 저장, datetime은 날짜 기록용
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import User
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv
import pymysql
pymysql.install_as_MySQLdb()

load_dotenv()

# Flask 앱 만들기 (웹앱의 본체)
app = Flask(__name__)
app.secret_key = 'todaysfinds0921'
# DB 연결 설정 - MySQL 관련 설정
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('MYSQL_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app) # db 객체 생성

# Flask-Migrate 초기 설정
migrate = Migrate(app, db)

# 테이블 변경 시 1) flask db migrate -m "메시지" 2) flask db upgrade

login_manager = LoginManager() # 인스턴트 생성
login_manager.init_app(app) # 애플리케이션에 적용
login_manager.login_view = 'login'  # 로그인 안 했을 때 이동할 기본 페이지



# ---------- 모델 ---------- # -> models.py에 똑같이
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_admin = db.Column(db.Boolean, default=False)
    username = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# ---------- 유저 로딩 ---------- #
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 모델 기반 테이블 실제 DB에 생성 + 관리자 계정 생성
with app.app_context():
    # db.create_all()
    # 관리자 계정 생성 + 같은 유저 건너뛰기
    if not User.query.filter_by(username='euirim').first():
        admin = User(
            username='euirim',
            password=generate_password_hash('0921', method='scrypt'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()


# ---------- 라우팅 ---------- #

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        pw = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, pw):
            login_user(user)
            return redirect(url_for('index'))
        flash('로그인 실패')
    return render_template('login.html')

@app.route('/index')
@login_required
def index():
    return render_template('index.html', username=current_user.username)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/check')
def check():
    user = User.query.filter_by(username='euirim').first()
    return '존재함' if user else '없음'

@app.route('/members')
@login_required
def member_list():
    users = User.query.order_by(User.is_admin.desc(), User.username.asc()).all()
    return render_template('members.html', users=users)



# 디버그 모드 활성화
if __name__ == '__main__':
    app.run(debug=True) # 실행하려면 터미널에 'python app.py'
