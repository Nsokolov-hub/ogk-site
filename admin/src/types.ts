export interface Me {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'content' | 'catalog' | 'viewer';
  roleName: string;
  permissions: string[];
  totpEnabled: boolean;
  totpSetupRequired: boolean;
  csrfToken: string;
}

export interface HistoryEntry {
  id: number;
  at: string;
  actor: string;
  entity: string;
  entityId: string;
  action: string;
  summary: string;
  restorable: boolean;
  before?: unknown;
  after?: unknown;
}

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type JsonObject = { [key: string]: Json };

export interface EditorView {
  entity: 'page' | 'category' | 'brand' | 'substance' | 'landing';
  id: string;
  title: string;
  label: string;
  path: string;
  kind: string | null;
  published: JsonObject;
  draft: JsonObject | null;
  publishAt: string | null;
  draftAuthor: string | null;
  draftUpdatedAt: string | null;
  previewUrl: string;
  previewUrlEn: string;
  shape: JsonObject;
  history: HistoryEntry[];
}

export interface Paged<T> {
  total: number;
  items: T[];
  page?: number;
}
