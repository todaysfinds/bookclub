# Flask는 웹 서버, DB 저장, datetime은 날짜 기록용
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, Account, User, Attendance
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

# Flask-Migrate 초기 설정, DB 연결
db.init_app(app)
migrate = Migrate(app, db)

# 테이블 변경 시
# 1) flask db migrate -m "메시지" 2) flask db upgrade

login_manager = LoginManager() # 인스턴트 생성
login_manager.init_app(app) # 애플리케이션에 적용
login_manager.login_view = 'login'  # 로그인 안 했을 때 이동할 기본 페이지


# ---------- 유저 로딩 ---------- #
@login_manager.user_loader
def load_user(account_id):
    return Account.query.get(int(account_id))

# 관리자 계정 한 번만 생성
with app.app_context():
    if not Account.query.filter_by(username='euirim').first():
        a = Account(
            username='euirim',
            password=generate_password_hash('0921', method='scrypt'),
        )
        db.session.add(a)
        db.session.commit()


# ---------- 라우팅 ---------- #
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        acct = Account.query.filter_by(username=request.form['username']).first()
        if acct and check_password_hash(acct.password, request.form['password']):
            login_user(acct)
            return redirect(url_for('index'))
        flash('로그인 실패')
    return render_template('lndex.html')

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

# members 조회 & 수정 폼 렌더링
@app.route('/members', methods=['GET'])
@login_required
def members():
    users = User.query.order_by(User.is_admin.desc(), User.id).all()
    return render_template('members.html', users=users)

# 신규 회원 추가
@app.route('/members/add', methods=['POST'])
@login_required
def add_member():
    username = request.form['username']
    age      = request.form.get('age') or None
    interest = request.form.get('interest') or None
    is_admin = bool(request.form.get('is_admin'))
    u = User(username=username, age=age, interest=interest, is_admin=is_admin)
    db.session.add(u)
    db.session.commit()
    return redirect(url_for('members'))

# 회원 정보 수정
@app.route('/members/edit/<int:user_id>', methods=['POST'])
@login_required
def edit_member(user_id):
    u = User.query.get_or_404(user_id)
    u.username   = request.form['username']
    u.age        = request.form.get('age') or None
    u.interest   = request.form.get('interest') or None
    u.is_admin   = bool(request.form.get('is_admin'))
    db.session.commit()
    return redirect(url_for('members'))

# 회원 삭제
@app.route('/members/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_member(user_id):
    u = User.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()
    return redirect(url_for('members'))


# 디버그 모드 활성화
if __name__ == '__main__':
    app.run(debug=True) # 실행하려면 터미널에 'python app.py'
