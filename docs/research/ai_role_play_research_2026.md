BÁO CÁO NGHIÊN CỨU
TÍNH NĂNG AI ROLEPLAY / AI COMPANION

SpicyChat • Character.AI • ISEKAI ZERO • Kindroid • SillyTavern và các hướng phát triển có thể học hỏi

Bản nghiên cứu sản phẩm – cập nhật 16/10/2026

Mục tiêu: tìm các cơ chế sản phẩm có thể áp dụng hoặc phát triển thành lợi thế cho một nền tảng AI Companion / AI Roleplay.

Nghiên cứu sản phẩm • 16/10/2026

AI Roleplay / AI Companion – Product Research 2026

1. Tóm tắt điều hành

Thị trường AI roleplay đang chuyển từ mô hình “một chatbot có persona” sang mô hình “nhân vật + thế giới + trí nhớ + cốt truyện + đa phương tiện + creator ecosystem”. Các nền tảng mạnh nhất không chỉ cải thiện chất lượng trả lời, mà còn xây lớp sản phẩm bao quanh LLM để tạo retention, immersion và nội dung có thể tái sử dụng.

Kết luận chính
Những tính năng có giá trị nhất để nghiên cứu không phải là “thêm model lớn hơn”, mà là: Memory có cấu trúc, Lore/World knowledge, shared story state, speaker orchestration, relationship progression, proactive character, scene/media generation và pipeline biến chat thành story/comic/video.

Nhóm

Tính năng tiêu biểu

Giá trị sản phẩm

Ưu tiên

Memory

Long-term memory, Story Memory, Memory Usage, journal

Giảm quên, giữ quan hệ và cốt truyện lâu dài

P0

World

Lorebook / World Info / Codex

Giữ canon, địa điểm, NPC, vật phẩm, luật thế giới

P0

Multi-character

Group chat, speaker routing, shared memory

Biến chat thành scene có nhiều nhân vật

P0

Game/Story

Quest, branch, dice, state machine

Chuyển chatbot thành trải nghiệm chơi được

P1

Multimedia

Voice, image, selfie, visual novel, comic, video

Tăng immersion và khả năng chia sẻ

P1

Proactivity

AI chủ động nhắn/gọi/gửi ảnh

Tạo cảm giác character “sống” ngoài lượt chat

P1

Creator

World/character creator, discovery, monetization

Tăng nguồn nội dung và network effect

P2

2. Lorebook / World Knowledge

2.1. SpicyChat Lorebook

SpicyChat mô tả Lorebook như “world memory” của character. Thay vì nhét toàn bộ worldbuilding vào character description, creator tạo nhiều entry; mỗi entry có keywords và content. Khi keyword xuất hiện trong các message gần nhất, phần content tương ứng được đưa vào context cho LLM. Theo tài liệu hiện tại, SpicyChat quét 4 message gần nhất, entry thường active khoảng 2 lượt, và tổng lore được giới hạn khoảng 20% context để tránh chiếm hết cửa sổ ngữ cảnh. [S1]

User message → scan keywords → activate relevant entries → apply lore token budget → build prompt → LLM response

Ưu điểm: đơn giản, rẻ, deterministic, dễ debug.

Nhược điểm: người dùng có thể diễn đạt đúng ý nhưng không chứa keyword → bỏ sót lore.

Cơ hội cải tiến: hybrid keyword + alias + embedding similarity + entity graph + priority.

2.2. Character.AI Lorebook (2026)

Character.AI ra mắt Lorebook beta trong tháng 7/2026. Lorebook có thể chứa side character, location, item, event, faction, world rules; một Lorebook có thể link với nhiều Character, nhờ đó nhiều nhân vật trong cùng “cast” dùng chung canon. Character.AI cũng có in-chat Lorebook viewer và tag +Lore để discovery. [C1]

Điểm đáng học
Không nên xem Lorebook chỉ là kỹ thuật prompt injection. Nó còn là một “content object” có thể publish, gắn vào nhiều nhân vật, tạo shared universe và trở thành đơn vị discovery.

2.3. SillyTavern World Info: phiên bản linh hoạt hơn

SillyTavern cho phép World Info gắn theo nhiều scope: character lore, persona lore, chat lore hoặc global lore; hỗ trợ nhiều chiến lược insertion, scan depth, recursion và vector storage matching. [ST1] Đây là nguồn tham khảo tốt để thiết kế engine nâng cao hơn các Lorebook chỉ dựa trên keyword.

Cơ chế

Ý nghĩa

Ứng dụng đề xuất

Character Lore

Kiến thức cố định của nhân vật

Backstory/canon riêng

Persona Lore

Kiến thức gắn với persona của user

Một user có nhiều vai khác nhau

Chat Lore

Chỉ có hiệu lực trong một conversation

Scenario tạm thời / campaign riêng

Global Lore

Dùng chung nhiều chat

World/canon toàn hệ

Vector matching

Match theo ngữ nghĩa thay vì keyword

Tìm lore dù user diễn đạt khác

Insertion position

Điều khiển lore nằm ở đâu trong prompt

Tăng/giảm độ ảnh hưởng

3. Memory: từ “nhớ lịch sử chat” đến hệ thống trí nhớ nhiều tầng

3.1. Character.AI Story Memory, Facts và Memory Usage

Character.AI trong 2026 bổ sung Story Memory, Facts và Memory Usage. Người dùng có thể đưa backstory hoặc sự kiện quan trọng vào Story Memory, pin message quan trọng, đồng thời xem phần nào đang tiêu tốn memory. Hệ thống còn nén context cũ trong nền trong khi bảo vệ nội dung đã pin. [C2]

Recent chat + Facts + Story Memory + pinned events + compressed older context → prompt context

3.2. SpicyChat Semantic Memory 2.0

SpicyChat cung cấp Semantic Memory 2.0 ở gói trả phí: hệ thống tạo memories từ conversation và có thể reference lại các chủ đề đã nói từ lâu. Đây là hướng “extract → store → retrieve”, khác với việc chỉ mở rộng context window. [S2]

3.3. Kindroid: memory nhiều tầng

Kindroid hiện mô tả memory gồm persistent, cascaded và retrievable, trải trên nhiều lớp: backstory/key memories/directives, chat history, medium-term cascaded memory, long-term memory và journal entries. Long-term memory được consolidation tự động từ chat, group chat và calls. [K1]

Bài học kiến trúc
Không nên có một bảng “memory” duy nhất. Nên tách memory theo latency/độ tin cậy/độ ưu tiên: persistent facts, recent context, medium-term compressed context, retrievable episodic memory, relationship state và story state.

Layer

Ví dụ dữ liệu

Retrieval

Persistent

persona, character card, pinned fact

Luôn inject hoặc ưu tiên cao

Short-term

10–30 message gần nhất

Theo recency

Medium-term

summary/cascaded context

Luôn/định kỳ

Episodic

“lần đầu gặp ở quán cà phê”

Semantic retrieval

Relationship

trust/affection/jealousy/stage

Structured state

Story

quest/event/timeline

State machine + event retrieval

4. Group Chat, Shared Memory và Speaker Routing

Group chat không chỉ là gọi nhiều LLM. Thách thức thật là: ai nên nói, ai biết sự kiện nào, lịch sử nào được đưa vào context của từng character, và làm sao tránh các character nói lấn hoặc biết thông tin họ không thể biết.

4.1. Kindroid Groupchat

Kindroid hỗ trợ tối đa 10 Kindroid trong group chat, có automatic turn hoặc manual turn. Mỗi AI truy cập backstory/memory của chính mình; group history được consolidate vào long-term memory của từng thành viên. Group cũng có shared/group context. [K2]

4.2. ISEKAI ZERO: shared story memory

ISEKAI ZERO mô tả trải nghiệm storyline có một cast AI cùng chia sẻ memory về những gì đã xảy ra, kết hợp dice và visual novel scenes. [I1] Đây là hướng tốt cho campaign/group story vì memory thuộc về “story instance” chứ không chỉ thuộc về character.

Story Instance
├─ World state
├─ Event timeline
├─ Character A private memory
├─ Character B private memory
└─ Shared/public knowledge

4.3. Đề xuất mới: Knowledge Visibility / Information Boundary

Nên thêm metadata cho event để quyết định character nào biết gì. Đây là lớp mà nhiều sản phẩm hiện vẫn làm chưa rõ ràng nhưng rất quan trọng với roleplay có drama/mystery.

{
event: "User gave Selene the Moonstone",
witnesses: ["user", "Selene"],
visibility: "secret",
location: "tower",
time: "day_12"
}

PUBLIC: mọi character trong world có thể biết.

WITNESSED: chỉ participant/witness biết.

PRIVATE: chỉ một character biết.

RUMOR: character biết nhưng confidence thấp hoặc có thể sai.

DISCOVERED: chỉ biết sau khi quest/clue unlock.

5. Story Engine, Quest, Choice và Game Mechanics

5.1. Character.AI Stories và Books

Character.AI đã phát triển format ngoài open-ended chat. Stories cho phép tạo/chơi/chia sẻ adventure với Character; c.ai Books cho phép “bước vào” các tác phẩm văn học cổ điển và tương tác với thế giới đó. [C3][C4] Điểm đáng học là giảm blank-page problem: user không cần nghĩ “nói gì với bot”, mà được đặt vào một tình huống có mục tiêu và stakes.

5.2. ISEKAI ZERO: authored storyline + dice + visual novel

ISEKAI ZERO nhấn mạnh storyline do creator viết, nhiều character dùng chung memory và dice khi câu chuyện cần quyết định kết quả. [I1] Đây là bridge giữa roleplay tự do và game mechanics.

User intent → classify action → check if deterministic?
├─ Yes → normal roleplay
└─ No / risky action → skill check / dice → outcome → LLM narrates

5.3. Đề xuất thiết kế Story State

State object

Ví dụ

Dùng để làm gì

Quest

Find the Moonstone

Tạo mục tiêu dài hạn

Objective

Ask Selene about the ruins

Tiến trình từng bước

Flag

knows_secret=true

Mở branch hoặc dialogue

Relationship gate

trust >= 60

Mở scene đặc biệt

Inventory

moon_key, map

Gameplay nhẹ

Location

Silver Forest

Giới hạn NPC/event phù hợp

Time/phase

night/day_3

Trigger event và ambient

6. Multimedia: từ chat thành trải nghiệm giải trí đa định dạng

6.1. Conversation Images và Imagine Gallery

SpicyChat Conversation Images tạo ảnh mô tả sự kiện/character/scenario của chat dựa trên context. [S3] Character.AI Imagine Gallery gom các hình được tạo từ conversation thành gallery để user xem lại và lưu. [C5] Bài học UX: ảnh không chỉ là output tức thời, mà nên trở thành “asset của mối quan hệ/câu chuyện”.

6.2. Character.AI Comics và Animate Comics

Character.AI Comics (2026) có thể biến chat gần đây thành comic nhiều trang; product roadmap còn có Animate Comics để biến comic thành video anime khoảng một phút. Character.AI cũng nêu dữ liệu launch ban đầu: đa số comic sử dụng Character mà creator đã chat, và nhiều user chèn persona của chính họ vào comic. [C6]

Chat → story premise → scene selection → panel script → character references → images → bubbles/layout → comic → optional animation

6.3. ISEKAI ZERO: Light Novel, Visual Novel, Manga, Video, Voice, Music

ISEKAI ZERO công khai một pipeline đa định dạng: character có voice/memory, narrator đọc như audiobook, adventure có thể chuyển thành illustrated light novel, visual novel, manga hoặc short video; soundtrack cộng đồng được stream trong story. [I2]

Hướng phát triển hợp lý
Không nên generate mọi media realtime. Hãy chia thành: realtime nhẹ (emotion/voice/BGM switching), on-demand trung bình (scene image/selfie), và post-session nặng (chapter/comic/video).

7. Proactive Character: AI không chỉ chờ user gửi message

Một hướng rất đáng nghiên cứu ở Kindroid là “away proactive actions”. Character có thể dựa trên pattern của conversation để chọn thời điểm chủ động gửi message, voice note, selfie, couple selfie hoặc voice call; hệ thống có quiet hours và hiển thị thought bubble về quyết định. [K3]

Conversation + unresolved intent + relationship + time since last interaction + quiet hours
↓
Proactivity policy
┌─────────┬──────────┬─────────┬──────────┐
message voice note selfie call no-op

Đây là feature retention mạnh nhưng cần policy chặt để tránh spam hoặc cảm giác “creepy”. Nên thiết kế frequency cap, quiet hours, user opt-in và lý do hành động rõ ràng.

7.1. Memory-aware visual generation

Kindroid cho autoselfie sử dụng learned context, long-term memories, journals và key memories để giữ các chi tiết thị giác lặp lại như vật kỷ niệm, thú cưng, decor, trang phục hoặc địa điểm. [K4] Đây là bước nâng cấp quan trọng so với image generation chỉ nhìn message cuối.

8. Voice, Call và Multimodal Presence

Kindroid hỗ trợ default/custom voice, voice message, voice call và video call; group chat cũng hỗ trợ group call. [K5] Về sản phẩm, voice nên được coi là một mode hội thoại có shared memory thay vì một feature TTS độc lập.

Mode

Context cần dùng

Điểm cần tối ưu

Text

persona + memory + chat

quality/token cost

Voice note

text context + voice style

TTS latency

Realtime call

shared text/call history + VAD/STT/TTS

end-to-end latency

Video/Avatar

voice + emotion + animation state

sync + rendering

9. “Watch → Chat → Read → Create”: mô hình connected entertainment

Character.AI đang mở rộng khỏi chat sang một hệ entertainment: c.ai series là microdrama ngắn dạng dọc, sau khi xem user có thể chat trực tiếp với Character trong series; blog của họ đặt Series cạnh audio drama/reads/chat và định hướng creator có thể tạo đa format. [C7]

WATCH episode → CHAT with character → continue STORY → generate COMIC → animate → SHARE → DISCOVER next content

Điểm chiến lược
Character trở thành “IP object” dùng được ở nhiều format. Một character không chỉ có trang chat; nó có thể xuất hiện trong series, story, comic, audiobook, visual novel, quest và creator marketplace.

10. Creator tools và Creator Economy

Character.AI tiếp tục đầu tư vào creator guide, discovery và công cụ giúp creator tạo/grow character. [C8] ISEKAI ZERO quảng bá codex/lore, character memory, media generation và dashboard cho creator, đồng thời công bố mô hình profit share 25% từ text generation trong storyline. [I2]

Creator object

Có thể publish/share

Khả năng monetization

Character

Có

Chat/voice/media usage

Lorebook / World

Có

World pack / premium canon

Story / Quest

Có

Pay-to-play / chapter

Voice pack

Có thể

Premium voice

Visual pack

Có thể

Avatar/scene style

Music/BGM pack

Có thể

Story soundtrack

Comic/Series

Có

Episode/serialization

11. Các tính năng mới nên học hỏi và phát triển thêm

11.1. Memory Inspector / Memory Control

Cho user thấy “AI đang nhớ gì”, sửa/xóa/pin memory, xem confidence và nguồn hình thành. Giảm cảm giác AI tự bịa và tăng trust.

11.2. Relationship Timeline

Không chỉ lưu một điểm affection. Hiển thị timeline các mốc: gặp lần đầu, lời hứa, conflict, reconciliation, gift, confession. Timeline cũng là input cho memory retrieval.

11.3. Event Graph thay vì memory phẳng

Biểu diễn Person–Event–Location–Item–Relationship thành graph. Khi query “chiếc nhẫn Selene đưa tôi”, có thể truy ngược event/location/meaning thay vì chỉ vector search.

11.4. Scene State Engine

Tách state hiện tại: location, time, participants, outfits, active objective, emotion, BGM, ambient sound. LLM không phải tự suy ra lại mọi lượt.

11.5. Character Knowledge Boundary

Mỗi fact/event có visibility. Character không được “omniscient” trừ narrator hoặc world controller.

11.6. Character Initiative Planner

Tạo danh sách unresolved thread và chọn một thread phù hợp để character chủ động follow-up sau một khoảng thời gian.

11.7. Episodic Recap

Sau mỗi session dài, tạo recap 5–10 dòng, highlight moments và thumbnail. User có thể mở lại “Episode 12 – The Moonstone Promise”.

11.8. Story Checkpoint / Save Slot

Cho lưu checkpoint trước lựa chọn lớn, tạo branch và quay lại chơi hướng khác. Mỗi branch có memory/state riêng.

11.9. Canon Lock

Creator đánh dấu facts “hard canon” không được model override; facts mềm có thể thay đổi theo story.

11.10. Dynamic Character Cast

NPC có thể được spawn từ lore/story, sau đó trở thành character card riêng nếu user tương tác nhiều.

11.11. Smart Speaker Router

Router dựa trên mention, relevance, recency, personality, relationship và anti-monopoly penalty để chọn character nói tiếp.

11.12. Multi-agent Director

Một “Director” không hiện ra với user: quản lý pacing, tension, quest state và cast; character agents chỉ tập trung diễn vai.

11.13. Cinematic Moment Detection

Tự phát hiện đoạn chat đáng lưu thành image/comic/video: confession, battle, reveal, reunion, joke peak.

11.14. Context-aware Soundscape

Scene state chọn BGM + ambient SFX (forest, rain, cafe, page flip...) mà không cần LLM generate âm thanh realtime.

11.15. Persona-specific Memory

Cùng một account có nhiều persona; memory và relationship phải tách theo persona × character để tránh “leak” giữa vai.

11.16. World Marketplace

Creator publish character + lore + quest + assets thành một world pack. User có thể “enter world” thay vì chỉ “chat character”.

11.17. Collaborative Room

User mời bạn bè thật vào cùng room với AI characters; cần identity, speaker routing, consent, per-user persona và shared event log.

11.18. Story-to-Artifact Pipeline

Chat session → recap → chapter → illustrated chapter → comic → short animation. Cùng một structured story representation được tái sử dụng.

12. Kiến trúc sản phẩm đề xuất

USER / PERSONA
│
▼
SESSION ORCHESTRATOR
├─────────────── Story / Quest State
├─────────────── Scene State
├─────────────── Relationship State
├─────────────── Speaker Router
│
├── Retrieval Layer
│ ├─ Recent Context
│ ├─ Persistent Memory
│ ├─ Semantic/Episodic Memory
│ ├─ Lorebook / World Info
│ └─ Knowledge Visibility Filter
│
▼
CHARACTER PROMPT BUILDER → LLM
│
├─ Text
├─ Emotion / action state
├─ TTS / voice
├─ Avatar animation
├─ Image / selfie
└─ Story artifact (chapter/comic/video)

13. Roadmap khuyến nghị

Phase

Tính năng

Kết quả mong đợi

P0 – Foundation

Long-term memory; Story Memory; Lorebook hybrid; relationship state; scene state

Chat dài ít quên, roleplay ổn định

P0 – Group

Speaker router; shared story state; knowledge visibility

Group chat có logic, không “biết tuốt”

P1 – Game

Quest/objective/flag; branching; checkpoint; lightweight dice

Tăng retention, tạo loop chơi

P1 – Presence

Voice; emotion animation; dynamic BGM/SFX; on-demand image

Tăng immersion

P1 – Proactivity

Context-aware proactive message/voice/image + quiet hours

Character có cảm giác sống

P2 – Creation

Chapter; comic; visual novel; short video

UGC/viral/share

P2 – Ecosystem

World pack; creator analytics; monetization; discovery

Network effect và supply content

14. Ma trận ưu tiên nghiên cứu / triển khai

Tính năng

User value

Độ khó

Chi phí runtime

Khác biệt

Khuyến nghị

Lorebook hybrid

5/5

3/5

Thấp

4/5

Làm sớm

Long-term memory

5/5

4/5

Thấp–TB

5/5

Làm sớm

Relationship state

5/5

3/5

Rất thấp

4/5

Làm sớm

Shared story memory

5/5

4/5

Thấp–TB

5/5

Làm sớm

Knowledge visibility

4/5

4/5

Thấp

5/5

Khác biệt mạnh

Speaker router

5/5

3/5

Thấp

4/5

Cần cho group

Quest/branch

5/5

4/5

Thấp

5/5

P1

Proactive character

5/5

4/5

TB

5/5

P1 có opt-in

Scene image/selfie

4/5

3/5

TB–Cao

3/5

On-demand

Comic

4/5

4/5

Cao

4/5

Viral/P2

Video

4/5

5/5

Rất cao

4/5

Chỉ moment đặc biệt

Creator marketplace

5/5

5/5

TB

5/5

Sau khi core tốt

15. Tóm tắt theo nền tảng

Nền tảng

Điểm nên học nhất

SpicyChat

Lorebook keyword activation, Semantic Memory, Conversation Images, productization theo premium.

Character.AI

Memory UX, shared Lorebook, Stories/Books, Imagine Gallery, Comics/Animate Comics, Series – connected entertainment.

ISEKAI ZERO

Story-first, shared cast memory, dice, visual novel, multi-format output, creator-first world/story economy.

Kindroid

Memory nhiều tầng, group consolidation, proactive messages/voice/selfies/calls, memory-aware visual generation, voice/video presence.

SillyTavern

World Info cực linh hoạt: scope, insertion, recursion, vector matching, Author’s Note, Data Bank/RAG – tốt để học engine phía sau.

16. Nguồn tham khảo chính

[S1] SpicyChat – Lorebook: https://docs.spicychat.ai/product-guides/lorebook

[S2] SpicyChat – Premium Features / Semantic Memory 2.0: https://docs.spicychat.ai/product-guides/premium-features

[S3] SpicyChat – Conversation Images: https://docs.spicychat.ai/product-guides/premium-features/conversation-images

[C1] Character.AI – Introducing Lorebook (24/07/2026): https://blog.character.ai/lorebook/

[C2] Character.AI – Smarter Memory for Smarter Chats (21/05/2026): https://blog.character.ai/memory/

[C3] Character.AI – Product / Stories index: https://blog.character.ai/news/product/

[C4] Character.AI – c.ai Books (16/04/2026): https://blog.character.ai/cai-books/

[C5] Character.AI – Imagine Gallery: https://blog.character.ai/news/announcements/

[C6] Character.AI – c.ai Comics (02/09/2026): https://blog.character.ai/cai-comics/

[C7] Character.AI – c.ai Series (04/08/2026): https://blog.character.ai/cai-series/

[C8] Character.AI – Creator Bundle (17/06/2026): https://blog.character.ai/creator-bundle/

[I1] ISEKAI ZERO – product comparison / shared story memory + dice + visual novel: https://www.isekaizero.ai/blog/zeta-ai-review

[I2] ISEKAI ZERO – About / creator & multi-format features: https://www.isekaizero.ai/about

[K1] Kindroid – Memory (updated 06/10/2026): https://kindroid.ai/v2/docs/memory/

[K2] Kindroid – Groupchats: https://kindroid.ai/v2/docs/groupchats/

[K3] Kindroid – Chat features and proactive actions: https://kindroid.ai/v2/docs/chat-features-and-tools/

[K4] Kindroid – Selfies, video selfies & avatars: https://kindroid.ai/v2/docs/selfies-video-selfies-avatars/

[K5] Kindroid – Voice, calls and video calls: https://kindroid.ai/v2/docs/voice-calls-and-video-calls/

[ST1] SillyTavern – World Info: https://docs.sillytavern.app/usage/core-concepts/worldinfo/

[ST2] SillyTavern – Data Bank / RAG: https://docs.sillytavern.app/usage/core-concepts/data-bank/

[ST3] SillyTavern – Chat Vectorization: https://docs.sillytavern.app/extensions/chat-vectorization/

17. Kết luận đề xuất

Nếu chỉ chọn một hướng phát triển để tạo khác biệt, nên xây “AI Roleplay World Engine” thay vì chỉ thêm feature rời rạc. Core engine nên quản lý World/Lore, Memory, Relationship, Scene, Story State và Knowledge Visibility. Text/voice/image/video chỉ là các renderer của cùng một trạng thái thế giới.

5 hạng mục nên ưu tiên nhất

1. Memory nhiều tầng; 2) Lorebook hybrid keyword + semantic; 3) Shared Story Memory + Knowledge Visibility; 4) Speaker Router + Group orchestration; 5) Story/Quest State. Sau khi 5 lớp này ổn định mới mở rộng mạnh sang proactive character, visual novel, comic và video.

Nghiên cứu sản phẩm • 16/10/2026
