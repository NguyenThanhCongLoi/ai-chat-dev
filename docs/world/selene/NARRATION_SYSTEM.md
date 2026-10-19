# Bốn loại đầu ra

NARRATION: chữ cảnh/điện ảnh, nhãn người kể, không có avatar Selene. Có TTS narrator khi cấu hình riêng.
CHARACTER_SPEECH: lời Selene, tên/ảnh Selene; dùng model TTS và Voice ID đang gán cho chat thường.
CHARACTER_THOUGHT: thẻ/bubble suy nghĩ, dấu chấm và biểu cảm; không TTS.
SYSTEM: manh mối/objective/chapter/memory feedback; không TTS.

Phân loại bằng event.type, không đoán qua dấu *, ngoặc hay format text. Voice endpoint từ chối thought/system trước khi gọi provider.

Registry các event theo yêu cầu nằm trong visual_events, gồm duration/animation/audio/vfx/skippable/reduced_motion. V1 có hiệu ứng CSS thực tế cho intro, chuyển cảnh, suy nghĩ, clue, memory/chapter; các loại memory reconstruction/Arc complete là slot cho chương sau, không phải gameplay đã triển khai.

Narrator EN/VI phải khác giọng Selene. Backend chặn trùng ID; không dùng giọng nhân vật làm fallback người kể.
