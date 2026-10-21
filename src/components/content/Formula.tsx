/**
 * Брутто-формула с подстрочными индексами (ТЗ 11.4: индексы — тегом sub).
 * Цифра после буквы или скобки — индекс; коэффициент после «·» (3H2O, 2HCl) — обычная цифра.
 */
export function Formula({ value, className }: { value: string; className?: string }) {
  const parts: { text: string; sub: boolean }[] = [];
  let prev = '';
  for (const ch of value) {
    const isDigit = /\d/.test(ch);
    const sub = isDigit && (/[A-Za-z)]/.test(prev) || (/\d/.test(prev) && parts.at(-1)?.sub === true));
    const last = parts.at(-1);
    if (last && last.sub === sub) last.text += ch;
    else parts.push({ text: ch, sub });
    prev = ch;
  }
  return (
    <span className={className}>
      {parts.map((p, i) => (p.sub ? <sub key={i}>{p.text}</sub> : <span key={i}>{p.text}</span>))}
    </span>
  );
}
