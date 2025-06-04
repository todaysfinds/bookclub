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
import pymysql

pymysql.install_as_MySQLdb()

# .env 파일에서 MYSQL_URL을 읽어옵니다.
from dotenv import load_dotenv
load_dotenv()

# Blueprint 생성 ──
from flask import Blueprint
bp = Blueprint('member', __name__)  # 'member'라는 이름으로 Blueprint 선언

app = Flask(__name__)
app.secret_key = 'todaysfinds0921'

# MySQL 연결 설정 (환경 변수로부터 불러옵니다)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy, Migrate, LoginManager 초기화
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
        admin = Account(
            username='euirim',
            password=generate_password_hash('0921', method='scrypt'),
        )
        db.session.add(admin)
        db.session.commit()


# ---------- 라우팅 ---------- #

@app.route('/')
def home():
    """
    로그인 여부와 관계없이 출석 페이지를 보여줍니다.
    다만, 출석 “저장” API는 POST 시에만 인증을 요구합니다.
    """
    # Member 목록만 조회해서 넘겨줍니다.
    member_names = [u.username for u in User.query.order_by(User.username).all()]
    return render_template('index.html', all_members=member_names)

# 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        acct = Account.query.filter_by(username=request.form['username']).first()
        if acct and check_password_hash(acct.password, request.form['password']):
            login_user(acct)
            return redirect(url_for('home'))
        flash('로그인 정보가 일치하지 않습니다.')
    return render_template('login.html')

# 로그아웃
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/index')
def index_redirect():
    return redirect(url_for('home'))

# ───────────────────────────────────────────────────
#  회원 관리 페이지: 조회 (GET)
#  (/members 라우트는 기존과 동일)
# ───────────────────────────────────────────────────
@bp.route('/members', methods=['GET'])
def members():
    # 1) 운영진만 뽑아서 id(숫자) 순서로 정렬
    admins = User.query.filter_by(is_admin=True).order_by(User.id).all()
    # 2) 일반 회원만 뽑아서 username(이름) 순서로 정렬
    others = User.query.filter_by(is_admin=False).order_by(User.username).all()
    # 3) 두 리스트를 합치면, 운영진이 위에(숫자 순), 일반 회원이 아래(이름 순)
    users = admins + others
    
    summary = []
    for u in users:
        # 정상 출석(attended 또는 late) 횟수 집계
        normal = sum(1 for a in u.attendances if a.status in ('attended', 'late'))
        # 도장 누락(stamp_missing=True) 횟수 집계
        missed = sum(1 for a in u.attendances if a.stamp_missing)
        summary.append({
            'user': u,
            'attended_count': normal,
            'missed_count': missed
        })

    return render_template('members.html', data=summary, users=users)

# ───────────────────────────────────────────────────
# 신규 회원 추가 (POST)
# ───────────────────────────────────────────────────
@bp.route('/members/add', methods=['POST'])
@login_required
def add_member():
    username = request.form['username'].strip()
    age      = request.form.get('age') or None
    interest = request.form.get('interest') or None
    is_admin = bool(request.form.get('is_admin'))
    if username:
        exists = User.query.filter_by(username=username).first()
        if not exists:
            new_user = User(
                username=username,
                age=age,
                interest=interest,
                is_admin=is_admin
            )
            db.session.add(new_user)
            db.session.commit()
        else:
            flash('이미 등록된 회원 이름입니다.')
    return redirect(url_for('member.members'))


# ───────────────────────────────────────────────────
# 회원 수정 폼 보여주기 (GET)
# ───────────────────────────────────────────────────
@bp.route('/members/edit/<int:user_id>', methods=['GET'])
@login_required
def edit_member_form(user_id):
    # 운영진만 회원 정보를 수정할 수 있도록 제한
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    u = User.query.get_or_404(user_id)
    return render_template('members_edit.html', u=u)

# ───────────────────────────────────────────────────
# 회원 정보 실제 수정 처리 (POST)
# ───────────────────────────────────────────────────
@bp.route('/members/edit/<int:user_id>', methods=['POST'])
@login_required
def edit_member(user_id):
    # 운영진만 수정 가능
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    u = User.query.get_or_404(user_id)

    # 폼 필드 이름(member_edit.html에 정의된 name 속성)과 맞춰서 가져옵니다.
    new_username = request.form['username'].strip()
    new_age      = request.form.get('age') or None
    new_interest = request.form.get('interest') or None
    new_is_admin = True if request.form.get('is_admin') == 'on' else False

    # 1) 새 이름이 유효한지 (빈 문자열이 아닌지)
    if not new_username:
        flash('이름을 입력해주세요.')
        return redirect(url_for('member.edit_member_form', user_id=u.id))

    # 2) 새 이름이 이미 다른 회원에 사용 중인지 확인 (중복 검사)
    exists = User.query.filter_by(username=new_username).first()
    if exists and exists.id != u.id:
        flash('이미 존재하는 이름입니다.')
        return redirect(url_for('member.edit_member_form', user_id=u.id))

    # 3) 모든 값이 유효하면, 실제로 DB 레코드를 업데이트
    u.username = new_username
    u.age      = new_age
    u.interest = new_interest
    u.is_admin = new_is_admin

    db.session.commit()
    flash('회원 정보가 수정되었습니다.')
    return redirect(url_for('member.members'))

# ───────────────────────────────────────────────────
# 회원 삭제: POST 요청은 로그인된 운영진만 가능
# ───────────────────────────────────────────────────
@bp.route('/members/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_member(user_id):
    u = User.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()
    return redirect(url_for('member.members'))


@app.route('/books')
def books():
    """
    지정도서 히스토리 페이지: 로그인 없이 모두에게 공개합니다.
    """
    past_books = [
        {'title': '표백', 'author': '장강명'},
        {'title': '법의학자 유성호의 유언노트', 'author': '유성호'},
        # 필요하면 DB로 확장 가능
    ]
    return render_template('books.html', books=past_books)


@app.route('/api/save_attendance', methods=['POST'])
@login_required
def save_attendance():
    """
    출석 명단 저장: POST 요청은 로그인된 운영진만 가능.
    JSON 형식: { "attendees": [ { "name": "...", "status": "...", "time": "..." }, ... ] }
    """
    data = request.get_json()
    attendees = data.get('attendees', [])
    today = date.today()

    # 오늘자 기존 출석 레코드 삭제
    Attendance.query.filter_by(date=today).delete()
    db.session.commit()

    from datetime import datetime as dt
    for att in attendees:
        name = att.get('name')
        status = att.get('status')
        timestamp_str = att.get('time')
        if not (name and status and timestamp_str):
            continue
        user = User.query.filter_by(username=name).first()
        if not user:
            continue
        timestamp = dt.fromisoformat(timestamp_str)
        record = Attendance(
            user_id=user.id,
            date=today,
            status=status,
            timestamp=timestamp,
            stamp_missing=(status == 'missed')
        )
        db.session.add(record)

    db.session.commit()
    return jsonify({'status': 'ok'}), 200

@app.route('/about')
def about():
    return render_template('about.html')

# ── Blueprint를 앱에 등록 ──
app.register_blueprint(bp)

# 디버그 모드 활성화
if __name__ == '__main__':
    app.run(debug=True) # 실행하려면 터미널에 'python app.py'
