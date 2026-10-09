const fs = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");
const digest = value => createHash("sha256").update(value).digest("hex");
function createRewriteState(root, style) {
  const directory = path.join(root, "../backups/ui-locales", digest(style).slice(0,16));
  const file = path.join(directory, "progress.json");
  const state = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file,"utf8")) : {};
  const key = (source,code) => digest(JSON.stringify([source,code]));
  return {
    completed: (source,code,value) => state[key(source,code)] === digest(value),
    mark: (source,code,value) => { state[key(source,code)] = digest(value); },
    backup(packs) {
      fs.mkdirSync(directory,{recursive:true});
      const snapshot = path.join(directory,"original-packs.json");
      if (!fs.existsSync(snapshot)) fs.writeFileSync(snapshot,JSON.stringify(packs,null,2)+"\n",{flag:"wx"});
    },
    save() {
      fs.mkdirSync(directory,{recursive:true});
      const temp = file+".tmp";
      fs.writeFileSync(temp,JSON.stringify(state,null,2)+"\n");
      fs.renameSync(temp,file);
    }
  };
}
module.exports = { createRewriteState };
