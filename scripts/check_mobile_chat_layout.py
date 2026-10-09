# Verify the real stylesheet at phone sizes without production API calls.
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def css(path):
    text=path.read_text(encoding="utf-8")
    return re.sub(r'@import\s+"([^"]+)";',lambda m:css((ROOT/"frontend/node_modules"/m[1]) if m[1].startswith("@") else path.parent/m[1]),text)
styles=css(ROOT/"frontend/src/app-styles.css")
markup='''<div class="shell chatShell"><main><div class="chatWorkspace">
<div class="chat"><header class="chatEmotionHeader singleCharacter"><div class="emotionPortraitWrap"></div><h1>Ruby</h1><p>Character conversation</p></header><div class="messages"><div class="bubble">Hello</div></div><div class="composer"><div class="composerBox"><textarea></textarea></div></div></div>
<aside class="characterTools"><button class="collapseTools">Close</button><div class="toolProfile"><div class="toolProfileArtwork"></div><div><strong>Ruby</strong><small>A friendly character introduction that must remain visible without feelings overlapping it.</small><span>3 users</span></div></div><div class="characterFeelings">'''+''.join('<div class="characterFeeling"><span>🥰</span><span class="feelingName">'+name+'</span><strong>20%</strong><span class="feelingTrack"></span></div>' for name in ["Familiarity","Trust","Affection","Conflict","Thinking"])+'''</div><div class="toolReactions"><button>❤️</button><button>🔥</button></div><div class="toolMenu"><button>Memories</button><button>Character information</button><div class="rpCharacterMusicControl"><div class="rpMusicControl"><div class="rpMusicControlRow"><button class="rpMusicMute">♪</button><button class="rpBackgroundMusicButton"><span>Music volume</span><span>30%</span></button></div><div class="rpMusicVolumePanel"><input aria-label="Music volume" type="range" min="0" max="100" value="30" oninput="document.querySelector('output').textContent=this.value+'%'"><output>30%</output></div></div></div><button>Reaction sounds</button></div></aside></div></main></div>'''
def run():
    output=ROOT/".diagnostics";output.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel="msedge",headless=True)
        for width,height in [(390,844),(375,667),(320,568)]:
            page=browser.new_page(viewport={"width":width,"height":height},has_touch=True,is_mobile=True)
            page.route("**/*", lambda route:route.abort())
            page.set_content('<meta name="viewport" content="width=device-width,initial-scale=1"><style>'+styles+'</style>'+markup)
            profile=page.locator(".toolProfile").bounding_box();feelings=page.locator(".characterFeelings").bounding_box()
            assert profile["y"]+profile["height"]<=feelings["y"],(profile,feelings)
            slider=page.get_by_label("Music volume");slider.scroll_into_view_if_needed();assert slider.is_visible()
            box=slider.bounding_box();assert box["width"]>100,box
            page.touchscreen.tap(box["x"]+box["width"]*.8,box["y"]+box["height"]/2)
            session=page.context.new_cdp_session(page)
            y=box["y"]+box["height"]/2
            start=box["x"]+box["width"]*.8
            session.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":start,"y":y}]})
            session.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":box["x"]+box["width"]*.2,"y":y}]})
            session.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]})
            assert int(slider.input_value())<40,slider.input_value()
            page.touchscreen.tap(box["x"]+box["width"]*.8,y)
            assert int(slider.input_value())>60,slider.input_value()
            assert page.locator("output").inner_text()!= "30%"
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output/f"chat-mobile-{width}.png"))
            print(f"PASS {width}x{height}: profile/feelings separate, slider interactive, no horizontal overflow")
            page.close()
        browser.close()
if __name__=="__main__":run()
