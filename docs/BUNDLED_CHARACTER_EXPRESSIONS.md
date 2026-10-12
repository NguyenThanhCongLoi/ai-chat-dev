# Supplied character expression sheets
The backend prefers matching files in image/react over existing generated/default
expression images. Matching uses exact accent-insensitive names/display names:
Ruby, Hà, KimAnh, Trịnh Khải Nguyên, Mira (or Mira Sunpetal), Lyra, Ren, Aurelion,
Merr and Nguyễn Vũ. Unmatched characters retain their current expression path.
Original card avatars and source sheets are preserved.

The supplied files contain nine cells: happy, sad, angry, surprised, laughing,
crying, winking, playful and thinking. Reviewed crop coordinates exclude labels
and borders. The UI supports the existing six states plus thinking: happy/sad/angry/surprised map
directly, neutral uses Happy Smile as requested; thinking uses Thinking separately; shy uses winking as the closest supplied pose.
All nine crops are retained on the server, with the two compatibility aliases.
Remaining extra poses do not automatically expand the existing LLM emotion contract.

Cuts use aspect-preserving 512px WebP canvases, no image API or model download.
A shared __bundled__:name owner stores each set once across user copies.
Source file hashes invalidate saved crops on replacement; frontend cache version
4 avoids replaying older object URLs after the new deployment.

Build frontend then deploy Modal web; image is already included in the API image.
The set is installed lazily on expression access/status and persisted to the DB.
No manual production database edit or separate image-generation worker is needed.


Thinking is preloaded after room entry and displayed while typing is active
(before the first text delta). The first delta removes that character's typing
state; reaction/final events then display the expressed emotion, including thinking.
This waiting pose adds no LLM call. The emotion classification prompt includes
thinking, and CMS previews expose its label and all supplied crop labels.


## Elf / Selene Moonbrook

image/react/elf.webp được cắt thành 9 biểu cảm: happy, sad, angry, surprised, laughing, crying, winking, playful, thinking. Neutral dùng Happy Smile, shy dùng Winking. Bộ được chia sẻ dưới __bundled__:elf và cập nhật theo hash file khi deploy ảnh mới; không gọi model tạo ảnh. Tên Selene Moonbrook/Elf hoặc preset_type=elf dùng bộ này.
