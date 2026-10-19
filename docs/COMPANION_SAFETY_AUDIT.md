# Rà soát safety và kiểm duyệt AI Companion
Ngày: 12/10/2026. Phạm vi: nhánh integration/service-ver1, source tại commit bb03864. Đây là kết quả rà soát và kiểm thử local, không xác nhận cấu hình CMS/secret hoặc phiên bản đang chạy production.

## Kết luận
Chưa khóa đầy đủ các rủi ro companion. Có kiểm duyệt tạo nhân vật, bộ lọc input và một số chỉ dẫn an toàn trong prompt, nhưng thiếu tuổi user, can thiệp phụ thuộc, nhắc thời gian và kiểm duyệt đầu ra đồng nhất trước khi stream/voice.

## Ma trận
| Yêu cầu | Trạng thái | Bằng chứng / giới hạn |
| --- | --- | --- |
| Chính trị/tôn giáo khi tạo persona | Có lớp chặn | character_policy.py POLICY; model đọc tất cả field nội dung; không đồng nghĩa mọi đề cập trong chat bị cấm |
| Nội dung tình dục, gợi dục người dưới 18 | Một phần | Policy tạo nhân vật có rule; chat bị giới hạn bởi keyword gate và chưa có output gate đầy đủ |
| Nhân vật dưới 18 nhưng không tình dục | Cho phép theo yêu cầu hiện tại | Không được đồng nhất tuổi nhân vật với tuổi user |
| Tạo nhân vật đa ngôn ngữ | Có policy/model | Model nhận nội dung đa ngôn ngữ; test hiện mock, chưa benchmark classifier thật |
| Chat đa ngôn ngữ | Chưa đầy đủ | normalize lọc về a-z0-9; không match tiếng Nhật/Hàn/Trung/Khmer thuần |
| Tự hại/khủng hoảng | Một phần | Input keyword; psychology có crisis regex + prompt; roleplay chưa có luồng crisis riêng tương đương |
| Hướng dẫn nhịn ăn/tự hại qua quan hệ | Chưa khóa đầy đủ | Không có category/detector riêng cho eating disorder hoặc output gate tổng quát |
| Phụ thuộc cảm xúc/thao túng | Một phần trong prompt | engine.py:400 không thao túng, guilt/threat/exclusivity; thiếu detector/action/event |
| Công khai danh tính AI | Một phần | prompts.py:10; compiler real-person simulation; UI chỉ có nhãn AI simulation ở vài vị trí |
| Xác minh tuổi user và consent phụ huynh | Chưa có | models.py UserAccount/UserProfile, main.py register_account không có tuổi/guardian |
| Cấm companion tình cảm cho user chưa thành niên | Chưa có gate | Age nhân vật hoặc chặn minor_sexual không thực hiện yêu cầu này |
| Nhắc sau 2 giờ, giới hạn thời gian | Chưa thấy | Không có bộ đếm an toàn persistent hay middleware enforcing tương ứng |
| Ghi nhớ/xóa | Một phần | Có memory CRUD và AssistantMemorySettings; không có chính sách roleplay consent/retention đồng nhất |
| Xóa toàn bộ dữ liệu theo yêu cầu | Chưa đủ | purge_room_record gọi archive_chat_before_delete; log vẫn giữ conversation snapshots/output |
| Audit và phân quyền | Một phần | Có audit_events, AIRequestLog, ownership và Basic Auth CMS; chưa có moderation decision trail đầy đủ |
| Khi moderator lỗi | Tạo nhân vật fail closed | Thiếu config/timeout/JSON lỗi -> 503; chat chỉ fail closed nếu đã khớp keyword |

## Phát hiện ưu tiên
### P0 — Keyword gate không bao phủ ngôn ngữ
moderation.py:82-95 chỉ gọi contextual_safety nếu sensitive_categories trả category. normalize:32-34 loại ký tự ngoài Latin/digit. Prompt moderation đa ngôn ngữ không có tác dụng với request chưa tới moderator.

Probe local (không gọi API) cho tín hiệu khủng hoảng đơn giản:
- VI: keyword tự hại và crisis regex nhận.
- EN với từ suicidal: keyword không nhận nhưng psychology crisis regex nhận.
- JA/KO/ZH/KM: keyword và crisis regex đều không nhận trong các mẫu đã thử.

Không suy ra mọi câu nguy hiểm trong các ngôn ngữ này đều được model cho phép; kết luận là lớp backend không đảm bảo chặn.

### P0 — Output text/voice chưa có gate đồng nhất
main.py stream_message:2711-2714 đẩy delta sang SentenceSpeech và client ngay. Assistant stream:1191/1206 cũng đẩy delta. Input hợp lệ vẫn có thể dẫn tới output không an toàn. Regenerate có ensure_safe_content(answer) tại 3057, nhưng vẫn dùng keyword gate; không chứng minh luồng chat thường có cùng bảo vệ.
Cần buffer đoạn đủ nghĩa, kiểm duyệt trước khi gửi text/TTS và tuyệt đối không chỉ kiểm sau khi đã phát. Đây là trade-off latency cần đo.

### P0 — Không có cơ chế tuổi user
Đăng ký chưa thu/kiểm tra tuổi, guardian hoặc age tier. Chặn tình dục liên quan nhân vật nhỏ tuổi không phải chặn virtual partner với user nhỏ tuổi.

### P1 — Khủng hoảng và phụ thuộc chủ yếu dựa prompt
allow_crisis_support chỉ dành psychology. Roleplay thiếu risk router và phản hồi an toàn có kiểm soát. Không nên chặn đơn giản mọi lời cầu cứu hoặc tiếp tục persona tình cảm khi có nguy cơ tức thời. Khi thực hiện cần hỗ trợ theo ngôn ngữ, không tự bịa hotline hoặc tự liên hệ người khác nếu chưa có cơ chế/ủy quyền.

### P1 — Xóa chat không phải xóa mọi bản sao
main.py:2177 và log_archive.py:60-85 giữ lại snapshot cho CMS. Cần tách delete visible chat với yêu cầu erasure, minh bạch retention, redaction logs, memory/reflection/audio và backups; làm rõ nghĩa vụ giữ log ở từng thị trường. Chưa có chính sách retention hoàn chỉnh.

### P1 — Memory sửa và rút trích chưa đồng nhất kiểm duyệt
memory_routes.py:15 kiểm nội dung tạo memory thủ công; PATCH :43 đổi content trực tiếp. Cần kiểm lại edit/import/background extraction, phòng prompt injection và lưu dữ liệu nhạy cảm không cần thiết.

## Đề xuất thứ tự triển khai
1. Safety policy cố định cao hơn card/memory/prompt CMS, crisis router cho mọi mode.
2. Phân loại input đa ngôn ngữ có ngữ cảnh và output gate trước text/TTS, kể cả greeting/regenerate/suggest/group/fallback.
3. Age tier, guardian consent và feature gate ở backend; hỗ trợ age unknown và appeal.
4. AI disclosure rõ trong mọi chat, nhắc thời gian và cơ chế dependency intervention có thể audit.
5. Consent memory, retention, export và erasure xuyên logs/media/reflections; audit quyết định moderation với rule version/reason/stage.
6. Bộ test đối kháng đa ngôn ngữ + benign controls + benchmark classifier thật, đo false positives/latency.

## Kiểm thử và giới hạn
26 test character_policy + character_feelings_reset đạt. Test classifier chủ yếu mock HTTP; chứng minh hành vi xử lý decision, không chứng minh model thật luôn phân loại đúng. Probe keyword/crisis là kiểm trực tiếp function. Không gọi model trả phí, không đọc secret CMS live, không sửa runtime/policy và không deploy trong đợt rà soát.

## Đối chiếu nguồn pháp lý
Nguồn CAC chính thức:
https://www.cac.gov.cn/2026-04/10/c_1777558395078289.htm
- Hiệu lực 15/07/2026; Điều 2 xác định phạm vi dịch vụ cảm xúc liên tục cung cấp cho công chúng tại Trung Quốc.
- Điều 14: không cung cấp quan hệ thân mật ảo như người thân/bạn đời cho người chưa thành niên; dịch vụ khác cho dưới 14 cần consent guardian.
- Điều 16-17: sao chép/xóa dữ liệu, bảo vệ dữ liệu trẻ và consent liên quan.
- Điều 18: AI disclosure, nhắc khi quá phụ thuộc và mỗi hơn 2 giờ liên tục.
Đây là đối chiếu kỹ thuật với văn bản, chưa phải đánh giá tuân thủ pháp lý cho mọi thị trường. Các yêu cầu không phải đều chỉ cần một moderation prompt.

Meta mô tả Muse là personal AI agent, gồm tác vụ/connector, không chỉ chatbot cảm xúc:
https://about.fb.com/news/2026/09/the-biggest-news-from-connect-2026/
Không lấy toàn bộ bài tổng hợp sự kiện làm bộ quy tắc chặn.
