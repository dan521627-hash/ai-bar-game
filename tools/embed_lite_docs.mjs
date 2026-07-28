import { readFile, writeFile } from "node:fs/promises";

const root = new URL("../", import.meta.url);
const scriptUrl = new URL("bar_game_lite.py", root);
const [script, rulebook, examples] = await Promise.all([
  readFile(scriptUrl, "utf8"),
  readFile(new URL("LIGHT_RULEBOOK.md", root), "utf8"),
  readFile(new URL("LIGHT_EXAMPLE_CARDS.md", root), "utf8"),
]);

if (rulebook.includes('"""') || examples.includes('"""')) {
  throw new Error('Markdown contains Python triple quotes and cannot be embedded safely.');
}

const begin = "# === EMBEDDED_GAME_GUIDE_START ===";
const end = "# === EMBEDDED_GAME_GUIDE_END ===";
const start = script.indexOf(begin);
const finish = script.indexOf(end);
if (start < 0 || finish < start) {
  throw new Error("Embedded guide markers are missing.");
}

const block = `${begin}
EMBEDDED_RULEBOOK = r"""${rulebook.trim()}"""
EMBEDDED_EXAMPLE_CARDS = r"""${examples.trim()}"""
${end}`;
const output = script.slice(0, start) + block + script.slice(finish + end.length);
await writeFile(scriptUrl, output, "utf8");
console.log(`embedded rulebook=${rulebook.length} examples=${examples.length}`);
