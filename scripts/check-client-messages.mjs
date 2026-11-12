// Словарь интерфейса для браузера (src/i18n/client-messages.ts) должен покрывать все разделы, которые читает хук
// useTranslations: раздел вне списка в браузере не найдётся, и вместо текста появится его ключ. Запускается в npm run lint.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const walk = (dir) =>
  readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : /\.tsx?$/.test(name) ? [path] : [];
  });

const listed = new Set(
  [...readFileSync('src/i18n/client-messages.ts', 'utf8').match(/CLIENT_NAMESPACES = \[([^\]]*)\]/s)[1].matchAll(/'([^']+)'/g)].map((m) => m[1]),
);
const messages = JSON.parse(readFileSync('messages/ru.json', 'utf8'));
const problems = [];
const used = new Set();
for (const file of walk('src')) {
  const source = readFileSync(file, 'utf8');
  for (const call of source.matchAll(/useTranslations\(([^)]*)\)/g)) {
    const literal = call[1].trim().match(/^'([^']+)'$/);
    if (!literal) {
      problems.push(`${file}: useTranslations(${call[1]}) — раздел должен быть строкой, иначе его не проверить`);
      continue;
    }
    const namespace = literal[1].split('.')[0];
    used.add(namespace);
    if (!listed.has(namespace)) problems.push(`${file}: раздел «${namespace}» не в CLIENT_NAMESPACES (src/i18n/client-messages.ts)`);
  }
}
for (const namespace of listed) {
  if (!(namespace in messages)) problems.push(`CLIENT_NAMESPACES: раздела «${namespace}» нет в messages/ru.json`);
  else if (!used.has(namespace)) problems.push(`CLIENT_NAMESPACES: раздел «${namespace}» не читает ни один useTranslations — уберите его из списка`);
}
if (problems.length) {
  console.error(problems.join('\n'));
  process.exit(1);
}
console.log(`Словарь для браузера: ${listed.size} разделов из ${Object.keys(messages).length}.`);
