import { notFound } from 'next/navigation';

/** Любой неизвестный адрес внутри локали → локализованная 404 */
export default function CatchAll() {
  notFound();
}
