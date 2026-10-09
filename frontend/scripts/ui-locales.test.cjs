const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
const { spawn } = require("node:child_process");
const frontend = path.resolve(__dirname, "..");
const script = fs.readFileSync(path.join(__dirname, "ui-locales.cjs"), "utf8");

function fixture() {
  const project = fs.mkdtempSync(path.join(os.tmpdir(), "avibi-ui-locales-"));
  const root = path.join(project,"frontend");
  fs.mkdirSync(path.join(project,"docs"));
  fs.copyFileSync(path.join(frontend,"../docs/UI_LOCALIZATION_STYLE.md"),path.join(project,"docs/UI_LOCALIZATION_STYLE.md"));
  for (const folder of ["scripts", "src/assistant", "src/roleplay", "src/locales"])
    fs.mkdirSync(path.join(root, folder), { recursive: true });
  fs.writeFileSync(path.join(root, "scripts/ui-locales.cjs"), script);
  fs.copyFileSync(path.join(__dirname,"ui-locale-rewrite.cjs"),path.join(root,"scripts/ui-locale-rewrite.cjs"));
  fs.copyFileSync(path.join(frontend, "src/uiTranslationValidation.ts"), path.join(root, "src/uiTranslationValidation.ts"));
  fs.writeFileSync(path.join(root, "src/i18n.ts"),
    'const UI_LANGUAGES=[{label:"Français"}]; const EN={"Xin chào":"Hello"};');
  fs.writeFileSync(path.join(root, "src/assistant/config.ts"), "");
  fs.writeFileSync(path.join(root, "src/EmojiPicker.tsx"), "");
  fs.writeFileSync(path.join(root, "src/roleplay/Card.tsx"),
    'export const Card=()=> <p>Đang tải…</p>;');
  return root;
}
function cleanup(root) {
  const project = path.dirname(root);
  assert.equal(path.dirname(path.resolve(project)), path.resolve(os.tmpdir()));
  assert.ok(path.basename(project).startsWith("avibi-ui-locales-"));
  fs.rmSync(project, {recursive:true,force:true});
}
function run(root, args, base) {
  return new Promise(resolve => {
    const child=spawn(process.execPath, [path.join(root,"scripts/ui-locales.cjs"), ...args], {
      env:{...process.env, NODE_PATH:path.join(frontend,"node_modules"),
        UI_I18N_API_KEY:"test-key-not-a-secret", UI_I18N_API_BASE:base}
    });
    let output="";
    child.stdout.on("data",value=>output+=value);
    child.stderr.on("data",value=>output+=value);
    child.on("exit",code=>resolve({code,output}));
  });
}
async function gateway(handler) {
  const server=http.createServer(async(req,res)=>{
    let body="";
    for await(const part of req) body+=part;
    handler(JSON.parse(body),res);
  });
  await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
  return {server,base:"http://127.0.0.1:"+server.address().port+"/v1"};
}
test("saved UI translations are reused; edits translate only new text",async()=>{
  const root=fixture(), calls=[];
  const {server,base}=await gateway((body,res)=>{
    const input=JSON.parse(body.messages[1].content);
    calls.push(input);
    const rows=input.map(item=>{
      const row={source:item.source};
      for(const code of item.languages) row[code]=({en:"EN",zh:"中文",ja:"日本語",ko:"한국어",my:"မြန်မာ",km:"ភាសាខ្មែរ"})[code]+" "+item.source;
      return row;
    });
    res.setHeader("Content-Type","application/json");
    res.end(JSON.stringify({choices:[{message:{content:JSON.stringify(rows)}}]}));
  });
  try {
    assert.equal((await run(root,["--update"],base)).code,0);
    assert.ok(calls.length);
    const initial=calls.length;
    assert.equal((await run(root,["--update"],base)).code,0);
    assert.equal(calls.length,initial);
    const catalog=JSON.parse(fs.readFileSync(path.join(root,"src/locales/catalog.json"),"utf8"));
    assert.ok(!catalog.some(item=>item.source==="Français"));
    fs.writeFileSync(path.join(root,"src/roleplay/Card.tsx"),'export const Card=()=> <p>Câu mới</p>;');
    assert.equal((await run(root,["--update"],base)).code,0);
    assert.equal(calls.length,initial+1);
    assert.deepEqual(calls.at(-1).map(item=>item.source),["Câu mới"]);
    assert.equal((await run(root,["--check"],base)).code,0);
    const en=JSON.parse(fs.readFileSync(path.join(root,"src/locales/en.json"),"utf8"));
    assert.equal(en["Xin chào"],"Hello");
  } finally {server.close();cleanup(root);}
});
test("authentication errors stop after one request and never expose key",async()=>{
  const root=fixture();let calls=0;
  const {server,base}=await gateway((_body,res)=>{
    calls++;res.statusCode=401;res.end("private gateway response");
  });
  try {
    const result=await run(root,["--update"],base);
    assert.equal(result.code,1);
    assert.equal(calls,1);
    assert.match(result.output,/HTTP 401/);
    assert.ok(!result.output.includes("test-key-not-a-secret"));
    assert.ok(!result.output.includes("private gateway response"));
    assert.equal((await run(root,["--check"],base)).code,1);
  } finally {server.close();cleanup(root);}
});

test("retry only the failed Chinese field; keep other language translations",async()=>{
  const root=fixture(),calls=[];
  const {server,base}=await gateway((body,res)=>{
    const input=JSON.parse(body.messages[1].content);
    calls.push(input);
    const rows=input.map(item=>{
      const row={source:item.source};
      for(const code of item.languages) {
        row[code]=({en:"EN",zh:"中文",ja:"日本語",ko:"한국어",my:"မြန်မာ",km:"ភាសាខ្មែរ"})[code]+" "+item.source;
        if(code==="zh" && item.source==="Đang tải…" && calls.length===1) row[code]="Loading...";
      }
      return row;
    });
    res.setHeader("Content-Type","application/json");
    res.end(JSON.stringify({choices:[{message:{content:JSON.stringify(rows)}}]}));
  });
  try {
    const result=await run(root,["--update"],base);
    assert.equal(result.code,0,result.output);
    assert.ok(calls.length>=2);
    const retry=calls.find((input,index)=>index>0 && input.some(item=>item.source==="Đang tải…"));
    assert.ok(retry);
    assert.deepEqual(retry.find(item=>item.source==="Đang tải…").languages,["zh"]);
    assert.equal((await run(root,["--check"],base)).code,0);
  } finally {server.close();cleanup(root);}
});
test("permanent invalid translation is reported without losing valid fields",async()=>{
  const root=fixture();let calls=0;
  const {server,base}=await gateway((body,res)=>{
    calls++;
    const rows=JSON.parse(body.messages[1].content).map(item=>{
      const row={source:item.source};
      for(const code of item.languages)
        row[code]=code==="zh" ? "bad English fallback" : ({en:"EN",ja:"日本語",ko:"한국어",my:"မြန်မာ",km:"ភាសាខ្មែរ"})[code]+" "+item.source;
      return row;
    });
    res.setHeader("Content-Type","application/json");
    res.end(JSON.stringify({choices:[{message:{content:JSON.stringify(rows)}}]}));
  });
  try {
    const result=await run(root,["--update"],base);
    assert.equal(result.code,1);
    assert.match(result.output,/Untranslated \[zh\]/);
    assert.ok(calls<=14,"retries must be bounded");
    const ja=JSON.parse(fs.readFileSync(path.join(root,"src/locales/ja.json"),"utf8"));
    assert.ok(ja["Đang tải…"]);
    assert.equal((await run(root,["--check"],base)).code,1);
  } finally {server.close();cleanup(root);}
});

test("rewrite replaces valid fields, keeps failed old fields and resumes only remainder",async()=>{
  const root=fixture(),calls=[];
  let fail=false;
  const {server,base}=await gateway((body,res)=>{
    const input=JSON.parse(body.messages[1].content); calls.push(input);
    const rows=input.map(item=>{
      const row={source:item.source};
      for(const code of item.languages) row[code]=({en:"Ready",zh:"准备好了",ja:"準備できました",ko:"준비됐어요",my:"အဆင်သင့်ပါ",km:"រួចរាល់ហើយ"})[code];
      if(fail) row.zh="invalid";
      return row;
    });
    res.setHeader("Content-Type","application/json");
    res.end(JSON.stringify({choices:[{message:{content:JSON.stringify(rows)}}]}));
  });
  try {
    assert.equal((await run(root,["--update"],base)).code,0);
    const old=JSON.parse(fs.readFileSync(path.join(root,"src/locales/en.json"),"utf8"));
    fail=true; const initial=calls.length;
    assert.equal((await run(root,["--rewrite"],base)).code,1);
    assert.ok(calls.slice(initial).some(batch=>batch.some(item=>item.languages.includes("en"))));
    assert.equal(JSON.parse(fs.readFileSync(path.join(root,"src/locales/zh.json"),"utf8"))["Xin chào"],"准备好了");
    const backups=path.join(root,"../backups/ui-locales");
    const original=JSON.parse(fs.readFileSync(path.join(backups,fs.readdirSync(backups)[0],"original-packs.json"),"utf8"));
    assert.deepEqual(original.en,old);
    const retry=calls.length; fail=false;
    assert.equal((await run(root,["--rewrite"],base)).code,0);
    assert.ok(calls.slice(retry).every(batch=>batch.every(item=>item.languages.join(",")==="zh")));
    const finished=calls.length;
    assert.equal((await run(root,["--rewrite"],base)).code,0);
    assert.equal(calls.length,finished);
  } finally { server.close();cleanup(root); }
});
