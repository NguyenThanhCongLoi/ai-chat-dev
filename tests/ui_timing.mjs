import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const base=process.env.UI_TIMING_BASE_URL?.replace(/\/$/,'');
const username=process.env.UI_TIMING_USERNAME;
const password=process.env.UI_TIMING_PASSWORD;
const roomId=process.env.UI_TIMING_ROOM_ID;
if(!base || !username || !password || !roomId){
  throw new Error('Set UI_TIMING_BASE_URL, UI_TIMING_USERNAME, UI_TIMING_PASSWORD and UI_TIMING_ROOM_ID.');
}
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const login=await fetch(`${base}/v1/auth/login`,{
  method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({username,password}),
});
if(!login.ok)throw new Error(`Login failed: HTTP ${login.status}`);
const {token}=await login.json();
const browser=await chromium.launch({headless:true});
try{
  const page=await browser.newPage();
  await page.addInitScript(value=>localStorage.setItem('auth_token',value),token);
  await page.goto(`${base}/role-play-ai?workspace=1&view=chat&room=${encodeURIComponent(roomId)}`,{waitUntil:'domcontentloaded'});
  const input=page.locator('.composer textarea');
  await input.waitFor({state:'visible'});
  const message=`UI timing ${Date.now()}`;
  await input.fill(message);
  const started=Date.now();
  await page.locator('.composer button').last().click();
  await page.getByText(message,{exact:true}).waitFor({state:'visible',timeout:3000});
  const userVisibleMs=Date.now()-started;
  await page.locator('.typingDots').waitFor({state:'visible',timeout:3000});
  const typingVisibleMs=Date.now()-started;
  console.log(JSON.stringify({userVisibleMs,typingVisibleMs}));
}finally{await browser.close();}
