# Nguồn mở và quyết định kỹ thuật cho Worlds demo

Đọc trực tiếp ngày 16/10/2026. Chỉ tham khảo nguồn chính thức; không cài thêm framework, tải weights hoặc sao chép implementation bên ngoài.

| Nguồn đã đọc | Ý tưởng áp dụng | Hiện trạng |
| --- | --- | --- |
| SillyTavern World Info | activation/relevance theo keyword/alias, scan/context budget | Lọc quyền trước ranking; chuẩn hóa dấu/hoa thường; giới hạn ký tự lore. Chưa recursion hoặc vector matching |
| Ink | choices, variables, conditions, branching narrative | Backend rule engine kiểm tra địa điểm/manh mối/kết thúc; d20 chỉ ở tình huống cụ thể |
| LangGraph persistence | định danh một luồng, checkpoint, khôi phục trạng thái | Journey ID, revision, snapshot và branch riêng. Không import LangGraph |
| Hugging Face multilingual-e5-small | candidate cho semantic retrieval đa ngôn ngữ, query/passages có prefix theo model card | Chỉ nghiên cứu. Chưa tải model hoặc đo CPU/quality |

Nguồn:
- [SillyTavern World Info implementation](https://github.com/SillyTavern/SillyTavern/blob/release/public/scripts/world-info.js)
- [SillyTavern license](https://github.com/SillyTavern/SillyTavern/blob/release/LICENSE)
- [Ink — Writing with Ink](https://github.com/inkle/ink/blob/master/Documentation/WritingWithInk.md)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [multilingual-e5-small model card](https://huggingface.co/intfloat/multilingual-e5-small)

## Vì sao chưa nhúng các repo vào dự án

SillyTavern có license AGPL-3.0; demo dùng ý tưởng thiết kế và implementation tự viết, không chép source. Ink và LangGraph là nguồn tham khảo cho state/branch; đưa thêm runtime vào lúc này làm tăng phạm vi tích hợp và kiểm thử. E5 model card ghi MIT; trước khi tích hợp vẫn cần pin revision, kiểm tra dependencies/giấy phép và đo tài nguyên, latency, retrieval quality trên câu Việt/Anh thực tế.

## Thứ tự nâng cấp sau demo

1. Đo lỗi truy hồi thực tế với keyword/alias, không mặc định cần vector DB.
2. Thử embedding CPU hoặc provider API sau khi lọc quyền; không đưa private memory của mọi user vào một kho truy hồi không có scope.
3. Cân nhắc typed event tables và migration khi campaign/state lớn, hoặc cần analytics/cộng tác.
4. Chỉ thêm director LLM ở mốc truyện khi rules không đủ; có budget và fallback.
5. Tách đề xuất AI khỏi canon; creator duyệt trước khi publish.
