'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { auth } from '@/lib/api';

export default function NavBar() {
  const pathname = usePathname();
  const router = useRouter();

  if (pathname === '/login') return null;

  const links = [
    { href: '/', label: 'Dashboard' },
    { href: '/agents', label: 'Agents' },
    { href: '/runs', label: 'Run History' },
  ];

  const handleLogout = async () => {
    await auth.logout();
    router.push('/login');
  };

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="container mx-auto px-4 max-w-6xl flex items-center justify-between h-14">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-bold text-indigo-600 text-lg tracking-tight">
            agent-99
          </Link>
          <div className="flex gap-1">
            {links.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  pathname === href
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                {label}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/settings"
            className="px-3 py-1.5 rounded-md text-sm text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            Settings
          </Link>
          <button
            onClick={handleLogout}
            className="px-3 py-1.5 rounded-md text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
