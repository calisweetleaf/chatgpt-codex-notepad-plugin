import { readdir, readFile } from 'node:fs/promises';
import { join, extname } from 'node:path';

const extensions = new Set(['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs']);

async function files(directory) {
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error.code === 'ENOENT') return [];
    throw error;
  }
  const results = await Promise.all(entries.map(async (entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return files(path);
    return entry.isFile() && extensions.has(extname(entry.name)) && !entry.name.endsWith('.d.ts') ? [path] : [];
  }));
  return results.flat();
}

// Count lines containing code, excluding whitespace and comment-only lines.
function countCodeLines(text) {
  let blockComment = false;
  let quote = null;
  let escaped = false;
  let count = 0;
  for (const line of text.split(/\r?\n/)) {
    let code = '';
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      const next = line[i + 1];
      if (blockComment) {
        if (char === '*' && next === '/') { blockComment = false; i++; }
      } else if (quote) {
        code += char;
        if (escaped) escaped = false;
        else if (char === '\\') escaped = true;
        else if (char === quote) quote = null;
      } else if (char === '/' && next === '/') {
        break;
      } else if (char === '/' && next === '*') {
        blockComment = true;
        i++;
      } else if (char === '"' || char === "'" || char === '`') {
        quote = char;
        code += char;
      } else if (!/\s/.test(char)) {
        code += char;
      }
    }
    if (code && !/^[\s{}()[\],;]*$/.test(code)) count++;
    if (quote !== '`') { quote = null; escaped = false; }
  }
  return count;
}

async function count(directory) {
  const paths = await files(directory);
  const contents = await Promise.all(paths.map((path) => readFile(path, 'utf8')));
  return contents.reduce((total, content) => total + countCodeLines(content), 0);
}

const [source, tests] = await Promise.all([count('src'), count('test')]);
console.log(`Application: ${source} lines; tests: ${tests} lines; limit: ${Math.floor(source * 1.15)} lines`);
if (tests > source * 1.15) {
  console.error('Test code exceeds 115% of application code.');
  process.exitCode = 1;
}
