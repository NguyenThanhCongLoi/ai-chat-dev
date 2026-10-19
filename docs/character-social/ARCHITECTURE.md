# Character social — chat Roleplay thông thường

Ngày: 17/10/2026. Áp dụng cho chat riêng và phòng nhóm hiện có; chưa tích hợp AI World.

## Quy tắc đã chốt sau phản hồi của user

- User chỉ chọn hai nhân vật muốn kết nối.
- Không có ô nhập quan hệ, chọn trạng thái, sửa trust/tình cảm hoặc viết canon quan hệ trong bảng kết nối.
- Kết nối chỉ giới thiệu tên và vai trò. Không tự tạo phòng, tự gửi tin hay giả lập cuộc gặp.
- Khi user chủ động tạo phòng nhóm bằng chức năng sẵn có và cả hai có câu trả lời hoàn tất cho cùng một lượt user, hệ thống mới ghi nhận đã gặp.
- Thân thiết hay cạnh tranh do hệ thống đánh giá từ tương tác; user không đặt kết quả.

Quy tắc này thay thế phần USER-CREATED CANON và nút Let them meet trong yêu cầu đính kèm ban đầu.

## Đã tận dụng gì

FastAPI/SQLAlchemy/SQLite; Character/Room/RoomMember/Message hiện có; engine.assemble; bộ định tuyến nhóm; memory riêng từng nhân vật; trình tải ảnh expression/surprised. Không thêm engine chat, model GPU, graph database hay thư viện hoạt ảnh.

ID nhân vật hiện có được dùng lại. Nhân vật hệ thống được đưa vào danh sách cá nhân qua quy trình materialize/reuse preset sẵn có; không tạo kho nhân vật thứ hai. Không thay prompt cá tính hay lorebook đã soạn cho 11 nhân vật.

## Mô hình SQL

| Bảng | Vai trò |
| --- | --- |
| character_social_state | Trạng thái có hướng A → B, owner/scope, active, số lượt, thời điểm gặp và 7 chiều độc lập |
| character_social_knowledge | Danh tính đã được giới thiệu/được chứng kiến, nguồn, confidence, visibility |
| character_social_canon | Lớp dữ kiện do hệ thống/tác giả đáng tin cậy chuẩn bị, tách khỏi diễn biến; V1 không có API user ghi bảng này |
| character_shared_interaction | Biên nhận cặp/lượt duy nhất, nguồn hội thoại, trích dẫn có người nói, fingerprint và delta đã duyệt |

UNKNOWN là không có bản ghi. Khóa định danh chứa user + scope + cặp nhân vật; canon dùng cặp không thứ tự, quan hệ động dùng hướng riêng.

Bổ sung Message.reply_to_message_id nullable và index bằng migration additive khi khởi động. Giữ nguyên tin nhắn cũ; không suy đoán cuộc gặp từ lịch sử chưa có liên kết nguồn. Các bảng mới được tạo qua Base.metadata.create_all. Backup SQLite nguyên file bao gồm bảng mới; production vẫn cần backup trước nâng cấp.

## Suy diễn và chi phí

Một receipt chỉ được tạo khi có tin nhắn user đã lưu và hai AI cùng phòng, cùng owner, đúng reply_to, có nội dung và đã hoàn tất. Greeting, partial, generating, error và một AI đơn lẻ không đủ. ID receipt cố định giúp retry không cộng lượt hai lần. Cả POST thường và SSE đều gọi pipeline sau khi lưu câu trả lời.

- Lần đầu đủ điều kiện: MET.
- Từ 3 lượt chung khác nhau: RELATIONSHIP, nghĩa là đã có lịch sử, không mặc định là bạn bè.
- affinity, trust, respect, jealousy, rivalry, fear, romantic_interest có hướng riêng, trong [0,100].
- Delta mỗi chiều tối đa ±3 mỗi receipt. Khóa dòng được dùng khi DB hỗ trợ; SQLite vẫn theo giới hạn ghi của SQLite.
- Evaluator V1 chỉ nhận một số câu khẳng định trực tiếp rất rõ bằng Anh/Việt: gọi đúng tên đầy đủ, rồi tuyên bố tin/không tin hoặc cảm ơn ngắn. Câu hỏi, trích dẫn, điều kiện, ngữ cảnh mơ hồ không đổi điểm.
- Hiện evaluator thay đổi affinity/trust/respect/rivalry; ba chiều còn lại dự phòng, không tự bịa ghen tuông hay tình cảm.
- Nhãn deterministic: rival khi rivalry ≥18 và trust <15; suspicious khi rivalry ≥6 và trust ≤2; friend khi affinity ≥30 và trust ≥35; còn lại introduced/acquaintance.
- Zero là chưa có bằng chứng cảm xúc, không tự hiểu là ghét.

Không gọi thêm LLM/JEV/classifier cho tính năng này. Có thêm truy vấn SQL, tải ảnh biểu cảm hiện có và context prompt: tối đa 12 liên kết, 3 trích dẫn gần nhất/cặp, khoảng 5.500 ký tự dữ liệu liên kết. Đây là giới hạn ký tự, không phải token đo được. Không tuyên bố miễn phí token.

Canon đã được chuẩn bị đáng tin cậy có thể xác lập quan hệ nền ngay, nhưng không tạo ngày gặp hay receipt giả. Diễn biến đối đầu không xóa quan hệ nền. Hiện chưa có màn hình CMS mới cho canon này và không có endpoint cho user tự ghi.

## Ranh giới riêng tư

Context của A chỉ có dữ kiện A được phép biết, trạng thái A → B và lời đã nói trong phòng chung có nguồn hợp lệ. Không đưa prompt riêng, biography đầy đủ, memory riêng, chat riêng hoặc quan hệ user–B của B vào context A. Roster nhóm chỉ chia sẻ ID/tên/vai trò.

Tên/vai trò được chụp tại lúc giới thiệu; sửa card B sau đó không âm thầm cập nhật điều A đã học. Không tự gửi toàn bộ catalog vào prompt. Mention chỉ gợi ý khi khớp duy nhất một nhân vật đã sở hữu; cần user xác nhận.

Mỗi nguồn trích dẫn được đối chiếu owner/phòng/nội dung/fingerprint khi đọc. Nguồn bị sửa/xóa thì không nhắc lại trích dẫn cũ; số lượt lịch sử vẫn được giữ. Không đưa private text vào analytics mới. Chưa tìm thấy nhà cung cấp analytics cho luồng này.

Ngắt kết nối đặt active=false cả hai hướng; không xóa nhân vật, knowledge, canon hay lịch sử. Xóa nhân vật mới dọn các tham chiếu social của nhân vật đó. Không có reset/forget phá dữ liệu.

## API hiện có

| Method | Path |
| --- | --- |
| GET/POST | /v1/roleplay/characters/{character_id}/connections |
| GET | /v1/roleplay/characters/{character_id}/connection-suggestion |
| GET/DELETE | /v1/roleplay/character-connections/{connection_id} |
| POST | /v1/roleplay/character-connections/{connection_id}/introduce |
| POST | /v1/roleplay/character-connections/{connection_id}/shared-interaction |

Mọi route kiểm owner. Body không nhận state, điểm hoặc delta. Receipt endpoint chỉ nhận room_id/source_message_id, kiểm tra lại bản ghi server. Không có route /meet hoặc PUT /canon. Tạo nhóm vẫn qua POST /v1/rooms hiện có, do user chủ động.

## Trải nghiệm

Chat riêng → Mối liên kết → chọn nhân vật → chạm sợi nối. Hai chân dung có hiệu ứng sợi sáng đang chờ; chỉ sau thành công mới nối hoàn chỉnh, lóe sáng và phản ứng surprised khoảng 1,2 giây. Dùng ảnh surprised có sẵn; thiếu ảnh thì chân dung/hiệu ứng ! vẫn dùng được. Lỗi API rút sợi, không hiển thị thành công giả. CSS được giới hạn bằng cs* và sửa xung đột header với chat hiện tại.

Dialog có nhãn, focus bàn phím, Escape và thông báo trạng thái; reduced motion không chạy hoạt ảnh chuyển động. Mobile có bố cục nhỏ hơn. Không hiện điểm nội bộ. Bảng chỉ cho xem mức quen biết, số lượt, ngày gặp, kiến thức tối thiểu và ngắt/nối lại.

UI có tiếng Việt/Anh và dùng bộ dịch UI hiện có nếu có bản dịch; những chuỗi ngôn ngữ khác còn thiếu sẽ fallback Anh, chưa được dịch đầy đủ. Không dùng provider dịch có phí trong kiểm thử.

## Kiểm chứng và giới hạn

- 20 kiểm thử social: mặc định UNKNOWN, owner/scope, giới thiệu, privacy hai chiều, snapshot, receipt giả/lặp, partial/greeting, hướng độc lập, clamp, canon không do user ghi, disconnect, nguồn bị xóa, mention mơ hồ, POST/SSE và migration cũ.
- Bộ hồi quy chọn lọc social + chat/lore/memory + routing/JEV + World + API contract: **174 passed**.
- TypeScript/Vite build thành công. Còn cảnh báo bundle >500 kB và thiếu một số chuỗi dịch UI.
- Chạy thêm tests/test_app.py: 48 passed, 7 failed. Sáu lỗi dừng tại kiểm duyệt tạo nhân vật với character_policy_unavailable; một lỗi kỳ vọng trạng thái tạo biểu cảm failed nhưng code hiện trả default-icons. Các nhánh này nằm ngoài thay đổi social; chưa sửa chính sách kiểm duyệt/GPU để làm test qua.
- Kết quả trình duyệt và ảnh: xem ACCEPTANCE.md.

Prompt hạn chế bịa quan hệ và chỉ cung cấp dữ kiện được phép. Điều này không chứng minh LLM không bao giờ hallucinate; chưa nghiệm thu hành vi với provider thật. Evaluator chưa phân tích mọi loại phản bội/quà/ghen hay mọi ngôn ngữ. Không chứng nhận tải/concurrency production; chưa deploy/push.

## Dùng lại cho World sau này

Các bảng có scope, owner, nguồn và hướng rõ ràng. World phải truyền scope riêng và kiểm quyền/witness theo scene qua adapter được duyệt; không tự dùng graph Roleplay. V1 không sửa runtime World hay tự chuyển memory từ chat sang World.
