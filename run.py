from app import create_app, init_db_data
import threading

app = create_app()

def run_app(port):
    # Chạy Flask, tắt reloader để debug mode không gây lỗi khi chạy nhiều port
    app.run(debug=True, port=port, use_reloader=False)

if __name__ == '__main__':
    # Khởi tạo dữ liệu mẫu nếu chưa có
    init_db_data()
    print("✅ Server đang chạy tại http://127.0.0.1:5000 và http://127.0.0.1:5001")

    # Tạo 2 thread để chạy app trên 2 port
    t1 = threading.Thread(target=run_app, args=(5000,))
    t2 = threading.Thread(target=run_app, args=(5001,))

    t1.start()
    t2.start()
