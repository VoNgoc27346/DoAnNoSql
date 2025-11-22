from . import get_driver

class Dao:
    @staticmethod
    def _get_session():
        return get_driver().session()

    @staticmethod
    def init_db():
        with Dao._get_session() as session:
            # Hàm phụ: Chạy lệnh tạo constraint và bỏ qua lỗi nếu nó đã tồn tại
            # Cách này an toàn hơn dùng "IF NOT EXISTS" vì tương thích mọi phiên bản Neo4j
            def create_constraint_safe(query):
                try:
                    session.run(query)
                except Exception:
                    pass 

            # Tạo constraints (Bỏ IF NOT EXISTS)
            create_constraint_safe("CREATE CONSTRAINT FOR (t:Teacher) REQUIRE t.teacher_id IS UNIQUE")
            create_constraint_safe("CREATE CONSTRAINT FOR (s:Student) REQUIRE s.student_id IS UNIQUE")
            create_constraint_safe("CREATE CONSTRAINT FOR (c:Course) REQUIRE c.course_id IS UNIQUE")
            create_constraint_safe("CREATE CONSTRAINT FOR (a:Admin) REQUIRE a.username IS UNIQUE")
            
            # Tạo Admin & Dữ liệu mẫu
            session.run("""
                MERGE (a:Admin {username: 'admin'})
                ON CREATE SET a.password = 'admin123', a.name = 'Quản trị viên'
            """)
            session.run("""
                MERGE (:Department {dept_id: 'CNTT', name: 'Công nghệ thông tin'})
                MERGE (:Department {dept_id: 'KT', name: 'Kinh tế'})
            """)
            session.run("""
                MERGE (:Semester {semester_id: 'HK1_2024', year: 2024, term: '1'})
            """)

    @staticmethod
    def verify_user(username, password, role):
        with Dao._get_session() as session:
            if role == 'admin':
                # Đổi $pass thành $password để tránh từ khóa reserved của Python
                query = "MATCH (a:Admin {username: $user, password: $password}) RETURN a"
            else:
                # Đổi $pass thành $password
                query = "MATCH (s:Student {student_id: $user, password: $password}) RETURN s"
            
            # Sửa tham số pass=password thành password=password
            result = session.run(query, user=username, password=password)
            return result.single() is not None

    # --- TEACHER ---
    @staticmethod
    def get_all_teachers():
        with Dao._get_session() as session:
            result = session.run("MATCH (t:Teacher) OPTIONAL MATCH (t)-[:BELONGS_TO]->(d:Department) RETURN t, d.name as dept_name")
            return [{"data": r["t"], "dept": r["dept_name"]} for r in result]

    @staticmethod
    def add_teacher(tid, name, phone, position, dept_id):
        with Dao._get_session() as session:
            session.run("""
                CREATE (t:Teacher {teacher_id: $tid, name: $name, phone: $phone, position: $pos, status: 'Đang giảng dạy'})
                WITH t
                MATCH (d:Department {dept_id: $dept_id})
                MERGE (t)-[:BELONGS_TO]->(d)
            """, tid=tid, name=name, phone=phone, pos=position, dept_id=dept_id)
            
    @staticmethod
    def delete_teacher(tid):
        with Dao._get_session() as session:
            session.run("MATCH (t:Teacher {teacher_id: $tid}) DETACH DELETE t", tid=tid)

    # --- STUDENT ---
    @staticmethod
    def get_all_students():
        with Dao._get_session() as session:
            result = session.run("MATCH (s:Student) OPTIONAL MATCH (s)-[:MAJOR_IN]->(d:Department) RETURN s, d.name as major_name")
            return [{"data": r["s"], "major": r["major_name"]} for r in result]

    @staticmethod
    def add_student(sid, name, phone, _class, year, major_id, password):
        with Dao._get_session() as session:
            session.run("""
                CREATE (s:Student {
                    student_id: $sid, name: $name, phone: $phone, 
                    class: $_class, year: $year, status: 'Đang học',
                    password: $password 
                })
                WITH s
                MATCH (d:Department {dept_id: $major_id})
                MERGE (s)-[:MAJOR_IN]->(d)
            """, sid=sid, name=name, phone=phone, _class=_class, year=year, password=password, major_id=major_id)
            
    @staticmethod
    def delete_student(sid):
        with Dao._get_session() as session:
            session.run("MATCH (s:Student {student_id: $sid}) DETACH DELETE s", sid=sid)

    # --- COURSE ---
    @staticmethod
    def get_all_courses():
        with Dao._get_session() as session:
            result = session.run("MATCH (c:Course) OPTIONAL MATCH (c)-[:BELONGS_TO]->(d:Department) RETURN c, d.name as dept_name")
            return [{"data": r["c"], "dept": r["dept_name"]} for r in result]

    @staticmethod
    def add_course(cid, name, credit, semester_std, dept_id):
        with Dao._get_session() as session:
            session.run("""
                CREATE (c:Course {course_id: $cid, name: $name, credit: $credit, semester: $sem})
                WITH c
                MATCH (d:Department {dept_id: $dept_id})
                MERGE (c)-[:BELONGS_TO]->(d)
            """, cid=cid, name=name, credit=credit, sem=semester_std, dept_id=dept_id)

    # --- CLASS SECTION ---
    @staticmethod
    def create_section(class_id, room, schedule, course_id, teacher_id, semester_id):
        with Dao._get_session() as session:
            session.run("""
                MATCH (c:Course {course_id: $cid})
                MATCH (t:Teacher {teacher_id: $tid})
                MATCH (sem:Semester {semester_id: $sem_id})
                CREATE (cl:Class {class_id: $class_id, room: $room, schedule: $schedule})
                MERGE (c)-[:HAS_CLASS]->(cl)
                MERGE (t)-[:TEACHES]->(cl)
                MERGE (cl)-[:OFFERED_IN]->(sem)
            """, cid=course_id, tid=teacher_id, sem_id=semester_id, class_id=class_id, room=room, schedule=schedule)

    @staticmethod
    def get_data_for_section_form():
        with Dao._get_session() as session:
            teachers = session.run("MATCH (t:Teacher) RETURN t.teacher_id as id, t.name as name")
            courses = session.run("MATCH (c:Course) RETURN c.course_id as id, c.name as name")
            semesters = session.run("MATCH (s:Semester) RETURN s.semester_id as id")
            return {
                "teachers": [{"id": r["id"], "name": r["name"]} for r in teachers],
                "courses": [{"id": r["id"], "name": r["name"]} for r in courses],
                "semesters": [{"id": r["id"]} for r in semesters]
            }