from . import get_driver

class Dao:
    @staticmethod
    def _get_session():
        return get_driver().session()

    @staticmethod
    def init_db():
        with Dao._get_session() as session:
            def create_constraint_safe(query):
                try:
                    session.run(query)
                except Exception:
                    pass 

            create_constraint_safe("CREATE CONSTRAINT FOR (t:Teacher) REQUIRE t.teacher_id IS UNIQUE")
            create_constraint_safe("CREATE CONSTRAINT FOR (s:Student) REQUIRE s.student_id IS UNIQUE")
            create_constraint_safe("CREATE CONSTRAINT FOR (c:Course) REQUIRE c.course_id IS UNIQUE")
            create_constraint_safe("CREATE CONSTRAINT FOR (a:Admin) REQUIRE a.username IS UNIQUE")
            
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
                query = "MATCH (a:Admin {username: $user, password: $password}) RETURN a"
            else:
                query = "MATCH (s:Student {student_id: $user, password: $password}) RETURN s"
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

    # --- STUDENT PORTAL FUNCTIONS (NEW) ---
    @staticmethod
    def get_student_info(sid):
        """Lấy thông tin cá nhân sinh viên"""
        with Dao._get_session() as session:
            query = """
            MATCH (s:Student {student_id: $sid})
            OPTIONAL MATCH (s)-[:MAJOR_IN]->(d:Department)
            RETURN s, d.name as major
            """
            result = session.run(query, sid=sid).single()
            if result:
                return {"data": result["s"], "major": result["major"]}
            return None

    @staticmethod
    def get_student_enrolled_classes(sid):
        """Lấy danh sách lớp đã đăng ký (TKB)"""
        with Dao._get_session() as session:
            query = """
            MATCH (s:Student {student_id: $sid})-[:ENROLLED_IN]->(cl:Class)
            MATCH (cl)<-[:HAS_CLASS]-(c:Course)
            MATCH (cl)<-[:TEACHES]-(t:Teacher)
            RETURN cl, c.name as course_name, c.credit as credit, t.name as teacher_name
            ORDER BY cl.class_id
            """
            result = session.run(query, sid=sid)
            return [{
                "class_id": r["cl"]["class_id"],
                "room": r["cl"]["room"],
                "schedule": r["cl"]["schedule"],
                "course_name": r["course_name"],
                "credit": r["credit"],
                "teacher_name": r["teacher_name"]
            } for r in result]

    @staticmethod
    def get_available_classes_for_registration(sid):
        """Lấy danh sách các lớp MỞ mà sinh viên CHƯA đăng ký"""
        with Dao._get_session() as session:
            query = """
            MATCH (cl:Class)
            MATCH (cl)<-[:HAS_CLASS]-(c:Course)
            MATCH (cl)<-[:TEACHES]-(t:Teacher)
            WHERE NOT EXISTS {
                MATCH (s:Student {student_id: $sid})-[:ENROLLED_IN]->(cl)
            }
            RETURN cl, c.name as course_name, c.credit as credit, t.name as teacher_name
            ORDER BY cl.class_id
            """
            result = session.run(query, sid=sid)
            return [{
                "class_id": r["cl"]["class_id"],
                "room": r["cl"]["room"],
                "schedule": r["cl"]["schedule"],
                "course_name": r["course_name"],
                "credit": r["credit"],
                "teacher_name": r["teacher_name"]
            } for r in result]

    @staticmethod
    def enroll_class(sid, class_id):
        """Sinh viên đăng ký lớp (Tạo quan hệ ENROLLED_IN)"""
        with Dao._get_session() as session:
            session.run("""
                MATCH (s:Student {student_id: $sid})
                MATCH (cl:Class {class_id: $cid})
                MERGE (s)-[:ENROLLED_IN]->(cl)
            """, sid=sid, cid=class_id)

    @staticmethod
    def unenroll_class(sid, class_id):
        """Hủy đăng ký lớp"""
        with Dao._get_session() as session:
            session.run("""
                MATCH (s:Student {student_id: $sid})-[r:ENROLLED_IN]->(cl:Class {class_id: $cid})
                DELETE r
            """, sid=sid, cid=class_id)

    @staticmethod
    def search_graph(keyword):
        """
        Tìm kiếm đa năng:
        1. Tìm Môn học -> Trả về danh sách Giảng viên đang dạy môn đó.
        2. Tìm Giảng viên -> Trả về danh sách Môn học họ đang dạy.
        """
        keyword = keyword.lower()
        with Dao._get_session() as session:
            # Query 1: Tìm Course
            q1 = """
            MATCH (c:Course) WHERE toLower(c.name) CONTAINS $kw
            OPTIONAL MATCH (c)-[:HAS_CLASS]->(cl:Class)<-[:TEACHES]-(t:Teacher)
            RETURN 
                'Môn học' as type, 
                c.name as title, 
                c.course_id as id,
                collect(DISTINCT t.name) as related_info
            """
            
            # Query 2: Tìm Teacher
            q2 = """
            MATCH (t:Teacher) WHERE toLower(t.name) CONTAINS $kw
            OPTIONAL MATCH (t)-[:TEACHES]->(cl:Class)<-[:HAS_CLASS]-(c:Course)
            RETURN 
                'Giảng viên' as type, 
                t.name as title, 
                t.teacher_id as id,
                collect(DISTINCT c.name) as related_info
            """
            
            # Chạy 2 query và gộp kết quả
            res1 = session.run(q1, kw=keyword).data()
            res2 = session.run(q2, kw=keyword).data()
            return res1 + res2

    @staticmethod
    def get_classmates(sid):
        """
        Tìm những sinh viên học chung các lớp học phần.
        Mô hình: (Me)-[:ENROLLED_IN]->(Class)<-[:ENROLLED_IN]-(Friend)
        """
        with Dao._get_session() as session:
            query = """
            MATCH (me:Student {student_id: $sid})-[:ENROLLED_IN]->(cl:Class)<-[:ENROLLED_IN]-(friend:Student)
            WHERE me.student_id <> friend.student_id
            RETURN 
                friend.name as name, 
                friend.student_id as id, 
                friend.class as class_sh,
                count(cl) as shared_count, 
                collect(cl.class_id) as shared_classes
            ORDER BY shared_count DESC
            LIMIT 10
            """
            return session.run(query, sid=sid).data()

    @staticmethod
    def get_credit_stats(sid):
        """Thống kê số tín chỉ đã đăng ký nhóm theo Khoa quản lý môn học"""
        with Dao._get_session() as session:
            query = """
            MATCH (s:Student {student_id: $sid})-[:ENROLLED_IN]->(cl:Class)<-[:HAS_CLASS]-(c:Course)-[:BELONGS_TO]->(d:Department)
            RETURN d.name as dept, sum(c.credit) as total_credit
            """
            return session.run(query, sid=sid).data()

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