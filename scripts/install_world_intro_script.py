"""Install the authored 93.7s intro in the default content and local CMS.

Run without --apply-cms to update source only. Never changes providers or voices.
"""
import argparse
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]
ROWS=[
('intro_door',0,7.5,
'Có những cánh cửa không dẫn đến một nơi... mà dẫn đến cả một thế giới.',
'Some doors do not lead to a place… but to an entire world.',
'有些门通往的不是一个地方……而是一整个世界。',
'ある扉の先にあるのは、ひとつの場所ではなく……ひとつの世界。',
'어떤 문은 한 장소가 아니라… 하나의 세계로 이어집니다.',
'တချို့တံခါးတွေက နေရာတစ်ခုဆီ မဟုတ်ဘဲ… ကမ္ဘာတစ်ခုလုံးဆီ ပို့ဆောင်ပေးတယ်။',
'ទ្វារខ្លះមិននាំទៅកាន់ទីកន្លែងមួយទេ… តែនាំទៅកាន់ពិភពលោកទាំងមូល។'),
('intro_journey',23.5,32,
'Bước qua cánh cửa ấy, bạn trở thành một phần trong hành trình của họ. Những nhân vật có câu chuyện, ký ức và bí mật riêng.',
'Step through, and you become part of their journey. Each character has a story, memories, and secrets of their own.',
'跨过那扇门，你便成为他们旅程的一部分。每个角色都有自己的故事、记忆与秘密。',
'扉を越えれば、あなたも彼らの旅の一部に。誰もが自分だけの物語と記憶、秘密を持っています。',
'그 문을 넘으면 당신도 그들의 여정에 함께합니다. 저마다 이야기와 기억, 비밀을 간직한 인물들이죠.',
'တံခါးကို ဖြတ်လိုက်တာနဲ့ သူတို့ခရီးရဲ့ အစိတ်အပိုင်း ဖြစ်လာမယ်။ ဇာတ်ကောင်တိုင်းမှာ ကိုယ်ပိုင်ဇာတ်လမ်း၊ အမှတ်တရနဲ့ လျှို့ဝှက်ချက်တွေ ရှိတယ်။',
'ពេលឆ្លងទ្វារនោះ អ្នកក្លាយជាផ្នែកមួយនៃដំណើររបស់ពួកគេ។ តួអង្គម្នាក់ៗមានរឿងរ៉ាវ ការចងចាំ និងអាថ៌កំបាំងរៀងខ្លួន។'),
('intro_memories',32,39.5,
'Qua những vùng đất bị lãng quên, theo dấu ký ức còn sót lại... cùng họ tìm những điều ngay cả chính họ cũng chưa thể nhớ ra.',
'Cross forgotten lands, follow the traces of memory… and uncover what even they cannot yet remember.',
'走过被遗忘的土地，追寻记忆留下的痕迹……和他们一起找回连自己都想不起的往事。',
'忘れられた土地を歩き、残された記憶をたどる……彼ら自身も思い出せないものを、一緒に探して。',
'잊힌 땅을 지나 남겨진 기억을 따라가며… 그들조차 떠올리지 못하는 이야기를 함께 찾아보세요.',
'မေ့လျော့ခံမြေတွေကို ဖြတ်သန်းပြီး ကျန်ရစ်တဲ့အမှတ်တရနောက် လိုက်ရင်း… သူတို့ကိုယ်တိုင် မမှတ်မိနိုင်သေးတာတွေကို အတူရှာဖွေပါ။',
'ឆ្លងកាត់ដែនដីដែលគេភ្លេច តាមដានស្នាមនៃការចងចាំ… ហើយស្វែងរកអ្វីដែលសូម្បីពួកគេផ្ទាល់ក៏មិនទាន់ចាំបាន។'),
('intro_everyday',39.5,47.5,
'Nhưng không phải thế giới nào cũng có phép thuật. Đôi khi, câu chuyện bắt đầu giữa thành phố không ngủ... hay trong một văn phòng trên cao.',
'But not every world holds magic. Sometimes a story begins in a sleepless city… or an office high above it.',
'但并非每个世界都有魔法。有时，故事始于不眠的城市……或高楼中的一间办公室。',
'けれど、すべての世界に魔法があるわけではありません。眠らない街で……高層階のオフィスで、始まる物語も。',
'모든 세계에 마법이 있는 건 아닙니다. 잠들지 않는 도시에서… 높은 빌딩의 사무실에서 이야기가 시작되기도 하죠.',
'ကမ္ဘာတိုင်းမှာ မှော်ပညာရှိတာတော့ မဟုတ်ဘူး။ တစ်ခါတလေ ဇာတ်လမ်းဟာ မအိပ်တဲ့မြို့ထဲ… ဒါမှမဟုတ် အမြင့်ထပ်ရုံးခန်းမှာ စတင်တတ်တယ်။',
'ប៉ុន្តែមិនមែនគ្រប់ពិភពលោកសុទ្ធតែមានមន្តអាគមទេ។ ពេលខ្លះ រឿងចាប់ផ្តើមក្នុងទីក្រុងមិនដេក… ឬការិយាល័យលើអគារខ្ពស់។'),
('intro_encounter',47.5,54,
'Hay chỉ từ một lần tình cờ gặp nhau ở hành lang trường học. Mỗi nhân vật... lại mở ra một hành trình mới.',
'Or simply a chance encounter in a school corridor. Each character… opens a new journey.',
'也可能只是学校走廊里的一次偶遇。每个角色……都开启一段新的旅程。',
'学校の廊下で、ふと出会ったことから。ひとりの登場人物が……新たな旅の扉を開きます。',
'학교 복도에서 우연히 마주친 순간일 수도 있습니다. 인물 한 사람마다… 새로운 여정이 열립니다.',
'ဒါမှမဟုတ် ကျောင်းစင်္ကြံမှာ မထင်မှတ်ဘဲ ဆုံမိရာကနေ။ ဇာတ်ကောင်တစ်ယောက်စီက… ခရီးအသစ်တစ်ခုကို ဖွင့်ပေးတယ်။',
'ឬគ្រាន់តែជាការជួបគ្នាដោយចៃដន្យនៅច្រកសាលារៀន។ តួអង្គម្នាក់ៗ… បើកដំណើរថ្មីមួយ។'),
('intro_connections',54,63,
'Phiêu lưu. Bí ẩn. Tình bạn. Tình cảm. Một bí mật trong ký ức, hay một người đang đợi cuối đường... mỗi cuộc gặp đều có thể đổi hướng câu chuyện.',
'Adventure. Mystery. Friendship. Romance. A secret within a memory, or someone waiting ahead… every encounter can change the story’s direction.',
'冒险。悬疑。友情。爱情。记忆中的秘密，或路尽头等待的人……每次相遇都可能改变故事的方向。',
'冒険。謎。友情。恋。記憶に隠された秘密、道の先で待つ誰か……出会いのたびに、物語の行方は変わります。',
'모험. 미스터리. 우정. 사랑. 기억 속 비밀, 길 끝에서 기다리는 누군가… 만남마다 이야기의 방향은 달라질 수 있습니다.',
'စွန့်စားခန်း။ လျှို့ဝှက်ဆန်းကြယ်မှု။ ခင်မင်မှု။ အချစ်။ အမှတ်တရထဲက လျှို့ဝှက်ချက်ဖြစ်ဖြစ်၊ လမ်းဆုံးမှာစောင့်နေသူဖြစ်ဖြစ်… တွေ့ဆုံမှုတိုင်းက ဇာတ်လမ်းကို ပြောင်းစေနိုင်တယ်။',
'ដំណើរផ្សងព្រេង។ អាថ៌កំបាំង។ មិត្តភាព។ ស្នេហា។ អាថ៌កំបាំងក្នុងការចងចាំ ឬមនុស្សនៅចុងផ្លូវ… រាល់ការជួបគ្នាអាចប្តូរទិសរឿងបាន។'),
('intro_characters',63,70.5,
'Ở đây, nhân vật không chỉ tồn tại để trò chuyện. Họ có quá khứ, có điều muốn tìm lại... và những lựa chọn cần bạn cùng đưa ra.',
'Here, characters exist for more than conversation. They have a past, things to recover… and choices to make together with you.',
'在这里，角色不只是陪你聊天。他们有过去，有想找回的东西……也有需要与你一起做出的选择。',
'ここで彼らは、話し相手だけではありません。過去があり、取り戻したいものがあり……あなたと共に選びたい未来があります。',
'이곳의 인물들은 대화만을 위해 존재하지 않습니다. 과거가 있고, 되찾고 싶은 것이 있고… 당신과 함께 내려야 할 선택이 있습니다.',
'ဒီမှာ ဇာတ်ကောင်တွေဟာ စကားပြောဖို့သက်သက် ရှိနေတာမဟုတ်ဘူး။ သူတို့မှာ အတိတ်၊ ပြန်ရှာချင်တာတွေ… သင်နဲ့အတူ ဆုံးဖြတ်ရမယ့်ရွေးချယ်မှုတွေ ရှိတယ်။',
'នៅទីនេះ តួអង្គមិនមែនមានសម្រាប់តែជជែកទេ។ ពួកគេមានអតីតកាល មានអ្វីចង់រកមកវិញ… និងជម្រើសដែលត្រូវការអ្នកចូលរួម។'),
('intro_choices',70.5,77.5,
'Bạn không chỉ là người xem. Bạn cùng họ viết tiếp câu chuyện. Đôi khi... chỉ một lựa chọn cũng thay đổi cách nó kết thúc.',
'You are more than a spectator. You write the story with them. Sometimes… one choice can change how it ends.',
'你不只是旁观者。你与他们一起续写故事。有时……一个选择就能改变结局。',
'あなたは、ただの観客ではありません。共に物語の続きを紡ぐ人。たったひとつの選択が……結末を変えることも。',
'당신은 그저 관객이 아닙니다. 그들과 함께 이야기를 이어 갑니다. 때로는… 단 하나의 선택이 결말을 바꿉니다.',
'သင်ဟာ ကြည့်ရှုသူသက်သက် မဟုတ်ဘူး။ သူတို့နဲ့အတူ ဇာတ်လမ်းကို ဆက်ရေးသူပါ။ တစ်ခါတလေ… ရွေးချယ်မှုတစ်ခုကပဲ အဆုံးသတ်ကို ပြောင်းနိုင်တယ်။',
'អ្នកមិនមែនគ្រាន់តែជាអ្នកមើលទេ។ អ្នករួមសរសេររឿងបន្តជាមួយពួកគេ។ ពេលខ្លះ… ជម្រើសតែមួយក៏អាចប្តូរចុងបញ្ចប់បាន។'),
('intro_return',83.5,87.3,
'Rời thế giới ấy, câu chuyện vẫn ở lại cùng bạn.',
'You may leave that world. Its story stays with you.',
'即使离开那个世界，故事依然与你同在。',
'その世界を離れても、物語はあなたと共に。',
'그 세계를 떠나도, 이야기는 당신 곁에 남습니다.',
'အဲဒီကမ္ဘာကနေ ထွက်လာလည်း ဇာတ်လမ်းက သင်နဲ့အတူ ကျန်နေမယ်။',
'ទោះចាកចេញពីពិភពនោះ រឿងរ៉ាវនៅតែស្ថិតជាមួយអ្នក។'),
('intro_welcome',89.8,93.6,
'Chào mừng đến với World Mode. Nơi mỗi nhân vật... mở ra một thế giới.',
'Welcome to World Mode. Every character… opens a world.',
'欢迎来到 World Mode。每个角色……都开启一个世界。',
'World Modeへようこそ。ひとりひとりが……世界への扉に。',
'World Mode에 오신 걸 환영합니다. 인물 한 사람마다… 하나의 세계가 열립니다.',
'World Mode မှ ကြိုဆိုပါတယ်။ ဇာတ်ကောင်တစ်ယောက်စီက… ကမ္ဘာတစ်ခုကို ဖွင့်ပေးတယ်။',
'សូមស្វាគមន៍មកកាន់ World Mode។ តួអង្គម្នាក់ៗ… បើកពិភពលោកមួយ។')]

def authored():
    langs=('vi','en','zh','ja','ko','my','km')
    return dict(revision=0,enabled=True,music_gain=.45,duck_gain=.14,voice_gain=1,
      duration_seconds=93.708,
      silent_windows=[
        dict(id='screen_pull',start=7.5,end=18.5,label='Hai người bị hút qua màn hình'),
        dict(id='first_fantasy',start=18.5,end=23.5,label='Fantasy world đầu tiên mở ra'),
        dict(id='montage_peak',start=77.5,end=83.5,label='Đỉnh nhạc montage nhiều thế giới'),
        dict(id='before_welcome',start=87.3,end=89.8,label='Nghỉ 2,5 giây trước lời chào World Mode')],
      cues=[dict(id=r[0],start=r[1],end=r[2],text=dict(zip(langs,r[3:]))) for r in ROWS])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-cms',action='store_true')
    parser.add_argument('--data-dir',type=Path,default=ROOT/'data')
    args=parser.parse_args()
    from character_chat.api.hub_narration import validate
    value=validate(authored())
    (ROOT/'character_chat/story_data/world_hub_narration.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if args.apply_cms:
        path=args.data_dir/'character_chat.sqlite'
        if not path.is_file():raise SystemExit('CMS database not found; no database created')
        with sqlite3.connect(path) as db:
            old=db.execute('select value from app_settings where key=?',('world_hub_narration',)).fetchone()
            if old:
                previous=json.loads(old[0]);value['revision']=previous.get('revision',0)+1
                db.execute('insert or replace into app_settings(key,value,updated_at) values(?,?,datetime(\'now\'))',('world_hub_narration_backup_'+str(value['revision']),old[0]))
            db.execute('insert or replace into app_settings(key,value,updated_at) values(?,?,datetime(\'now\'))',('world_hub_narration',json.dumps(value,ensure_ascii=False)))
    print(json.dumps(dict(cues=len(value['cues']),silences=len(value['silent_windows']),duration=value['duration_seconds'],cms_updated=args.apply_cms,audio_generated=False)))

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT))
    main()
