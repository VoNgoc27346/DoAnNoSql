from . import get_driver
from SPARQLWrapper import JSON, POST
import requests # Thêm thư viện này
import uuid

# Namespace dùng chung cho dự án
PREFIXES = """
    PREFIX uni: <http://example.org/university/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

class Dao:
    @staticmethod
    def _query(query_str):
        """Hàm hỗ trợ chạy lệnh SELECT (Vẫn dùng SPARQLWrapper tốt)"""
        sparql = get_driver()
        sparql.setQuery(PREFIXES + query_str)
        sparql.setReturnFormat(JSON)
        try:
            results = sparql.query().convert()
            return results["results"]["bindings"]
        except Exception as e:
            print(f"Lỗi SPARQL Query: {e}")
            return []

    @staticmethod
    def _update(update_str):
        """
        Hàm hỗ trợ chạy lệnh INSERT/DELETE
        Sử dụng 'requests' trực tiếp để tránh lỗi QueryBadFormed của SPARQLWrapper
        khi làm việc với GraphDB /statements endpoint.
        """
        sparql = get_driver()
        base_endpoint = sparql.endpoint
        
        # GraphDB yêu cầu endpoint kết thúc bằng /statements cho lệnh Update SPARQL 1.1
        if not base_endpoint.endswith('/statements'):
            update_endpoint = base_endpoint + "/statements"
        else:
            update_endpoint = base_endpoint
            
        # Header bắt buộc cho GraphDB Update
        headers = {
            "Content-Type": "application/sparql-update",
            "Accept": "application/json"
        }
        
        full_query = PREFIXES + update_str
        
        try:
            # Gửi POST request trực tiếp với raw body
            response = requests.post(update_endpoint, data=full_query.encode('utf-8'), headers=headers)
            response.raise_for_status() # Sẽ báo lỗi nếu HTTP Code không phải 200/204
        except Exception as e:
            print(f"Lỗi SPARQL Update: {e}")
            if 'response' in locals():
                print(f"Chi tiết lỗi từ Server: {response.text}")

    @staticmethod
    def init_db():
        # Kiểm tra xem đã có admin chưa
        check_admin = Dao._query("SELECT ?s WHERE { ?s rdf:type uni:Admin } LIMIT 1")
        if not check_admin:
            print("Đang khởi tạo dữ liệu mẫu...")
            query = """
            INSERT DATA {
                uni:admin_01 rdf:type uni:Admin ;
                             uni:username "admin" ;
                             uni:password "admin123" ;
                             uni:name "Quản trị viên" .
                             
                uni:dept_CNTT rdf:type uni:Department ;
                              uni:id "CNTT" ;
                              uni:name "Công nghệ thông tin" .
                              
                uni:dept_KT rdf:type uni:Department ;
                            uni:id "KT" ;
                            uni:name "Kinh tế" .

                uni:dept_NN rdf:type uni:Department ;
                            uni:id "NN" ;
                            uni:name "Ngoại ngữ" .

                uni:dept_QTKD rdf:type uni:Department ;
                              uni:id "QTKD" ;
                              uni:name "Quản trị Kinh doanh" .

                uni:dept_DL rdf:type uni:Department ;
                            uni:id "DL" ;
                            uni:name "Du lịch & Khách sạn" .
                            
                uni:sem_HK1_2024 rdf:type uni:Semester ;
                                 uni:id "HK1_2024" ;
                                 uni:year "2024" ;
                                 uni:term "1" .
            }
            """
            Dao._update(query)

    @staticmethod
    def verify_user(username, password, role):
        rdf_type = "uni:Admin" if role == 'admin' else "uni:Student"
        if role == 'admin':
            query = f"""
            SELECT ?s WHERE {{
                ?s rdf:type {rdf_type} ;
                   uni:username "{username}" ;
                   uni:password "{password}" .
            }}
            """
        else:
            query = f"""
            SELECT ?s WHERE {{
                ?s rdf:type {rdf_type} ;
                   uni:id "{username}" ;
                   uni:password "{password}" .
            }}
            """
        res = Dao._query(query)
        return len(res) > 0

    @staticmethod
    def _parse_result(binding, keys):
        res = {}
        for k in keys:
            if k in binding:
                res[k] = binding[k]["value"]
            else:
                res[k] = None
        return res

    # --- TEACHER ---
    @staticmethod
    def get_all_teachers():
        query = """
        SELECT ?id ?name ?phone ?pos ?status ?deptName
        WHERE {
            ?t rdf:type uni:Teacher ;
               uni:id ?id ;
               uni:name ?name .
            OPTIONAL { ?t uni:phone ?phone }
            OPTIONAL { ?t uni:position ?pos }
            OPTIONAL { ?t uni:status ?status }
            OPTIONAL { ?t uni:belongsTo ?d . ?d uni:name ?deptName }
        }
        """
        bindings = Dao._query(query)
        teachers = []
        for b in bindings:
            t_data = Dao._parse_result(b, ["id", "name", "phone", "pos", "status"])
            t_data['teacher_id'] = t_data['id'] 
            teachers.append({
                "data": t_data,
                "dept": b.get("deptName", {}).get("value", "")
            })
        return teachers

    @staticmethod
    def add_teacher(tid, name, phone, position, dept_id):
        query = f"""
        INSERT {{
            uni:teacher_{tid} rdf:type uni:Teacher ;
                              uni:id "{tid}" ;
                              uni:name "{name}" ;
                              uni:phone "{phone}" ;
                              uni:position "{position}" ;
                              uni:status "Đang giảng dạy" ;
                              uni:belongsTo uni:dept_{dept_id} .
        }} WHERE {{}}
        """
        Dao._update(query)

    @staticmethod
    def delete_teacher(tid):
        query = f"DELETE WHERE {{ uni:teacher_{tid} ?p ?o . }}"
        Dao._update(query)

    # --- STUDENT ---
    @staticmethod
    def get_all_students():
        query = """
        SELECT ?id ?name ?class ?year ?status ?deptName
        WHERE {
            ?s rdf:type uni:Student ;
               uni:id ?id ;
               uni:name ?name .
            OPTIONAL { ?s uni:class ?class }
            OPTIONAL { ?s uni:year ?year }
            OPTIONAL { ?s uni:status ?status }
            OPTIONAL { ?s uni:majorIn ?d . ?d uni:name ?deptName }
        }
        """
        bindings = Dao._query(query)
        students = []
        for b in bindings:
            s_data = Dao._parse_result(b, ["id", "name", "class", "year", "status"])
            s_data['student_id'] = s_data['id']
            students.append({
                "data": s_data,
                "major": b.get("deptName", {}).get("value", "")
            })
        return students

    @staticmethod
    def add_student(sid, name, phone, _class, year, major_id, password):
        query = f"""
        INSERT {{
            uni:student_{sid} rdf:type uni:Student ;
                              uni:id "{sid}" ;
                              uni:name "{name}" ;
                              uni:phone "{phone}" ;
                              uni:class "{_class}" ;
                              uni:year "{year}" ;
                              uni:status "Đang học" ;
                              uni:password "{password}" ;
                              uni:majorIn uni:dept_{major_id} .
        }} WHERE {{}}
        """
        Dao._update(query)

    @staticmethod
    def delete_student(sid):
        query = f"DELETE WHERE {{ uni:student_{sid} ?p ?o }}"
        Dao._update(query)

    # --- COURSE ---
    @staticmethod
    def get_all_courses():
        query = """
        SELECT ?id ?name ?credit ?sem ?deptName
        WHERE {
            ?c rdf:type uni:Course ;
               uni:id ?id ;
               uni:name ?name .
            OPTIONAL { ?c uni:credit ?credit }
            OPTIONAL { ?c uni:semester ?sem }
            OPTIONAL { ?c uni:belongsTo ?d . ?d uni:name ?deptName }
        }
        """
        bindings = Dao._query(query)
        courses = []
        for b in bindings:
            c_data = Dao._parse_result(b, ["id", "name", "credit", "sem"])
            c_data['course_id'] = c_data['id']
            c_data['semester'] = c_data['sem']
            courses.append({
                "data": c_data,
                "dept": b.get("deptName", {}).get("value", "")
            })
        return courses

    @staticmethod
    def add_course(cid, name, credit, semester_std, dept_id):
        query = f"""
        INSERT {{
            uni:course_{cid} rdf:type uni:Course ;
                             uni:id "{cid}" ;
                             uni:name "{name}" ;
                             uni:credit "{credit}" ;
                             uni:semester "{semester_std}" ;
                             uni:belongsTo uni:dept_{dept_id} .
        }} WHERE {{}}
        """
        Dao._update(query)

    # --- CLASS SECTION ---
    @staticmethod
    def create_section(class_id, room, schedule, course_id, teacher_id, semester_id):
        class_uri = class_id.replace(" ", "_")
        query = f"""
        INSERT {{
            uni:class_{class_uri} rdf:type uni:Class ;
                                  uni:id "{class_id}" ;
                                  uni:room "{room}" ;
                                  uni:schedule "{schedule}" ;
                                  uni:offeredIn uni:sem_{semester_id} .
            uni:course_{course_id} uni:hasClass uni:class_{class_uri} .
            uni:teacher_{teacher_id} uni:teaches uni:class_{class_uri} .
        }} WHERE {{}}
        """
        Dao._update(query)

    @staticmethod
    def get_data_for_section_form():
        t_res = Dao._query("SELECT ?id ?name WHERE { ?t rdf:type uni:Teacher ; uni:id ?id ; uni:name ?name }")
        c_res = Dao._query("SELECT ?id ?name WHERE { ?c rdf:type uni:Course ; uni:id ?id ; uni:name ?name }")
        s_res = Dao._query("SELECT ?id WHERE { ?s rdf:type uni:Semester ; uni:id ?id }")
        return {
            "teachers": [Dao._parse_result(r, ["id", "name"]) for r in t_res],
            "courses": [Dao._parse_result(r, ["id", "name"]) for r in c_res],
            "semesters": [Dao._parse_result(r, ["id"]) for r in s_res]
        }

    # --- SINH VIÊN ---
    @staticmethod
    def get_student_info(sid):
        query = f"""
        SELECT ?id ?name ?class ?year ?status ?majorName
        WHERE {{
            uni:student_{sid} uni:id ?id ;
                              uni:name ?name .
            OPTIONAL {{ uni:student_{sid} uni:class ?class }}
            OPTIONAL {{ uni:student_{sid} uni:year ?year }}
            OPTIONAL {{ uni:student_{sid} uni:status ?status }}
            OPTIONAL {{ uni:student_{sid} uni:majorIn ?d . ?d uni:name ?majorName }}
        }}
        """
        res = Dao._query(query)
        if res:
            data = Dao._parse_result(res[0], ["id", "name", "class", "year", "status"])
            data['student_id'] = data['id']
            return {"data": data, "major": res[0].get("majorName", {}).get("value", "")}
        return None

    @staticmethod
    def get_available_classes_for_registration(sid):
        query = f"""
        SELECT ?classId ?room ?schedule ?courseName ?credit ?teacherName
        WHERE {{
            ?cl rdf:type uni:Class ;
                uni:id ?classId ;
                uni:room ?room ;
                uni:schedule ?schedule .
            ?c uni:hasClass ?cl ;
               uni:name ?courseName ;
               uni:credit ?credit .
            ?t uni:teaches ?cl ;
               uni:name ?teacherName .
            FILTER NOT EXISTS {{ uni:student_{sid} uni:enrolledIn ?cl . }}
        }}
        """
        bindings = Dao._query(query)
        results = []
        for b in bindings:
            item = Dao._parse_result(b, ["class_id", "room", "schedule", "course_name", "credit", "teacher_name"])
            item['class_id'] = b['classId']['value']
            item['course_name'] = b['courseName']['value']
            item['teacher_name'] = b['teacherName']['value']
            results.append(item)
        return results

    @staticmethod
    def get_student_enrolled_classes(sid):
        query = f"""
        SELECT ?classId ?room ?schedule ?courseName ?credit ?teacherName
        WHERE {{
            uni:student_{sid} uni:enrolledIn ?cl .
            ?cl uni:id ?classId ;
                uni:room ?room ;
                uni:schedule ?schedule .
            ?c uni:hasClass ?cl ;
               uni:name ?courseName ;
               uni:credit ?credit .
            ?t uni:teaches ?cl ;
               uni:name ?teacherName .
        }}
        """
        bindings = Dao._query(query)
        results = []
        for b in bindings:
            item = Dao._parse_result(b, ["room", "schedule", "credit"])
            item['class_id'] = b['classId']['value']
            item['course_name'] = b['courseName']['value']
            item['teacher_name'] = b['teacherName']['value']
            results.append(item)
        return results

    @staticmethod
    def enroll_class(sid, class_id):
        class_uri = class_id.replace(" ", "_")
        query = f"INSERT DATA {{ uni:student_{sid} uni:enrolledIn uni:class_{class_uri} . }}"
        Dao._update(query)

    @staticmethod
    def unenroll_class(sid, class_id):
        class_uri = class_id.replace(" ", "_")
        query = f"DELETE DATA {{ uni:student_{sid} uni:enrolledIn uni:class_{class_uri} . }}"
        Dao._update(query)

    # --- TRA CỨU ---
    @staticmethod
    def search_graph(keyword):
        keyword = keyword.lower()
        # Tìm Course
        q1 = f"""
        SELECT ?id ?name (GROUP_CONCAT(DISTINCT ?tName; separator=", ") AS ?related)
        WHERE {{
            ?c rdf:type uni:Course ;
               uni:id ?id ;
               uni:name ?name .
            FILTER(CONTAINS(LCASE(?name), "{keyword}"))
            OPTIONAL {{
                ?c uni:hasClass ?cl .
                ?t uni:teaches ?cl ; uni:name ?tName .
            }}
        }} GROUP BY ?id ?name
        """
        # Tìm Teacher
        q2 = f"""
        SELECT ?id ?name (GROUP_CONCAT(DISTINCT ?cName; separator=", ") AS ?related)
        WHERE {{
            ?t rdf:type uni:Teacher ;
               uni:id ?id ;
               uni:name ?name .
            FILTER(CONTAINS(LCASE(?name), "{keyword}"))
            OPTIONAL {{
                ?t uni:teaches ?cl .
                ?c uni:hasClass ?cl ; uni:name ?cName .
            }}
        }} GROUP BY ?id ?name
        """
        res1 = Dao._query(q1)
        res2 = Dao._query(q2)
        
        final_res = []
        for r in res1:
            final_res.append({
                "type": "Môn học", "title": r["name"]["value"], "id": r["id"]["value"],
                "related_info": r["related"]["value"].split(", ") if "related" in r else []
            })
        for r in res2:
            final_res.append({
                "type": "Giảng viên", "title": r["name"]["value"], "id": r["id"]["value"],
                "related_info": r["related"]["value"].split(", ") if "related" in r else []
            })
        return final_res

    # --- VISUALIZATION ---
    @staticmethod
    def get_graph_data_json():
        query = """
        SELECT ?s ?p ?o ?sName ?oName ?sType ?oType
        WHERE {
            ?s ?p ?o .
            FILTER(STRSTARTS(STR(?s), "http://example.org/university/"))
            FILTER(STRSTARTS(STR(?o), "http://example.org/university/"))
            # Lọc không hiển thị Grade node để đỡ rối
            MINUS { ?s rdf:type uni:Grade }
            MINUS { ?o rdf:type uni:Grade }

            OPTIONAL { ?s uni:name ?sName }
            OPTIONAL { ?s uni:id ?sId }
            OPTIONAL { ?s rdf:type ?sType }
            
            OPTIONAL { ?o uni:name ?oName }
            OPTIONAL { ?o uni:id ?oId }
            OPTIONAL { ?o rdf:type ?oType }
        } LIMIT 200
        """
        bindings = Dao._query(query)
        nodes = {}
        edges = []
        
        for b in bindings:
            s_uri = b['s']['value']
            o_uri = b['o']['value']
            pred = b['p']['value'].split('/')[-1]
            
            if s_uri not in nodes:
                label = b.get('sName', {}).get('value') or s_uri.split('_')[-1]
                group = b.get('sType', {}).get('value', 'Unknown').split('/')[-1]
                nodes[s_uri] = {"id": s_uri, "label": label, "group": group}
                
            if b['o']['type'] == 'uri':
                if o_uri not in nodes:
                    label = b.get('oName', {}).get('value') or o_uri.split('_')[-1]
                    group = b.get('oType', {}).get('value', 'Unknown').split('/')[-1]
                    nodes[o_uri] = {"id": o_uri, "label": label, "group": group}
                edges.append({"from": s_uri, "to": o_uri, "label": pred})

        return {"nodes": list(nodes.values()), "edges": edges}

    # --- THỐNG KÊ (STATS) ---
    @staticmethod
    def get_system_stats():
        q_count = """
        SELECT (COUNT(?s) as ?cnt) ?type
        WHERE { ?s rdf:type ?type } GROUP BY ?type
        """
        res = Dao._query(q_count)
        stats = {"students": 0, "teachers": 0, "courses": 0, "classes": 0}
        for r in res:
            t = r['type']['value'].split('/')[-1]
            c = int(r['cnt']['value'])
            if t == 'Student': stats['students'] = c
            elif t == 'Teacher': stats['teachers'] = c
            elif t == 'Course': stats['courses'] = c
            elif t == 'Class': stats['classes'] = c
            
        q_dept = """
        SELECT ?deptName (COUNT(?s) as ?cnt)
        WHERE {
            ?s rdf:type uni:Student ; uni:majorIn ?d .
            ?d uni:name ?deptName .
        } GROUP BY ?deptName
        """
        res_dept = Dao._query(q_dept)
        dept_stats = [{"dept": r['deptName']['value'], "count": r['cnt']['value']} for r in res_dept]
        return {"general": stats, "by_dept": dept_stats}

    # === CÁC HÀM MỚI CHUYỂN ĐỔI (Phần bạn yêu cầu) ===

    @staticmethod
    def get_classmates(sid):
        """Tìm bạn cùng lớp: Đếm số lớp học chung"""
        query = f"""
        SELECT ?name ?id ?class (COUNT(?cl) as ?shared_count) (GROUP_CONCAT(DISTINCT ?clId; separator=", ") AS ?shared_classes)
        WHERE {{
            uni:student_{sid} uni:enrolledIn ?cl .
            ?friend uni:enrolledIn ?cl ;
                    uni:id ?id ;
                    uni:name ?name .
            FILTER(?friend != uni:student_{sid})
            
            ?cl uni:id ?clId .
            OPTIONAL {{ ?friend uni:class ?class }}
        }}
        GROUP BY ?name ?id ?class
        ORDER BY DESC(?shared_count)
        LIMIT 10
        """
        bindings = Dao._query(query)
        results = []
        for b in bindings:
            item = Dao._parse_result(b, ["name", "id", "class", "shared_count", "shared_classes"])
            item['class_sh'] = item.pop('class') # Đổi tên key cho khớp HTML
            item['shared_classes'] = item['shared_classes'].split(", ") if item['shared_classes'] else []
            results.append(item)
        return results

    @staticmethod
    def get_credit_stats(sid):
        """Thống kê tín chỉ theo Khoa"""
        query = f"""
        SELECT ?deptName (SUM(xsd:integer(?credit)) as ?total_credit)
        WHERE {{
            uni:student_{sid} uni:enrolledIn ?cl .
            ?c uni:hasClass ?cl ;
               uni:credit ?credit ;
               uni:belongsTo ?d .
            ?d uni:name ?deptName .
        }} GROUP BY ?deptName
        """
        res = Dao._query(query)
        return [{"dept": r['deptName']['value'], "total_credit": r['total_credit']['value']} for r in res]

    @staticmethod
    def get_class_roster(class_id):
        """Lấy danh sách sinh viên kèm điểm số của 1 lớp"""
        # Tạo URI cho class
        class_uri = class_id.replace(" ", "_")
        query = f"""
        SELECT ?id ?name ?score
        WHERE {{
            ?s uni:enrolledIn uni:class_{class_uri} ;
               uni:id ?id ;
               uni:name ?name .
            
            # Lấy điểm từ Node trung gian Grade (nếu có)
            OPTIONAL {{
                ?g rdf:type uni:Grade ;
                   uni:class uni:class_{class_uri} ;
                   uni:student ?s ;
                   uni:value ?score .
            }}
        }} ORDER BY ?name
        """
        bindings = Dao._query(query)
        return [Dao._parse_result(b, ["id", "name", "score"]) for b in bindings]

    @staticmethod
    def update_grade(class_id, student_id, score):
        """Cập nhật điểm: Xóa Node Grade cũ và tạo Node Grade mới"""
        class_uri = class_id.replace(" ", "_")
        
        # 1. Xóa điểm cũ (nếu có)
        delete_query = f"""
        DELETE WHERE {{
            ?g rdf:type uni:Grade ;
               uni:class uni:class_{class_uri} ;
               uni:student uni:student_{student_id} ;
               ?p ?o .
        }}
        """
        Dao._update(delete_query)
        
        # 2. Nếu có điểm mới thì Insert
        if score and score.strip():
            # Tạo ID ngẫu nhiên cho Node Grade để không trùng
            grade_uuid = str(uuid.uuid4())
            insert_query = f"""
            INSERT DATA {{
                uni:grade_{grade_uuid} rdf:type uni:Grade ;
                                       uni:class uni:class_{class_uri} ;
                                       uni:student uni:student_{student_id} ;
                                       uni:value "{score}" .
            }}
            """
            Dao._update(insert_query)

    @staticmethod
    def export_full_data():
        """Xuất toàn bộ dữ liệu quan trọng ra JSON"""
        return {
            "teachers": Dao.get_all_teachers(),
            "students": Dao.get_all_students(),
            "courses": Dao.get_all_courses()
            # Lưu ý: Class Section có cấu trúc phức tạp hơn, 
            # trong phạm vi demo ta tập trung vào 3 thực thể chính này trước.
        }

    @staticmethod
    def import_from_json(data):
        if "teachers" in data:
            for t in data["teachers"]:
                d = t["data"]
                dept_id = "CNTT"
                if t["dept"] == "Kinh tế": dept_id = "KT"
                elif t["dept"] == "Ngoại ngữ": dept_id = "NN"
                elif t["dept"] == "Quản trị Kinh doanh": dept_id = "QTKD"
                elif t["dept"] == "Du lịch & Khách sạn": dept_id = "DL"
                
                Dao.add_teacher(d["teacher_id"], d["name"], d["phone"], d["position"], dept_id)

        if "students" in data:
            for s in data["students"]:
                d = s["data"]
                dept_id = "CNTT"
                if s.get("major") == "Kinh tế": dept_id = "KT"
                elif s.get("major") == "Ngoại ngữ": dept_id = "NN"
                elif s.get("major") == "Quản trị Kinh doanh": dept_id = "QTKD"
                elif s.get("major") == "Du lịch & Khách sạn": dept_id = "DL"
                
                pwd = d.get("password", "123456") 
                
                Dao.add_student(d["student_id"], d["name"], d["phone"], d["class"], d["year"], dept_id, pwd)

        if "courses" in data:
            for c in data["courses"]:
                d = c["data"]
                dept_id = "CNTT"
                if c["dept"] == "Kinh tế": dept_id = "KT"
                elif c["dept"] == "Ngoại ngữ": dept_id = "NN"
                elif c["dept"] == "Quản trị Kinh doanh": dept_id = "QTKD"
                elif c["dept"] == "Du lịch & Khách sạn": dept_id = "DL"
                
                Dao.add_course(d["course_id"], d["name"], d["credit"], d["semester"], dept_id)
        
        return True
    
        # === CÁC HÀM UPDATE (SỬA ĐỔI) ===

    # --- 1. UPDATE TEACHER ---
    @staticmethod
    def get_teacher_by_id(tid):
        """Lấy thông tin chi tiết GV để đổ vào form sửa"""
        query = f"""
        SELECT ?id ?name ?phone ?pos ?status ?deptId
        WHERE {{
            uni:teacher_{tid} uni:id ?id ;
                              uni:name ?name .
            OPTIONAL {{ uni:teacher_{tid} uni:phone ?phone }}
            OPTIONAL {{ uni:teacher_{tid} uni:position ?pos }}
            OPTIONAL {{ uni:teacher_{tid} uni:status ?status }}
            OPTIONAL {{ uni:teacher_{tid} uni:belongsTo ?d . ?d uni:id ?deptId }}
        }}
        """
        res = Dao._query(query)
        if res:
            return Dao._parse_result(res[0], ["id", "name", "phone", "pos", "status", "deptId"])
        return None

    @staticmethod
    def update_teacher(tid, name, phone, position, dept_id):
        """Cập nhật GV: Xóa thuộc tính cũ và Insert thuộc tính mới"""
        # 1. Xóa thông tin cũ (Lưu ý: Không xóa quan hệ teaches để tránh mất lớp dạy)
        delete_query = f"""
        DELETE {{
            uni:teacher_{tid} uni:name ?name ;
                              uni:phone ?phone ;
                              uni:position ?pos ;
                              uni:belongsTo ?d .
        }}
        WHERE {{
            uni:teacher_{tid} uni:name ?name .
            OPTIONAL {{ uni:teacher_{tid} uni:phone ?phone }}
            OPTIONAL {{ uni:teacher_{tid} uni:position ?pos }}
            OPTIONAL {{ uni:teacher_{tid} uni:belongsTo ?d }}
        }}
        """
        Dao._update(delete_query)
        
        # 2. Thêm thông tin mới
        insert_query = f"""
        INSERT DATA {{
            uni:teacher_{tid} uni:name "{name}" ;
                              uni:phone "{phone}" ;
                              uni:position "{position}" ;
                              uni:belongsTo uni:dept_{dept_id} .
        }}
        """
        Dao._update(insert_query)

    # --- 2. UPDATE STUDENT ---
    @staticmethod
    def get_student_by_id(sid):
        query = f"""
        SELECT ?id ?name ?phone ?class ?year ?deptId ?password
        WHERE {{
            uni:student_{sid} uni:id ?id ;
                              uni:name ?name .
            OPTIONAL {{ uni:student_{sid} uni:phone ?phone }}
            OPTIONAL {{ uni:student_{sid} uni:class ?class }}
            OPTIONAL {{ uni:student_{sid} uni:year ?year }}
            OPTIONAL {{ uni:student_{sid} uni:password ?password }}
            OPTIONAL {{ uni:student_{sid} uni:majorIn ?d . ?d uni:id ?deptId }}
        }}
        """
        res = Dao._query(query)
        if res:
            return Dao._parse_result(res[0], ["id", "name", "phone", "class", "year", "deptId", "password"])
        return None

    @staticmethod
    def update_student(sid, name, phone, _class, year, dept_id, password):
        delete_query = f"""
        DELETE {{
            uni:student_{sid} uni:name ?name ;
                              uni:phone ?phone ;
                              uni:class ?class ;
                              uni:year ?year ;
                              uni:password ?pwd ;
                              uni:majorIn ?d .
        }}
        WHERE {{
            uni:student_{sid} uni:name ?name .
            OPTIONAL {{ uni:student_{sid} uni:phone ?phone }}
            OPTIONAL {{ uni:student_{sid} uni:class ?class }}
            OPTIONAL {{ uni:student_{sid} uni:year ?year }}
            OPTIONAL {{ uni:student_{sid} uni:password ?pwd }}
            OPTIONAL {{ uni:student_{sid} uni:majorIn ?d }}
        }}
        """
        Dao._update(delete_query)
        
        insert_query = f"""
        INSERT DATA {{
            uni:student_{sid} uni:name "{name}" ;
                              uni:phone "{phone}" ;
                              uni:class "{_class}" ;
                              uni:year "{year}" ;
                              uni:password "{password}" ;
                              uni:majorIn uni:dept_{dept_id} .
        }}
        """
        Dao._update(insert_query)

    # --- 3. UPDATE COURSE ---
    @staticmethod
    def get_course_by_id(cid):
        query = f"""
        SELECT ?id ?name ?credit ?sem ?deptId
        WHERE {{
            uni:course_{cid} uni:id ?id ;
                             uni:name ?name .
            OPTIONAL {{ uni:course_{cid} uni:credit ?credit }}
            OPTIONAL {{ uni:course_{cid} uni:semester ?sem }}
            OPTIONAL {{ uni:course_{cid} uni:belongsTo ?d . ?d uni:id ?deptId }}
        }}
        """
        res = Dao._query(query)
        if res:
            return Dao._parse_result(res[0], ["id", "name", "credit", "sem", "deptId"])
        return None

    @staticmethod
    def update_course(cid, name, credit, semester, dept_id):
        delete_query = f"""
        DELETE {{
            uni:course_{cid} uni:name ?name ;
                             uni:credit ?credit ;
                             uni:semester ?sem ;
                             uni:belongsTo ?d .
        }}
        WHERE {{
            uni:course_{cid} uni:name ?name .
            OPTIONAL {{ uni:course_{cid} uni:credit ?credit }}
            OPTIONAL {{ uni:course_{cid} uni:semester ?sem }}
            OPTIONAL {{ uni:course_{cid} uni:belongsTo ?d }}
        }}
        """
        Dao._update(delete_query)
        
        insert_query = f"""
        INSERT DATA {{
            uni:course_{cid} uni:name "{name}" ;
                             uni:credit "{credit}" ;
                             uni:semester "{semester}" ;
                             uni:belongsTo uni:dept_{dept_id} .
        }}
        """
        Dao._update(insert_query)

    @staticmethod
    def delete_course(cid):
        """Xóa môn học"""
        # Xóa tất cả bộ ba có chủ ngữ là môn học này
        query = f"DELETE WHERE {{ uni:course_{cid} ?p ?o . }}"
        Dao._update(query)