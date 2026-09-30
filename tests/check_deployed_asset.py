import re, requests
base="https://nguyenthanhcongloi332004--character-chat-web.modal.run"
index=requests.get(base+"/?cache_bust=20260923-latest",headers={"Cache-Control":"no-cache"},timeout=300)
asset=re.search(r'src="([^"]+\.js)"',index.text).group(1)
javascript=requests.get(base+asset,timeout=120)
print("index",index.status_code,index.headers.get("cache-control"))
print("asset",asset,javascript.status_code,javascript.headers.get("cache-control"),len(javascript.content))
print("old-label", "Đang trả lời" in javascript.text)
print("new-typing", "typingBubble" in javascript.text)
print("forced-paint", "requestAnimationFrame" in javascript.text)
print("health",requests.get(base+"/health?cache_bust=latest",headers={"Cache-Control":"no-cache"},timeout=300).json())
