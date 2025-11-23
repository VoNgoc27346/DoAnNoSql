from flask import Flask
from SPARQLWrapper import SPARQLWrapper, JSON, POST
from config import Config

# Khởi tạo biến sparql toàn cục
sparql = None

def init_driver(endpoint):
    global sparql
    sparql = SPARQLWrapper(endpoint)
    # Cấu hình trả về JSON để dễ xử lý trong Python
    sparql.setReturnFormat(JSON)
    # Cấu hình method để hỗ trợ cả Query (SELECT) và Update (INSERT/DELETE)
    sparql.setMethod(POST) 

def get_driver():
    return sparql

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Kết nối GraphDB
    init_driver(app.config['GRAPHDB_ENDPOINT'])

    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app

def init_db_data():
    from .dao import Dao
    Dao.init_db()