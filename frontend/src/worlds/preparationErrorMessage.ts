const messages:Record<string,Record<string,string>>={
  "audio_unprepared": {
    "vi": "Một số lời thoại chưa có giọng đọc sẵn. Hãy chuẩn bị giọng đọc chương trong CMS, rồi thử lại.",
    "en": "Some dialogue audio has not been prepared yet. Prepare the chapter voices in CMS, then retry.",
    "ja": "まだ音声が用意されていないセリフがあります。CMSでこの章の音声を準備してから、もう一度お試しください。",
    "zh": "部分台词还没有准备好配音。请先在 CMS 中生成本章语音，再重试。",
    "ko": "아직 음성이 준비되지 않은 대사가 있어요. CMS에서 이 장의 음성을 준비한 뒤 다시 시도해 주세요.",
    "my": "တချို့စကားပြောခန်းတွေအတွက် အသံ မပြင်ဆင်ရသေးပါဘူး။ CMS မှာ ဒီအခန်းရဲ့အသံတွေကို ပြင်ဆင်ပြီး ပြန်စမ်းကြည့်ပါ။",
    "km": "សំឡេងសម្រាប់សន្ទនាខ្លះមិនទាន់បានរៀបចំទេ។ សូមរៀបចំសំឡេងជំពូកក្នុង CMS រួចព្យាយាមម្តងទៀត។"
  },
  "audio": {
    "vi": "Chưa tải được giọng đọc. Vui lòng kiểm tra kết nối rồi thử lại.",
    "en": "Voice audio could not be loaded. Check your connection and retry.",
    "ja": "音声を読み込めませんでした。接続を確認して、もう一度お試しください。",
    "zh": "语音加载失败，请检查网络后重试。",
    "ko": "음성을 불러오지 못했어요. 연결을 확인하고 다시 시도해 주세요.",
    "my": "အသံကို မဖွင့်နိုင်သေးပါဘူး။ အင်တာနက်ချိတ်ဆက်မှုကို စစ်ပြီး ပြန်စမ်းကြည့်ပါ။",
    "km": "មិនអាចទាញយកសំឡេងបានទេ។ សូមពិនិត្យការតភ្ជាប់ ហើយព្យាយាមម្តងទៀត។"
  },
  "media": {
    "vi": "Một số ảnh hoặc video chưa tải được. Vui lòng thử lại; những phần đã tải sẽ được giữ lại.",
    "en": "Some images or videos could not be loaded. Retry to finish loading; prepared files will be reused.",
    "ja": "一部の画像や動画を読み込めませんでした。再試行すると、読み込み済みのデータはそのまま使われます。",
    "zh": "部分图片或视频未能加载。请重试，已加载的内容会保留。",
    "ko": "일부 이미지나 영상을 불러오지 못했어요. 다시 시도하면 이미 준비된 파일은 그대로 사용해요.",
    "my": "ပုံနဲ့ဗီဒီယိုတချို့ကို မတင်နိုင်သေးပါဘူး။ ပြန်စမ်းကြည့်ပါ။ တင်ပြီးသားဖိုင်တွေကို ဆက်သုံးမှာပါ။",
    "km": "រូបភាព ឬវីដេអូខ្លះមិនទាន់ទាញយកបានទេ។ សូមព្យាយាមម្តងទៀត។ ឯកសារដែលទាញយករួចនឹងត្រូវបានរក្សាទុក។"
  }
};
export function preparationErrorMessage(kind:string,language:string){const group=messages[kind]||messages.media;return group[language]||group.en;}
