from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file, make_response
from .dao import Dao
import json
import io

main_bp = Blueprint('main', __name__)

# ==========================================
# 1. AUTHENTICATION (ĐĂNG NHẬP/ĐĂNG XUẤT)
# ==========================================
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

# ==========================================
# 2. STUDENT FUNCTIONS (CHỨC NĂNG SINH VIÊN)
# ==========================================
@main_bp.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student': return redirect('/')
    
    sid = session['user']
    info = Dao.get_student_info(sid)
    my_classes = Dao.get_student_enrolled_classes(sid)
    stats = Dao.get_credit_stats(sid)
    
    total_credit = sum(int(c['credit']) for c in my_classes) if my_classes else 0
    
    return render_template('student/dashboard.html', info=info, classes=my_classes, total_credit=total_credit, stats=stats)

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

@main_bp.route('/student/search', methods=['GET', 'POST'])
def student_search():
    if session.get('role') != 'student': return redirect('/')
    results = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '')
        if keyword:
            results = Dao.search_graph(keyword)
    return render_template('student/search.html', results=results, keyword=keyword)

@main_bp.route('/student/classmates')
def student_classmates():
    if session.get('role') != 'student': return redirect('/')
    classmates = Dao.get_classmates(session['user'])
    return render_template('student/classmates.html', classmates=classmates)

# ==========================================
# 3. ADMIN FUNCTIONS (QUẢN TRỊ VIÊN)
# ==========================================

# --- Quản lý Giảng viên ---
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

# --- Quản lý Sinh viên ---
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

# --- Quản lý Môn học ---
@main_bp.route('/admin/courses', methods=['GET', 'POST'])
def admin_courses():
    if session.get('role') != 'admin': return redirect('/')
    if request.method == 'POST':
        Dao.add_course(request.form['id'], request.form['name'], int(request.form['credit']), 
                       request.form['sem'], request.form['dept'])
        flash("Đã thêm môn học!")
    courses = Dao.get_all_courses()
    return render_template('admin/courses.html', courses=courses, title="Quản lý Môn học")

# --- Quản lý Lớp Học Phần ---
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

# --- Routes Edit Teacher ---
@main_bp.route('/admin/teachers/edit/<tid>', methods=['GET', 'POST'])
def edit_teacher(tid):
    if session.get('role') != 'admin': return redirect('/')
    
    teacher = Dao.get_teacher_by_id(tid)
    if not teacher:
        flash("Không tìm thấy giảng viên!")
        return redirect(url_for('main.admin_teachers'))

    if request.method == 'POST':
        Dao.update_teacher(tid, request.form['name'], request.form['phone'], 
                           request.form['position'], request.form['dept'])
        flash(f"Đã cập nhật thông tin giảng viên {tid}!")
        return redirect(url_for('main.admin_teachers'))
    
    return render_template('admin/edit_teacher.html', t=teacher)

# --- Routes Edit Student ---
@main_bp.route('/admin/students/edit/<sid>', methods=['GET', 'POST'])
def edit_student(sid):
    if session.get('role') != 'admin': return redirect('/')
    
    student = Dao.get_student_by_id(sid)
    if not student:
        flash("Không tìm thấy sinh viên!")
        return redirect(url_for('main.admin_students'))

    if request.method == 'POST':
        Dao.update_student(sid, request.form['name'], request.form['phone'],
                           request.form['class'], int(request.form['year']), 
                           request.form['dept'], request.form['password'])
        flash(f"Đã cập nhật thông tin sinh viên {sid}!")
        return redirect(url_for('main.admin_students'))
        
    return render_template('admin/edit_student.html', s=student)

# --- Routes Edit Course ---
@main_bp.route('/admin/courses/edit/<cid>', methods=['GET', 'POST'])
def edit_course(cid):
    if session.get('role') != 'admin': return redirect('/')
    
    course = Dao.get_course_by_id(cid)
    if not course:
        flash("Không tìm thấy môn học!")
        return redirect(url_for('main.admin_courses'))

    if request.method == 'POST':
        Dao.update_course(cid, request.form['name'], int(request.form['credit']), 
                          request.form['sem'], request.form['dept'])
        flash(f"Đã cập nhật môn học {cid}!")
        return redirect(url_for('main.admin_courses'))
        
    return render_template('admin/edit_course.html', c=course)

# --- Route Xóa Môn học ---
@main_bp.route('/admin/courses/delete/<cid>')
def delete_course_route(cid):
    if session.get('role') != 'admin': return redirect('/')
    Dao.delete_course(cid)
    flash(f"Đã xóa môn học {cid}!")
    return redirect(url_for('main.admin_courses'))

# --- Quản lý Điểm (Grading) ---
@main_bp.route('/admin/grading', methods=['GET', 'POST'])
def admin_grading():
    if session.get('role') != 'admin': return redirect('/')
    
    selected_class = request.args.get('class_id')
    roster = []
    
    if request.method == 'POST':
        class_id = request.form.get('class_id')
        student_id = request.form.get('student_id')
        score = request.form.get('score')
        Dao.update_grade(class_id, student_id, score)
        flash("Đã cập nhật điểm!")
        return redirect(url_for('main.admin_grading', class_id=class_id))
        
    if selected_class:
        roster = Dao.get_class_roster(selected_class)
    
    return render_template('admin/grading.html', roster=roster, selected_class=selected_class)

# ==========================================
# 4. HỖ TRỢ & HỆ THỐNG (VISUALIZATION, STATS, IO)
# ==========================================

# --- Trực quan hóa (Visualization) ---
@main_bp.route('/admin/visualization')
def admin_visualization():
    if session.get('role') != 'admin': return redirect('/')
    return render_template('admin/visualization.html', title="Trực quan hóa Đồ thị")

@main_bp.route('/api/graph-data')
def api_graph_data():
    """API trả về JSON cho Javascript vẽ (Đây là route bị lỗi trước đó)"""
    if session.get('role') != 'admin': return jsonify({})
    try:
        data = Dao.get_graph_data_json()
        return jsonify(data)
    except Exception as e:
        print(f"Lỗi API Visualization: {e}")
        return jsonify({"nodes": [], "edges": [], "error": str(e)})

# --- Thống kê (Stats) ---
@main_bp.route('/admin/stats')
def admin_stats():
    if session.get('role') != 'admin': return redirect('/')
    data = Dao.get_system_stats()
    return render_template('admin/stats.html', stats=data, title="Thống kê hệ thống")

# --- Import / Export Data ---
@main_bp.route('/admin/data-io')
def admin_data_io():
    if session.get('role') != 'admin': return redirect('/')
    return render_template('admin/data_io.html', title="Nhập/Xuất Dữ liệu")

@main_bp.route('/admin/export-json')
def admin_export_json():
    if session.get('role') != 'admin': return redirect('/')
    
    data = Dao.export_full_data()
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    mem = io.BytesIO()
    mem.write(json_str.encode('utf-8'))
    mem.seek(0)
    
    return send_file(
        mem, 
        as_attachment=True, 
        download_name='university_data.json', 
        mimetype='application/json'
    )

@main_bp.route('/admin/import-json', methods=['POST'])
def admin_import_json():
    if session.get('role') != 'admin': return redirect('/')
    
    if 'file' not in request.files:
        flash("Chưa chọn file!")
        return redirect(url_for('main.admin_data_io'))
        
    file = request.files['file']
    if file.filename == '':
        flash("Tên file không hợp lệ")
        return redirect(url_for('main.admin_data_io'))

    if file:
        try:
            data = json.load(file)
            Dao.import_from_json(data)
            flash("✅ Import dữ liệu thành công!")
        except Exception as e:
            flash(f"❌ Lỗi Import: {str(e)}")
            
    return redirect(url_for('main.admin_data_io'))