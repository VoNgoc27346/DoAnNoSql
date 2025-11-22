from flask import Flask
from neo4j import GraphDatabase
from config import Config

# Khởi tạo driver Neo4j ở cấp độ module để dùng chung
driver = None

def init_driver(uri, username, password):
    global driver
    driver = GraphDatabase.driver(uri, auth=(username, password))

def get_driver():
    return driver

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Kết nối Database
    init_driver(
        app.config['NEO4J_URI'],
        app.config['NEO4J_USER'],
        app.config['NEO4J_PASSWORD']
    )

    # Đăng ký các Routes (Blueprint)
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app

# Hàm khởi tạo dữ liệu mẫu (được gọi từ run.py)
def init_db_data():
    from .dao import Dao
    Dao.init_db()