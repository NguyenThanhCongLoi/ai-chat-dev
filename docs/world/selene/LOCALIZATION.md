# Ngôn ngữ văn bản và audio

content_language được chọn khi bắt đầu lượt; voice_language là thiết lập riêng ở UI, mặc định EN/VI tương ứng nếu có, Off cho các ngôn ngữ khác. Không tự đọc khi chưa bật auto-reader/nhấn nghe.

Story authoring có dict vi/en tối thiểu; CMS cho bổ sung ja/zh/ko/my/km. Chưa có bản dịch thì hiện EN và ghi chú fallback, không giả vờ mọi story đã được dịch. Hội thoại AI vẫn yêu cầu content_language.

TTS chỉ VI/EN. Chọn voice EN/VI khi dùng text ngôn ngữ khác phải là hành động rõ ràng; authored line lấy bản dịch có sẵn. AI line cần dịch bằng provider đã gán, có moderation; phụ đề không đổi. Không gửi trực tiếp text JA/ZH/... vào VI/EN TTS.

UI mới có VI/EN fallback; các bản dịch UI khác phụ thuộc pack hiện có, chưa hoàn thiện toàn bộ. Một logic chương dùng chung cho mọi locale.
