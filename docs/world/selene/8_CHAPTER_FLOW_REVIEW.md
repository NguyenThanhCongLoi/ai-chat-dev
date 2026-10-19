> Rà soát vật phẩm cả 8 chương (19/10/2026): [ITEM_AUDIT_20261019.md](ITEM_AUDIT_20261019.md).

> Thứ tự bấm chi tiết mới: [Mỗi map một mục tiêu — cả 8 chương](ITEM_INTERACTION_ORDER.md).

> Cập nhật 19/10/2026: [điều kiện khám phá, map gộp, admin preview và xem lại](EXPLORATION_MEDIA_FIXES_20261019.md). Các bước chung BG không còn là tab map riêng.

# Echoes of Moonfall — Flow 8 chương sau khi mở rộng

Ngày cập nhật: 18/10/2026. Nội dung bên dưới được chép từ dữ liệu World đã sửa. Không thay chat thường, điểm lựa chọn, vật phẩm, điều kiện mở chương hoặc công thức ending. Các tương tác truyện mới phải được trải qua trước puzzle cũ.

Mỗi chương có 4 địa điểm khám phá, sau đó là puzzle/lựa chọn, ký ức và cuốn thư. Mỗi đoạn trước hoặc sau clip có tối đa một lời dẫn và một thoại chính; một tương tác có thể có cả câu báo trước và câu phản ứng sau clip. Có tương tác chỉ có lời dẫn.

Ảnh mới chưa có: dùng nền sạch hiện có và điểm tương tác dạng marker. Các event mới hiện bằng lời kể; chưa gán video khác để giả làm video mới. Video ký ức M01–M08 và mở cổng vẫn dùng asset hiện có. Danh sách cần tạo: [NARRATIVE_MEDIA_PENDING.md](NARRATIVE_MEDIA_PENDING.md).

Mục tiêu nhịp đọc/chơi: 5–8 phút/chương, toàn tuyến khoảng 45–70 phút. Đây là mục tiêu thiết kế, chưa phải thời lượng đã đo; không thêm thời gian chờ cưỡng ép.

CMS đã lưu có thể ghi đè mặc định. Save cũ giữ snapshot, không bị thêm các bước mới giữa lượt chơi. Bản sửa áp dụng mặc định cho lượt mới dùng cấu hình mới; chưa triển khai production hoặc ghi đè CMS đang chạy.

Nội dung mới có tiếng Việt/Anh. Các ngôn ngữ khác dùng fallback hiện có cho câu chưa được dịch; không gắn nhãn bản tiếng Anh là bản dịch.

## Chương 1 — Tàn tích thức giấc

**Flow:** Cổng cổ → Con đường bị bỏ quên → Dư âm vòng phép → Tàn tích ngoài → puzzle → lựa chọn → ký ức → cuốn thư.

### Cổng cổ

Nền dự phòng hiện có: `ancient_gate`. Mã cảnh: `ancient_gate`.

**Lời dẫn:** Cánh cổng cổ đứng im dưới ánh trăng. Selene dừng lại trước những nét khắc đã bạc màu.

**Selene:** Tôi có cảm giác đã từng đến đây... Mình xem cánh cổng trước nhé.

**Tương tác: Ổ khóa cổng** — bắt buộc (`selene_01_old_gate`).

Vật phẩm: `moon_rune`.

**Lời dẫn:** Cánh cổng không nhúc nhích. Ổ khóa hình trăng vẫn nguyên vẹn; bên bậc đá có thứ ánh bạc ló ra.

**Selene:** Nó bị khóa rồi... Khoan đã, dưới bậc đá kia có gì lấp lánh. Mình thử nhìn kỹ nhé.

**Tương tác: Lối đi sụp** — bắt buộc (`selene_01_collapsed_path`).

Vật phẩm: `ancient_key`.

**Lời dẫn:** Bạn tìm được chiếc chìa khóa cổ dưới bậc đá. Những nét rune trên thân chìa giống với nét khắc ở ổ khóa.

**Selene:** Một chiếc chìa khóa... Nhưng hình như vẫn thiếu điều gì đó. Mình tìm thêm những dấu khắc quanh đây nhé.

### Con đường bị bỏ quên

Nền dự phòng hiện có: `moonfall_outer_ruins`. Mã cảnh: `side_path`.

**Lời dẫn:** Lối nhỏ vòng quanh cổng bị đá vụn che khuất. Những khe chữ nhật chạy dọc tường.

**Tương tác: Dời đá chắn lối** — bắt buộc (`selene_01_clear_stones`).

**Lời dẫn:** Bạn dời đá rời để lộ một hàng phiến lát. Vệt mòn chạy sát tường rồi dừng trước huy hiệu trăng.

**Tương tác: Đối chiếu dấu chân** — bắt buộc (`selene_01_footprints`).

**Lời dẫn:** Dấu giày cũ vòng tránh phiến đá giữa đường. Người từng qua đây biết có thứ nằm dưới nó.

**Tương tác: Phiến đá có huy hiệu** — bắt buộc (`selene_01_arrow_trap`).

**Lời dẫn:** Một tiếng tách vang dưới chân; tên bật khỏi tường. Selene giơ vòng phép bạc, giữ mũi tên giữa không trung rồi để nó rơi xuống.

**Selene:** Đừng nhúc nhích.

### Dư âm vòng phép

Nền dự phòng hiện có: `moonfall_outer_ruins`. Mã cảnh: `ward_aftermath`.

**Lời dẫn:** Cơ chế đã ngừng. Selene vẫn nhìn bàn tay vừa giơ lên.

**Tương tác: Kiểm tra mũi tên** — bắt buộc (`selene_01_fallen_arrow`).

**Lời dẫn:** Vòng bạc đã tan, nhưng mũi tên thật còn nằm đó. Phép thuật đến trước khi Selene nhớ mình từng học nó.

**Selene:** Tôi không nghĩ… Tôi chỉ biết mình phải làm vậy.

**Tương tác: Đọc huy hiệu Moonbrook** — bắt buộc (`selene_01_oath_mark`).

**Lời dẫn:** Dưới huy hiệu là bàn tay đặt lên rune. Người Moonbrook dùng ký hiệu như lời thề, không chỉ như phép thuật.

### Tàn tích ngoài

Nền dự phòng hiện có: `moonfall_outer_ruins`. Mã cảnh: `outer_ruins`.

**Lời dẫn:** Giữa tàn tích ngoài, những nét khắc còn sót lại trên đá. Pho tượng và bức tường có vẻ cùng kể một câu chuyện.

**Selene:** Hoang tàn đến thế mà những văn tự cổ vẫn còn... Mình thử đọc quanh pho tượng rồi so với bức tường kia nhé.

**Tương tác: Pho tượng vỡ** — bắt buộc (`selene_01_broken_statue`).

Vật phẩm: `moonstone`.

**Lời dẫn:** Sau lưng tượng, dòng chữ gợi ý: ánh trăng soi đường; ký ức giữ tên; máu đóng lời thề.

**Selene:** Pho tượng vỡ vẫn còn những nét chữ. Có lẽ chúng sẽ giúp mình hiểu các ký hiệu trên tường.

**Tương tác: Bức tường rune** — bắt buộc (`selene_01_rune_wall`).

**Lời dẫn:** Ba biểu tượng còn xoay được: TRĂNG, KÝ ỨC, MÁU. Đây là một thứ tự, không phải phép hiến tế.

**Selene:** Những ký hiệu này có thể xoay được. Mình thử đối chiếu chúng với dòng chữ bên pho tượng nhé.

### Puzzle — Lời thề trên đá

Đáp án giữ nguyên: TRĂNG → KÝ ỨC → MÁU.

**Selene:** Nó nhận ra chìa khóa… và cả thứ tự tôi đã quên.

### Lựa chọn

Bạn muốn cùng Selene đi tiếp thế nào?

- Tôi sẽ giúp cô tìm lại mọi ký ức.
- Mình chỉ tìm những điều cô thực sự muốn nhớ.
- Có lẽ cô quên chúng vì một lý do.

Điểm/cờ của các lựa chọn giữ nguyên.

### M01 — `memory_video_01`

Trước M01: người chơi bấm mở cổng → `enter_ruins_video` → M01.

Lời đầu đi cùng phim. Các lời còn lại sau phim; giới hạn một lời dẫn và một thoại chính, phần vượt giới hạn lưu trong lịch sử.

**Lời dẫn:** Dưới ánh trăng, Selene trẻ chạy qua hành lang Moonbrook về phía cánh cửa rune đang hé.

**Lời dẫn:** Một giọng nói chưa rõ người cất lên: “Selene! Đừng mở cánh cửa đó!”

**Selene:** Tôi đã ngoảnh lại… Nhưng gương mặt ấy không còn trong mảnh nhớ này.

### Cuốn thư

Chương 1 dùng cuốn thư riêng trong `chapter_one_flow`, tiêu đề **Moonbrook — nơi những cái tên còn ngủ quên**:

Từng có người đi qua những hành lang này với sách vở trong tay, tin rằng trăng sẽ còn soi sáng sân học viện vào ngày mai. Giờ chỉ những nét rune nhận ra người trở lại.

Cánh cổng đã mở, nhưng ký ức đầu tiên dừng lại trước một gương mặt. Ai đã gọi Selene? Và vì sao lời cảnh báo ấy vẫn còn vang giữa một nơi tưởng như đã quên tất cả?

Hãy mang câu hỏi đó trở về cùng cô. Có những câu chuyện chỉ hé tiếp khi hai người đủ sẵn lòng lắng nghe.

## Chương 2 — Mặt dây chuyền bạc

**Flow:** Tàn tích trong → Vườn nguyệt hoa → Bóng người qua mái vòm → Kho lưu trữ cổ → puzzle → lựa chọn → ký ức → cuốn thư.

### Tàn tích trong

Nền dự phòng hiện có: `inner_ruins`. Mã cảnh: `inner_ruins`.

**Lời dẫn:** Phía trong cổng còn những đồ vật nhỏ giữa đống đổ nát. Chúng có thể nối chiếc vòng bạc với một người từng ở đây.

**Selene:** Mình bắt đầu từ những thứ gần gũi nhé. Chiếc vòng và cánh hoa có thể kể chuyện khác với những bức tường này.

**Tương tác: Mặt dây chuyền bạc** — bắt buộc (`selene_02_pendant`).

Vật phẩm: `silver_pendant`.

**Lời dẫn:** Ở mặt trong vòng là hai nét khắc đan vào nhau. Selene không nhận ra chữ, nhưng ngón tay cô dừng đúng vị trí.

**Selene:** Chiếc vòng này có gì đó khiến tôi bận tâm. Mình thử xem mặt trong, nơi ít bị thời gian làm mòn hơn nhé.

**Tương tác: Cánh hoa dưới đá** — tùy chọn (`selene_02_moonflower`).

Vật phẩm: `moonflower_petal`.

**Lời dẫn:** Một cánh nguyệt hoa ép khô còn mùi mưa. Trong tích tắc, có tiếng cười trên mái nhà.

**Selene:** Một cánh hoa nằm giữa đá vụn... Mình nên xem nó có liên quan đến những đồ vật còn lại không.

### Vườn nguyệt hoa

Nền dự phòng hiện có: `inner_ruins`. Mã cảnh: `moonflower_garden`.

**Lời dẫn:** Qua mái vòm là sân vườn cũ. Cây đã khô; một bụi nguyệt hoa vẫn còn bên ghế đá.

**Tương tác: Ghế đá dưới vòm** — bắt buộc (`selene_02_stone_bench`).

**Lời dẫn:** Mặt ghế lõm thành hai chỗ ngồi. Giữa chúng, hai cái tên bị cạo đi nhưng đường viền vẫn còn.

**Tương tác: Nét tên bị xóa** — bắt buộc (`selene_02_erased_names`).

**Lời dẫn:** Những nét xóa tập trung vào tên, giống khoảng trống ở gương mặt trong M01; chưa đủ để khẳng định cùng một người.

**Selene:** Cùng một khoảng trống… nhưng mình vẫn cần bằng chứng.

### Bóng người qua mái vòm

Nền dự phòng hiện có: `inner_ruins`. Mã cảnh: `echo_archway`.

**Lời dẫn:** Tiếng cười thoáng qua sân. Một bóng nữ lướt dưới mái vòm dẫn về kho sách.

**Tương tác: Lần theo bóng người** — bắt buộc (`selene_02_follow_silhouette`).

**Lời dẫn:** Selene chạy tới mái vòm; bóng người tan trước khi cô nhìn rõ. Không ai đứng sau cột đá.

**Selene:** Chờ đã!

**Tương tác: Nơi bóng người tan** — bắt buộc (`selene_02_echo_trace`).

**Lời dẫn:** Một cánh hoa rơi rồi tan vào ánh trăng. Đây là dấu vết ký ức, không phải người vừa chạy khỏi sân.

### Kho lưu trữ cổ

Nền dự phòng hiện có: `ancient_archive`. Mã cảnh: `archive`.

**Lời dẫn:** Trong kho lưu trữ, một cuốn nhật ký còn được bảo vệ. Những trang rời có thể thuộc về nó.

**Selene:** Nếu còn một lời hứa ở đây, có lẽ nó nằm trong những trang này. Mình thử tìm đoạn bị thiếu nhé.

**Tương tác: Nhật ký cổ** — bắt buộc (`selene_02_journal`).

Vật phẩm: `ancient_journal`.

**Lời dẫn:** Ba dòng còn đọc được: lời hứa, tặng vật, người nhận. Một trang bị xé trước phần tên người tặng.

**Selene:** Cuốn nhật ký có thể giúp mình lần lại câu chuyện của chiếc vòng. Thử tìm những đoạn nhắc đến một món quà nhé.

**Tương tác: Trang nhật ký rách** — bắt buộc (`selene_02_torn_page`).

Vật phẩm: `torn_diary_page`.

**Lời dẫn:** Mép giấy khớp với trang thiếu. Dòng “để nó nhớ thay em” nằm trước lời đáp “em sẽ không quên”.

**Selene:** Mảnh giấy này có vẻ thuộc cuốn nhật ký. Thử đặt cạnh mép trang bị thiếu rồi đọc nối lại xem sao.

### Puzzle — Ghép lời hứa

Đáp án giữ nguyên: Tặng mặt dây chuyền → Selene hứa sẽ nhớ → Cô gái trêu lời hứa.

**Selene:** Tôi nhớ cảm giác lúc nhận nó. Còn tên cô ấy… vẫn chưa.

### Lựa chọn

Bạn đáp lại sự im lặng của Selene thế nào?

- Không cần ép mình nhớ ngay.
- Mình có thể tìm cô gái ấy là ai.
- Tại sao ký ức này lại bị xóa?

Điểm/cờ của các lựa chọn giữ nguyên.

### M02 — `memory_video_02`

Lời đầu đi cùng phim. Các lời còn lại sau phim; giới hạn một lời dẫn và một thoại chính, phần vượt giới hạn lưu trong lịch sử.

**Lời dẫn:** Một cô gái elf đặt mặt dây chuyền vào tay Selene trẻ.

**Lời dẫn:** Cô gái nói: “Nếu một ngày em quên chị… hãy để nó nhớ thay em.”

**Selene:** Tôi đã nói: “Em sẽ không quên.” Cô ấy cười: “Em lúc nào cũng nói vậy.”

### Cuốn thư

Chiếc vòng và lời hứa là thật. Một người quan trọng đã trao nó cho Selene, nhưng tên và gương mặt vẫn chưa trở lại.

Nếu ký ức này dịu dàng như vậy, tại sao nó lại cần bị xóa?

## Chương 3 — Nghi lễ cấm

**Flow:** Cầu thang dưới học viện → Căn phòng ngầm → Bẫy phong ấn → Khoảng lặng sau biến cố → puzzle → lựa chọn → ký ức → cuốn thư.

### Cầu thang dưới học viện

Nền dự phòng hiện có: `underground_chamber`. Mã cảnh: `descent`.

**Lời dẫn:** Cầu thang xoắn dẫn xuống tầng ngầm. Rune đỏ dừng trước một lớp màng sáng.

**Tương tác: Chạm phong ấn lối xuống** — bắt buộc (`selene_03_barrier`).

**Lời dẫn:** Selene đưa tay; lớp màng mở ở chỗ ngón tay chạm. Phong ấn không coi cô là người lạ.

**Selene:** Nơi này từng cho tôi đi qua. Điều đó chưa nói tôi đã làm gì.

**Tương tác: Dấu chân trước cửa** — bắt buộc (`selene_03_approach`).

**Lời dẫn:** Bụi giữ một lối đi thẳng vào phòng. Không có vệt kéo lê trên các bậc cuối.

### Căn phòng ngầm

Nền dự phòng hiện có: `underground_chamber`. Mã cảnh: `chamber`.

**Lời dẫn:** Dấu vết trong căn phòng ngầm còn đủ để đối chiếu: vòng nghi lễ, rune, thư cháy và niêm phong.

**Selene:** Tôi thấy nơi này quen một cách khó chịu. Mình xem từng dấu vết trước nhé, đừng để cảm giác quyết định thay bằng chứng.

**Tương tác: Vòng nghi lễ** — bắt buộc (`selene_03_ritual_circle`).

Vật phẩm: `witch_symbol`.

**Lời dẫn:** Dấu chân đi vào tâm vòng, không có vết kéo lê. Người bước vào đã tự đi.

**Selene:** Đừng chạm vào tâm vòng vội. Dấu vết quanh nó có thể cho biết người ta đã bước vào đây như thế nào.

**Tương tác: Rune màu đỏ** — bắt buộc (`selene_03_blood_rune`).

Vật phẩm: `seal_stone`.

**Lời dẫn:** Màu đỏ đã khô từ lâu. Dấu tay nhỏ và một nét cong giống vòng của Selene nằm ở tâm.

**Selene:** Nét cong trên rune trông quen quá. Có lẽ nên so nó với thứ tôi đang mang.

**Tương tác: Lá thư cháy** — bắt buộc (`selene_03_burned_letter`).

**Lời dẫn:** Một phần thư còn đọc được: “Người mang vật dẫn phải tự nguyện.” Không có tên người mang.

**Selene:** Lá thư còn lại rất ít chữ. Mình đọc kỹ điều kiện của nghi lễ trước khi đoán ai đã tham gia nhé.

**Tương tác: Dấu Hội đồng** — bắt buộc (`selene_03_council_seal`).

Vật phẩm: `council_record`.

**Lời dẫn:** Sáp niêm phong của Hội đồng đè lên tro cũ. Những người chủ trì đã xác nhận việc này sau khi bắt đầu.

**Selene:** Dấu niêm này có thể cho biết ai đã xác nhận nghi lễ. Nhưng người đóng dấu chưa chắc là người đứng trong vòng.

### Bẫy phong ấn

Nền dự phòng hiện có: `underground_chamber`. Mã cảnh: `seal_trap`.

**Lời dẫn:** Ở mép vòng nghi lễ, những đường rune nối vào một phiến điều khiển.

**Tương tác: Kiểm tra phiến điều khiển** — bắt buộc (`selene_03_seal_contact`).

**Lời dẫn:** Phiến đá sáng đỏ khi chạm; xiềng phép vọt khỏi sàn. Selene phá một vòng xiềng, vòng khác sượt cổ tay.

**Selene:** Lùi lại, ra ngoài đường rune!

**Tương tác: Tách phiến điều khiển** — bắt buộc (`selene_03_seal_release`).

**Lời dẫn:** Bạn kéo phiến đá khỏi rãnh tiếp xúc. Xiềng tắt, để lại thoáng hình người đứng giữa vòng, chưa thể nhận diện.

**Selene:** Mình cần đối chiếu dấu tay và chiếc vòng trước khi gọi tên người đó.

### Khoảng lặng sau biến cố

Nền dự phòng hiện có: `underground_chamber`. Mã cảnh: `quiet_landing`.

**Lời dẫn:** Lối vừa qua đã yên. Hãy đối chiếu các dấu vết trước khi kết luận điều cảnh nhớ chưa nói hết.

### Puzzle — Ai đứng giữa vòng nghi lễ?

Đáp án giữ nguyên: Selene.

**Selene:** Là tôi. Nhưng đừng để một đáp án trở thành cả bản án.

### Lựa chọn

Bạn nói gì trước điều vừa suy ra?

- Điều đó không có nghĩa cô có tội.
- Cô biết nhiều hơn điều đang kể.
- Mình vẫn chưa biết tại sao cô chọn làm vậy.

Điểm/cờ của các lựa chọn giữ nguyên.

### M03 — `memory_video_03`

Lời đầu đi cùng phim. Các lời còn lại sau phim; giới hạn một lời dẫn và một thoại chính, phần vượt giới hạn lưu trong lịch sử.

**Lời dẫn:** Selene trẻ tự bước vào vòng nghi lễ. Một pháp sư Hội đồng giữ tay trên ấn.

**Lời dẫn:** Pháp sư cảnh báo cô không thể rời đi khi phong ấn bắt đầu. Selene đáp: “Tôi biết.” Câu hỏi về hậu quả còn dang dở khi mảnh nhớ đứt.

**Lời dẫn:** Pháp sư hỏi cô có hiểu hậu quả không. Mảnh nhớ đứt trước câu trả lời.

**Selene:** Tôi đã bước vào. Điều đó có thật. Nhưng tại sao… vẫn nằm bên kia mảnh nhớ.

### Cuốn thư

Selene tự bước vào vòng và biết mình không thể rời đi khi phong ấn bắt đầu. Chưa biết cô đã được nói toàn bộ hậu quả hay chưa.

Cô đã chọn điều gì — và đã biết bao nhiêu khi lựa chọn?

## Chương 4 — Đêm Moonfall

**Flow:** Moonbrook được tái dựng → Moonbrook trong ký ức → Hành lang sụp đổ → Khoảng lặng sau biến cố → puzzle → lựa chọn → ký ức → cuốn thư.

### Moonbrook được tái dựng

Nền dự phòng hiện có: `moonfall_past`. Mã cảnh: `reconstruction`.

**Lời dẫn:** Học viện trở lại nguyên vẹn rồi thoáng nhòe. Đây là cảnh tái dựng, không phải đường quay về quá khứ.

**Tương tác: Vòm cửa lặp lại** — bắt buộc (`selene_04_flicker`).

**Lời dẫn:** Một học viên qua cùng vòm cửa hai lần với đúng một động tác. Cảnh nhớ đang lặp lại phần nó còn giữ.

**Tương tác: Đánh dấu các góc nhìn** — bắt buộc (`selene_04_viewpoints`).

**Lời dẫn:** Tinh thể nhìn ra sân; phiến đá quay vào phòng; hành lang chỉ giữ hướng chạy. Không điểm nào nhìn hết học viện.

**Selene:** Đừng để vẻ hoàn chỉnh của nơi này đánh lừa mình.

### Moonbrook trong ký ức

Nền dự phòng hiện có: `moonfall_past`. Mã cảnh: `past`.

**Lời dẫn:** Ký ức dựng lại một đêm hỗn loạn. Mỗi dấu vết chỉ giữ một phần cảnh tượng; hãy tìm những góc nhìn có thể đối chiếu.

**Selene:** Mình chỉ đang nhìn lại đêm ấy. Thử xem tinh thể, phiến đá và hành lang có kể cùng một chuyện không nhé.

**Tương tác: Mảnh tinh thể** — bắt buộc (`selene_04_crystal`).

Vật phẩm: `crystal_fragment`.

**Lời dẫn:** Tinh thể lưu một cảnh từ góc nhìn bên ngoài Selene. Mỗi mảnh có một góc nhìn riêng, không phải sự thật toàn cảnh.

**Selene:** Thử nhìn xem tinh thể ghi lại cảnh này từ đâu. Có thể nó đã bỏ sót điều ở ngoài tầm nhìn.

**Tương tác: Tiếng vọng đang vỡ** — tùy chọn (`selene_04_echo`).

**Lời dẫn:** Bạn dừng lại giữ tiếng vọng ổn định thay vì đuổi theo ngay. Một đứa trẻ trong ký ức kịp tìm được cửa trú.

**Selene:** Tiếng vọng này mong manh quá. Mình có thể lắng nghe một chút, không cần đuổi theo mọi ánh sáng.

**Tương tác: Phiến đá gãy** — bắt buộc (`selene_04_tablet`).

Vật phẩm: `broken_tablet`.

**Lời dẫn:** Một câu được khắc như lời nhắn cho người sẽ xem: các mảnh nhớ giữ khoảng cách giữa người mang và điều được mang.

**Selene:** Phiến đá vẫn còn một lời nhắn. Có lẽ nó giải thích cách đọc những mảnh ký ức quanh mình.

**Tương tác: Hành lang đổ nát** — bắt buộc (`selene_04_corridor`).

**Lời dẫn:** Những đốm sáng dẫn vào nguy hiểm. Selene trẻ chạy theo chúng, ngược với đám đông.

**Selene:** Hành lang cho mình một góc nhìn khác. Thử đối chiếu hướng chạy ở đây với cảnh trong tinh thể nhé.

### Hành lang sụp đổ

Nền dự phòng hiện có: `moonfall_past`. Mã cảnh: `collapse_passage`.

**Lời dẫn:** Chuông học viện vang. Những bóng người chạy qua khi ánh sáng trên cao đứt thành từng vệt.

**Tương tác: Băng qua đoạn trần nứt** — bắt buộc (`selene_04_falling_ceiling`).

**Lời dẫn:** Đá rơi chắn lối. Selene dựng màn chắn, giữ đủ khoảng trống để hai người vượt qua trước khi trần sập.

**Selene:** Đi sát tôi!

**Tương tác: Nhìn theo đám đông** — bắt buộc (`selene_04_opposite_direction`).

**Lời dẫn:** Selene trẻ chạy ngược dòng người. Lối tới tiếng vọng mắc kẹt vẫn ở bên kia; bạn có thể dừng giúp nó hoặc tiếp tục lần dấu.

### Khoảng lặng sau biến cố

Nền dự phòng hiện có: `moonfall_past`. Mã cảnh: `quiet_landing`.

**Lời dẫn:** Lối vừa qua đã yên. Hãy đối chiếu các dấu vết trước khi kết luận điều cảnh nhớ chưa nói hết.

### Puzzle — Một ký ức nói được điều gì?

Đáp án giữ nguyên: Một góc nhìn, cần đối chiếu.

**Selene:** Vậy mình giữ lấy điều đã thấy, mà không ép nó trả lời điều chưa thấy.

### Lựa chọn

Bạn muốn làm gì với lời cảnh báo trong ký ức?

- Mình sẽ so sánh các mảnh, không tin riêng một mảnh.
- Tôi sẽ ở bên cô khi mình tìm tiếp.
- Mình phải giữ bằng chứng về đêm ấy.

Điểm/cờ của các lựa chọn giữ nguyên.

### M04 — `memory_video_04`

Lời đầu đi cùng phim. Các lời còn lại sau phim; giới hạn một lời dẫn và một thoại chính, phần vượt giới hạn lưu trong lịch sử.

**Lời dẫn:** Selene trẻ giữa đám đông và mảnh vỡ trong học viện. Ánh sáng phía sau chập chờn khi khuôn mặt cô hiện gần hơn.

**Lời dẫn:** Trong tiếng vọng ngoài khung hình, một giọng hỏi: “Nếu họ phát hiện cô thực sự là gì—” Selene trẻ đáp: “Vậy đừng để họ phát hiện.” Lời nhắn còn lại: “Đừng tin tất cả những gì tôi để lại.”

**Lời dẫn:** Lời cảnh báo thuộc tiếng vọng còn lại; hình ảnh không xác nhận Selene trẻ đang nhìn thấy người xem.

**Selene:** Hình ảnh chỉ giữ một góc nhìn. Tôi sẽ nghe lời cảnh báo ấy, nhưng không coi nó là cả sự thật.

### Cuốn thư

Các góc nhìn không bao quát cả đêm Moonfall. Selene trẻ đi ngược đám đông; tiếng vọng để lại lời cảnh báo đừng tin mọi điều cô lưu lại.

Nếu chính quá khứ cảnh báo về ký ức, điều gì đang bị che giấu?

## Chương 5 — Kẻ bị gọi là phù thủy

**Flow:** Kho lưu trữ cổ → Hệ thống bảo vệ kho → Lối tới nhà bên rừng → Ngôi nhà bên rừng → puzzle → lựa chọn → ký ức → cuốn thư.

### Kho lưu trữ cổ

Nền dự phòng hiện có: `ancient_archive`. Mã cảnh: `records`.

**Lời dẫn:** Hồ sơ Hội đồng nằm trên bàn, nhưng mực, sáp và ngày tháng không nhất thiết thuộc cùng một thời điểm.

**Selene:** Tên tôi ở ngay đây... Nhưng mình hãy xem cách hồ sơ được viết trước. Mực và ngày tháng có thể nói nhiều hơn tiêu đề.

**Tương tác: Lớp mực** — bắt buộc (`selene_05_ink`).

Vật phẩm: `council_record`.

**Lời dẫn:** Mực quanh tên Selene mới hơn dòng mô tả sự kiện. Chữ được thêm sau.

**Selene:** Màu mực quanh cái tên có vẻ khác phần còn lại. Mình nên xem các dòng có được viết cùng lúc không.

**Tương tác: Dấu niêm** — bắt buộc (`selene_05_seal`).

**Lời dẫn:** Dấu sáp khớp Hội đồng, nhưng chồng lên một chữ ký đã bị gạch.

**Selene:** Dấu niêm không nói được toàn bộ câu chuyện. Thử xem bên dưới lớp sáp còn dấu vết nào không.

**Tương tác: Ngày chỉnh sửa** — bắt buộc (`selene_05_timestamp`).

**Lời dẫn:** Ghi chú lề xác nhận hồ sơ bị sửa ba ngày sau Moonfall.

**Selene:** Ngày tháng có thể giúp mình kiểm tra bản hồ sơ. Tìm xem người ta đã ghi lại lần chỉnh sửa ở đâu nhé.

### Hệ thống bảo vệ kho

Nền dự phòng hiện có: `ancient_archive`. Mã cảnh: `archive_defense`.

**Lời dẫn:** Khi hồ sơ rời bàn, rune trên kệ sáng. Giấy tự lật về cùng một dòng buộc tội.

**Tương tác: Những trang giấy bay** — bắt buộc (`selene_05_paper_accusation`).

**Lời dẫn:** Giấy xoáy quanh Selene thành bóng phù thủy; các chữ PHÙ THỦY, PHẢN BỘI, QUÁI VẬT bám theo cô.

**Selene:** Một từ được viết đủ nhiều lần không tự biến thành sự thật.

**Tương tác: Tìm dấu niêm thư viện** — bắt buộc (`selene_05_security_seal`).

**Lời dẫn:** Bạn đặt dấu niêm trùng đường khắc trên bàn. Giấy rơi; chữ QUÁI VẬT nấn ná rồi tắt.

### Lối tới nhà bên rừng

Nền dự phòng hiện có: `witch_area`. Mã cảnh: `forest_threshold`.

**Lời dẫn:** Một dấu người gửi trên phong bì dẫn tới ngôi nhà sát rừng.

**Tương tác: So dấu người gửi** — bắt buộc (`selene_05_sender_mark`).

**Lời dẫn:** Ký hiệu hộp thư khớp phong bì. Nó nối thư với ngôi nhà, chưa xác nhận mọi điều người viết kể.

**Tương tác: Kiểm tra bản nháp thư** — bắt buộc (`selene_05_letter_context`).

**Lời dẫn:** Bản nháp chừa chỗ ghi ngày sửa hồ sơ. Người viết cũng tìm bằng chứng, không chỉ gửi lời minh oan.

**Selene:** Tôi muốn sự thật, không phải một lời minh oan dễ chịu.

### Ngôi nhà bên rừng

Nền dự phòng hiện có: `witch_area`. Mã cảnh: `witch_house`.

**Lời dẫn:** Trong ngôi nhà bên rừng còn thư từ và nét chữ để đối chiếu với hồ sơ Hội đồng.

**Selene:** Ở đây vẫn còn thư. Mình so nét chữ và ngày viết với hồ sơ nhé; biết đâu hai bản kể không khớp nhau.

**Tương tác: Thư Elarion** — bắt buộc (`selene_05_letter`).

Vật phẩm: `elarion_letter`.

**Lời dẫn:** Thư viết: “Nếu lịch sử cần một con quái vật, họ đã chọn cô.” Ngày thư sớm hơn bản sửa hồ sơ.

**Selene:** Thư của Elarion có thể là một nguồn đối chiếu. Mình so ngày viết với hồ sơ, thay vì tin ngay một bên nhé.

**Tương tác: Chữ ký và vết cháy** — bắt buộc (`selene_05_signature`).

**Lời dẫn:** Một chữ ký trùng nét trong nhật ký. Những vết cháy che tên người làm chứng, không che ngày.

**Selene:** Chữ ký này đáng đối chiếu với nét chữ mình đã thấy. Những phần không cháy cũng có thể giúp xác định thời điểm.

### Puzzle — Điều gì được bằng chứng xác nhận?

Đáp án giữ nguyên: Hồ sơ bị sửa sau sự kiện.

**Selene:** Họ không chỉ xóa ký ức của tôi. Họ sửa cả cách lịch sử nhớ về tôi.

### Lựa chọn

Bạn hiểu hành động ấy theo hướng nào?

- Ai đó đã ép cô quên đi.
- Có lẽ cô đang bảo vệ một người.
- Có thể cô bảo vệ mọi người khỏi chính ký ức ấy.

Điểm/cờ của các lựa chọn giữ nguyên.

### M05 — `memory_video_05`

Lời đầu đi cùng phim. Các lời còn lại sau phim; giới hạn một lời dẫn và một thoại chính, phần vượt giới hạn lưu trong lịch sử.

**Lời dẫn:** Bản gốc ghi một phong ấn do Hội đồng giám sát. Ba ngày sau, một bàn tay thêm tên Selene vào phần tội trạng.

**Lời dẫn:** Elarion niêm lá thư: “Nếu lịch sử cần một con quái vật, họ đã chọn cô.”

**Selene:** Một dòng mực đã quyết định người khác sợ tôi thế nào. Nhưng nó không được quyết định tôi là ai.

### Cuốn thư

Hồ sơ chính thức bị sửa sau Moonfall. Điều đó chưa đủ để kết luận Selene hoàn toàn vô tội hoặc mọi lời Hội đồng đều sai.

Họ che giấu điều Selene đã làm — hay điều cô đã ngăn lại?

## Chương 6 — Hai mươi chín phút bị mất

**Flow:** Hầm sâu → Hành lang gương → Chiếu nghỉ đồng hồ → Hành lang ký ức → puzzle → lựa chọn → ký ức → cuốn thư.

### Hầm sâu

Nền dự phòng hiện có: `deep_vault`. Mã cảnh: `vault`.

**Lời dẫn:** Trong hầm, đồng hồ và dấu vết nghi lễ giữ lại những mốc rời. Cần tìm điểm bắt đầu trước khi sắp lại đêm ấy.

**Selene:** Tôi muốn hiểu đêm ấy đã diễn ra thế nào, nhưng mình cứ chậm thôi. Bắt đầu từ những mốc còn kiểm tra được nhé.

**Tương tác: 23:47 · Kích hoạt** — bắt buộc (`selene_06_activation`).

**Lời dẫn:** Nghi lễ bắt đầu lúc 23:47 theo cả đồng hồ và nhật ký.

**Selene:** Mình cần một mốc bắt đầu chắc chắn. Thử xem đồng hồ và bản ghi có cùng chỉ về một thời điểm không.

**Tương tác: 23:52 · Hàng rào phía bắc** — bắt buộc (`selene_06_barrier`).

**Lời dẫn:** Hàng rào phía bắc đổ lúc 23:52; đây không phải thời điểm nghi lễ kết thúc.

**Selene:** Hàng rào đổ là một sự kiện riêng. Mình đừng nhầm nó với lúc mọi chuyện kết thúc nhé.

**Tương tác: Mảnh gương** — tùy chọn (`selene_06_mirror`).

Vật phẩm: `mirror_shard`.

**Lời dẫn:** Hình Selene trong gương chậm hơn cô một nhịp. Một bản thể được nhớ lại không hoàn toàn trùng với người đang đứng đây.

**Selene:** Hình trong gương không hoàn toàn theo kịp tôi. Mình quan sát nó như một dấu vết, đừng vội coi đó là hiện tại.

### Hành lang gương

Nền dự phòng hiện có: `deep_vault`. Mã cảnh: `mirror_hall`.

**Lời dẫn:** Các mặt gương phản chiếu Selene ở những độ tuổi khác nhau. Không mặt nào giữ trọn căn phòng.

**Tương tác: Phản chiếu chậm nhịp** — bắt buộc (`selene_06_mirror_desync`).

**Lời dẫn:** Selene bước trái; phản chiếu đứng yên rồi tự tiến sát kính. Một hình trắng mờ thoáng hiện sau nó.

**Selene:** Đừng nhìn nó như tôi.

**Tương tác: Rời khỏi mặt kính** — bắt buộc (`selene_06_mirror_boundary`).

**Lời dẫn:** Selene giơ phép; gương nứt và phản chiếu tan. Những mặt còn lại vẫn cho thấy các thời điểm khác nhau.

### Chiếu nghỉ đồng hồ

Nền dự phòng hiện có: `memory_corridor`. Mã cảnh: `clock_landing`.

**Lời dẫn:** Bánh răng dừng giữa hai ngày. Những con số phải được đọc qua nửa đêm.

**Tương tác: Kiểm tra mốc đổi ngày** — bắt buộc (`selene_06_midnight`).

**Lời dẫn:** Dấu đổi ngày nằm giữa 23:52 và 00:03. Đặt 00:03 trước 23:47 sẽ biến chuỗi sự kiện thành ngày khác.

**Tương tác: Đối chiếu khoảng thời gian** — bắt buộc (`selene_06_elapsed_time`).

**Lời dẫn:** Từ 23:47 tới 00:16 là hai mươi chín phút. Mốc tách ký ức nằm trong khoảng đó, không phải lúc nghi lễ bắt đầu.

**Selene:** Mình phải giữ cả thứ tự lẫn khoảng trống giữa các mốc.

### Hành lang ký ức

Nền dự phòng hiện có: `memory_corridor`. Mã cảnh: `corridor`.

**Lời dẫn:** Hành lang ký ức giữ những mốc sau nửa đêm. Chúng có thể nối tiếp các dấu vết trong hầm.

**Selene:** Mình còn thiếu đoạn nối giữa lúc hàng rào đổ và lúc Moonfall dừng. Thử tìm các dấu mốc ở hành lang này nhé.

**Tương tác: 00:03 · Dấu tách** — bắt buộc (`selene_06_separation`).

**Lời dẫn:** Dấu hằn dưới lớp phủ ghi 00:03 — Tách ký ức. Sau nó, sức ép trong hầm giảm.

**Selene:** Có một dấu mốc bị lớp phủ che đi. Nó có thể nối khoảng trống giữa hai sự kiện mình đã tìm được.

**Tương tác: 00:16 · Moonfall dừng** — bắt buộc (`selene_06_stops`).

**Lời dẫn:** 00:16 là thời điểm Moonfall dừng, không phải lúc ký ức bị tách.

**Selene:** Mốc cuối này cần đặt cạnh các mốc khác. Nhớ là đêm ấy đã đi qua nửa đêm nhé.

### Puzzle — Ghép 29 phút

Đáp án giữ nguyên: 23:47 · Kích hoạt → 23:52 · Hàng rào đổ → 00:03 · Tách ký ức → 00:16 · Moonfall dừng.

**Selene:** Không phải tôi quên toàn bộ đêm đó. Có người đã chọn phần nào được ở lại.

### Lựa chọn

Bạn đáp thế nào trước cánh cửa Selene không muốn mở?

- Sự thật quan trọng hơn nỗi sợ.
- Nếu cô muốn dừng, mình dừng.
- Nếu muốn quên hẳn, sao cô để đường quay về?

Điểm/cờ của các lựa chọn giữ nguyên.

### M06 — `memory_video_06`

Lời đầu đi cùng phim. Các lời còn lại sau phim; giới hạn một lời dẫn và một thoại chính, phần vượt giới hạn lưu trong lịch sử.

**Lời dẫn:** Selene trẻ nói với Elarion: “Làm đi.” Ông đáp: “Cô sẽ quên tất cả.”

**Lời dẫn:** “Không phải tất cả,” cô nói. “Để lại đủ để tôi tìm được đường về.”

**Selene:** Tôi đã yêu cầu điều đó. Cả quên đi, lẫn con đường để nhớ lại. Hai việc ấy cùng là lựa chọn của tôi.

### Cuốn thư

Selene đã yêu cầu quên đi, đồng thời giữ đủ dấu vết để tìm đường về. Cả hai đều là lựa chọn của cô.

Tại sao một người muốn quên lại chuẩn bị cho ngày nhớ lại?

## Chương 7 — Vầng Trăng Nhợt

**Flow:** Đền Trăng → Ranh giới trong Đền Trăng → Bóng hình chưa hoàn chỉnh → Phòng Trăng Nhợt → puzzle → lựa chọn → ký ức → cuốn thư.

### Đền Trăng

Nền dự phòng hiện có: `moon_temple`. Mã cảnh: `temple`.

**Lời dẫn:** Bốn hõm trong Đền Trăng chờ những vật đã được mang qua hành trình. Hình dạng và dấu khắc có thể giúp đối chiếu.

**Selene:** Những vật mình giữ lại có lẽ không tình cờ cùng đến đây. Thử xem chúng hợp với các hõm thế nào nhé.

**Tương tác: Bàn thờ bốn vật** — bắt buộc (`selene_07_altar`).

**Lời dẫn:** Nguyệt thạch giữ dấu nơi chốn. Rune giữ thứ tự. Đá phong ấn giữ ranh giới. Tinh thể giữ góc nhìn.

**Selene:** Các hõm có hình dạng khác nhau. Mình thử đối chiếu chúng với những vật đã giữ lại, đừng đặt bừa nhé.

**Tương tác: Dòng khắc dưới ánh trăng** — tùy chọn (`selene_07_inscription`).

**Lời dẫn:** Qua cánh hoa và mảnh gương, câu khắc hiện rõ: NHỚ LẠI KHÔNG CÓ NGHĨA LÀ TRỞ THÀNH.

**Selene:** Dòng chữ này khó đọc dưới ánh sáng thường. Có lẽ những vật mình mang theo sẽ giúp nhìn rõ hơn.

### Ranh giới trong Đền Trăng

Nền dự phòng hiện có: `moon_temple`. Mã cảnh: `temple_boundary`.

**Lời dẫn:** Bốn rãnh từ bàn thờ nối tới các vòng không chạm nhau. Mỗi vật có một vị trí riêng.

**Tương tác: Vết trên bốn hõm** — bắt buộc (`selene_07_socket_traces`).

**Lời dẫn:** Bụi ngắt ở từng hõm; không có lối tắt qua tâm. Cơ chế từng giữ các vật tách rời.

**Tương tác: Đọc vành ngoài bàn thờ** — bắt buộc (`selene_07_boundary_warning`).

**Lời dẫn:** Dấu đóng nằm ngoài vành. Mở lối không nhất thiết là mở thứ đang được giữ bên trong.

**Selene:** Có lẽ mình mang chúng tới để giữ thứ gì đó đóng lại.

### Bóng hình chưa hoàn chỉnh

Nền dự phòng hiện có: `pale_moon_chamber`. Mã cảnh: `manifestation`.

**Lời dẫn:** Không gian trắng xanh mở ra. Các mảnh nhớ bắt đầu trôi về cùng một điểm.

**Tương tác: Các mảnh hội tụ** — bắt buộc (`selene_07_gathering_fragments`).

**Lời dẫn:** Một hình nữ trắng chưa rõ mặt tụ giữa các mảnh. Selene ôm đầu khi những cảnh đã biết chớp quanh cô.

**Tương tác: Giữ khoảng cách các mảnh** — bắt buộc (`selene_07_separate_fragments`).

**Lời dẫn:** Selene đẩy các mảnh tách ra bằng phép. Bóng hình tan khi đường sáng lại hiện giữa chúng.

**Selene:** Nó không muốn tôi nhớ. Nó muốn được hoàn chỉnh.

### Phòng Trăng Nhợt

Nền dự phòng hiện có: `pale_moon_chamber`. Mã cảnh: `pale_chamber`.

**Lời dẫn:** Trong Phòng Trăng Nhợt, các mảnh vẫn cách nhau bằng những khoảng sáng. Dấu vật dẫn có thể giải thích cách giữ chúng tách biệt.

**Selene:** Mình đừng ghép mọi thứ ngay. Tôi muốn hiểu những ranh giới này đang giữ điều gì trước đã.

**Tương tác: Dấu vật dẫn** — bắt buộc (`selene_07_vessel`).

**Lời dẫn:** Các dấu vết cho thấy Selene từng là vật dẫn. Nhận diện làm thực thể mạnh lên; nhớ hoàn chỉnh có thể dựng lại nó.

**Selene:** Dấu vật dẫn có liên quan đến điều mình đã thấy trong phòng nghi lễ. Mình đối chiếu hai nơi trước nhé.

**Tương tác: Ranh giới giữa các mảnh** — bắt buộc (`selene_07_split`).

**Lời dẫn:** Selene cố ý chia ký ức thành những mảnh chưa thể hợp nhất, giữ thực thể ở trạng thái không hoàn chỉnh.

**Selene:** Khoảng cách giữa các mảnh có vẻ được giữ rất cẩn thận. Thử tìm hiểu vì sao chúng chưa hòa vào nhau.

### Puzzle — Bốn vật, một ranh giới

Đáp án giữ nguyên: Nguyệt thạch → Đá phong ấn → Rune Trăng → Mảnh tinh thể.

**Selene:** Tôi không đánh bại nó bằng cách mạnh hơn. Tôi đã không để nó có đủ một hình hài.

### Lựa chọn

Theo bạn, quá khứ có quyền định nghĩa Selene đến đâu?

- Cô là những lựa chọn mình đang làm.
- Quá khứ vẫn là một phần của cô.
- Cả hai đều là cô, nhưng không điều nào sở hữu toàn bộ cô.

Điểm/cờ của các lựa chọn giữ nguyên.

### M07 — `memory_video_07`

Lời đầu đi cùng phim. Các lời còn lại sau phim; giới hạn một lời dẫn và một thoại chính, phần vượt giới hạn lưu trong lịch sử.

**Lời dẫn:** Selene đứng trước vòng trăng lớn với rune xanh; cảnh nhớ tiến gần đôi mắt cô.

**Lời dẫn:** Tiếng vọng Elarion cảnh báo: “Nếu nó tồn tại hoàn chỉnh bên trong cô, chúng ta sẽ không tách được hai người.” Selene trẻ đáp: “Vậy tôi sẽ không để nó tồn tại hoàn chỉnh trong tôi.” Lời ấy giải thích ranh giới giữa các mảnh, không phải thao tác tách mảnh nhìn rõ trong phim.

**Selene:** Tôi đã chia ký ức để nó không thành hình. Không phải để phủ nhận mình đã sống.

### Cuốn thư

Ký ức không chỉ giữ quá khứ: chúng còn mang Vầng Trăng Nhợt. Selene giữ các mảnh tách rời để thực thể không hoàn chỉnh.

Mảnh cuối sẽ trả lại toàn bộ Selene, hay trả lại cả hiểm nguy trong cô?

## Chương 8 — Ký ức cuối cùng

**Flow:** Không gian ký ức → Lời nhắn trong chiếc vòng → Trước ngưỡng quyết định → Căn phòng cuối → puzzle → lựa chọn → ký ức → cuốn thư.

### Không gian ký ức

Nền dự phòng hiện có: `memory_space`. Mã cảnh: `memory_space`.

**Lời dẫn:** Những ký ức đã mở trôi riêng biệt trong không gian. Kho ký ức và chiếc vòng là hai điểm để bắt đầu đối chiếu.

**Selene:** Mình đã đi xa rồi. Trước khi mở cánh cửa cuối, cùng xem lại những gì chiếc vòng và các ký ức thực sự giữ nhé.

**Tương tác: Những điều đã giữ** — bắt buộc (`selene_08_archive`).

**Lời dẫn:** Bảy ký ức đã mở nằm cách nhau bằng những đường sáng. Bạn có thể đọc lại trong Kho ký ức.

**Selene:** Mình có thể đọc lại những ký ức đã giữ trước khi quyết định. Không cần vội ghép chúng thành một câu chuyện duy nhất.

**Tương tác: Mặt dây chuyền đang ấm** — bắt buộc (`selene_08_pendant`).

**Lời dẫn:** Chiếc vòng giữ một lời hứa chưa bị xóa. Nó không ép Selene trở lại thành người trong lời hứa ấy.

**Selene:** Chiếc vòng đã đi cùng mình từ đầu. Thử nghĩ xem nó giữ điều gì mà những bản ghi không giữ được.

### Lời nhắn trong chiếc vòng

Nền dự phòng hiện có: `memory_space`. Mã cảnh: `pendant_echo`.

**Lời dẫn:** Mặt dây chuyền ấm lên; những ký ức vẫn ở ngoài Selene.

**Tương tác: Tiếng vọng chiếc vòng** — bắt buộc (`selene_08_pendant_message`).

**Lời dẫn:** Bóng cô gái hiện rồi tan, để lại lời: “Nếu còn nhớ được một điều, hãy nhớ vì sao mình đã chọn.”

**Tương tác: Đặt vòng cạnh bản ghi** — bắt buộc (`selene_08_present_promise`).

**Lời dẫn:** Lời hứa, bản ghi và góc nhìn đều còn. Không thứ nào tự có quyền chọn Selene phải trở thành ai.

**Selene:** Tôi muốn hiểu giá của từng lựa chọn trước khi chạm vào chúng.

### Trước ngưỡng quyết định

Nền dự phòng hiện có: `pale_moon_chamber`. Mã cảnh: `decision_threshold`.

**Lời dẫn:** Ba cơ chế còn im. Có thể đọc từng cái trước khi dựng khung ký ức.

**Tương tác: Đọc cơ chế khôi phục** — bắt buộc (`selene_08_restore_cost`).

**Lời dẫn:** RESTORE trả mảnh cuối về Selene. Những mảnh đã tách có thể hợp nhất; hiểm nguy trong chúng cũng có thể trở lại đầy đủ.

**Tương tác: Đọc cơ chế phá hủy** — bắt buộc (`selene_08_destroy_cost`).

**Lời dẫn:** DESTROY làm mất vĩnh viễn mảnh cuối. Nó chặn sự hoàn chỉnh, đồng thời đóng một phần đời Selene.

**Tương tác: Đọc cơ chế chuyển giao** — bắt buộc (`selene_08_transfer_cost`).

**Lời dẫn:** TRANSFER đổi người mang phong ấn. Gánh nặng không biến mất khi rời Selene.

### Căn phòng cuối

Nền dự phòng hiện có: `pale_moon_chamber`. Mã cảnh: `final_chamber`.

**Lời dẫn:** Căn phòng cuối có ba cơ chế và những đường sáng ngăn các mảnh. Có thể xem xét chúng trước khi đưa ra quyết định.

**Selene:** Tôi muốn mình hiểu rõ từng lựa chọn. Mình xem cơ chế và đường sáng trước, rồi mới quyết định điều gì sẽ xảy ra nhé.

**Tương tác: Ba cơ chế** — bắt buộc (`selene_08_mechanisms`).

**Lời dẫn:** Khôi phục trả mảnh cuối về Selene; phá hủy làm nó không thể hoàn chỉnh; chuyển giao đổi người mang phong ấn.

**Selene:** Ba cơ chế làm những việc khác nhau. Mình cần đọc kỹ tác dụng của từng cái trước khi chạm vào.

**Tương tác: Đường sáng ngăn các mảnh** — bắt buộc (`selene_08_boundary`).

**Lời dẫn:** Những đường sáng đang giữ ký ức có thể được nhìn mà không hòa vào nhau. Không có gì tự động quyết định thay bạn.

**Selene:** Đường sáng đang ngăn các mảnh chạm nhau. Có lẽ hiểu ranh giới này cũng quan trọng như hiểu từng mảnh.

### Puzzle — Dựng khung cho ký ức

Đáp án giữ nguyên: Mặt dây chuyền → Nhật ký → Mảnh tinh thể.

**Selene:** Mình đã đến đây. Nhưng đến cuối đường không có nghĩa là chỉ được chọn điều dễ gọi tên nhất.

### Lựa chọn

Bạn muốn làm gì với ký ức cuối?

- Khôi phục ký ức
- Phá hủy ký ức
- Nhận phong ấn

Điểm/cờ của các lựa chọn giữ nguyên.

### M08 — `memory_video_08`

Chỉ nhánh ẩn phát M08. Ba kết thường không phát video mái nhà. Lời đầu dưới đây đi cùng phim; lời còn lại sau phim, một lời dẫn và một thoại Selene chính.

**Lời dẫn:** Trên mái nhà Moonbrook, cô gái hỏi: “Nếu một ngày em không nhớ mình từng là ai… em nghĩ mình sẽ trở thành người thế nào?”

**Lời dẫn:** Selene trẻ mỉm cười: “Em nghĩ… em sẽ tự quyết định.” Trở lại hiện tại, ký ức vẫn tách rời, có thể nhìn lại mà không hòa vào cô. Vầng Trăng Nhợt vẫn không hoàn chỉnh.

**Selene:** Tôi cứ nghĩ phải chọn giữa nhớ và quên. Có lẽ tôi có thể sống cùng điều đã nhớ mà vẫn tự chọn người mình trở thành. Anh vẫn đi cùng tôi chứ?

## Bốn kết thúc

Giữ ba kết thường và một kết ẩn, cùng điều kiện hiện tại. Chưa thêm ngưỡng Trust hoặc điều kiện Secret Door mới vì yêu cầu giữ logic khác. Đề xuất cửa bí mật trong tài liệu ending chưa được biến thành một điều kiện khóa mới.

### Hãy nhớ tôi

**Lời dẫn/cuốn thư:** Mảnh cuối trở về. Vầng Trăng Nhợt mở mắt trong ký ức của Selene. Sự thật đã đầy đủ; hiểm nguy cũng vậy.

**Selene:** Tôi nhớ rồi. Tôi nhớ tất cả. Anh đã giúp tôi tìm lại người mình từng là. Giờ hãy giúp tôi bảo đảm cô ấy không hủy hoại thế giới này.

### Hãy để tôi quên

**Lời dẫn/cuốn thư:** Mảnh cuối tan đi. Vầng Trăng Nhợt không bao giờ có thể hoàn chỉnh. Một phần đời Selene cũng rời khỏi tầm với.

**Selene:** Vậy là hết. Tôi không biết mình đã mất gì. Có lẽ vì thế nên mới đau. Nhưng tôi biết mình vẫn còn ai bên cạnh.

### Người giữ phong ấn mới

**Lời dẫn/cuốn thư:** Phong ấn rời Selene. Trong câu chuyện này, bạn nhận lấy vai trò người giữ nó; Selene lần đầu cảm thấy đôi tay mình nhẹ đi.

**Selene:** Đừng quên giọng tôi. Nếu một ngày anh không còn nhớ mình là ai… tôi sẽ nhớ thay anh.

### Giữa ký ức và ánh trăng

**Lời dẫn/cuốn thư:** Không khôi phục, không phá hủy, không chuyển giao. Ký ức ở lại trong không gian riêng, có thể được thăm lại mà không hòa vào Selene. Vầng Trăng Nhợt vẫn không hoàn chỉnh.

**Selene:** Tôi hiểu rồi. Tôi cứ nghĩ chỉ có hai lựa chọn: nhớ lại, hoặc quên đi. Nhưng một ký ức không cần sở hữu người mang nó.

## Bốn lỗi media đã xử lý

- M01: hành lang dưới ánh trăng, bỏ mô tả đầy nắng.
- M04 mới: Selene trẻ gặp người đàn ông lớn tuổi trong hành lang học viện; lời mở đầu khớp cuộc gặp trong hình.
- M07: mô tả vòng trăng/rune đúng hình; lời giải thích về chia ký ức đặt sau phim.
- M08: ký ức mái nhà trước kết ẩn; câu hỏi trên mái nhà đi cùng phim, lời đáp và kết quả sau phim; câu “Anh vẫn đi cùng tôi chứ?” nằm trong thoại chính.



## Thứ tự thoại–clip đã rà soát (19/10/2026)

Thứ tự phát mới nhất của cả 8 chương, gồm câu trước/sau từng clip và bản sửa kẹt 99% khi mở cổng: [DIALOGUE_CLIP_SEQUENCE_REVIEW.md](DIALOGUE_CLIP_SEQUENCE_REVIEW.md). Lời phản ứng được giấu và chờ clip kết thúc, không cần bấm thêm để nghe câu sau cảnh bẫy tên.

## Bộ hình và video thay thế (18/10/2026)

Đã gắn 18 nền WebP, M01–M08, 7 video sự kiện, mở cổng và bốn clip kết. Có ánh sáng gợi ý vùng bấm. M04 mới hiện cuộc gặp trong hành lang. Chi tiết: [NARRATIVE_MEDIA_PENDING.md](NARRATIVE_MEDIA_PENDING.md).
