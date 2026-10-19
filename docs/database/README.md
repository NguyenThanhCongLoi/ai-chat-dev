# Schema database hiện tại

Mở [ai_companion.dbml](ai_companion.dbml), copy toàn bộ nội dung và dán vào editor của https://dbdiagram.io/.

Schema sinh từ Base.metadata trong character_chat/models.py, gồm mọi bảng/cột, kiểu dữ liệu, nullability, primary key (kể cả composite), unique constraints/indexes và foreign keys khai báo. Không đọc rows, database production hoặc secrets.

Tái xuất khi model thay đổi:

~~~powershell
cd D:\ai_chat_char
python -X utf8 scripts/export_database_dbml.py
~~~

Các điểm cần lưu ý:

- Đây là schema ứng dụng SQLite hiện tại, chưa phải thiết kế PostgreSQL tương lai.
- ID vẫn VARCHAR, thời gian vẫn VARCHAR, JSON vẫn TEXT và binary vẫn BLOB theo model thực tế.
- Các default=... của SQLAlchemy chạy ở phía ứng dụng nên ghi trong note. Không giả lập chúng thành SQL DEFAULT hoặc tự thêm increment.
- Foreign key chỉ vẽ khi model khai báo. Một số character_id/reference chứa preset hoặc system identifier nên chưa có FK tới characters.
- FK là khóa chính/unique phía bảng con được thể hiện bằng quan hệ một-một; các FK khác dùng nhiều-một.
- Không tự thêm ON DELETE CASCADE. Các luồng xóa trong service không đồng nghĩa database có cascade.
- Database cũ sau ALTER TABLE trong character_chat/db.py có thể khác nullability/default. File thể hiện schema của source hiện tại, không khẳng định đã reflect đúng live deployment.
- Sơ đồ không chứa dữ liệu thật. Giới hạn hiển thị số bảng trên dbdiagram phụ thuộc gói của tài khoản.
