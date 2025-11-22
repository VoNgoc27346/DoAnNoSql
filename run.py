from app import create_app, init_db_data

app = create_app()

if __name__ == '__main__':
    # Khởi tạo dữ liệu mẫu nếu chưa có
    init_db_data()
    print("✅ Server đang chạy tại http://127.0.0.1:5000")
    app.run(debug=True)