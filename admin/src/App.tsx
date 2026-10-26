import { lazy, Suspense, type ReactNode } from 'react';
import { BrowserRouter, Navigate, NavLink, Route, Routes } from 'react-router';
import {
  BookOpen,
  Boxes,

  FileText,
  FolderTree,
  Gauge,
  History,
  Inbox,
  LibraryBig,
  ListChecks,
  LogOut,
  Mail,
  Search,
  Settings as SettingsIcon,
  Tags,
  Upload,
  User,
  Users as UsersIcon,
} from 'lucide-react';
import { useAuth } from './auth';
import { Login } from './pages/Login';
import { Profile } from './pages/Profile';
import { Loading } from './ui';

const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })));
const Products = lazy(() => import('./pages/Products').then((m) => ({ default: m.Products })));
const ProductEditor = lazy(() => import('./pages/ProductEditor').then((m) => ({ default: m.ProductEditor })));
const Pages = lazy(() => import('./pages/Pages').then((m) => ({ default: m.Pages })));
const EntityEditor = lazy(() => import('./pages/EntityEditor').then((m) => ({ default: m.EntityEditor })));
const Categories = lazy(() => import('./pages/Catalog').then((m) => ({ default: m.Categories })));
const Brands = lazy(() => import('./pages/Catalog').then((m) => ({ default: m.Brands })));
const Substances = lazy(() => import('./pages/Catalog').then((m) => ({ default: m.Substances })));
const Landings = lazy(() => import('./pages/Seo').then((m) => ({ default: m.Landings })));
const Redirects = lazy(() => import('./pages/Seo').then((m) => ({ default: m.Redirects })));
const SeoRules = lazy(() => import('./pages/Seo').then((m) => ({ default: m.SeoRules })));
const SeoReport = lazy(() => import('./pages/Seo').then((m) => ({ default: m.SeoReport })));
const Imports = lazy(() => import('./pages/Imports').then((m) => ({ default: m.Imports })));
const Batch = lazy(() => import('./pages/Imports').then((m) => ({ default: m.Batch })));
const Queues = lazy(() => import('./pages/Queues').then((m) => ({ default: m.Queues })));
const Dictionaries = lazy(() => import('./pages/Dictionaries').then((m) => ({ default: m.Dictionaries })));
const Requests = lazy(() => import('./pages/Requests').then((m) => ({ default: m.Requests })));
const Subscribers = lazy(() => import('./pages/Requests').then((m) => ({ default: m.Subscribers })));
const Settings = lazy(() => import('./pages/Settings').then((m) => ({ default: m.Settings })));
const Users = lazy(() => import('./pages/Users').then((m) => ({ default: m.Users })));
const Journal = lazy(() => import('./pages/Journal').then((m) => ({ default: m.Journal })));

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  permission: string;
}

const NAV: { title: string; items: NavItem[] }[] = [
  { title: '', items: [{ to: '/', label: 'Сводка', icon: <Gauge size={17} />, permission: 'dashboard' }] },
  {
    title: 'Каталог',
    items: [
      { to: '/products', label: 'Товары', icon: <Boxes size={17} />, permission: 'products.read' },
      { to: '/categories', label: 'Разделы', icon: <FolderTree size={17} />, permission: 'taxonomy.read' },
      { to: '/brands', label: 'Бренды', icon: <Tags size={17} />, permission: 'taxonomy.read' },
      { to: '/substances', label: 'Субстанции', icon: <LibraryBig size={17} />, permission: 'taxonomy.read' },
      { to: '/import', label: 'Импорт', icon: <Upload size={17} />, permission: 'import.read' },
      { to: '/queues', label: 'Очереди', icon: <ListChecks size={17} />, permission: 'queues.read' },
      { to: '/dictionaries', label: 'Справочники', icon: <BookOpen size={17} />, permission: 'dictionaries.read' },
    ],
  },
  {
    title: 'Сайт',
    items: [
      { to: '/pages', label: 'Страницы', icon: <FileText size={17} />, permission: 'pages.read' },
      { to: '/landings', label: 'SEO-посадочные', icon: <Search size={17} />, permission: 'seo.read' },
      { to: '/redirects', label: 'Редиректы', icon: <Search size={17} />, permission: 'seo.read' },
      { to: '/seo', label: 'Шаблоны и robots.txt', icon: <Search size={17} />, permission: 'seo.read' },
      { to: '/seo/report', label: 'Отчёт SEO', icon: <Search size={17} />, permission: 'seo.read' },
    ],
  },
  {
    title: 'Заявки',
    items: [
      { to: '/requests', label: 'Журнал заявок', icon: <Inbox size={17} />, permission: 'requests.journal' },
      { to: '/subscribers', label: 'Подписчики', icon: <Mail size={17} />, permission: 'subscribers.read' },
    ],
  },
  {
    title: 'Управление',
    items: [
      { to: '/settings', label: 'Настройки', icon: <SettingsIcon size={17} />, permission: 'settings.read' },
      { to: '/users', label: 'Сотрудники', icon: <UsersIcon size={17} />, permission: 'users.write' },
      { to: '/journal', label: 'Журнал изменений', icon: <History size={17} />, permission: 'audit.read' },
    ],
  },
];

function Shell({ children }: { children: ReactNode }) {
  const { me, can, signOut } = useAuth();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <span>ОГК-ХИМ</span>
        </div>
        <nav>
          {NAV.map((section) => {
            const items = section.items.filter((item) => can(item.permission));
            if (!items.length) return null;
            return (
              <div key={section.title} className="nav-section">
                {section.title ? <div className="nav-title">{section.title}</div> : null}
                {items.map((item) => (
                  <NavLink key={item.to} to={item.to} end={item.to === '/' || item.to === '/seo'} className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
                    {item.icon}
                    {item.label}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          <NavLink to="/profile" className="nav-link">
            <User size={17} />
            {me?.name}
          </NavLink>
          <button type="button" className="nav-link" onClick={() => void signOut()}>
            <LogOut size={17} />
            Выйти
          </button>
        </div>
      </aside>
      <main className="content">
        <Suspense fallback={<Loading />}>{children}</Suspense>
      </main>
    </div>
  );
}

export function App() {
  const { me, loading } = useAuth();
  if (loading) return <Loading text="Проверяем вход…" />;
  if (!me) return <Login />;
  return (
    <BrowserRouter>
      <Shell>
        {me.totpSetupRequired ? (
          <Routes>
            <Route path="*" element={<Profile />} />
          </Routes>
        ) : (
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:id" element={<ProductEditor />} />
            <Route path="/pages" element={<Pages />} />
            <Route path="/edit/:entity/:id" element={<EntityEditor />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/brands" element={<Brands />} />
            <Route path="/substances" element={<Substances />} />
            <Route path="/landings" element={<Landings />} />
            <Route path="/redirects" element={<Redirects />} />
            <Route path="/seo" element={<SeoRules />} />
            <Route path="/seo/report" element={<SeoReport />} />
            <Route path="/import" element={<Imports />} />
            <Route path="/import/batches/:id" element={<Batch />} />
            <Route path="/queues" element={<Queues />} />
            <Route path="/dictionaries" element={<Dictionaries />} />
            <Route path="/requests" element={<Requests />} />
            <Route path="/subscribers" element={<Subscribers />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/users" element={<Users />} />
            <Route path="/journal" element={<Journal />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </Shell>
    </BrowserRouter>
  );
}

