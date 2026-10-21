import type { ComponentProps } from 'react';

/** Скрытое поле-ловушка для ботов (RFQ-06). Человек его не видит и не заполняет. */
export function Honeypot(props: Omit<ComponentProps<'input'>, 'type'>) {
  return (
    <div aria-hidden className="absolute -left-[9999px] h-px w-px overflow-hidden" /* taste-skill-ignore: скрытое поле-ловушка, не видно */>
      <label>
        Website
        <input type="text" tabIndex={-1} autoComplete="off" {...props} />
      </label>
    </div>
  );
}
