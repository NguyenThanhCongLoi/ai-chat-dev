# Biểu cảm và độ mở

Tái sử dụng expression endpoint + loadExpressionPortrait + bundled_expressions. Selene được ánh xạ tới image/react/elf.webp; không tạo hệ reaction thứ hai, không gọi GPU.

Bộ elf có happy, sad, angry, surprised, laughing, crying, winking, playful, thinking. Mapping neutral→happy, shy→winking hiện có được giữ. World dùng các trạng thái tương thích classifier; art bổ sung worried/afraid/vulnerable có thể chuẩn bị sau, hiện dùng thinking/sad.

Immediate emotion khác emotional access GUARDED/OPEN/VULNERABLE/DEEPLY_CONNECTED. Access được suy ra từ World trust snapshot/growth và bị chặn bởi max_access của chương, không cho Chương 1 tự lộ toàn bộ đời Selene.

Ảnh chuyển bằng preload/cache + fade, giữ ảnh cũ khi ảnh mới đang tải. Không sửa nhãn emotion global của chat thường.
