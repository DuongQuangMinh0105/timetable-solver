import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ LỖI: Chưa có DATABASE_URL trong file .env")
else:
    print(f"Đang thử kết nối tới: {DATABASE_URL}")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).fetchone()[0]
            print(f"✅ KẾT NỐI THÀNH CÔNG! Phiên bản: {version}")

            # Thử tạo bảng blobs (nếu chưa có) để test quyền ghi
            from timetable.infrastructure.persistence.models import Base

            Base.metadata.create_all(engine)
            print("✅ Đã kiểm tra/tạo bảng thành công.")
    except Exception as e:
        print(f"❌ KẾT NỐI THẤT BẠI. Lỗi: {e}")
