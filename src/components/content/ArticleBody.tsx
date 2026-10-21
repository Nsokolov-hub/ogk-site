import { Info } from 'lucide-react';
import type { ArticleBlock } from '@/types/content';

/** Тело статьи из блоков админки: заголовки с якорями, абзацы, списки, таблицы, примечания */
export function ArticleBody({ blocks }: { blocks: ArticleBlock[] }) {
  return (
    <div className="flex flex-col gap-5 text-body text-text md:text-lg">
      {blocks.map((b, i) => {
        switch (b.type) {
          case 'h2':
            return (
              <h2 key={b.id} id={b.id} className="mt-8 scroll-mt-32 text-h3 font-medium text-text first:mt-0">
                {b.text}
              </h2>
            );
          case 'p':
            return <p key={i}>{b.text}</p>;
          case 'ul':
            return (
              <ul key={i} className="flex flex-col gap-2.5 pl-1">
                {b.items.map((item) => (
                  <li key={item} className="flex gap-3">
                    <span aria-hidden className="mt-[0.6em] size-2 shrink-0 rounded-full bg-accent" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            );
          case 'table':
            return (
              <div key={i} className="my-2 overflow-x-auto rounded-field">
                <table className="w-full min-w-[560px] border-collapse text-left text-body">
                  <caption className="pb-3 text-left text-small text-text-secondary">{b.caption}</caption>
                  <thead className="bg-surface-strong">
                    <tr>
                      {b.head.map((h, j) => (
                        <th key={`${h}-${j}`} scope="col" className="px-4 py-3 text-small font-medium text-text-secondary">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {b.rows.map((row, r) => (
                      <tr key={row.join('|')} className={r % 2 === 0 ? 'bg-surface' : undefined}>
                        {row.map((cell, j) =>
                          j === 0 ? (
                            <th key={j} scope="row" className="px-4 py-3 font-medium text-text">
                              {cell}
                            </th>
                          ) : (
                            <td key={j} className="px-4 py-3 text-text">
                              {cell}
                            </td>
                          ),
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          case 'note':
            return (
              <p key={i} className="flex gap-3 rounded-field bg-surface p-5 text-body text-text">
                <Info aria-hidden size={22} strokeWidth={1.5} className="mt-0.5 shrink-0 text-accent" />
                {b.text}
              </p>
            );
          default:
            return null;
        }
      })}
    </div>
  );
}
