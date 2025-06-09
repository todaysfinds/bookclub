# Flask는 웹 서버, DB 저장, datetime은 날짜 기록용
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, Account, User, Attendance, MeetingDay
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
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
app.secret_key = os.environ.get('SECRET_KEY', 'todaysfinds0921')

# 데이터베이스 연결 설정
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # PostgreSQL URL 수정 (Render에서 필요)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # 로컬 개발용 SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookclub.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy, Migrate, LoginManager 초기화
db.init_app(app)
migrate = Migrate(app, db)

# 테이블 변경 시
# 1) flask db migrate -m "메시지" 2) flask db upgrade

# 로그인 매니저 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ---------- 유저 로딩 ---------- #
@login_manager.user_loader
def load_user(account_id):
    return Account.query.get(int(account_id))

# 관리자 계정 생성 부분에 예외 처리 추가
try:
    with app.app_context():
        if not Account.query.filter_by(username='euirim').first():
            admin = Account(
                username='euirim',
                password=generate_password_hash('0921', method='scrypt'),
            )
            db.session.add(admin)
            db.session.commit()
except Exception:
    # 마이그레이션이나 다른 CLI 커맨드를 실행할 때
    # DB 연결 오류가 발생하면 그냥 넘어가도록 처리
    pass


# ---------- 라우팅 ---------- #

@app.route('/')
def home():
    """
    로그인 여부와 관계없이 출석 페이지를 보여줍니다.
    다만, 출석 "저장" API는 POST 시에만 인증을 요구합니다.
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
    join_date_str = request.form.get('join_date') or None
    is_admin = bool(request.form.get('is_admin'))
    
    # 가입일 파싱
    join_date = None
    if join_date_str:
        try:
            join_date = datetime.strptime(join_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('올바른 날짜 형식이 아닙니다.')
            return redirect(url_for('member.members'))
    
    if username:
        exists = User.query.filter_by(username=username).first()
        if not exists:
            new_user = User(
                username=username,
                age=int(age) if age else None,
                join_date=join_date,
                is_admin=is_admin
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'{username}님이 추가되었습니다.')
        else:
            flash('이미 등록된 회원 이름입니다.')
    else:
        flash('이름을 입력해주세요.')
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

    # 폼 필드 이름과 맞춰서 가져옵니다.
    new_username = request.form['username'].strip()
    new_age = request.form.get('age') or None
    join_date_str = request.form.get('join_date') or None
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

    # 3) 가입일 파싱
    new_join_date = None
    if join_date_str:
        try:
            new_join_date = datetime.strptime(join_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('올바른 날짜 형식이 아닙니다.')
            return redirect(url_for('member.edit_member_form', user_id=u.id))

    # 4) 모든 값이 유효하면, 실제로 DB 레코드를 업데이트
    u.username = new_username
    u.age = int(new_age) if new_age else None
    u.join_date = new_join_date
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


# 기록 페이지 제거됨 (사용하지 않음)
# @app.route('/books')
# def books():
#     """
#     지정도서 히스토리 페이지: 로그인 없이 모두에게 공개합니다.
#     """
#     past_books = [
#         {'title': '표백', 'author': '장강명'},
#         {'title': '법의학자 유성호의 유언노트', 'author': '유성호'},
#         # 필요하면 DB로 확장 가능
#     ]
#     return render_template('books.html', books=past_books)


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

@app.route('/save_attendance', methods=['POST'])
@login_required
def save_single_attendance():
    """
    개별 출석 저장: 출석 완료 시에만 호출됨
    JSON 형식: { "name": "...", "status": "...", "time": "...", "absence_reason": "..." }
    """
    data = request.get_json()
    name = data.get('name')
    status = data.get('status')
    timestamp_str = data.get('time')
    absence_reason = data.get('absence_reason', '')
    
    if not (name and status and timestamp_str):
        return jsonify({'status': 'error', 'message': '필수 정보가 누락되었습니다.'}), 400
    
    user = User.query.filter_by(username=name).first()
    if not user:
        return jsonify({'status': 'error', 'message': '사용자를 찾을 수 없습니다.'}), 404
    
    try:
        from datetime import datetime as dt
        today = date.today()
        timestamp = dt.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # 오늘 날짜의 기존 기록이 있으면 삭제 후 새로 생성 (덮어쓰기 방지)
        existing_records = Attendance.query.filter_by(user_id=user.id, date=today).all()
        for record in existing_records:
            db.session.delete(record)
        
        # 새 기록 생성
        record = Attendance(
            user_id=user.id,
            date=today,
            status=status,
            timestamp=timestamp,
            absence_reason=absence_reason if status == 'absent' else None
        )
        db.session.add(record)
        
        db.session.commit()
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ───────────────────────────────────────────────────
# 템플릿 헬퍼 함수들
# ───────────────────────────────────────────────────
@app.template_global()
def get_attendance_count(user_id, status):
    """사용자의 특정 상태 출석 횟수를 반환"""
    count = Attendance.query.filter_by(user_id=user_id, status=status).count()
    return count

@app.template_global()
def get_total_attendance_count(user_id):
    """사용자의 총 참석 횟수를 반환 (출석 + 지각)"""
    attended = Attendance.query.filter_by(user_id=user_id, status='attended').count()
    late = Attendance.query.filter_by(user_id=user_id, status='late').count()
    return attended + late

# ───────────────────────────────────────────────────
# API 엔드포인트들
# ───────────────────────────────────────────────────

@app.route('/api/update_user_field', methods=['POST'])
@login_required
def update_user_field():
    """인라인 수정을 위한 API"""
    data = request.get_json()
    user_id = data.get('user_id')
    field = data.get('field')
    value = data.get('value')
    
    if not user_id or not field:
        return jsonify({'status': 'error', 'message': '필수 정보가 누락되었습니다.'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': '사용자를 찾을 수 없습니다.'}), 404
    
    try:
        if field == 'username':
            if not value or not value.strip():
                return jsonify({'status': 'error', 'message': '이름은 필수입니다.'}), 400
            # 중복 체크
            existing = User.query.filter_by(username=value.strip()).first()
            if existing and existing.id != user.id:
                return jsonify({'status': 'error', 'message': '이미 사용 중인 이름입니다.'}), 400
            user.username = value.strip()
        elif field == 'age':
            user.age = int(value) if value else None
        elif field == 'join_date':
            if value:
                user.join_date = datetime.strptime(value, '%Y-%m-%d').date()
            else:
                user.join_date = None
        else:
            return jsonify({'status': 'error', 'message': '잘못된 필드입니다.'}), 400
        
        db.session.commit()
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/toggle_admin', methods=['POST'])
@login_required
def toggle_admin():
    """운영진 상태 토글 API"""
    data = request.get_json()
    user_id = data.get('user_id')
    is_admin = data.get('is_admin')
    
    if not user_id:
        return jsonify({'status': 'error', 'message': '사용자 ID가 필요합니다.'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': '사용자를 찾을 수 없습니다.'}), 404
    
    try:
        user.is_admin = is_admin
        db.session.commit()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/delete_user', methods=['POST'])
@login_required
def delete_user():
    """사용자 삭제 API"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'status': 'error', 'message': '사용자 ID가 필요합니다.'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': '사용자를 찾을 수 없습니다.'}), 404
    
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get_absence_memos/<int:user_id>')
@login_required
def get_absence_memos(user_id):
    """사용자의 결석 메모 조회 API"""
    try:
        # 결석 기록만 조회
        absences = Attendance.query.filter_by(
            user_id=user_id, 
            status='absent'
        ).order_by(Attendance.date.desc()).all()
        
        memos = []
        for absence in absences:
            memo = {
                'id': absence.id,
                'date': absence.date.strftime('%Y-%m-%d'),
                'reason': absence.absence_reason or ''
            }
            memos.append(memo)
        
        return jsonify({'status': 'ok', 'memos': memos}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/delete_memo', methods=['POST'])
@login_required
def delete_memo():
    """결석 메모 삭제 API"""
    data = request.get_json()
    memo_id = data.get('memo_id')
    
    if not memo_id:
        return jsonify({'status': 'error', 'message': 'memo_id가 필요합니다.'}), 400
    
    attendance = Attendance.query.get(memo_id)
    if not attendance:
        return jsonify({'status': 'error', 'message': '기록을 찾을 수 없습니다.'}), 404
    
    try:
        db.session.delete(attendance)
        db.session.commit()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get_user_attendance/<int:user_id>')
@login_required
def get_user_attendance(user_id):
    """특정 사용자의 실시간 출석 데이터 반환"""
    try:
        attended = get_attendance_count(user_id, 'attended')
        late = get_attendance_count(user_id, 'late')
        absent = get_attendance_count(user_id, 'absent')
        total_attended = get_total_attendance_count(user_id)
        
        return jsonify({
            'status': 'ok',
            'attended': attended,
            'late': late,
            'absent': absent,
            'total_attended': total_attended
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get_attendance_count/<username>')
def get_attendance_count_by_name(username):
    """사용자 이름으로 출석 횟수 조회 (로그인 불필요)"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'status': 'error', 'message': '사용자를 찾을 수 없습니다.'}), 404
        
        attended = get_attendance_count(user.id, 'attended')
        late = get_attendance_count(user.id, 'late')
        total = attended + late
        
        return jsonify({
            'status': 'ok',
            'total_attended': total,
            'attended': attended,
            'late': late
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/save_all_attendance', methods=['POST'])
@login_required
def save_all_attendance():
    """모든 출석 기록을 한 번에 저장"""
    try:
        data = request.get_json()
        attendees = data.get('attendees', [])
        today = date.today()
        
        if not attendees:
            return jsonify({'status': 'error', 'message': '출석 데이터가 없습니다.'}), 400
        
        # 오늘 날짜의 모든 기존 출석 기록 삭제 (중복 방지)
        existing_records = Attendance.query.filter_by(date=today).all()
        for record in existing_records:
            db.session.delete(record)
        
        # 새로운 출석 기록들 저장
        from datetime import datetime as dt
        for att in attendees:
            name = att.get('name')
            status = att.get('status')
            timestamp_str = att.get('time')
            absence_reason = att.get('absenceReason', '')
            
            if not (name and status and timestamp_str):
                continue
                
            user = User.query.filter_by(username=name).first()
            if not user:
                continue
                
            timestamp = dt.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            record = Attendance(
                user_id=user.id,
                date=today,
                status=status,
                timestamp=timestamp,
                absence_reason=absence_reason if status == 'absent' else None
            )
            db.session.add(record)
        
        db.session.commit()
        return jsonify({'status': 'ok', 'message': '모든 출석 기록이 저장되었습니다.'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/complete_meeting', methods=['POST'])
@login_required
def complete_meeting():
    """출석 완료 - 오늘을 모임일로 등록"""
    try:
        today = date.today()
        
        # 이미 등록된 모임일인지 확인
        existing_meeting = MeetingDay.query.filter_by(date=today).first()
        if not existing_meeting:
            # 새로운 모임일 등록
            meeting_day = MeetingDay(
                date=today,
                description=f"{today.strftime('%Y년 %m월 %d일')} 모임"
            )
            db.session.add(meeting_day)
            db.session.commit()
        
        return jsonify({'status': 'ok', 'message': '모임이 완료되었습니다.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/clear_today_attendance', methods=['POST', 'GET'])
@login_required
def clear_today_attendance():
    """오늘 출석 기록 모두 삭제 (테스트용)"""
    try:
        today = date.today()
        
        # 오늘 날짜의 모든 출석 기록 삭제
        deleted_count = Attendance.query.filter_by(date=today).delete()
        
        # 오늘 모임일도 삭제
        MeetingDay.query.filter_by(date=today).delete()
        
        db.session.commit()
        return jsonify({
            'status': 'ok', 
            'message': f'오늘 출석 기록 {deleted_count}개가 삭제되었습니다.'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 소개 페이지 제거됨 (사용하지 않음)
# @app.route('/about')
# def about():
#     return render_template('about.html')

# ── Blueprint를 앱에 등록 ──
app.register_blueprint(bp)

# 디버그 모드 활성화
if __name__ == '__main__':
    app.run(debug=True) # 실행하려면 터미널에 'python app.py'
