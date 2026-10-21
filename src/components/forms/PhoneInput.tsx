'use client';

import { Input, type InputProps } from '@/components/ui/Input';
import { digitsOnly, formatPhoneInput } from '@/lib/phone';

/**
 * Поле телефона с маской. Удаление «скобки» или «дефиса» удаляет и цифру перед ним,
 * чтобы маска не возвращала символ обратно.
 */
export function PhoneInput({
  value,
  onChange,
  ...rest
}: Omit<InputProps, 'value' | 'onChange' | 'type'> & { value: string; onChange: (value: string) => void }) {
  return (
    <Input
      {...rest}
      type="tel"
      inputMode="tel"
      autoComplete="tel"
      value={value}
      onChange={(e) => {
        const raw = e.target.value;
        let next = formatPhoneInput(raw);
        const deleting = raw.length < value.length;
        if (deleting && next.length > 0 && digitsOnly(next) === digitsOnly(value)) {
          const d = digitsOnly(value).slice(0, -1);
          next = d.length <= 1 && value.startsWith('+7') ? (d.length ? '+7' : '') : formatPhoneInput(`+${d}`);
        }
        onChange(next);
      }}
    />
  );
}
