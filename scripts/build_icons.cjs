/* Preserve the established icon classes, with local SVG masks instead of fonts. */
const fs = require('node:fs');
const path = require('node:path');
const root = 'node_modules/@fortawesome/fontawesome-free';
const metadata = JSON.parse(fs.readFileSync(path.join(root, 'metadata/icon-families.json'), 'utf8'));
const names = new Set();
function scan(folder) {
  for (const item of fs.readdirSync(folder, {withFileTypes: true})) {
    const name = path.join(folder, item.name);
    if (item.isDirectory()) scan(name);
    else if (/\.(html|js)$/.test(name)) {
      const text = fs.readFileSync(name, 'utf8');
      for (const match of text.matchAll(/\bfa-([a-z0-9-]+)/g)) names.add(match[1]);
    }
  }
}
scan('src/templates'); scan('src/static/js');
const aliases = {sparkles: 'wand-magic-sparkles'};
for (const [name, data] of Object.entries(metadata)) {
  for (const alias of data.aliases?.names || []) aliases[alias] = name;
}
let css = '/* Font Awesome Free 6.4.0 SVG icons: CC BY 4.0. See fontawesome-LICENSE.txt. */\n' +
  '.fa,.fa-solid,.fa-regular,.fa-brands{display:inline-block;width:1em;height:1em;vertical-align:-.125em;background-color:currentColor;mask:var(--fa-icon) no-repeat center/contain;-webkit-mask:var(--fa-icon) no-repeat center/contain;font-style:normal;flex-shrink:0}\n';
for (const name of [...names].sort()) {
  if (['solid','regular','brands','spin','fw'].includes(name)) continue;
  const canonical = metadata[name] ? name : aliases[name];
  if (!canonical) throw new Error('Unknown icon: ' + name);
  const styles = Object.keys(metadata[canonical].svgs.classic);
  const style = styles.includes('solid') ? 'solid' : styles[0];
  const svg = fs.readFileSync(path.join(root, 'svgs', style, canonical + '.svg'), 'utf8');
  css += '.fa-' + name + '{--fa-icon:url("data:image/svg+xml,' + encodeURIComponent(svg) + '")}\n';
}
fs.writeFileSync('src/static/css/icons.css', css);
fs.copyFileSync(path.join(root, 'LICENSE.txt'), 'src/static/css/fontawesome-LICENSE.txt');
console.log('Built local masks for ' + names.size + ' icon classes.');
