# Chat thường: recap, góc nhìn, sự kiện và gợi chuyện

Cập nhật ngày 16/10/2026. Bổ sung trên nhánh thử nghiệm, chưa deploy hoặc push.

## Dùng thế nào?

Chat Bot AI → mở phòng → Ký ức & cốt truyện → Nhật ký phiên → Nhật ký phiên.
Chọn Góc nhìn nhân vật rồi bấm Tạo recap AI. Model chat cần được phân công trong CMS.
Bật cả Dùng ký ức và Tự ghi nhớ để tạo bản mới. Nút này có thể phát sinh phí API.

- Tóm tắt tối đa 60 tin nhắn gần nhất, trong ngân sách khoảng 16000 ký tự; có thể ít hơn.
- Mỗi nhân vật giữ một bản riêng theo phòng. Không tự gom ký ức giữa nhiều tài khoản/phòng.
- Có thể sửa tóm tắt/góc nhìn hoặc xóa. Đổi nhân vật để xem góc nhìn khác.
- Bấm lại khi nguồn không đổi sẽ trả bản đã lưu, không gọi model viết recap lại.
- Đây là ghi chú theo cửa sổ hội thoại, chưa phải thư viện episode toàn bộ lịch sử.

## Các kỹ thuật đã làm

| Kỹ thuật | Bản hiện tại |
| --- | --- |
| Recap AI | Tạo theo yêu cầu, schema có giới hạn, kiểm duyệt kết quả, nguồn và quyền phòng |
| Persona-specific Memory | Bản đầu: một perspective riêng theo giá trị/mục tiêu của character card; lưu độc lập với recap của nhân vật khác |
| Event Graph nhẹ | Node sự kiện có nguồn; liên kết listed_after theo thứ tự model liệt kê, không khẳng định nhân quả |
| Initiative Planner nhẹ | Luật không gọi API, tối đa một lời mời tùy chọn mỗi 4 lượt user; model có thể bỏ qua nếu không phù hợp |

Góc nhìn là suy luận có thể sai. Tóm tắt và câu nói nhân vật không biến thành sự thật đã xác minh hoặc canon.
Sự kiện được kiểm tra ID nguồn thuộc đúng dữ liệu đã gửi; việc câu tóm tắt diễn giải đúng nội dung vẫn cần người dùng đánh giá.
Graph hiện hiển thị thành chuỗi dễ đọc, chưa là đồ thị tương tác hoặc causal reasoning engine.

## Đưa vào prompt

Khi Dùng ký ức bật, engine lấy bản của đúng user/phòng/nhân vật và chỉ dùng nếu tất cả nguồn còn nguyên.
Khối episode_and_initiative được đánh dấu dữ liệu tham khảo, không phải instruction hoặc canon.
Nguồn sửa/xóa làm bản cũ mất hiệu lực. Xóa tin nhắn qua luồng purge cũng xóa recap phụ thuộc.
Bỏ nhân vật hoặc xóa phòng dọn ghi chú tương ứng.

Recap chỉ đọc lời thoại chung trong phòng và persona của chính nhân vật.
Không gửi lore riêng của người khác, private reflections, provider keys hoặc system prompt vào model tóm tắt.
Lịch sử phòng hiện vẫn là lịch sử chung: chưa có audience riêng trên từng message hoặc lọc theo thời điểm NPC gia nhập.

## Gợi chuyện

Không có tin nhắn tự phát ngoài lượt chat. Không đặt nhiệm vụ/vật phẩm hay tự di chuyển nhân vật.
Sau mỗi 4 lượt user, có thể thêm một gợi ý mềm từ recap/bối cảnh đang được phép dùng.
Lời nhắc “chỉ lắng nghe”, “tạm dừng”, “just listen”, “pause”… bỏ gợi ý trong lượt đó.
Đây là heuristic VI/EN, chưa là bộ nhận diện ý định đa ngôn ngữ. Không thay JEV speaker router hoặc tự mời thêm nhân vật.
Tắt Dùng ký ức cũng bỏ episode và gợi chuyện. Chưa có công tắc riêng cho initiative.

## Môi trường, dữ liệu và chi phí

Không GPU/dependency mới, không migration schema. Dữ liệu JSON nằm trong AppSetting với prefix roleplay_episode:.
Bản backup DB hiện có chứa các ghi chú này.
JEV làm kiểm duyệt/phân loại nếu bật; model chat viết recap.
Không dùng JEV để tạo văn bản tóm tắt. Không tự gọi recap sau mỗi tin nhắn.
Mỗi bản mới tối đa một lượt model, cộng lượt kiểm duyệt cấu hình hiện có.

## Giới hạn còn lại

Chưa làm Dynamic Cast, Director nhiều agent, Cinematic Detection, soundscape tự động, marketplace hoặc phòng nhiều người thật.
Những mục đó không được coi là hoàn thành bởi bản cập nhật này.
AI provider thật, chất lượng recap đa ngôn ngữ và load production chưa được đo.

## Code

- character_chat/roleplay_episode.py: schema, fingerprint, source window, context và planner.
- character_chat/api/roleplay_continuity.py: API owner-only GET/POST/PUT/DELETE episode.
- frontend/src/roleplay/EpisodeNotes.tsx: tạo/sửa/xóa/nguồn sự kiện trong dialog hiện có.
- tests/test_roleplay_episode.py: ownership, consent, cache, invalid source, race và purge.

## Xác minh

- 127 tests liên quan đạt: episode/continuity, JEV, routing, character policy, Worlds và API contract.
- TypeScript/Vite build đạt; 623 nhãn UI × 6 bản dịch ngoài tiếng Việt đầy đủ theo catalog. Chưa QA bản dịch bởi người bản ngữ.
- Edge với DB giả lập riêng: đọc ghi chú, sửa, xem nguồn, refresh cache và xóa đạt. Không gọi provider thật.
- Bộ test ứng dụng rộng hơn từng còn 7 lỗi cấu hình moderation/avatar đã ghi ở JEV_INTEGRATION.md; không tuyên bố toàn bộ suite xanh.
- Chưa push hoặc deploy Modal. Sau deploy, thử recap bằng model/key thật đã cấu hình trong CMS.

## Phân chia trải nghiệm — 16/10/2026

Có tab Trải nghiệm cạnh Nhân vật của tôi / Nhân vật hệ thống / Cộng đồng.
Worlds là lựa chọn riêng cho cách chơi thẻ, nhiệm vụ và manh mối; dùng chung catalog nhân vật nhưng tiến trình riêng.
Nút phiêu lưu đã bỏ khỏi thanh công cụ chat thường. Tab mới có lối quay về chọn nhân vật trò chuyện.
Recap, góc nhìn, context, cảm xúc và gợi ý không yêu cầu đổi cách chat nên vẫn hỗ trợ chat thường.
Recap vẫn là thao tác theo yêu cầu để kiểm soát phí; không tự chạy sau mỗi tin.
Direct link: /role-play-ai?workspace=1&view=experiences.
