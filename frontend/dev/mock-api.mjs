// Mock API for previewing the UI locally without the Modal backend.
// Serves sample data (same as "Avibi Platform Prototype") on the port Vite
// proxies /v1 to (8000). Any username and password logs in. Chat replies are
// streamed like the real backend. Nothing is persisted; restarting resets
// everything.
//
//   npm run mock   (in one terminal)
//   npm run dev    (in another), then open http://127.0.0.1:5173
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';

const PORT = Number(process.env.MOCK_PORT || 8000);
const IMAGE_DIR = fileURLToPath(new URL('../../image/', import.meta.url));
const img = (file) => `/v1/mock-images/${file}`;
const now = Date.now();
const iso = (offset = 0) => new Date(now + offset).toISOString();
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const pick = (list) => list[Math.floor(Math.random() * list.length)];

/* ---------- Tài khoản ---------- */
const account = { id: 'u1', username: 'thuyhien', display_name: 'Thúy Hiền', theme: 'light', bio: 'BA ở Hà Nội. Thích trà sen và podcast công nghệ.', language: 'vi', reduced_motion: false, avatar_url: null };

/* ---------- Chat Bot AI ---------- */
const chars = [
  { id: 'c1', name: 'Luna', display_name: 'Luna', description: 'Bạn đồng hành học tập, giải thích khái niệm khó theo cách dễ hiểu.', creation_type: 'preset', simulation_label: false, category: 'utility', avatar_url: img('girl_friend.png'), tags: ['Học tập', 'ấm áp'], rating: 4.8, rating_count: 120, usage_count: 3400, is_public: true, reactions: { '❤️': 12, '😂': 3, '🔥': 5, '👍': 8, '😮': 1 }, support: { primary_role: 'study', strengths: ['study', 'work'], introduction: 'Xin chào, mình là Luna! Bài nào khó, mình cùng chia nhỏ ra nhé.' } },
  { id: 'c2', name: 'Anthony', display_name: 'Anthony', description: 'Cố vấn công việc, giúp bạn lập kế hoạch và ưu tiên.', creation_type: 'preset', simulation_label: false, category: 'utility', avatar_url: img('anthony.png'), tags: ['Công việc'], rating: 4.6, rating_count: 80, usage_count: 2100, is_public: true, reactions: { '❤️': 4, '😂': 1, '🔥': 9, '👍': 15, '😮': 0 }, support: { primary_role: 'work', strengths: ['work'], introduction: 'Chào bạn. Kể mình nghe dự án đang vướng ở đâu.' } },
  { id: 'c3', name: 'Bạn thân', display_name: 'Bạn thân', description: 'Người bạn luôn lắng nghe và trò chuyện vui vẻ.', creation_type: 'preset', simulation_label: false, category: 'entertainment', avatar_url: img('best_friend.png'), tags: ['Đồng hành'], rating: 4.9, rating_count: 300, usage_count: 9000, is_public: true, reactions: { '❤️': 40, '😂': 22, '🔥': 6, '👍': 18, '😮': 2 }, support: { primary_role: 'companion', strengths: ['companion'], introduction: 'Hey! Hôm nay của cậu thế nào?' } },
  { id: 'c4', name: 'Tổng tài', display_name: 'Tổng tài', description: 'CEO lạnh lùng, nói ít nhưng câu nào cũng sắc.', creation_type: 'custom', simulation_label: true, category: 'entertainment', avatar_url: img('tong_tai.png'), tags: ['Chính kịch', 'Role play'], rating: 4.7, rating_count: 210, usage_count: 5400, is_public: true, reactions: { '❤️': 61, '😂': 9, '🔥': 88, '👍': 20, '😮': 14 }, support: { primary_role: 'companion', strengths: ['companion'], introduction: '*liếc nhìn đồng hồ* Cô có năm phút.' } },
];
// Vị trí trên trang chủ của nhân vật hệ thống (CMS > Nhân vật > Ẩn/Hiện).
const presetHomeSections = { c3: 'hidden' };
const rooms = [
  { id: 'r1', name: 'Trò chuyện với Luna', character_ids: ['c1'], created_at: iso(-1800e3) },
  { id: 'r2', name: 'Nhóm làm việc', character_ids: ['c1', 'c2'], created_at: iso(-86400e3) },
];
const roomMessages = {
  r1: [
    { id: 'm1', sender_type: 'user', character_id: null, text: 'Giải thích giúp mình đạo hàm là gì?' },
    { id: 'm2', sender_type: 'character', character_id: 'c1', text: '*mỉm cười* Đạo hàm đo tốc độ thay đổi của một hàm số tại một điểm — giống như độ dốc của đường cong ở đúng chỗ đó.', emotion: 'happy', suggestions: ['Cho ví dụ', 'Công thức cơ bản', 'Ứng dụng thực tế'] },
  ],
  r2: [
    { id: 'm3', sender_type: 'character', character_id: 'c2', text: 'Tuần này team cần chốt gì trước?', emotion: 'neutral' },
    { id: 'm4', sender_type: 'character', character_id: 'c1', text: 'Mình sẽ tóm tắt tài liệu nếu bạn cần nhé.', emotion: 'happy' },
  ],
};
const ROLEPLAY_REPLIES = [
  ['*gật đầu* Mình hiểu rồi. Kể thêm chút nữa đi, phần nào khiến cậu bận tâm nhất?', 'happy', ['Kể tiếp', 'Đổi chủ đề', 'Cho mình lời khuyên']],
  ['*nghiêng đầu suy nghĩ* Câu hỏi hay đấy. Mình nghĩ ta nên bắt đầu từ ví dụ đơn giản trước.', 'neutral', ['Cho ví dụ', 'Giải thích kỹ hơn', 'Tóm tắt lại']],
  ['*bật cười* Ôi, chuyện này thú vị thật! Rồi sau đó thế nào?', 'happy', ['Rồi sao nữa?', 'Kể chuyện vui đi', 'Nghỉ chút nhé']],
  ['*tròn mắt* Thật á? Mình không ngờ luôn đó!', 'surprised', ['Thật mà!', 'Đùa thôi', 'Còn nữa cơ']],
];

/* ---------- Trợ lý AI ---------- */
const assistantChats = [
  { id: 'a1', mode: 'assistant_general', title: 'Lập kế hoạch tuần làm việc', created_at: iso(-3600e3) },
  { id: 'a2', mode: 'assistant_psychology', title: 'Áp lực trước buổi demo', created_at: iso(-86400e3) },
  { id: 'a3', mode: 'assistant_homework', title: 'Đạo hàm hàm hợp', created_at: iso(-2 * 86400e3) },
];
const assistantMessages = {
  a1: [
    { id: 'am1', role: 'user', text: 'Giúp mình chia việc tuần này: viết FRD module thanh toán, review test case xCall, họp khách thứ Năm.' },
    { id: 'am2', role: 'assistant', text: 'Gợi ý chia theo năng lượng trong ngày:\nThứ Hai–Ba: viết FRD buổi sáng (việc cần tập trung), chiều review 30–40 test case mỗi ngày.\nThứ Tư: hoàn thiện FRD, gửi bản nháp để kịp nhận góp ý trước buổi họp.\nThứ Năm: sáng chuẩn bị agenda và câu hỏi mở, chiều họp khách.\nThứ Sáu: cập nhật FRD theo góp ý, chốt test case còn lại.', suggestions: ['Viết agenda họp thứ Năm', 'Ước lượng thời gian cho từng việc', 'Chuyển thành checklist'] },
  ],
  a2: [
    { id: 'am3', role: 'user', text: 'Mai demo cho khách mà mình thấy lo quá, sợ hỏi câu không trả lời được.' },
    { id: 'am4', role: 'assistant', text: 'Lo trước một buổi quan trọng là phản ứng rất bình thường; nó cho thấy bạn quan tâm đến kết quả. Mình thử tách nỗi lo ra nhé: điều bạn sợ nhất là câu hỏi về phần nào của sản phẩm', interrupted: true },
  ],
  a3: [],
};
const ASSISTANT_REPLIES = {
  assistant_general: ['Đây là cách mình sẽ tiếp cận:\n1. Làm rõ mục tiêu: bạn cần kết quả trong bao lâu và cho ai đọc?\n2. Chia nhỏ: tách thành 3–4 đầu việc có thể hoàn thành trong một buổi.\n3. Ưu tiên: việc nào chặn việc khác thì làm trước.', ['Áp dụng cho việc của mình', 'Viết thành checklist', 'Giải thích kỹ bước 2']],
  assistant_psychology: ['Cảm ơn bạn đã chia sẻ. Nghe như bạn đang mang khá nhiều thứ cùng lúc. Nếu được, bạn thử gọi tên cảm xúc mạnh nhất lúc này: lo, mệt, hay thất vọng?\nKhông cần trả lời ngay; mình vẫn ở đây.', ['Mình thấy mệt', 'Mình lo về công việc', 'Gợi ý cách thư giãn nhanh']],
  assistant_health: ['Mình giải thích ở mức thông tin chung nhé:\nCó thể liên quan: thiếu ngủ, mất nước, căng thẳng kéo dài.\nNên đi khám sớm nếu: kèm sốt cao, đau dữ dội, hoặc kéo dài quá 3 ngày.\nThông tin này không thay thế chẩn đoán của bác sĩ.', ['Mình nên hỏi bác sĩ gì?', 'Thói quen nào giúp cải thiện?']],
  assistant_homework: ['Mình làm từng bước nhé.\nBước 1: Xác định hàm ngoài f(u) và hàm trong u(x).\nBước 2: Đạo hàm hàm hợp: (f∘u)\' = f\'(u) · u\'(x).\nBước 3: Thay vào và rút gọn.\nBạn thử làm bước 1 với đề của bạn rồi gửi mình xem?', ['Cho mình ví dụ khác', 'Kiểm tra bài làm của mình', 'Giải thích lại bước 2']],
  assistant_tarot: ['Trải bài ba lá minh họa cho câu hỏi của bạn:\nQuá khứ — The Hermit: một giai đoạn tự nhìn lại.\nHiện tại — Two of Cups: kết nối, hợp tác đang mở ra.\nGợi ý — The Star: giữ niềm tin, đi từng bước nhỏ.\nHãy xem đây là gợi ý để suy ngẫm.', ['Rút thêm một lá', 'Đọc Bát Tự minh họa']],
};
const ROOM_TITLES = { assistant_general: 'Trợ lý AI', assistant_psychology: 'Tư vấn tâm lý', assistant_health: 'Tư vấn sức khỏe', assistant_homework: 'Hỗ trợ bài tập', assistant_tarot: 'Tarot và chiêm nghiệm' };
const assistantModels = [
  { id: 'avibi-flash', name: 'Avibi Flash', role: 'primary' },
  { id: 'avibi-pro', name: 'Avibi Pro · suy luận', role: 'primary' },
  { id: 'avibi-lite', name: 'Avibi Lite', role: 'primary' },
];
const memoryState = { enabled: true };
const memories = [{ id: 'mm1', room_id: 'a1', mode: 'assistant_general', content: 'Mình làm việc tập trung nhất vào buổi sáng.', created_at: iso(-3600e3) }];
const reminders = [
  { id: 'rm1', title: 'Uống nước, đứng dậy vận động 5 phút', due_at: iso(3600e3), status: 'active', last_notified_at: null },
  { id: 'rm2', title: 'Nộp báo cáo tuần cho anh Tùng', due_at: iso(86400e3), status: 'active', last_notified_at: null },
  { id: 'rm3', title: 'Đặt lịch khám răng', due_at: iso(3 * 86400e3), status: 'paused', last_notified_at: null },
];
const roomFiles = { a3: [{ id: 'f1', filename: 'De-cuong-giai-tich-1.pdf', status: 'ready' }] };


/* ---------- Sáng tạo nhân vật ---------- */
const ROLE_LABELS = { companion: 'Đồng hành', study: 'Học tập', work: 'Công việc', entertainment: 'Giải trí', romance: 'Tình cảm', roleplay: 'Role play' };
function makeCharacter({ name, description, role, greeting }) {
  const character = {
    id: randomUUID(), name: name || 'Nhân vật mới', display_name: name || 'Nhân vật mới',
    description: description || 'Nhân vật do bạn sáng tạo.', creation_type: 'custom', simulation_label: false,
    category: 'utility', avatar_url: null, tags: [], rating: 0, rating_count: 0, usage_count: 1, is_public: false,
    reactions: { '❤️': 0, '😂': 0, '🔥': 0, '👍': 0, '😮': 0 },
    support: { primary_role: ROLE_LABELS[role] ? role : 'companion', strengths: ['companion'], introduction: greeting || `Chào bạn, mình là ${name || 'nhân vật mới'}!` },
  };
  chars.unshift(character);
  return character;
}
const storyDocuments = {};
const drain = async (req) => { for await (const _ of req) { /* bỏ qua nội dung tệp */ } };


/* ---------- CMS: model & cấu hình Trợ lý AI ---------- */
const ASSISTANT_PURPOSES = ['assistant_general', 'assistant_psychology', 'assistant_health', 'assistant_homework', 'assistant_tarot', 'assistant_suggestion'];
const adminSettings = { assistant_system_instruction: 'Bạn là Trợ lý AI của Avibi. Trả lời bằng ngôn ngữ của người dùng, ngắn gọn, có cấu trúc. Nói rõ khi không chắc chắn.', llm_model: 'm1', fallback_model: '', moderation_model: '', llm_api_base: '', response_instruction: '', suggestion_instruction: '', compiler_instruction: '', default_temperature: '0.8', short_temperature: '0.4', default_max_tokens: '1024', short_max_tokens: '256', _base_prompts: { response: '', suggestion: '', compiler: '' } };
const makeModel = (id, name, provider, modelId, assistantName, enabled, thinking, effort) => ({
  id, name, provider, model_id: modelId, api_base: 'https://gateway.avibi.ai/v1', logo: '', enabled: true,
  assistant_name: assistantName, assistant_model_id: modelId, assistant_enabled: enabled,
  assistant_thinking_mode: thinking, assistant_reasoning_effort: effort, role: 'available',
  has_api_key: true, api_key_hint: 'sk-…a1b2', purposes: [],
  response_instruction: '', suggestion_instruction: '', compiler_instruction: '', moderation_instruction: '', emotion_instruction: '',
  temperature: '0.8', short_temperature: '0.4', max_tokens: '1024', short_max_tokens: '256', gateway_read_timeout_seconds: '60', tts_default_voice: '', thinking_mode: 'default', reasoning_effort: 'default',
});
const adminModels = [
  makeModel('m1', 'Claude Sonnet', 'Anthropic', 'claude-sonnet', 'Avibi Pro · suy luận', true, 'enabled', 'high'),
  makeModel('m2', 'GPT-4.1 mini', 'OpenAI', 'gpt-4.1-mini', 'Avibi Lite', true, 'disabled', 'default'),
  makeModel('m3', 'Gemini 2.5 Flash', 'Google', 'gemini-2.5-flash', 'Avibi Flash', true, 'default', 'default'),
  makeModel('m4', 'Qwen 2.5 72B', 'Alibaba', 'qwen-2.5-72b', 'Avibi Qwen', false, 'default', 'default'),
  makeModel('m5', 'Vbee TTS v3', 'Vbee', 'vbee-tts-v3', 'Vbee TTS', false, 'default', 'default'),
];
adminModels[3].api_base = 'https://api.vbee.local/v1';
adminModels[4].api_base = 'https://tts.vbee.vn/v1';
adminModels[4].purposes = ['tts'];
adminModels[4].tts_default_voice = 'hn_female_ngochuyen';
adminModels[1].has_api_key = false;
adminModels[2].has_api_key = false;
adminModels[3].has_api_key = false;
adminModels[4].has_api_key = false;
adminModels[0].purposes.push('response', 'compiler');
adminModels[1].purposes.push('suggestion', 'moderation', 'emotion');
adminModels[2].purposes.push('fallback', 'suggestion_fallback');
const credentialState = { avibi: { configured: true, source: 'cms', hint: 'sk-…a1b2' }, bases: [{ id: 'b1', api_base: 'https://tts.vbee.vn/v1', hint: 'vb-…7f3c' }] };
const keyHint = (key) => `${String(key).slice(0, 3)}…${String(key).slice(-4)}`;
let modelSeq = adminModels.length;
const ASSISTANT_PROMPTS = {
  assistant_general: 'Giúp người dùng hoàn thành việc: lên kế hoạch, tóm tắt, viết nội dung. Hỏi lại khi thiếu thông tin.',
  assistant_psychology: 'Lắng nghe, phản hồi đồng cảm, không chẩn đoán. Khi có dấu hiệu khủng hoảng, khuyến khích tìm hỗ trợ chuyên môn.',
  assistant_health: 'Không chẩn đoán. Khuyến nghị gặp bác sĩ khi có dấu hiệu nguy hiểm. Trích nguồn khi có tài liệu.',
  assistant_homework: 'Giải thích từng bước, hỏi lại để kiểm tra hiểu bài, không đưa đáp án ngay khi người học chưa thử.',
  assistant_tarot: 'Luôn nhắc nội dung chỉ để tham khảo và chiêm nghiệm. Không đưa lời khuyên tài chính, y tế.',
  assistant_suggestion: 'Sinh 3 gợi ý trả lời ngắn (≤ 8 từ) dựa trên câu trả lời cuối.',
};
// Chuỗi model mẫu giống prototype: có trợ lý đủ 3 model, có trợ lý thiếu dự phòng.
function assignPurpose(purpose, ids, prompts = {}) {
  for (const model of adminModels) model.purposes = model.purposes.filter((p) => p !== purpose && p !== `${purpose}_fallback` && p !== `${purpose}_fallback_2`);
  const roles = [purpose, `${purpose}_fallback`, `${purpose}_fallback_2`];
  const fields = [`${purpose}_instruction`, `${purpose}_fallback_instruction`, `${purpose}_fallback_2_instruction`];
  ids.forEach((id, i) => {
    const model = adminModels.find((m) => m.id === id);
    if (!model) return;
    model.purposes.push(roles[i]);
    if (prompts[i] !== undefined) model[fields[i]] = prompts[i];
  });
}
assignPurpose('assistant_general', ['m1', 'm2', 'm3'], [ASSISTANT_PROMPTS.assistant_general]);
assignPurpose('assistant_psychology', ['m1', 'm2', 'm3'], [ASSISTANT_PROMPTS.assistant_psychology]);
assignPurpose('assistant_health', ['m1', 'm3'], [ASSISTANT_PROMPTS.assistant_health]);
assignPurpose('assistant_homework', ['m3', 'm1', 'm2'], [ASSISTANT_PROMPTS.assistant_homework]);
assignPurpose('assistant_tarot', ['m3'], [ASSISTANT_PROMPTS.assistant_tarot]);
assignPurpose('assistant_suggestion', ['m2', 'm3', 'm4'], [ASSISTANT_PROMPTS.assistant_suggestion]);


/* ---------- CMS: hồ sơ hiển thị và thống kê của từng trợ lý ---------- */
const stats = (requests, fallback_rate, latency, error_rate, days) => ({ requests, fallback_rate, latency, error_rate, days });
const assistantProfiles = {
  order: [],
  items: {
    assistant_general: { title: 'Trợ lý AI', slogan: 'Một câu hỏi mở ra thêm một khả năng.', description: 'Hỏi mình bất cứ điều gì', greeting: 'Chào bạn! Mang câu hỏi tới đây, mình mang sự tò mò — cùng bắt đầu nhé!', starters: ['Lên kế hoạch tuần làm việc', 'Tóm tắt tài liệu mình gửi', 'Viết email xin nghỉ phép', 'Giải thích một khái niệm khó'], visible: true, temperature: 0.7, max_tokens: 1200, user_pick: true, stats: stats(48210, 3.1, 1.4, 0.4, [5.8, 6.2, 6.9, 7.1, 6.4, 7.6, 8.0]) },
    assistant_psychology: { title: 'Tâm lý', slogan: 'Chậm lại một nhịp, mình nghe bạn.', description: 'Lắng nghe và cùng bạn gỡ rối cảm xúc', greeting: 'Chào bạn. Hôm nay có điều gì khiến bạn bận lòng không? Bạn có thể kể từ bất kỳ chỗ nào, không cần sắp xếp.', starters: ['Mình đang thấy áp lực', 'Làm sao để ngủ ngon hơn?', 'Mình muốn tâm sự một chút'], visible: true, temperature: 0.6, max_tokens: 900, user_pick: false, stats: stats(12480, 2.4, 1.9, 0.2, [1.6, 1.7, 1.5, 1.9, 1.8, 2.0, 2.1]) },
    assistant_health: { title: 'Sức khỏe', slogan: 'Hiểu cơ thể mình, rồi hỏi bác sĩ đúng câu.', description: 'Thông tin sức khỏe thận trọng, dễ hiểu', greeting: 'Mình có thể giải thích triệu chứng, chỉ số xét nghiệm hay thói quen sinh hoạt. Với tình huống cấp cứu, hãy gọi 115.', starters: ['Đọc giúp chỉ số xét nghiệm', 'Đau đầu thường xuyên do đâu?', 'Gợi ý thực đơn lành mạnh'], visible: true, temperature: 0.3, max_tokens: 900, user_pick: false, stats: stats(9315, 5.8, 2.2, 1.1, [1.1, 1.3, 1.2, 1.4, 1.2, 1.5, 1.6]) },
    assistant_homework: { title: 'Học tập', slogan: 'Hiểu cách làm, không chỉ chép đáp án.', description: 'Giải thích từng bước từ tài liệu của bạn', greeting: 'Gửi đề bài hoặc tải tài liệu lên, mình sẽ giải thích từng bước và hỏi lại để chắc bạn đã nắm.', starters: ['Giải thích đạo hàm hàm hợp', 'Kiểm tra bài văn của mình', 'Tạo 5 câu trắc nghiệm ôn tập'], visible: true, temperature: 0.4, max_tokens: 1500, user_pick: true, stats: stats(21760, 1.9, 1.6, 0.3, [2.4, 2.9, 3.3, 3.1, 2.8, 3.4, 3.8]) },
    assistant_tarot: { title: 'Tarot & Tử vi', slogan: 'Một góc nhìn để suy ngẫm, không phải lời phán.', description: 'Gửi Bát Tự, lá số hoặc trải bài minh họa', greeting: 'Bạn muốn rút một trải bài ba lá, hay gửi giờ sinh để mình đọc Bát Tự minh họa?', starters: ['Rút một trải bài 3 lá', 'Đọc Bát Tự minh họa', 'Lá bài cho hôm nay'], visible: true, temperature: 0.9, max_tokens: 800, user_pick: false, stats: stats(15902, 7.5, 1.2, 2.9, [2.0, 2.2, 2.1, 2.6, 2.3, 2.4, 2.7]) },
    assistant_suggestion: { title: 'Gợi ý trả lời', slogan: '', description: 'Tác vụ nền: sinh 3 gợi ý dưới mỗi câu trả lời', greeting: '', starters: [], visible: true, temperature: 0.8, max_tokens: 120, user_pick: false, stats: stats(72100, 0.8, 0.5, 0.1, [9.1, 9.8, 10.4, 10.9, 10.1, 11.6, 12.2]) },
  },
};
let customAssistantSeq = 0;


/* ---------- CMS: danh mục trang chủ, logchat, nhật ký hoạt động ---------- */
const homeSectionsState = [
  { id: 'trending', name: 'Đang thịnh hành', rule: 'trending', tags: [] },
  { id: 'top_rated', name: 'Được đánh giá cao', rule: 'top_rated', tags: [] },
  { id: 'custom_lang', name: 'Học ngoại ngữ', rule: 'tags', tags: ['study', 'tiếng Anh', 'JLPT'] },
  { id: 'custom_fun', name: 'Giải trí', rule: 'tags', tags: ['entertainment', 'companion'], hidden: true },
];
const CHAT_LOG_COLUMNS = ['created_at', 'log_status', 'user', 'user_id', 'product', 'task', 'room', 'assistant_mode', 'character_id', 'character_name', 'character_avatar_url', 'user_message', 'model_response', 'primary_model', 'fallback_model', 'fallback_model_2', 'fallback_used', 'fallback_reason', 'actual_model', 'thinking_mode', 'reasoning_effort', 'continuation_count', 'finish_status', 'latency_ms', 'error'];
// Người trả lời của từng phòng mẫu: id nhân vật (Chat Bot AI) hoặc mode trợ lý.
const LOG_SPEAKERS = { 'Trò chuyện với Luna': 'c1', 'Nhóm làm việc': 'c2', 'Nhóm luyện tiếng Anh': 'c3', 'Trợ lý AI': 'assistant_general', 'Tư vấn tâm lý': 'assistant_psychology', 'Tarot và chiêm nghiệm': 'assistant_tarot' };
const logSpeaker = (product, room) => {
  if (product === 'assistant') return { assistant_mode: LOG_SPEAKERS[room] || 'assistant_general', character_id: '', character_name: '', character_avatar_url: '' };
  const c = chars.find((x) => x.id === LOG_SPEAKERS[room]);
  return { assistant_mode: '', character_id: c?.id || '', character_name: c?.name || '', character_avatar_url: c?.avatar_url || '' };
};
const chatLog = (minutesAgo, product, room, question, answer, primary, fallback, used, reason, latency, error = '', user = ['Thúy Hiền', 'u1']) => ({
  created_at: iso(-minutesAgo * 60e3), log_status: 'Đã ghi đầy đủ' + (error ? ' · request lỗi' : ''), user: user[0], user_id: user[1], product, task: 'response', room, ...logSpeaker(product, room),
  user_message: question, model_response: answer, primary_model: primary, fallback_model: fallback || 'Không phân công', fallback_model_2: 'Không phân công',
  fallback_used: used ? 'Có' : 'Không', fallback_reason: reason || '', actual_model: used ? fallback : primary, thinking_mode: 'default', reasoning_effort: 'default',
  continuation_count: 0, finish_status: error ? 'error' : 'stop', latency_ms: latency, error,
});
const chatLogs = [
  chatLog(1, 'roleplay', 'Trò chuyện với Luna', 'Hôm nay họp suốt, mệt ghê.', 'Xong FRD là cả một ngọn núi đấy!', 'claude-sonnet', 'gpt-4.1-mini', false, '', 1840),
  chatLog(2, 'roleplay', 'Nhóm làm việc', 'Ai thuận tay trái?', 'Người viết thuận tay trái.', 'gpt-4.1-mini', 'gemini-2.5-flash', false, '', 2210),
  chatLog(3, 'assistant', 'Trợ lý AI', 'Chia việc tuần này giúp mình', 'Gợi ý chia theo năng lượng trong ngày…', 'gemini-2.5-flash', 'claude-sonnet', false, '', 1320),
  chatLog(6, 'assistant', 'Tư vấn tâm lý', 'Mai demo mà lo quá', 'Lo trước một buổi quan trọng là bình thường…', 'claude-sonnet', 'gpt-4.1-mini', true, 'Timeout gateway 8000ms → fallback', 9650),
  chatLog(8, 'roleplay', 'Nhóm luyện tiếng Anh', 'Good morning', "Let's warm up!", 'gpt-4.1-mini', 'gemini-2.5-flash', false, '', 1120, '', ['Đức Anh', 'u_02']),
  chatLog(13, 'assistant', 'Tarot và chiêm nghiệm', 'Rút một lá', '', 'gemini-2.5-flash', '', false, '', 0, '429 rate limit'),
];
const ACTION_COLUMNS = ['created_at', 'status', 'status_code', 'category', 'action', 'username', 'user_id', 'method', 'path', 'latency_ms', 'ip_address', 'user_agent', 'error', 'details'];
const action = (minutesAgo, username, category, actionName, status, code, method, path, error = '') => ({
  created_at: iso(-minutesAgo * 60e3), status, status_code: code, category, action: actionName, username, user_id: username ? `u_${username}` : '', method, path,
  latency_ms: 120 + minutesAgo * 7, ip_address: '10.0.0.12', user_agent: 'Mozilla/5.0', error, details: '',
});
const actionLogs = [
  action(1, 'thuyhien', 'auth', 'Đăng nhập', 'success', 200, 'POST', '/v1/auth/login'),
  action(1, 'thuyhien', 'navigation', 'Mở app Chat Bot AI', 'success', 200, 'GET', '/role-play-ai'),
  action(2, 'ducanh', 'roleplay', 'Tạo nhân vật (custom)', 'success', 200, 'POST', '/v1/characters/generate'),
  action(3, 'huongtra', 'assistant', 'Gửi tin Trợ lý AI', 'partial', 200, 'POST', '/v1/assistant/chats/a2/messages/stream', 'Câu trả lời bị gián đoạn'),
  action(5, 'lamphong', 'api', 'Tạo phòng chat', 'error', 500, 'POST', '/v1/rooms', 'Internal Server Error'),
  action(7, 'spam_bot_77', 'auth', 'Đăng nhập (tài khoản bị khóa)', 'error', 403, 'POST', '/v1/auth/login', 'Tài khoản bị khóa'),
  action(9, 'thuyhien', 'document', 'Tải tài liệu lên', 'success', 200, 'POST', '/v1/character-sources'),
];
const matchQ = (row, q) => !q || Object.values(row).join(' ').toLowerCase().includes(q.toLowerCase());


/* ---------- CMS: Database Explorer (chỉ đọc, dữ liệu nhạy cảm đã che) ---------- */
const DB_TABLES = {
  users: [['id', 'username', 'display_name', 'password_hash', 'created_at'], [['u_01', 'thuyhien', 'Thúy Hiền', '[REDACTED]', '2026-05-12'], ['u_02', 'ducanh', 'Đức Anh', '[REDACTED]', '2026-06-02'], ['u_03', 'huongtra', 'Hương Trà', '[REDACTED]', '2026-06-18']]],
  characters: [['id', 'user_id', 'name', 'visibility', 'uses'], [['ch_11', 'u_01', 'Linh', 'private', '1'], ['ch_12', 'u_01', 'Thám tử Kha', 'public', '214'], ['ch_31', 'u_03', 'Bà Nội Bếp', 'public', '8820']]],
  rooms: [['id', 'user_id', 'name', 'members'], [['rm_1', 'u_01', 'Trò chuyện với Linh', '2'], ['rm_2', 'u_01', 'Trò chuyện với Thám tử Kha', '2'], ['rm_9', 'u_02', 'Luyện JLPT', '2']]],
  user_sessions: [['id', 'user_id', 'token', 'expires_at'], [['s_1', 'u_01', '[REDACTED]', '2026-10-08'], ['s_2', 'u_02', '[REDACTED]', '2026-10-03']]],
};
const dbRowsOf = (name, userId) => {
  const [columns, rows] = DB_TABLES[name] || [[], []];
  const userCol = columns.indexOf('user_id') >= 0 ? columns.indexOf('user_id') : name === 'users' ? 0 : -1;
  const list = rows.filter((r) => !userId || (userCol >= 0 && r[userCol] === userId)).map((r) => Object.fromEntries(columns.map((c, i) => [c, r[i]])));
  return { table: name, total: list.length, limit: 100, offset: 0, columns, rows: list };
};

/* ---------- Tiện ích HTTP ---------- */
async function readBody(req) {
  let body = '';
  for await (const chunk of req) body += chunk;
  try { return JSON.parse(body || '{}'); } catch { return {}; }
}
function json(res, payload, status = 200) {
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(JSON.stringify(payload));
}
function openStream(res) {
  res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache', connection: 'keep-alive' });
  return (event, data) => res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}
async function sendImage(res, file) {
  try {
    const data = await readFile(join(IMAGE_DIR, basename(file)));
    res.writeHead(200, { 'content-type': extname(file) === '.jpg' ? 'image/jpeg' : 'image/png', 'cache-control': 'max-age=3600' });
    res.end(data);
  } catch {
    res.writeHead(404); res.end();
  }
}

/* ---------- Route có tham số ---------- */
const dynamic = [
  // Ảnh mẫu lấy từ thư mục image/ của repo
  ['GET', /^\/v1\/mock-images\/(.+)$/, (req, res, [file]) => sendImage(res, file)],
  ['GET', /^\/v1\/characters\/([^/]+)\/expression\/([^/]+)$/, (req, res, [id]) => { const file = (chars.find((c) => c.id === id)?.avatar_url || '').split('/').pop(); if (!file) { res.writeHead(404); return res.end(); } return sendImage(res, file); }],

  // Chat Bot AI
  ['GET', /^\/v1\/rooms\/([^/]+)\/messages$/, (req, res, [id]) => json(res, roomMessages[id] || [])],
  ['DELETE', /^\/v1\/rooms\/([^/]+)$/, (req, res, [id]) => { const i = rooms.findIndex((r) => r.id === id); if (i >= 0) rooms.splice(i, 1); json(res, { ok: true }); }],
  ['POST', /^\/v1\/rooms\/([^/]+)\/messages\/stream$/, async (req, res, [id]) => {
    const body = await readBody(req);
    const room = rooms.find((r) => r.id === id) || { character_ids: ['c1'] };
    const send = openStream(res);
    const userMessage = { id: randomUUID(), sender_type: 'user', character_id: null, text: body.message || '' };
    (roomMessages[id] ||= []).push(userMessage);
    send('user_message', userMessage);
    const speakers = body.speaker_mode === 'everyone' ? room.character_ids
      : String(body.speaker_mode || '').startsWith('character:') ? [body.speaker_mode.slice(10)]
      : [pick(room.character_ids)];
    for (const characterId of speakers) {
      send('typing', { character_id: characterId });
      await sleep(900);
      const [text, emotion, suggestions] = pick(ROLEPLAY_REPLIES);
      const reply = { id: randomUUID(), sender_type: 'character', character_id: characterId, text, emotion, suggestions };
      roomMessages[id].push(reply);
      send('character_message', reply);
    }
    send('done', {});
    res.end();
  }],
  ['PUT', /^\/v1\/characters\/([^/]+)\/reaction$/, async (req, res, [id]) => {
    const body = await readBody(req);
    const character = chars.find((c) => c.id === id);
    if (character && body.reaction) character.reactions[body.reaction] = (character.reactions[body.reaction] || 0) + 1;
    json(res, character || {});
  }],

  // Sáng tạo nhân vật
  ['PATCH', /^\/v1\/characters\/([^/]+)\/publication$/, async (req, res, [id]) => { const body = await readBody(req); const c = chars.find((x) => x.id === id); if (c) { c.is_public = Boolean(body.is_public ?? body.public); if (Array.isArray(body.tags)) c.tags = body.tags; if (body.character_type) c.character_type = body.character_type; } json(res, c || {}); }],
  ['POST', /^\/v1\/characters\/([^/]+)\/avatar$/, async (req, res, [id]) => { await drain(req); const c = chars.find((x) => x.id === id); if (c) c.avatar_url = img('liost.png'); json(res, c || {}); }],
  ['GET', /^\/v1\/documents\/([^/]+)$/, (req, res, [id]) => json(res, { id, status: 'ready', filename: storyDocuments[id]?.filename || 'truyen.txt' })],
  ['POST', /^\/v1\/documents\/([^/]+)\/discover-characters$/, async (req, res) => { await drain(req); json(res, { candidates: [
    { name: 'Thám tử Kha', description: 'Thám tử Sài Gòn thập niên 60, lạnh lùng, quan sát sắc.', source_evidence: ['Kha gõ nhẹ tẩu thuốc lên mép bàn.'], importance: 0.9 },
    { name: 'Cô Lan', description: 'Nhân chứng duy nhất của vụ án, nói ít nhưng nhớ mọi chi tiết.', source_evidence: ['Lan đứng nép sau quầy thuốc.'], importance: 0.7 },
    { name: 'Ông chủ tiệm', description: 'Người giữ chìa khóa kho, hay kể chuyện ngày xưa.', source_evidence: ['Ông lắc đầu, chùm chìa khóa kêu leng keng.'], importance: 0.5 },
  ] }); }],

  ['PATCH', /^\/v1\/admin\/models\/([^/]+)$/, async (req, res, [id]) => {
    const body = await readBody(req);
    const model = adminModels.find((m) => m.id === id);
    if (model) {
      const { api_key, ...rest } = body;
      Object.assign(model, rest);
      if (api_key) Object.assign(model, { has_api_key: true, api_key_hint: keyHint(api_key) });
    }
    json(res, model || {});
  }],
  ['DELETE', /^\/v1\/admin\/models\/([^/]+)$/, (req, res, [id]) => { const i = adminModels.findIndex((m) => m.id === id); if (i >= 0) adminModels.splice(i, 1); json(res, { ok: true }); }],
  ['DELETE', /^\/v1\/admin\/credentials\/bases\/([^/]+)$/, (req, res, [id]) => { const i = credentialState.bases.findIndex((b) => b.id === id); if (i >= 0) credentialState.bases.splice(i, 1); json(res, { ok: true }); }],
  ['PUT', /^\/v1\/admin\/presets\/([^/]+)$/, async (req, res, [type]) => {
    const body = await readBody(req);
    const c = chars.find((x) => x.id === type);
    if (!c) return json(res, { detail: 'Preset not found' }, 404);
    for (const key of ['name', 'display_name', 'description']) if (typeof body[key] === 'string') c[key] = body[key];
    json(res, { id: c.id, user_id: null, source: 'preset', spec: { preset_type: c.id, avatar_url: c.avatar_url, creation_type: 'preset', name: c.name, description: c.description, system_prompt: body.system_prompt || '', scenario: body.scenario || '', initial_greeting: body.initial_greeting || '', tts_voice_id: body.tts_voice_id || '', identity: body.identity || { role: c.support?.primary_role || 'companion' }, goals: body.goals || [], behavior_rules: body.behavior_rules || [] } });
  }],
  ['PUT', /^\/v1\/admin\/presets\/([^/]+)\/home-section$/, async (req, res, [type]) => {
    const body = await readBody(req);
    if (!['auto', 'featured', 'popular', 'top_rated', 'hidden'].includes(body.home_section)) return json(res, { detail: 'Invalid home section' }, 400);
    presetHomeSections[type] = body.home_section;
    json(res, { preset_type: type, home_section: body.home_section });
  }],
  ['PATCH', /^\/v1\/admin\/home-sections\/([^/]+)$/, async (req, res, [id]) => {
    const body = await readBody(req);
    const section = homeSectionsState.find((x) => x.id === id);
    if (section) Object.assign(section, body);
    json(res, section || {});
  }],
  ['DELETE', /^\/v1\/admin\/home-sections\/([^/]+)$/, (req, res, [id]) => { const i = homeSectionsState.findIndex((x) => x.id === id); if (i >= 0) homeSectionsState.splice(i, 1); json(res, { ok: true }); }],
  ['GET', /^\/v1\/admin\/database\/([^/]+)$/, (req, res, [name]) => json(res, dbRowsOf(name, new URL(req.url, 'http://mock').searchParams.get('user_id') || ''))],
  // CMS: model của Trợ lý AI
  ['PATCH', /^\/v1\/admin\/assistant-models\/([^/]+)$/, async (req, res, [id]) => {
    const body = await readBody(req);
    const model = adminModels.find((m) => m.id === id);
    if (model) Object.assign(model, { assistant_name: body.name ?? model.assistant_name, assistant_model_id: body.model_id ?? model.assistant_model_id, assistant_enabled: body.enabled ?? model.assistant_enabled, assistant_thinking_mode: body.thinking_mode ?? model.assistant_thinking_mode, assistant_reasoning_effort: body.reasoning_effort ?? model.assistant_reasoning_effort });
    json(res, model || {});
  }],
  ['PUT', /^\/v1\/admin\/assistant-purposes\/([^/]+)$/, async (req, res, [purpose]) => {
    const body = await readBody(req);
    assignPurpose(purpose, [body.primary_model_id, body.fallback_model_id, body.fallback_2_model_id].map((id) => id || ''), [body.primary_prompt, body.fallback_prompt, body.fallback_2_prompt]);
    json(res, { ok: true });
  }],

  ['PUT', /^\/v1\/admin\/assistant-profiles\/([^/]+)$/, async (req, res, [id]) => {
    const body = await readBody(req);
    assistantProfiles.items[id] = { ...(assistantProfiles.items[id] || {}), ...body };
    json(res, assistantProfiles.items[id]);
  }],

  // Trợ lý AI
  ['GET', /^\/v1\/assistant\/chats\/([^/]+)\/messages$/, (req, res, [id]) => json(res, assistantMessages[id] || [])],
  ['GET', /^\/v1\/assistant\/chats\/([^/]+)\/files$/, (req, res, [id]) => json(res, roomFiles[id] || [])],
  ['POST', /^\/v1\/assistant\/chats\/([^/]+)\/files$/, async (req, res, [id]) => {
    for await (const _ of req) { /* bỏ qua nội dung tệp */ }
    const file = { id: randomUUID(), filename: 'tai-lieu-dinh-kem.pdf', status: 'ready' };
    (roomFiles[id] ||= []).push(file);
    json(res, file);
  }],
  ['DELETE', /^\/v1\/assistant\/chats\/([^/]+)\/files\/([^/]+)$/, (req, res, [id, fileId]) => { roomFiles[id] = (roomFiles[id] || []).filter((f) => f.id !== fileId); json(res, { ok: true }); }],
  ['DELETE', /^\/v1\/assistant\/chats\/([^/]+)$/, (req, res, [id]) => { const i = assistantChats.findIndex((c) => c.id === id); if (i >= 0) assistantChats.splice(i, 1); json(res, { ok: true }); }],
  ['POST', /^\/v1\/assistant\/chats\/([^/]+)\/messages\/stream$/, async (req, res, [id]) => {
    const body = await readBody(req);
    const chat = assistantChats.find((c) => c.id === id);
    const mode = chat?.mode || 'assistant_general';
    const list = (assistantMessages[id] ||= []);
    list.push({ id: randomUUID(), role: 'user', text: body.message || '' });
    if (chat && list.length === 1) chat.title = String(body.message || ROOM_TITLES[mode]).slice(0, 60);
    const [text, suggestions] = ASSISTANT_REPLIES[mode] || ASSISTANT_REPLIES.assistant_general;
    const send = openStream(res);
    await sleep(600);
    for (const word of text.split(/(?<=\s)/)) {
      send('delta', { text: word });
      await sleep(35);
    }
    const reply = { id: randomUUID(), role: 'assistant', text, suggestions };
    list.push(reply);
    send('done', reply);
    res.end();
  }],
  ['PATCH', /^\/v1\/assistant\/memory\/items\/([^/]+)$/, async (req, res, [id]) => { const body = await readBody(req); const item = memories.find((m) => m.id === id); if (item && body.content) item.content = body.content; json(res, item || {}); }],
  ['DELETE', /^\/v1\/assistant\/memory\/items\/([^/]+)$/, (req, res, [id]) => { const i = memories.findIndex((m) => m.id === id); if (i >= 0) memories.splice(i, 1); json(res, { ok: true }); }],
  ['PATCH', /^\/v1\/assistant\/reminders\/([^/]+)$/, async (req, res, [id]) => { const body = await readBody(req); const item = reminders.find((r) => r.id === id); if (item) Object.assign(item, body); json(res, item || {}); }],
  ['DELETE', /^\/v1\/assistant\/reminders\/([^/]+)$/, (req, res, [id]) => { const i = reminders.findIndex((r) => r.id === id); if (i >= 0) reminders.splice(i, 1); json(res, { ok: true }); }],
];

/* ---------- Route cố định ---------- */
const routes = {
  'GET /v1/auth/me': () => account,
  'POST /v1/auth/login': () => ({ ...account, token: 'mock' }),
  'POST /v1/auth/register': (body) => ({ ...account, display_name: body.display_name || account.display_name, username: body.username || account.username, token: 'mock' }),
  'GET /v1/characters': () => chars,
  'GET /v1/public/characters': () => chars,
  'GET /v1/presets': () => ({ characters: chars, groups: [] }),
  'GET /v1/rooms': () => rooms,
  'POST /v1/rooms': (body) => {
    const ids = body.character_ids || ['c1'];
    const room = { id: randomUUID(), name: body.name || `Trò chuyện với ${ids.map((id) => chars.find((c) => c.id === id)?.name || '?').join(', ')}`, character_ids: ids, created_at: new Date().toISOString() };
    rooms.unshift(room);
    roomMessages[room.id] = [];
    return room;
  },
  'POST /v1/characters/generate': (body) => { const c = makeCharacter({ name: body.name, description: body.description, role: body.role, greeting: body.initial_greeting }); roomMessages[c.id] = []; return c; },
  'POST /v1/characters/from-document': (body) => makeCharacter({ name: body.candidate_name, description: `Nhân vật được tạo từ truyện ${storyDocuments[body.document_id]?.filename || ''}.`.trim() }),
  'POST /v1/documents/from-url': (body) => { const doc = { id: randomUUID(), filename: body.url || 'truyen-tu-link' }; storyDocuments[doc.id] = doc; return doc; },
  'POST /v1/character-sources': () => { const doc = { id: randomUUID(), filename: 'truyen-tai-len.txt' }; storyDocuments[doc.id] = doc; return doc; },
  'GET /v1/home-sections': () => homeSectionsState,
  'POST /v1/admin/home-sections': (body) => { const section = { id: `custom_${randomUUID().slice(0, 8)}`, name: body.name, rule: body.rule || 'tags', tags: body.tags || [], hidden: Boolean(body.hidden) }; homeSectionsState.push(section); return section; },
  'PUT /v1/admin/home-sections/order': (body) => { const order = body.ids || []; homeSectionsState.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id)); return homeSectionsState; },
  'GET /v1/admin/chat-logs': (body, query) => {
    const product = query.get('product') || 'all', q = query.get('q') || '';
    const rows = chatLogs.filter((r) => (product === 'all' || r.product === product) && matchQ(r, q));
    return { total: rows.length, columns: CHAT_LOG_COLUMNS, rows };
  },
  'GET /v1/admin/action-logs': (body, query) => {
    const category = query.get('category') || 'all', status = query.get('status_filter') || 'all', q = query.get('q') || '';
    const rows = actionLogs.filter((r) => (category === 'all' || r.category === category) && (status === 'all' || r.status === status) && matchQ(r, q));
    return { total: rows.length, columns: ACTION_COLUMNS, rows };
  },

  'GET /v1/assistant/chats': () => assistantChats,
  'POST /v1/assistant/chats': (body) => {
    const mode = body.mode || 'assistant_general';
    const chat = { id: randomUUID(), mode, title: ROOM_TITLES[mode], created_at: new Date().toISOString() };
    assistantChats.unshift(chat);
    assistantMessages[chat.id] = [];
    return chat;
  },
  'GET /v1/assistant/models': (_body, query) => assistantProfiles.items[query.get('mode') || 'assistant_general']?.user_pick ? assistantModels : [],
  'GET /v1/assistant/memory': (body, query) => ({ enabled: memoryState.enabled, memories: memories.filter((m) => !query.get('room_id') || m.room_id === query.get('room_id')), reminders }),
  'PATCH /v1/assistant/memory': (body) => { memoryState.enabled = Boolean(body.enabled); if (!memoryState.enabled) memories.splice(0); return memoryState; },
  'POST /v1/assistant/memory/items': (body) => { const item = { id: randomUUID(), room_id: body.room_id, mode: 'assistant_general', content: body.content, created_at: new Date().toISOString() }; memories.push(item); return item; },
  'POST /v1/assistant/reminders': (body) => { const item = { id: randomUUID(), title: body.title, due_at: body.due_at, status: 'active', last_notified_at: null }; reminders.push(item); return item; },
  'GET /v1/assistant/reminders/due': () => [],
  'POST /v1/i18n/translate': (body) => ({ translations: body.texts || [] }),

  // ---- CMS (admin) ----
  'GET /v1/admin/overview': () => {
    const extra = [
      ['Mây', 'companion', 18420], ['Kiếm khách Vô Danh', 'roleplay', 15300], ['Mr. Ben', 'study', 15200], ['Cô Lan', 'study', 12050],
      ['Anh Khoa', 'companion', 9310], ['Bà Nội Bếp', 'companion', 8820], ['Coach Minh', 'work', 7710],
    ].map(([name, role, usage_count], i) => ({ id: `ov${i}`, name, role, type: 'preset', category: 'utility', updated_at: '2026-09-30', usage_count, avatar_url: null }));
    return {
      stats: { users: 1284, users_delta: 46, characters: 3972, characters_delta: 212, rooms: 8410, rooms_delta: 530, messages: 214380, messages_delta: 12400, memories: 19620, memories_delta: 1100, ready_documents: 1204, failed_documents: 17 },
      characters: [...chars.map((c) => ({ id: c.id, name: c.name, role: c.support.primary_role, type: 'preset', category: c.category, updated_at: '2026-09-30', usage_count: c.usage_count, avatar_url: c.avatar_url })), ...extra],
      rooms: rooms.map((r) => ({ id: r.id, name: r.name, members: r.character_ids.length, messages: (roomMessages[r.id] || []).length, updated_at: '' })),
      documents: [
        { id: 'doc_1', filename: 'tam-quoc-dien-nghia-q1.pdf', status: 'ready' },
        { id: 'doc_2', filename: 'so-tay-nhan-vien.docx', status: 'ready' },
        { id: 'doc_3', filename: 'scan-hop-dong.pdf', status: 'failed', error: 'không trích được chữ' },
      ],
      ai_activity: [
        { id: 'a1', room: 'Trò chuyện với Luna', layers: 6, memories: 3, documents: 0, created_at: iso(-60e3) },
        { id: 'a2', room: 'Thám tử Kha', layers: 7, memories: 1, documents: 2, created_at: iso(-72e3) },
        { id: 'a3', room: 'Nhóm luyện tiếng Anh', layers: 5, memories: 1, documents: 0, created_at: iso(-115e3) },
        { id: 'a4', room: 'Tư vấn tâm lý', layers: 4, memories: 0, documents: 0, created_at: iso(-199e3) },
      ],
    };
  },
  'GET /v1/admin/settings': () => adminSettings,
  'PUT /v1/admin/settings': (body) => Object.assign(adminSettings, body),
  'GET /v1/admin/access-control': () => ({ maintenance_mode: false, registration_enabled: true, accounts: [{ user_id: 'u1', username: account.username, display_name: account.display_name, status: 'active', is_admin: true, suspended_until: null, ban_reason: '', created_at: '2026-09-01', updated_at: '' }] }),
  'GET /v1/admin/characters': () => ({
    preset_catalog: chars.map((c) => ({ id: c.id, user_id: null, source: 'preset', home_section: presetHomeSections[c.id] || 'auto', spec: { preset_type: c.id, avatar_url: c.avatar_url, creation_type: 'preset', name: c.name, description: c.description, system_prompt: '', scenario: '', initial_greeting: c.support.introduction, tts_voice_id: '', identity: { role: c.support.primary_role }, goals: [], behavior_rules: [] } })),
    user_characters: [{ id: 'uc1', user_id: 'u1', source: 'user', spec: { avatar_url: null, creation_type: 'custom', name: 'Mèo Mun', description: 'Chú mèo đen hay càu nhàu.', system_prompt: '', scenario: '', initial_greeting: 'Meo.', identity: { role: 'companion' }, goals: [], behavior_rules: [] } }],
  }),
  'GET /v1/admin/assistant-profiles': () => assistantProfiles,
  'POST /v1/admin/assistant-profiles': (body) => {
    const id = `assistant_custom_${++customAssistantSeq}`;
    assistantProfiles.items[id] = { title: body.title, slogan: body.slogan || '', description: body.description, greeting: body.greeting || '', starters: [], visible: body.visible !== false, temperature: 0.7, max_tokens: 1024, user_pick: false, icon: body.icon, hue: body.hue, hair: body.hair, custom: true, stats: stats(0, 0, 0, 0, [0, 0, 0, 0, 0, 0, 0]) };
    assistantProfiles.order.push(id);
    return { id };
  },
  'GET /v1/admin/models': () => adminModels,
  'GET /v1/admin/database': () => Object.entries(DB_TABLES).map(([name, [columns, rows]]) => ({ name, rows: rows.length, columns })),
  'GET /v1/admin/credentials': () => credentialState,
  'PUT /v1/admin/credentials/avibi': (body) => Object.assign(credentialState.avibi, { configured: true, source: 'cms', hint: keyHint(body.api_key || '') }),
  'DELETE /v1/admin/credentials/avibi': () => Object.assign(credentialState.avibi, { configured: true, source: 'modal_secret', hint: 'Modal Secret' }),
  'PUT /v1/admin/credentials/bases': (body) => {
    const base = String(body.api_base || '').replace(/\/+$/, '').toLowerCase();
    const found = credentialState.bases.find((b) => b.api_base === base);
    if (found) found.hint = keyHint(body.api_key || '');
    else credentialState.bases.push({ id: randomUUID(), api_base: base, hint: keyHint(body.api_key || '') });
    return { ok: true };
  },
  'POST /v1/admin/models': (body) => {
    const model = makeModel(`m${++modelSeq}`, body.name || 'Model mới', body.provider || '', body.model_id || '', body.name || 'Model mới', false, 'default', 'default');
    Object.assign(model, { logo: body.logo || '', api_base: body.api_base || 'https://gateway.avibi.ai/v1', has_api_key: Boolean(body.api_key), api_key_hint: body.api_key ? keyHint(body.api_key) : '', enabled: body.enabled !== false });
    adminModels.push(model);
    return model;
  },
};

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://mock');
  const path = url.pathname;
  try {
    for (const [method, pattern, handler] of dynamic) {
      const match = req.method === method && path.match(pattern);
      if (match) return await handler(req, res, match.slice(1).map(decodeURIComponent));
    }
    const body = ['POST', 'PATCH', 'PUT'].includes(req.method) && !String(req.headers['content-type'] || '').startsWith('multipart/') ? await readBody(req) : {};
    // Giữ thay đổi giao diện / ngôn ngữ / hồ sơ trong phiên.
    if (req.method === 'PATCH' && path === '/v1/auth/me') return json(res, Object.assign(account, body));
    const handler = routes[`${req.method} ${path}`];
    json(res, handler ? handler(body, url.searchParams) : req.method === 'GET' ? [] : {});
  } catch (error) {
    if (!res.headersSent) json(res, { detail: String(error) }, 500);
    else res.end();
  }
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} is already in use (the real backend or another mock may be running).`);
    process.exit(1);
  }
  throw err;
});

server.listen(PORT, () => {
  console.log(`Mock API on http://localhost:${PORT} — log in with any username/password.`);
});
