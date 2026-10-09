const waiting:Record<string,string>={
 vi:"Chờ chút nhé, mình đang chuẩn bị đây!",
 en:"Hang tight, we're getting things ready!",
 zh:"正在准备中，稍等一下哦！",
 ja:"ただいま準備しています。少しお待ちくださいね。",
 ko:"준비하고 있어요. 잠시만 기다려 주세요!",
 my:"ပြင်ဆင်နေပါတယ်။ ခဏလေး စောင့်ပေးပါနော်။",
 km:"យើងកំពុងរៀបចំ។ សូមរង់ចាំបន្តិចណា!",
};
const languageLoading:Record<string,string>={
 vi:"Mình đang chuẩn bị ngôn ngữ bạn chọn. Cảm ơn bạn đã chờ nhé!",
 en:"We're getting your chosen language ready. Thanks for waiting!",
 zh:"正在准备你选择的语言，谢谢耐心等待！",
 ja:"選んだ言語を準備しています。お待ちいただきありがとうございます。",
 ko:"선택하신 언어를 준비하고 있어요. 기다려 주셔서 감사해요!",
 my:"သင်ရွေးထားတဲ့ ဘာသာစကားကို ပြင်ဆင်နေပါတယ်။ စောင့်ပေးလို့ ကျေးဇူးတင်ပါတယ်။",
 km:"យើងកំពុងរៀបចំភាសាដែលអ្នកបានជ្រើសរើស។ អរគុណដែលរង់ចាំ!",
};
export function friendlyWaitingText(language:string) {return waiting[language]||waiting.en;}
export function friendlyLanguageLoadingText(language:string) {return languageLoading[language]||languageLoading.en;}
