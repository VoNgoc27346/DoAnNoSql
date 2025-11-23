import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super_secret_key_123'
    
    # Cấu hình GraphDB (Ontotext)
    # Endpoint thường có dạng: http://localhost:7200/repositories/{Tên_Repo}
    GRAPHDB_ENDPOINT = "http://localhost:7200/repositories/university_db"
    
    # GraphDB Free mặc định không cần user/pass cho read/write local, 
    # nhưng nếu bạn set up security thì điền vào đây.

    GRAPHDB_USER = "admin" 
    GRAPHDB_PASSWORD = "root"