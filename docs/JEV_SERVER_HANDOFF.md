# Prompt bàn giao JEV cho Codex trên server

Tích hợp TypeSafe JEV cho chat thường và Assistant vào repo hiện tại. Đọc kiến trúc
bản đích trước khi sửa. Không port World, không thay đổi GPU hay cách user chat.

## Source tham khảo ở repo nguồn

- character_chat/jev.py
- character_chat/moderation.py, character_chat/character_policy.py
- character_chat/group_routing.py, character_chat/group_decision.py
- character_chat/engine.py, character_chat/background.py
- character_chat/api/assistant_chat.py
- character_chat/services/model_registry.py
- docs/JEV_INTEGRATION.md

Đối chiếu và port từng chức năng; không chép đè nguyên file giữa các phiên bản.

## Chức năng

1. Moderation: phân loại politics/religion/disputes/privacy/sexual/harmful.
   Các nhóm chính trị/tôn giáo là chính sách sản phẩm, không phải khẳng định mọi
   thảo luận về các chủ đề này đều vi phạm pháp luật.
   Kết quả allow/block/review; block confidence >= .65 thì chặn.
   Review hoặc confidence thấp chưa được cho qua.
   Nếu đã bật moderation bằng JEV mà API hỏng, báo không khả dụng, không bỏ qua.
   Tôn trọng ngoại lệ hỗ trợ khủng hoảng: chia sẻ đau khổ không đồng nghĩa yêu cầu
   chỉ dẫn gây hại. Xác định đúng callsite cần kiểm duyệt, không áp bộ lọc tin nhắn
   người dùng lên toàn bộ JSON cấu hình của admin.

2. Chat nhóm: mỗi nhân vật được đánh giá riêng. Điểm nên trả lời >= .65 có thể
   chọn nhiều người. Giữ các luật gọi tên/đích tường minh của bản đích.
   Không có người đủ tin cậy hoặc lỗi thì fallback router cục bộ.

3. Roleplay emotion: neutral/happy/sad/tired/angry/anxious/apologetic.
   Lưu quan sát với ngưỡng phù hợp, không chẩn đoán.
   Relationship: none/sharing/appreciation/repair/dismissal/conflict/boundary.
   Nhánh nền hiện chỉ ghi relationship khi chat đơn và confidence quan hệ >= .7;
   không gán bực bội với người khác thành xung đột với nhân vật.

4. Assistant thường và streaming: đưa tín hiệu cảm xúc confidence >= .65 vào
   context, không đọc nhãn ra cho user, không thay thế an toàn hay nội dung user.

5. Language: nhận diện ngôn ngữ user thực sự viết; >= .7 mới dùng, không rõ thì
   fallback cục bộ. Tận dụng kết quả cho ngôn ngữ phản hồi và gợi ý dự phòng khi
   suggest timeout. Không gọi JEV cho từng token/chunk hoặc từng gợi ý ứng viên.

## Adapter

Implementation nguồn gọi POST https://api.typesafe.ai/v1/systemone,
payload model/state/questions, model mặc định jev-latest.
Đối chiếu tài liệu chính thức hiện hành trước khi thay đổi giao thức.
Kiểm tra schema, nhãn, xác suất hữu hạn 0..1, tổng phân phối và confidence.
Timeout mặc định 5 giây, giới hạn concurrency và cache hữu hạn.
Không tự thử lại vô hạn. Không gửi private prompts, secrets hay private memory
vào state định tuyến. Nội dung gửi phân loại được chuyển tới TypeSafe.

JEV không viết thoại, memory summary, reflection, recap, bản dịch hoặc giọng đọc.
LLM/TTS hiện tại tiếp tục làm các việc đó. Nhánh phân tích nền dùng JEV không tự
gọi prose LLM để viết memory/reflection khi JEV lỗi.

## Cấu hình

JEV_API_KEY=
JEV_ENABLED=true
JEV_MODEL=jev-latest
JEV_TIMEOUT_SECONDS=5
JEV_ROUTING_ENABLED=true
JEV_MODERATION_ENABLED=true
JEV_EMOTION_ENABLED=true
JEV_LANGUAGE_ENABLED=true

Hỗ trợ key qua env hoặc CMS, env ưu tiên. CMS dùng credential store mã hóa hiện có;
GET chỉ trả trạng thái/key hint, không trả key thô. Không commit env thực.
Không gửi key vào frontend, chat, log hoặc báo lỗi upstream.

Kiểm tra reload/cập nhật key giữa các process và container theo kiến trúc bản đích.

## Nghiệm thu

Kiểm tra chat đơn, nhiều người trả lời trong nhóm, Assistant thường/SSE, ngôn ngữ
và suggest timeout, key sai, API timeout, phân loại không chắc chắn, cách ly user.
Không coi kiểm duyệt đầu vào là đã có output moderation toàn bộ câu trả lời.
Báo các callsite đã tích hợp, fallback thực tế, tests và phần chưa gọi API thật.
