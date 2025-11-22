import os

class Config:
    # Secret key dùng cho session và flash message
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super_secret_key_123'
    
    # Cấu hình Neo4j
    NEO4J_URI = "neo4j://127.0.0.1:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "12345678" # <--- ĐỔI PASSWORD CỦA BẠN Ở ĐÂY