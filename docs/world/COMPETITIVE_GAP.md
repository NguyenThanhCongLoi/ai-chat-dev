# So sánh có kiểm chứng

Ngày đọc nguồn: 17/10/2026. Baseline: [nghiên cứu gốc](../research/ai_role_play_research_2026.md). Đánh giá khả năng công khai được mô tả, không chấm chất lượng thực nghiệm hay thuật toán nội bộ.

BASIC = có cơ chế hẹp; GOOD = có đường dùng hoàn chỉnh được tài liệu hóa; ADVANCED = nhiều chiến lược/lớp có thể cấu hình; NONE = không có trong scope chúng ta kiểm tra; UNKNOWN = không đủ bằng chứng. Một nhãn ADVANCED không có nghĩa câu trả lời hay hơn. Cột ours tách S chat thường/W Academy khi cần. Không lấy feature legacy cộng vào W.

| System | Ours | Character.AI | Kindroid | SpicyChat | SillyTavern | ISEKAI ZERO | AI Town |
|---|---|---|---|---|---|---|---|
| Long-term memory | BASIC S; BASIC W | GOOD [C2] | UNKNOWN [K] | GOOD [S2] | GOOD [ST3] | BASIC [I2] | GOOD [ATM] |
| Lorebook | GOOD S; BASIC W public lore | GOOD [C1] | UNKNOWN [K] | GOOD [S1] | ADVANCED [ST1] | BASIC [I2] | UNKNOWN [AT] |
| Shared story memory | BASIC | BASIC shared canon [C1] | UNKNOWN [K] | UNKNOWN [S2] | BASIC shared group history [STG] | GOOD được hãng mô tả [I1] | GOOD shared state [AT] |
| Knowledge visibility | BASIC ACL; W còn lỗi | UNKNOWN [C1] | UNKNOWN [K] | UNKNOWN [S1] | BASIC character filters [ST1] | UNKNOWN [I1] | UNKNOWN [AT] |
| Relationship state | BASIC | UNKNOWN [C2] | UNKNOWN [K] | UNKNOWN [S2] | UNKNOWN [STG] | UNKNOWN [I2] | UNKNOWN [AT] |
| Character ↔ character relationship | NONE S; BASIC W | UNKNOWN [C2] | UNKNOWN [K] | UNKNOWN [S2] | UNKNOWN [STG] | UNKNOWN [I1] | UNKNOWN [AT] |
| Group chat | GOOD S; BASIC W | UNKNOWN trong nguồn đã đọc [C2] | UNKNOWN [K] | UNKNOWN: chưa đọc trang group [S2] | GOOD [STG] | GOOD cast-based story [I1] | GOOD hội thoại trong simulation [AT] |
| Speaker router | GOOD S; BASIC W | UNKNOWN [C2] | UNKNOWN [K] | UNKNOWN [S2] | ADVANCED [STG] | UNKNOWN [I1] | BASIC agent lifecycle [AT] |
| Scene state | BASIC | BASIC format Books [C4] | UNKNOWN [K] | UNKNOWN [S3] | BASIC scenario override [STG] | GOOD visual-novel scene [I2] | GOOD position/conversation [AT] |
| Quest | BASIC W | BASIC playable narrative [C4] | UNKNOWN [K] | UNKNOWN [S2] | UNKNOWN [STG] | BASIC authored adventure [I1] | UNKNOWN [AT] |
| Branching | BASIC W endings | BASIC AU/story modes [C4] | UNKNOWN [K] | UNKNOWN [S2] | BASIC branched chats [STG] | BASIC choices [I2] | UNKNOWN [AT] |
| Proactivity | BASIC in-turn S/lazy W | UNKNOWN [C2] | UNKNOWN [K] | UNKNOWN [S2] | BASIC opt-in auto-mode [STG] | UNKNOWN [I2] | ADVANCED autonomous agents [AT] |
| Voice | BASIC; provider chưa test | UNKNOWN trong nguồn này [C7] | UNKNOWN [K] | BASIC TTS được docs dẫn [S2] | UNKNOWN [STG] | GOOD voice/audiobook [I2] | UNKNOWN [AT] |
| Timeline | BASIC; capped W | UNKNOWN [C2] | UNKNOWN [K] | UNKNOWN [S2] | UNKNOWN [STG] | UNKNOWN [I2] | UNKNOWN UI timeline [AT] |
| Creator world | NONE self-service W; admin lore có | GOOD shared published lore [C1] | UNKNOWN [K] | GOOD creator lore [S1] | GOOD local authoring [ST1] | GOOD authoring/publishing được hãng mô tả [I2] | BASIC forkable project [AT] |

Các ô không phải khẳng định hai cơ chế bằng nhau: shared canon không phải shared event memory; AU không phải checkpoint gameplay; local authoring không phải marketplace; autonomous simulation không phải proactive notification cho companion.

## Xác minh và điều chỉnh baseline

| Nhận định baseline | Kết quả đọc nguồn hiện tại | Cách sử dụng |
|---|---|---|
| SpicyChat keyword lore, 4 message, khoảng 2 lượt và khoảng 20% context | Đọc được đúng mô tả trong [S1] | Dùng để học activation/budget; không sao chép quota gói vào sản phẩm mình |
| Character.AI Lorebook dùng chung nhiều character | [C1] mô tả entry keyword, link nhiều character, viewer/editor, beta | Có cơ sở so sánh CMS lore; không suy ra vector search/ACL bí mật |
| Story Memory/Facts/Memory Usage | [C2] mô tả pin, facts sửa được, nén lịch sử nền | So sánh trải nghiệm kiểm soát memory; backend ranking nội bộ UNKNOWN |
| Kindroid persistent/cascaded/retrievable, proactive, max 10 group | Các URL baseline trả trang shell “Connection looks slow”; tên miền docs thay thế trả 404 | Chưa xác minh trong lượt này. Không dùng các con số/kiến trúc đó để kết luận |
| ISEKAI shared memory/dice/VN | [I1] là bài do chính hãng viết; [I2] là about | Ghi là hãng công bố, chưa kiểm nghiệm chất lượng hay boundary thật |
| Comics/Animate Comics đều đã có | [C6] phân biệt Comics với Animate “launching soon” | Không coi Animate đã phát hành chỉ vì có roadmap |
| c.ai Series là user tự tạo series | [C7] mô tả studio-made trước, creator tools là hướng tương lai | Không coi công cụ creator tương lai đã hoạt động |
| SillyTavern routing cần LLM | [STG] mô tả mention/talkativeness/random/list/manual | Routing cơ bản không cần inference mới |
| AI Town áp dụng nguyên xi cho app | [AT] simulation ticks, engine state, scheduler; [ATM] memory/reflection | Học state invariants và retrieval; không bê vòng lặp tốn chi phí vào chat |

## Học gì để giải bài toán nào?

- **Character.AI:** cho người dùng kiểm soát điều AI nhớ; lore dùng lại giữa nhiều character. Chúng ta đã có pin/editor/entry target, còn thiếu UX memory usage theo token, tự nén đáng tin cậy. [C1][C2]
- **SpicyChat:** tránh nhét toàn bộ canon mỗi lượt; keyword và ngân sách context là giải pháp rẻ. Chúng ta tương tự ở keyword, thêm ACL trước match, chưa semantic memory tương đương. [S1][S2]
- **SillyTavern:** người nói đúng và lore đúng context; cấu hình insertion/recursion/activation phong phú. Chat thường học unique-name mention và cap automatic replies, chưa cần gọi director LLM mỗi lượt. [ST1][STG]
- **ISEKAI ZERO:** giảm “không biết nói gì” bằng cốt truyện, lựa chọn và scene. Academy mới đạt authored demo; chat tự do chưa nối vào nhiệm vụ. [I1][I2]
- **AI Town/Generative Agents:** kiến thức và hành vi cần state + observations + retrieval, không chỉ system prompt dài. Paper dùng relevance/recency/importance, reflection/planning; không là bằng chứng retention cho sản phẩm chúng ta. Nên thử recap theo sự kiện và scheduler có hạn mức sau khi core đúng. [AT][ATM][GA]

## Nguồn chính thức đã mở

[C1]: https://blog.character.ai/lorebook/
[C2]: https://blog.character.ai/memory/
[C4]: https://blog.character.ai/cai-books/
[C6]: https://blog.character.ai/cai-comics/
[C7]: https://blog.character.ai/cai-series/
[C8]: https://blog.character.ai/creator-bundle/
[S1]: https://docs.spicychat.ai/product-guides/lorebook
[S2]: https://docs.spicychat.ai/product-guides/premium-features
[S3]: https://docs.spicychat.ai/product-guides/premium-features/conversation-images
[ST1]: https://docs.sillytavern.app/usage/core-concepts/worldinfo/
[ST2]: https://docs.sillytavern.app/usage/core-concepts/data-bank/
[ST3]: https://docs.sillytavern.app/extensions/chat-vectorization/
[STG]: https://docs.sillytavern.app/usage/core-concepts/groupchats/
[I1]: https://www.isekaizero.ai/blog/zeta-ai-review
[I2]: https://www.isekaizero.ai/about
[AT]: https://github.com/a16z-infra/ai-town/blob/main/ARCHITECTURE.md
[ATM]: https://github.com/a16z-infra/ai-town/blob/main/convex/agent/memory.ts
[GA]: https://arxiv.org/abs/2304.03442
[K]: https://kindroid.ai/v2/docs/memory/

Mã nguồn ngoài được đọc trên nhánh main tại thời điểm kiểm tra, không pin commit. Snapshot text và kết quả tải ở artifacts/audit (artifact local, không dữ liệu người dùng). Không cài dependencies hay sao chép implementation từ các repo đó.
