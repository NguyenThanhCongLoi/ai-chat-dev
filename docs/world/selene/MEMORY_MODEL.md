# Memory và quyền riêng tư

Trạng thái World ở AppSetting có khóa owner-hash/run-ID, đọc theo owner; khác người không thấy. Backend giữ toàn bộ chương, projection chỉ phát dữ kiện đã được phép.

Phạm vi: WORLD_ONLY, CHARACTER_ONLY, USER_AND_CHARACTER, NORMAL_CHAT_SHARED, SECRET, CANON. V1 chỉ export NORMAL_CHAT_SHARED. SECRET/CANON không vào journal/reward title cho user.

Nút trở về chat có checkbox đồng ý. Export chỉ sau completed; fact do tác giả chuẩn bị, không lấy nguyên lời AI. Tạo Memory CHARACTER_PRIVATE đúng user/character, type world_shared, ID ổn định theo nguồn; retry không nhân bản. Không ghi đè điểm quan hệ chat thường.

Retriever và prompt builder kiểm nguồn lượt chơi completed + synced; gắn type world_shared giả không mở khóa được tương lai. Không tự chuyển graph quan hệ giữa nhân vật, private chat hay memory khác.

World không tự đọc private memories của chat. Nó dùng cá tính và trust của chính user–Selene. Khi user đồng ý export, chat Selene nhận tối đa 3 ký ức có nguồn, tôn trọng công tắc dùng memory của phòng.
