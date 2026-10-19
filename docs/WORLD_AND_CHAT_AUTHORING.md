> Cập nhật 16/10/2026: chat thường đã có [CMS Lorebook riêng](ROLEPLAY_LOREBOOK_CMS.md). World hiện dùng Moonfall Academy; [hai ô CMS World và nội dung mẫu](world/MOONFALL_CMS_COPY.md). Các mô tả journey/template dưới đây thuộc phiên bản Worlds cũ.

> Cập nhật tiếp ngày 16/10/2026: đã có recap AI theo yêu cầu, góc nhìn riêng, chuỗi sự kiện có nguồn và initiative theo luật. Xem [bản cập nhật episode](ROLEPLAY_EPISODE_UPDATE.md); trạng thái bên dưới mô tả bản trước.

# Viết prompt, lorebook và nội dung Worlds / Chat Bot AI

Ngày 16/10/2026. Đây là hướng dẫn cho code hiện có, tách rõ chức năng đã có với công cụ tác giả còn cần xây.

## 1. Prompt và lore làm hai việc khác nhau

- Prompt: quy định AI kể/nói ra sao, giữ persona, xử lý dữ liệu, tôn trọng người chơi và luật.
- Lore: nhân vật biết điều gì về địa điểm, lịch sử, vật phẩm, lời hứa và bí mật.
- Quest engine: xác nhận điều kiện, phần thưởng, vật phẩm, tiến trình và kết thúc.
- Character card: danh tính, cá tính, cách nói, động cơ và giới hạn riêng.

Không đưa toàn bộ bí mật vào narrator prompt rồi mong AI tự giữ kín. Không viết lệnh “hoàn thành nhiệm vụ”, “cộng trust” hoặc “tặng vật phẩm” vào lore để thay logic backend.

## 2. Prompt cho Worlds — dùng được ngay

File đầy đủ: [bản prompt lịch sử](world/LEGACY_WORLD_NARRATOR.txt) — chỉ tham khảo phiên bản cũ

CMS /worlds/admin → chọn thế giới → Người dẫn chuyện → chọn model → Prompt bổ sung cho thế giới.

Nếu ô prompt đang trống, có nút Dùng prompt mẫu. Nút chỉ điền bản nháp; Lưu phiên bản mới ghi vào DB. Không tự đè prompt đang có.

Prompt mẫu bằng tiếng Anh; yêu cầu đầu ra theo language của chuyến đi. Có các quy tắc: kể committed_event, giữ persona actor, không viết hành động/lời nói user, không tự tạo quest/vật phẩm/NPC, không dùng lore chưa được cấp, tin đồn không phải sự thật, cho phép giao lưu ngoài nhiệm vụ.

Muốn AI tự do trả lời: ngoài model/credentials trong CMS, cần JEV đã bật hoặc WORLD_MODERATION_API_KEY/OPENAI_API_KEY trên backend. Xem [cấu hình JEV](JEV_INTEGRATION.md). Thiếu moderation thì free text bị khóa; lỗi narrator sẽ dùng lời thoại soạn sẵn. Chọn model không tự cấu hình được dịch vụ moderation.

Journeys chụp phiên bản world khi bắt đầu. Đổi prompt/lore trong CMS không thay nội dung snapshot của chuyến đi cũ; tạo chuyến đi mới để thử bản vừa lưu.

## 3. Prompt bổ sung cho chat thường

File: [ROLEPLAY_PROMPT_ADDENDUM.txt](ROLEPLAY_PROMPT_ADDENDUM.txt)

Có thể nối vào cuối System prompt theo tác vụ → Trả lời hội thoại của model được phân công Roleplay, hoặc dùng làm hướng dẫn bổ sung khi biên tập system_prompt nhân vật. Giữ prompt/cá tính cũ; không thay cả character card bằng một prompt chung.

Engine đã tự thêm scene/lore/memory có scope vào prompt, nên không cần chép lại nội dung lore vào system prompt. Addendum chỉ mô tả cách dùng dữ liệu đó.

## 4. Lorebook Worlds nên viết gì?

Mỗi mục ngắn, một ý, có tên/alias và phạm vi phù hợp:

| Loại | Nội dung ví dụ | Thiết lập CMS hiện có |
| --- | --- | --- |
| Luật thế giới | “Thời gian chỉ tiến khi người chơi hành động. Không ai bị phạt vì rời ứng dụng.” | public, canon; keywords: thời gian, nghỉ, time |
| Địa điểm | “Quán trọ Cánh Hoa là nơi người giữ đèn nghỉ sau ca trực. Lời kể của khách chưa chắc chính xác.” | public, canon; keywords: quán trọ, người giữ đèn, inn |
| Vật phẩm | “Nguyệt Thạch duy trì phong ấn; trả về sai thời điểm có thể làm phong ấn yếu đi.” | discovered, unlock=tower, canon; keywords: nguyệt thạch, nghi lễ, seal |
| Tin đồn | “Có người nói một lữ khách đã lấy chiếc hộp. Chưa có bằng chứng xác nhận.” | rumor, canon=false; keywords: lữ khách, trộm, traveller |
| Bí mật truyện | “Chiếc hộp có thể đang che chở một người vô tội; cần đối chiếu bằng chứng trước khi công khai danh tính.” | discovered, unlock=forest, canon |

World CMS hiện có public/rumor/discovered với điều kiện mở theo địa điểm đã tìm được manh mối. Chưa có editor gán lore private cho từng NPC trong template world. Lời chứng riêng trong gameplay dùng witnesses của manh mối và thao tác báo cáo/chia sẻ trong engine.

Tên địa điểm, luật di chuyển, manh mối và ba nhiệm vụ hiện là khung chương demo trong code. Viết lore về một địa điểm hoặc vật phẩm mới chưa tự tạo nút di chuyển, card hoặc quest cho chúng.

## 5. Lorebook chat thường nên viết gì?

Vào phòng chat → Ký ức & cốt truyện → Bối cảnh → Nâng cao → Lore & bí mật.

### Ví dụ A: luật một cảnh chung
- Tiêu đề: Thư viện chỉ mở sau tiếng chuông.
- Nội dung: “Trong câu chuyện này, cửa thư viện mở sau tiếng chuông đêm. Các nhân vật chưa có chìa khóa riêng.”
- Ai biết: Cả phòng biết.
- Canon: bật nếu muốn giữ quy tắc nhất quán.
- Luôn xét: bật cho quy tắc xuyên suốt; nếu tắt dùng keywords: thư viện, cửa, tiếng chuông.

### Ví dụ B: lời hứa riêng
- Tiêu đề: Lời hứa với Selene.
- Nội dung: “Người dùng đã nhờ Selene giữ kín vị trí chiếc hộp; chưa kể cho Ren.”
- Ai biết: Một nhân vật biết → chọn Selene từ các thành viên phòng.
- Không đặt entry này public. Nếu đã nói nội dung đó trong lịch sử nhóm, không thể làm các nhân vật quên bằng cách đổi scope sau đó.

### Ví dụ C: tin đồn chưa xác minh
- Tiêu đề: Dấu chân ở tháp.
- Nội dung: “Người gác cổng cho rằng bóng áo trắng là thủ phạm. Đây chỉ là suy đoán, chưa được đối chứng.”
- Ai biết: Tin đồn; canon=false.

### Ví dụ D: điều chỉ được biết sau khám phá
- Tiêu đề: Chữ khắc dưới bàn.
- Nội dung: “Chữ khắc cho biết chiếc hộp được chuyển đi để tránh nghi lễ sai thời điểm.”
- Ai biết: Chờ khám phá. Chỉ bật Đã khám phá khi muốn cho bot biết.
- Chat thường chưa có trigger quest tự động bật mục này.

Ký ức cá nhân ổn định như sở thích, tên, lời hứa nên ghim từ tin nhắn hoặc quản lý ở Ký ức. Lore thích hợp cho bối cảnh/canon. Không lưu API key, mật khẩu hoặc thông tin liên hệ nhạy cảm vào lore.

## 6. CMS làm gì? Người chơi làm gì?

### Đã có
- Admin world: tên, mở đầu, VI/EN, lore, canon/tin đồn, unlock theo địa điểm, model, prompt narrator, duyệt public.
- Người chơi: chọn cast từ kho chung, chọn ký ức mang theo, hành động/giao lưu, giữ tiến trình riêng.
- Chủ phòng chat thường: scene và lore riêng, chọn người biết; không tự đưa vào kho public.
- Admin model: model/credentials/generation settings và prompt theo tác vụ.
- Mẫu prompt là nội dung thường, không có secrets; API key vẫn chỉ lưu qua backend/CMS credentials.

### CMS nên bổ sung tiếp — CHƯA có editor hoàn chỉnh
1. Cast của từng world: gán ID nhân vật thật cho vai truyện, động cơ, nơi gặp; không cần cố định theo thứ tự chọn.
2. Quest editor: giver, prerequisites, objectives, điều kiện mở, vật phẩm/phần thưởng, hệ quả, nhánh.
3. Card editor: thẻ gọi action hợp lệ nào, điều kiện hiện, mặt trước/sau, bản dịch và nội dung minh họa.
4. Knowledge editor theo NPC: người chứng kiến, private facts, reveal/share events.
5. Preview theo góc nhìn NPC và test đường đi trước publication.
6. Version/draft/review; chỉ admin duyệt mới thành canon public.
7. Thư viện template cho chat thường với bước người dùng chủ động áp dụng. Chưa đồng bộ lore phòng riêng ngược về CMS template.

AI director có thể đề xuất nội dung ở bản tiếp theo, nhưng backend vẫn phải kiểm điều kiện; không để model tự cấp thưởng hoặc tự publish canon.

## 7. Worlds bằng thẻ trong bản demo

- Thẻ nhân vật: tới cuộc gặp; giữ tiến trình, có lối quay lại.
- Thẻ hành động: Hỏi nhân vật / Khám phá / Giao lưu / Nghỉ chân.
- Khi đã tới đúng địa điểm của nhân vật, Hỏi nhân vật nhận lời chứng/manh mối soạn sẵn. Không cần trả lời câu đố bằng cách gõ đúng keyword.
- Tab Thẻ chứa bộ sưu tập manh mối. Thẻ chưa tìm chỉ hiện tên địa điểm, không có nội dung bí mật.
- Bấm thẻ chưa tìm để đến địa điểm; khi đã ở đó bấm để tìm. Thẻ đã thu thập có thể lật đọc.
- Hỏi lặp lại không tạo thêm manh mối/phần thưởng. Báo cáo và chia sẻ vẫn theo quyền trong engine.
- Đây là thẻ điều tra, không phải Tarot hay gacha. CSS/SVG, không tải model hoặc sinh ảnh/video GPU.

## 8. Đã áp dụng đủ 17 kỹ thuật cho chat thường chưa?

CHƯA. Không đánh đồng tính năng Worlds với tính năng chat thường.

| Mục 11 | Chat thường hiện tại |
| --- | --- |
| 1 Memory Inspector | Đã nâng: nguồn, confidence, dự kiến/đã dùng, sửa/xóa/ghim, bật/tắt |
| 2 Relationship Timeline | Có một phần: event timeline trong phòng; chưa có đầy đủ loại mốc và tổng hợp nhiều phiên |
| 3 Event Graph | Chưa |
| 4 Scene Engine | Có một phần: location/time/objective thủ công; chưa tự suy diễn scene đầy đủ |
| 5 Knowledge Boundary | Có một phần: scope lore/memory; chưa gán audience cho từng message hoặc mô phỏng người vắng mặt |
| 6 Initiative Planner | Chưa |
| 7 Episodic Recap | Mới có nhật ký trích đoạn, chưa có recap AI/episode library |
| 8 Checkpoint | Chỉ Worlds; chat thường chưa có |
| 9 Canon Lock | Có hướng dẫn và lọc lore trong prompt; chưa phải bảo đảm LLM không thể nói sai |
| 10 Dynamic Cast | Chưa |
| 11 Smart Router | Có từ trước; chưa nâng cấp mới trong đợt này |
| 12 Multi-agent Director | Chưa |
| 13 Cinematic Detection | Chưa |
| 14 Soundscape | Có BGM/SFX từ trước; chưa tự điều phối theo scene đầy đủ |
| 15 Persona-specific Memory | Chưa |
| 16 World Marketplace | Chưa có marketplace/thanh toán; world draft/publication chỉ là bước nền |
| 17 Collaborative Room | Chưa có nhiều người thật; chỉ nhóm AI |

## 9. Kiểm tra bản demo

- 30 tests Worlds/chapter và 1 API contract: đạt.
- TypeScript/Vite build: đạt; còn cảnh báo bundle app lớn có từ trước.
- Edge desktop với DB test riêng: gặp/hỏi nhân vật, lời chứng riêng, lật thẻ và hoàn thành ba nhiệm vụ: đạt.
- Chưa kiểm thử narrator bằng provider thật; chưa deploy Modal/push Git.
