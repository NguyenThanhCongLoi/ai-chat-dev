export type UiLanguage = string;
export const UI_LANGUAGES: {
    code: UiLanguage;
    label: string;
}[] = [
    { code: "vi", label: "Tiếng Việt" },
    { code: "en", label: "English" },
    { code: "zh", label: "中文" },
    { code: "ja", label: "日本語" },
    { code: "ko", label: "한국어" },
    { code: "my", label: "မြန်မာ" },
    { code: "km", label: "ភាសាខ្មែរ" },
].map((language) => ({
    ...language,
    label: language.label + " (" + language.code + ")",
}));
// Only locales shipped with this frontend build are selectable.
export function supportedUiLanguage(language: string | null | undefined): UiLanguage {
    return UI_LANGUAGES.some((item) => item.code === language) ? language! : "vi";
}
const ERROR_MESSAGES: Record<string, Record<number | "default", string>> = {
    km: {
        400: "ទិន្នន័យមិនត្រឹមត្រូវ។ សូមពិនិត្យហើយសាកល្បងម្តងទៀត។",
        401: "ឈ្មោះអ្នកប្រើ ពាក្យសម្ងាត់ ឬវគ្គចូលប្រើមិនត្រឹមត្រូវ។",
        403: "អ្នកមិនមានសិទ្ធិអនុវត្តសកម្មភាពនេះទេ។",
        404: "រកមិនឃើញទិន្នន័យដែលបានស្នើសុំ។",
        409: "ទិន្នន័យនេះមានរួចហើយ ឬមានការប៉ះទង្គិចជាមួយទិន្នន័យដែលមានស្រាប់។",
        413: "ឯកសារដែលបានផ្ទុកឡើងមានទំហំធំពេក។",
        429: "សេវាកម្មកំពុងមមាញឹក។ សូមសាកល្បងម្តងទៀតពេលក្រោយ។",
        500: "ប្រព័ន្ធមានបញ្ហា។ សូមសាកល្បងម្តងទៀត។",
        503: "សេវា AI មិនអាចប្រើបានជាបណ្តោះអាសន្ន។",
        default: "មានបញ្ហាកើតឡើង។ សូមសាកល្បងម្តងទៀត។",
    },
    vi: {
        400: "Dữ liệu không hợp lệ. Vui lòng kiểm tra lại.",
        401: "Tên đăng nhập, mật khẩu hoặc phiên đăng nhập không hợp lệ.",
        403: "Bạn không có quyền thực hiện thao tác này.",
        404: "Không tìm thấy dữ liệu yêu cầu.",
        409: "Dữ liệu đã tồn tại hoặc đang xung đột.",
        413: "Tệp tải lên quá lớn.",
        429: "Hệ thống đang bận. Vui lòng thử lại sau.",
        500: "Hệ thống gặp lỗi. Vui lòng thử lại.",
        503: "Dịch vụ AI tạm thời không khả dụng.",
        default: "Đã xảy ra lỗi. Vui lòng thử lại.",
    },
    en: {
        400: "Invalid data. Please check and try again.",
        401: "The username, password or session is invalid.",
        403: "You do not have permission to perform this action.",
        404: "The requested item was not found.",
        409: "The item already exists or conflicts with existing data.",
        413: "The uploaded file is too large.",
        429: "The service is busy. Please try again later.",
        500: "A system error occurred. Please try again.",
        503: "The AI service is temporarily unavailable.",
        default: "Something went wrong. Please try again.",
    },
    zh: {
        400: "数据无效，请检查后重试。",
        401: "用户名、密码或登录会话无效。",
        403: "您无权执行此操作。",
        404: "未找到请求的内容。",
        409: "数据已存在或发生冲突。",
        413: "上传的文件过大。",
        429: "系统繁忙，请稍后重试。",
        500: "系统发生错误，请重试。",
        503: "AI 服务暂时不可用。",
        default: "发生错误，请重试。",
    },
    ja: {
        400: "入力内容が正しくありません。確認してもう一度お試しください。",
        401: "ユーザー名、パスワード、またはセッションが無効です。",
        403: "この操作を行う権限がありません。",
        404: "指定されたデータが見つかりません。",
        409: "データが既に存在するか競合しています。",
        413: "アップロードしたファイルが大きすぎます。",
        429: "システムが混み合っています。後でもう一度お試しください。",
        500: "システムエラーが発生しました。",
        503: "AIサービスは一時的に利用できません。",
        default: "エラーが発生しました。もう一度お試しください。",
    },
    ko: {
        400: "입력한 데이터가 올바르지 않습니다. 다시 확인해 주세요.",
        401: "사용자 이름, 비밀번호 또는 로그인 세션이 올바르지 않습니다.",
        403: "이 작업을 수행할 권한이 없습니다.",
        404: "요청한 데이터를 찾을 수 없습니다.",
        409: "데이터가 이미 존재하거나 충돌합니다.",
        413: "업로드한 파일이 너무 큽니다.",
        429: "시스템이 혼잡합니다. 잠시 후 다시 시도해 주세요.",
        500: "시스템 오류가 발생했습니다.",
        503: "AI 서비스를 일시적으로 사용할 수 없습니다.",
        default: "오류가 발생했습니다. 다시 시도해 주세요.",
    },
    fr: {
        400: "Données invalides. Vérifiez-les puis réessayez.",
        401: "Le nom d’utilisateur, le mot de passe ou la session est incorrect.",
        403: "Vous n’avez pas l’autorisation d’effectuer cette action.",
        404: "L’élément demandé est introuvable.",
        409: "Les données existent déjà ou sont en conflit.",
        413: "Le fichier envoyé est trop volumineux.",
        429: "Le service est occupé. Réessayez plus tard.",
        500: "Une erreur système s’est produite.",
        503: "Le service d’IA est temporairement indisponible.",
        default: "Une erreur s’est produite. Réessayez.",
    },
    es: {
        400: "Los datos no son válidos. Revísalos e inténtalo de nuevo.",
        401: "El usuario, la contraseña o la sesión no son válidos.",
        403: "No tienes permiso para realizar esta acción.",
        404: "No se encontró el elemento solicitado.",
        409: "Los datos ya existen o están en conflicto.",
        413: "El archivo subido es demasiado grande.",
        429: "El servicio está ocupado. Inténtalo más tarde.",
        500: "Se produjo un error del sistema.",
        503: "El servicio de IA no está disponible temporalmente.",
        default: "Se produjo un error. Inténtalo de nuevo.",
    },
    de: {
        400: "Ungültige Daten. Bitte prüfen und erneut versuchen.",
        401: "Benutzername, Passwort oder Sitzung ist ungültig.",
        403: "Du hast keine Berechtigung für diese Aktion.",
        404: "Das angeforderte Element wurde nicht gefunden.",
        409: "Die Daten sind bereits vorhanden oder stehen in Konflikt.",
        413: "Die hochgeladene Datei ist zu groß.",
        429: "Der Dienst ist ausgelastet. Bitte später erneut versuchen.",
        500: "Ein Systemfehler ist aufgetreten.",
        503: "Der KI-Dienst ist vorübergehend nicht verfügbar.",
        default: "Ein Fehler ist aufgetreten. Bitte erneut versuchen.",
    },
    pt: {
        400: "Dados inválidos. Verifique e tente novamente.",
        401: "O nome de usuário, a senha ou a sessão é inválida.",
        403: "Você não tem permissão para realizar esta ação.",
        404: "O item solicitado não foi encontrado.",
        409: "Os dados já existem ou estão em conflito.",
        413: "O arquivo enviado é muito grande.",
        429: "O serviço está ocupado. Tente novamente mais tarde.",
        500: "Ocorreu um erro no sistema.",
        503: "O serviço de IA está temporariamente indisponível.",
        default: "Ocorreu um erro. Tente novamente.",
    },
    ru: {
        400: "Некорректные данные. Проверьте их и повторите попытку.",
        401: "Неверное имя пользователя, пароль или сеанс.",
        403: "У вас нет разрешения на это действие.",
        404: "Запрошенные данные не найдены.",
        409: "Данные уже существуют или конфликтуют.",
        413: "Загруженный файл слишком большой.",
        429: "Сервис перегружен. Повторите попытку позже.",
        500: "Произошла системная ошибка.",
        503: "Сервис ИИ временно недоступен.",
        default: "Произошла ошибка. Повторите попытку.",
    },
    th: {
        400: "ข้อมูลไม่ถูกต้อง โปรดตรวจสอบแล้วลองอีกครั้ง",
        401: "ชื่อผู้ใช้ รหัสผ่าน หรือเซสชันไม่ถูกต้อง",
        403: "คุณไม่มีสิทธิ์ดำเนินการนี้",
        404: "ไม่พบข้อมูลที่ต้องการ",
        409: "ข้อมูลมีอยู่แล้วหรือเกิดข้อขัดแย้ง",
        413: "ไฟล์ที่อัปโหลดมีขนาดใหญ่เกินไป",
        429: "ระบบกำลังมีผู้ใช้งานมาก โปรดลองอีกครั้งภายหลัง",
        500: "เกิดข้อผิดพลาดของระบบ",
        503: "บริการ AI ไม่พร้อมใช้งานชั่วคราว",
        default: "เกิดข้อผิดพลาด โปรดลองอีกครั้ง",
    },
    id: {
        400: "Data tidak valid. Periksa dan coba lagi.",
        401: "Nama pengguna, kata sandi, atau sesi tidak valid.",
        403: "Anda tidak memiliki izin untuk tindakan ini.",
        404: "Data yang diminta tidak ditemukan.",
        409: "Data sudah ada atau mengalami konflik.",
        413: "File yang diunggah terlalu besar.",
        429: "Layanan sedang sibuk. Coba lagi nanti.",
        500: "Terjadi kesalahan sistem.",
        503: "Layanan AI sementara tidak tersedia.",
        default: "Terjadi kesalahan. Silakan coba lagi.",
    },
};
export function localizedError(status: number, language: UiLanguage = storedLanguage()): string {
    const direct = ERROR_MESSAGES[language];
    if (direct)
        return direct[status] || direct.default;
    const source = ERROR_MESSAGES.vi[status] || ERROR_MESSAGES.vi.default;
    return translateDynamic(source);
}
const EN: Record<string, string> = {
    "Kênh AI": "AI channels",
    "Hỏi chủ đề mới": "New topic",
    "Đóng lịch sử": "Close history",
    "Trò chuyện với Trợ lý AI": "Chat with AI Assistant",
    "Bấm Chat để tiếp tục cuộc trò chuyện của từng tác vụ.": "Select Chat to continue each task's conversation.",
    "Dữ liệu không hợp lệ. Vui lòng kiểm tra lại.": "Invalid data. Please check and try again.",
    "Tên đăng nhập, mật khẩu hoặc phiên đăng nhập không hợp lệ.": "The username, password or session is invalid.",
    "Bạn không có quyền thực hiện thao tác này.": "You do not have permission to perform this action.",
    "Không tìm thấy dữ liệu yêu cầu.": "The requested item was not found.",
    "Dữ liệu đã tồn tại hoặc đang xung đột.": "The item already exists or conflicts with existing data.",
    "Tệp tải lên quá lớn.": "The uploaded file is too large.",
    "Hệ thống đang bận. Vui lòng thử lại sau.": "The service is busy. Please try again later.",
    "Hệ thống gặp lỗi. Vui lòng thử lại.": "A system error occurred. Please try again.",
    "Dịch vụ AI tạm thời không khả dụng.": "The AI service is temporarily unavailable.",
    "Đã xảy ra lỗi. Vui lòng thử lại.": "Something went wrong. Please try again.",
    "Đang tải…": "Loading…",
    "Đăng nhập để tiếp tục các cuộc trò chuyện của bạn.": "Sign in to continue your conversations.",
    "Tạo tài khoản demo được lưu trong database.": "Create an account saved in the database.",
    "Tên hiển thị": "Display name",
    "Tên của bạn": "Your name",
    "Tên đăng nhập": "Username",
    "ví dụ: thanhcong": "e.g. thanhcong",
    "Mật khẩu": "Password",
    "Đăng nhập": "Sign in",
    "Tạo tài khoản": "Create account",
    "Chưa có tài khoản? Đăng ký": "No account yet? Sign up",
    "Đã có tài khoản? Đăng nhập": "Already have an account? Sign in",
    "Ngôn ngữ": "Language",
    "Tiếng Việt": "Vietnamese",
    "Nhân vật luôn bên bạn": "Characters always by your side",
    "Trang chủ": "Home",
    "Cộng đồng": "Community",
    "Nhân vật của tôi": "My characters",
    "Tạo nhân vật": "Create character",
    "Cuộc trò chuyện": "Conversations",
    "Trò chuyện gần đây": "Recent chats",
    "Tìm nhân vật hoặc cuộc trò chuyện": "Search characters or conversations",
    Sáng: "Light",
    Tối: "Dark",
    "Cài đặt": "Settings",
    "Cài đặt cá nhân": "Personal settings",
    "Hồ sơ công khai": "Public profile",
    "Tài khoản": "Account",
    "Tùy chọn": "Preferences",
    "Đăng xuất": "Sign out",
    "Thay avatar": "Change avatar",
    "Giới thiệu": "Bio",
    "Giới thiệu ngắn về bạn…": "A short introduction about you…",
    "Lưu hồ sơ": "Save profile",
    "Gói hiện tại": "Current plan",
    "Mật khẩu hiện tại": "Current password",
    "Mật khẩu mới": "New password",
    "Ít nhất 6 ký tự": "At least 6 characters",
    "Đổi mật khẩu": "Change password",
    "Giao diện": "Appearance",
    "Giảm chuyển động": "Reduce motion",
    "Hạn chế animation trong giao diện.": "Limit animations in the interface.",
    "Đang hoàn thiện nhân vật...": "Finishing your character...",
    "Đang tải ngôn ngữ...": "Loading language...",
    "Lần đầu lúc nào cũng lâu, chờ xíu nha.": "The first time always takes a little longer. Please wait a moment.",
    "Đang chuẩn bị toàn bộ giao diện và nội dung nhân vật.": "Preparing the complete interface and character content.",
    "Giao diện sẽ tự mở khi mọi nội dung đã sẵn sàng.": "The interface will open when all content is ready.",
    "Đang chuẩn bị tài nguyên...": "Preparing resources...",
    "Đang tải nhân vật, bộ ảnh biểu cảm và phòng trò chuyện.": "Loading the character, expression set and chat room.",
    "Nhân vật đang đến với bạn, chờ đợi là hạnh phúc.": "Your character is on the way. Please wait a moment.",
    "Đi đâu mà vội mà vàng đúng không...": "You can chat as soon as preparation is complete.",
    "Tài nguyên đã chuẩn bị xong. Bạn có thể bắt đầu trò chuyện.": "Resources are ready. You can start chatting.",
    "Đang xây dựng tính cách, tạo chân dung chính diện và bộ ảnh biểu cảm.": "Building the personality, front portrait and expression set.",
    "Khung chat sẽ tự mở sau khi mọi bước hoàn tất.": "The chat will open when every step is complete.",
    "Mở thanh điều hướng": "Open navigation",
    "Thu thanh điều hướng": "Collapse navigation",
    "Xóa cuộc trò chuyện": "Delete conversation",
    "KHÁM PHÁ NHÂN VẬT": "DISCOVER CHARACTERS",
    "Hôm nay bạn cần ai đồng hành?": "Who would you like by your side today?",
    "Chọn một người phù hợp với tâm trạng, học tập hoặc công việc của bạn.": "Choose someone for your mood, studies or work.",
    "＋ Tạo nhân vật mới": "＋ Create new character",
    "Tạo nhân vật mới": "Create new character",
    "Tạo phòng nhóm": "Create group chat",
    "Tất cả nhân vật": "All characters",
    "Nhân vật hệ thống": "System characters",
    "Nhân vật của bạn": "Your characters",
    "Trò chuyện →": "Chat →",
    "Tiếp tục trò chuyện": "Continue chatting",
    "Yêu thích": "Favorites",
    "Phổ biến": "Popular",
    "Đánh giá cao": "Top rated",
    "Giải trí": "Entertainment",
    "NHÂN VẬT CỘNG ĐỒNG": "COMMUNITY CHARACTERS",
    "Khám phá nhân vật public": "Discover public characters",
    "Tìm theo tên, loại hoặc thẻ; mỗi nhân vật hiển thị rõ người tạo.": "Search by name, type or tag; every character shows its creator.",
    "Tất cả": "All",
    "Đồng hành": "Companion",
    "Học tập": "Study",
    "Công việc": "Work",
    "Tình cảm": "Romance",
    "Người dùng": "User",
    bởi: "by",
    "Biểu cảm từ cộng đồng": "Community reactions",
    "người theo dõi": "followers",
    "Theo dõi": "Follow",
    "người đã dùng": "users",
    "Đánh giá:": "Rate:",
    "Thêm vào nhân vật của tôi": "Add to my characters",
    "Chưa có nhân vật public phù hợp.": "No matching public characters yet.",
    "Mỗi nhân vật có tính cách, giọng nói và mục tiêu riêng.": "Each character has a distinct personality, voice and goals.",
    "Công khai": "Public",
    "Riêng tư": "Private",
    "Trò chuyện": "Chat",
    "Xóa nhân vật": "Delete character",
    "Chọn cách bắt đầu: dùng nhân vật có sẵn hoặc tạo một người hoàn toàn mới.": "Start with an existing character or create someone entirely new.",
    "Nhân vật có sẵn": "Existing characters",
    "Tạo mới": "Create new",
    "Chọn vai trò phù hợp": "Choose a suitable role",
    Avatar: "Avatar",
    "Hồ sơ nhân vật": "Character profile",
    "Thiết lập hồ sơ và quyền hiển thị của nhân vật.": "Set up the character profile and visibility.",
    "Tên nhân vật": "Character name",
    "Ví dụ: Linh": "e.g. Linh",
    "Mô tả tính cách hoặc cốt truyện": "Personality or story description",
    "Đây là nhân vật trong phim hoặc hoạt hình?": "Is this a movie or animated character?",
    "Bật để hệ thống nghiên cứu nhân vật và kết hợp với mô tả của bạn.": "Enable character research and combine it with your description.",
    "Tên nhân vật gốc": "Original character name",
    "Ví dụ: Tony Stark, Gojo Satoru...": "e.g. Tony Stark, Gojo Satoru...",
    "Tên phim, hoạt hình hoặc tác phẩm": "Movie, animation or work",
    "Ví dụ: Iron Man, Jujutsu Kaisen...": "e.g. Iron Man, Jujutsu Kaisen...",
    "Vai trò": "Role",
    "Ví dụ: bạn học, đồng nghiệp, người bạn thân...": "e.g. classmate, coworker, close friend...",
    "Chọn tối đa 8 tags": "Choose up to 8 tags",
    "Tìm hoặc nhập tag rồi nhấn Enter": "Search or enter a tag, then press Enter",
    "Công khai nhân vật": "Make character public",
    "Người khác có thể tìm thấy và thêm nhân vật này.": "Other users can discover and add this character.",
    "Bối cảnh": "Scenario",
    "Hai người quen nhau thế nào, đang ở đâu, mối quan hệ hiện tại...": "How you met, where you are and your current relationship...",
    "Lời chào đầu tiên": "First greeting",
    "Câu đầu tiên nhân vật nói khi bắt đầu chat": "The character's first message when chat begins",
    "Ví dụ hội thoại": "Dialogue examples",
    "Tạo và bắt đầu trò chuyện": "Create and start chatting",
    "Tạo phiên bản phản chiếu": "Create a mirrored character",
    "Ngày sinh": "Birthday",
    "Lời giới thiệu": "Introduction",
    "Tạo phòng chat": "Create chat room",
    "Chọn các nhân vật muốn đưa vào cùng một cuộc trò chuyện.": "Choose characters for one conversation.",
    "Tạo phòng": "Create room",
    "Trả lời khác": "Alternative reply",
    "↻ Trả lời khác": "↻ Alternative reply",
    Nguồn: "Sources",
    "Nhắn gì đó... Gõ @ để gọi nhân vật": "Write a message... Type @ to call a character",
    "Tự chọn": "Auto select",
    "Mọi người": "Everyone",
    Gửi: "Send",
    "Gửi →": "Send →",
    "＋ Cuộc trò chuyện mới": "＋ New chat",
    "Cuộc trò chuyện mới": "New chat",
    "Lịch sử trò chuyện": "Chat history",
    "Ký ức đã ghim": "Pinned memories",
    "Thông tin nhân vật": "Character information",
    "Tùy chỉnh": "Customize",
    "Ký ức": "Memories",
    "Bạn có thể chỉnh sửa, ghim hoặc xóa ký ức.": "You can edit, pin or delete memories.",
    Ghim: "Pin",
    "Bỏ ghim": "Unpin",
    Xóa: "Delete",
    "Đã lưu hồ sơ": "Profile saved",
    "Đã lưu tùy chọn": "Preferences saved",
    "Đã đổi mật khẩu": "Password changed",
    "Đã theo dõi người tạo": "Creator followed",
    Mới: "New",
    "lượt dùng": "uses",
    "người dùng": "users",
    "Xem →": "View →",
    "đang nhập...": "is typing...",
};
const textState = new WeakMap<Text, {
    source: string;
    rendered: string;
}>();
let runtimePack: Record<string, string> = {};
export function setRuntimeTranslations(values: Record<string, string>) {
    runtimePack = values;
}
export function translationSources(): string[] {
    return Object.keys(EN);
}
function translateDynamic(value: string): string {
    const error = value.match(/^Error:\s*(.+)$/s);
    if (error)
        return error[1];
    const decorated = value.match(/^([+⌂⌕☺＋▣☀☾↻]\s*)(.+)$/s);
    if (decorated)
        return decorated[1] + translateDynamic(decorated[2]);
    // Translate the stable label before preserving its live count. Otherwise
    // "Nhân vật của tôi (6)" cannot match the saved "Nhân vật của tôi" key.
    const counted = value.match(/^(.+?)(\s*\(\d+\))$/);
    if (counted && (runtimePack[counted[1].trim()] || EN[counted[1].trim()]))
        return translateDynamic(counted[1].trim()) + counted[2];
    const templates: Array<[RegExp, string, string]> = [
        [/^Đã chọn (\d+) nhân vật$/, "Đã chọn {count} nhân vật", "{count} characters selected"],
        [/^(.+) đang nhập\.\.\.$/, "{name} đang nhập...", "{name} is typing..."],
        [/^Trò chuyện với (.+)$/, "Trò chuyện với {name}", "Chat with {name}"],
        [/^Xóa (.+)$/, "Xóa {name}", "Delete {name}"],
        [/^Đã đánh giá (\d+) sao$/, "Đã đánh giá {count} sao", "Rated {count} stars"],
    ];
    for (const [pattern, source, english] of templates) {
        const match = value.match(pattern);
        if (match) return (runtimePack[source] || english).replace(/\{(?:name|count)\}/g, () => match[1]);
    }
    return runtimePack[value] || EN[value] || value;
}
export function translateUiText(value: string, language: UiLanguage): string {
    return language === "vi" ? value : translateDynamic(value);
}
export function restoredLanguage(accountLanguage?: string | null): UiLanguage {
    try {
        const saved = localStorage.getItem("ui_language");
        if (UI_LANGUAGES.some(item => item.code === saved)) return saved!;
    } catch {}
    return supportedUiLanguage(accountLanguage);
}
export function storedLanguage(): UiLanguage {
    return restoredLanguage();
}
export function rememberLanguage(language: UiLanguage) {
    language = supportedUiLanguage(language);
    try { localStorage.setItem("ui_language", language); } catch {}
    document.documentElement.lang = language;
}
export function localizeInterface(root: HTMLElement, language: UiLanguage) {
    rememberLanguage(language);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node: Text | null;
    while ((node = walker.nextNode() as Text | null)) {
        if (node.parentElement?.closest('[data-no-translate="true"]'))
            continue;
        const raw = node.nodeValue || "";
        const trimmed = raw.trim();
        if (!trimmed)
            continue;
        const previous = textState.get(node);
        const source = previous && raw === previous.rendered ? previous.source : trimmed;
        const translated = language === "vi" ? source : translateDynamic(source);
        const leading = raw.match(/^\s*/)?.[0] || "";
        const trailing = raw.match(/\s*$/)?.[0] || "";
        const rendered = `${leading}${translated}${trailing}`;
        if (raw !== rendered)
            node.nodeValue = rendered;
        textState.set(node, { source, rendered });
    }
    root
        .querySelectorAll<HTMLElement>("[placeholder],[title],[aria-label]")
        .forEach((element) => {
        if (element.closest('[data-no-translate="true"]'))
            return;
        for (const attribute of ["placeholder", "title", "aria-label"]) {
            const current = element.getAttribute(attribute);
            if (!current)
                continue;
            const key = `i18n${attribute.replace("-", "")}`;
            const priorRendered = element.dataset[key + "Rendered"];
            const source = priorRendered === current && element.dataset[key]
                ? element.dataset[key]!
                : current;
            const rendered = language === "vi" ? source : translateDynamic(source);
            element.dataset[key] = source;
            element.dataset[key + "Rendered"] = rendered;
            if (current !== rendered)
                element.setAttribute(attribute, rendered);
        }
    });
}
