from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .dao import Dao

main_bp = Blueprint('main', __name__)

# --- AUTH ---
@main_bp.route('/')
def index():
    if 'user' in session:
        if session['role'] == 'admin':
            return redirect(url_for('main.admin_teachers'))
        elif session['role'] == 'student':
            return redirect(url_for('main.student_dashboard'))
    return render_template('login.html')

@main_bp.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    
    if Dao.verify_user(username, password, role):
        session['user'] = username
        session['role'] = role
        return redirect(url_for('main.index'))
    else:
        flash("Sai tên đăng nhập hoặc mật khẩu!")
        return redirect(url_for('main.index'))

@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

# --- STUDENT ROUTES (NEW) ---
@main_bp.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student': return redirect('/')
    
    sid = session['user']
    info = Dao.get_student_info(sid)
    my_classes = Dao.get_student_enrolled_classes(sid)
    
    # Tính tổng tín chỉ đã đăng ký
    total_credit = sum(c['credit'] for c in my_classes) if my_classes else 0
    
    return render_template('student/dashboard.html', info=info, classes=my_classes, total_credit=total_credit)

@main_bp.route('/student/register', methods=['GET'])
def student_register_view():
    if session.get('role') != 'student': return redirect('/')
    
    sid = session['user']
    available_classes = Dao.get_available_classes_for_registration(sid)
    
    return render_template('student/register.html', classes=available_classes)

@main_bp.route('/student/enroll/<class_id>')
def student_enroll(class_id):
    if session.get('role') != 'student': return redirect('/')
    
    Dao.enroll_class(session['user'], class_id)
    flash(f"Đăng ký thành công lớp {class_id}")
    return redirect(url_for('main.student_register_view'))

@main_bp.route('/student/unenroll/<class_id>')
def student_unenroll(class_id):
    if session.get('role') != 'student': return redirect('/')
    
    Dao.unenroll_class(session['user'], class_id)
    flash(f"Đã hủy đăng ký lớp {class_id}")
    return redirect(url_for('main.student_dashboard'))

# --- ADMIN ROUTES ---
@main_bp.route('/admin/teachers', methods=['GET', 'POST'])
def admin_teachers():
    if session.get('role') != 'admin': return redirect('/')
    if request.method == 'POST':
        Dao.add_teacher(request.form['id'], request.form['name'], request.form['phone'], 
                        request.form['position'], request.form['dept'])
        flash("Đã thêm giảng viên!")
    teachers = Dao.get_all_teachers()
    return render_template('admin/teachers.html', teachers=teachers, title="Quản lý Giảng viên")

@main_bp.route('/admin/teachers/delete/<tid>')
def delete_teacher_route(tid):
    Dao.delete_teacher(tid)
    return redirect(url_for('main.admin_teachers'))

@main_bp.route('/admin/students', methods=['GET', 'POST'])
def admin_students():
    if session.get('role') != 'admin': return redirect('/')
    if request.method == 'POST':
        Dao.add_student(request.form['id'], request.form['name'], request.form['phone'],
                        request.form['class'], int(request.form['year']), request.form['dept'],
                        request.form['password'])
        flash(f"Đã thêm sinh viên (Pass: {request.form['password']})")
    students = Dao.get_all_students()
    return render_template('admin/students.html', students=students, title="Quản lý Sinh viên")

@main_bp.route('/admin/students/delete/<sid>')
def delete_student_route(sid):
    Dao.delete_student(sid)
    return redirect(url_for('main.admin_students'))

@main_bp.route('/admin/courses', methods=['GET', 'POST'])
def admin_courses():
    if session.get('role') != 'admin': return redirect('/')
    if request.method == 'POST':
        Dao.add_course(request.form['id'], request.form['name'], int(request.form['credit']), 
                       request.form['sem'], request.form['dept'])
        flash("Đã thêm môn học!")
    courses = Dao.get_all_courses()
    return render_template('admin/courses.html', courses=courses, title="Quản lý Môn học")

@main_bp.route('/admin/classes', methods=['GET', 'POST'])
def admin_classes():
    if session.get('role') != 'admin': return redirect('/')
    if request.method == 'POST':
        class_id = f"{request.form['course']}_{request.form['sem']}_01"
        Dao.create_section(class_id, request.form['room'], request.form['schedule'],
                           request.form['course'], request.form['teacher'], request.form['sem'])
        flash(f"Đã tạo lớp học phần: {class_id}")
    data = Dao.get_data_for_section_form()
    return render_template('admin/classes.html', data=data, title="Tạo Lớp Học Phần")