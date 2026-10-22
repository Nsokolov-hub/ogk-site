/**
 * Справочник перечней подконтрольных веществ (ТЗ 5.2.1): ПП РФ № 681 (наркотические средства, психотропные
 * вещества и прекурсоры) и ПП РФ № 964 (сильнодействующие и ядовитые вещества).
 * В проде загружается из xlsx в админке и обновляется при изменении перечней; здесь — несколько записей для проверки.
 */

export type ControlledList = 'pp681' | 'pp964';

export interface ControlledEntry {
  list: ControlledList;
  /** CAS основания и солей */
  cas: string[];
  /** Названия и синонимы RU/EN в нижнем регистре */
  names: string[];
}

export const CONTROLLED_REGISTER: ControlledEntry[] = [
  { list: 'pp681', cas: ['57-27-2', '52-26-6', '6055-06-7'], names: ['morphine', 'морфин'] },
  { list: 'pp681', cas: ['76-57-3', '52-28-8'], names: ['codeine', 'кодеин'] },
  { list: 'pp681', cas: ['439-14-5'], names: ['diazepam', 'диазепам'] },
  { list: 'pp681', cas: ['50-06-6'], names: ['phenobarbital', 'фенобарбитал'] },
  { list: 'pp964', cas: ['27203-92-5', '36282-47-0'], names: ['tramadol', 'трамадол'] },
];

const words = (s: string) => s.toLowerCase().split(/[^a-zа-яё0-9]+/i).filter(Boolean);

/**
 * Автопроверка при импорте и правке: совпадение по CAS или по слову из названия.
 * Спорные случаи (соли, изотопно-меченые формы) в проде уходят химику на проверку.
 */
export function matchControlled(p: { name: string; cas?: string }): ControlledEntry | undefined {
  const w = new Set(words(p.name));
  return CONTROLLED_REGISTER.find((e) => (p.cas && e.cas.includes(p.cas)) || e.names.some((n) => w.has(n)));
}
