# Xưng hô và giọng nói theo quan hệ

Áp dụng tự động cho chat Roleplay đơn và nhóm, tính riêng cho từng user–nhân vật. Không áp dụng lên các câu thoại World cố định. Không ghi lại card, prompt hoặc lorebook trong CMS.

## Các mốc mặc định

| Mốc | Điều kiện tối thiểu |
|---|---|
| Mới quen | Chưa đạt các mốc dưới |
| Quen thuộc | Familiarity 16%, trust 8% |
| Thân thiết | Familiarity 52%, trust 20%, affinity 10% |
| Gắn bó | Familiarity 75%, trust 35%, affinity 20% |

Sau khi đã khởi tạo trạng thái, mỗi bước chuyển cần 3 lượt user khác nhau đủ điều kiện. Retry và regenerate của cùng tin nhắn không tăng mốc. Quan hệ đã tích lũy từ trước được nhận đúng mốc khi tính năng bắt đầu chạy. Cảm xúc nhất thời không kéo lùi cách xưng hô.

Đây là ngưỡng của relationship (familiarity/trust/affinity), không phải phần trăm biểu cảm hiện thời. Không đọc mốc theo mood hoặc cơn dỗi của một câu.

## 11 hồ sơ mặc định

| Nhân vật | Mới quen (nhân vật – user) | Khi quen hơn |
|---|---|---|
| Liost | tôi – bạn | mình – cậu |
| Nguyễn Vũ | tôi – bạn | tôi – cậu |
| Merr | tôi – cậu | mình – cậu |
| Ruby | tôi – bạn | tôi – cậu |
| KimAnh | mình – bạn | mình – cậu |
| Trịnh Khải Nguyên | tôi – bạn | tôi – cậu |
| Aurelion Voss | ta – ngươi | tôi – cậu |
| Selene Moonbrook | ta – ngươi | tôi – cậu |
| Mira Sunpetal | mình – bạn | mình – cậu |
| Ren Quickshade | tôi – cậu | tôi – cậu |
| Lyra Ashveil | ta – ngươi | tôi – cậu |

Ở mức thân thiết/gắn bó, nhân vật có thể gọi tên hiển thị của user trong những thời điểm có ý nghĩa. Không gọi tên ở mọi câu. Không tự đặt biệt danh tình cảm, đoán tuổi/giới tính hoặc ép anh–em. Merr vẫn có thể dỗi nhẹ đúng ngữ cảnh; Selene vẫn thanh lịch và tò mò; Lyra vẫn dè dặt.

## Thứ tự ưu tiên

1. An toàn, quyền riêng tư và ngôn ngữ đầu ra.
2. Cách xưng hô/tên gọi user đã yêu cầu rõ ràng.
3. Cá tính và card hiện có.
4. Gợi ý theo mốc quan hệ khi chưa có yêu cầu khác.

Ngoài tiếng Việt, prompt yêu cầu diễn đạt tự nhiên theo văn hóa của ngôn ngữ đầu ra, không dịch máy cặp đại từ. Tên riêng giữ nguyên. Tên hiển thị là dữ liệu, không phải lệnh.

## Cơ chế và quản lý

- Hồ sơ 11 nhân vật: `character_chat/story_data/relationship_voices.json`.
- Chọn mốc, chống dao động và tạo chỉ dẫn ngắn: `character_chat/relationship_voice.py`.
- Chỉ dẫn được gắn vào post-history context của đúng người đang nói, không gọi thêm LLM.
- State lưu bằng AppSetting có khóa hash của user và character; reset phòng theo cơ chế hiện có sẽ xóa state của đúng user.
- Chưa thêm bảng chỉnh mốc/xưng hô riêng trong CMS. Các hồ sơ trên là cấu hình trong source; prompt riêng vẫn chỉnh cá tính và giọng văn. Không cần dán thêm 11 đoạn quy tắc vào lorebook.
- Đây là chỉ dẫn cho model; cách dùng từ cụ thể còn phụ thuộc model, nên cần nghiệm thu vài cuộc trò chuyện thật.

## Quay về từ World

URL quay về gắn `from_world=1`. Khi nạp phòng, client chọn duy nhất tin nhắn mới nhất của nhân vật để phát, thay cho lời chào đầu phòng. Mở phòng theo đường thông thường giữ hành vi cũ. Vẫn tuân theo cài đặt tự đọc và khả năng hỗ trợ TTS của chat.
