'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useVaultStore, useCockpitStore } from '@/lib/store';
import { fetchOverview, useApiStatus } from '@/lib/api';
import {
  Zap,
  Coins,
  TrendingUp,
  Scale,
  ShieldCheck,
  Bot,
  FileSpreadsheet,
  Lock,
  Unlock,
  Menu,
  X,
  Search,
  Wifi,
} from 'lucide-react';

const navigationItems = [
  { name: 'Cockpit', href: '/overview', icon: Zap },
  { name: 'Cash Book', href: '/cash-book', icon: Coins },
  { name: 'Forecast', href: '/forecast', icon: TrendingUp },
  { name: 'Review', href: '/review', icon: Scale },
  { name: 'Recover', href: '/receivables', icon: ShieldCheck },
  { name: 'Copilot', href: '/copilot', icon: Bot },
  { name: 'Exports', href: '/exports', icon: FileSpreadsheet },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { isUnlocked, lockVault } = useVaultStore();
  const role = useCockpitStore((s) => s.role);
  const setRole = useCockpitStore((s) => s.setRole);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const businessId = useCockpitStore((s) => s.businessId);
  const businessName = useCockpitStore((s) => s.businessName);
  const asOfDate = useCockpitStore((s) => s.asOfDate);
  const apiStatus = useApiStatus();

  // The API is the source of truth for the business name; the store holds the archetype's name until it answers.
  useEffect(() => {
    let cancelled = false;
    fetchOverview(businessId, asOfDate)
      .then((ov) => {
        if (!cancelled && ov.businessId === businessId && ov.businessName && ov.businessName !== useCockpitStore.getState().businessName) {
          useCockpitStore.setState({ businessName: ov.businessName });
        }
      })
      .catch(() => {
        /* API unreachable: keep the store's name; the status badge reports it. */
      });
    return () => {
      cancelled = true;
    };
  }, [businessId, asOfDate]);

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 flex flex-col justify-between border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-5 transition-transform duration-300 lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div>
          {/* Logo & Close button on mobile */}
          <div className="flex items-center justify-between px-2 mb-6">
            <Link href="/overview" className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-emerald-400 flex items-center justify-center text-white font-extrabold shadow-md">
                ₹
              </div>
              <div>
                <span className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-white block">
                  SME Cashflow
                </span>
                <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">
                  Copilot v2.0
                </span>
              </div>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 text-slate-400 hover:text-slate-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Business Profile Badge */}
          <div className="mx-2 mb-6 rounded-xl bg-slate-50 dark:bg-slate-800/60 p-3 border border-slate-200/80 dark:border-slate-800">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Active Entity
            </span>
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block truncate">
              {businessName} ({businessId})
            </span>
          </div>

          {/* Navigation Items */}
          <nav className="space-y-1">
            {navigationItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold transition ${
                    isActive
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'}`} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Vault Status */}
        <div className="space-y-2 pt-4 border-t border-slate-100 dark:border-slate-800">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-1.5 text-xs">
              {isUnlocked ? (
                <>
                  <Unlock className="h-4 w-4 text-emerald-500" />
                  <span className="font-semibold text-emerald-600 dark:text-emerald-400">Vault Unlocked</span>
                </>
              ) : (
                <>
                  <Lock className="h-4 w-4 text-amber-500" />
                  <span className="font-semibold text-slate-500">Vault Locked</span>
                </>
              )}
            </div>
            {isUnlocked ? (
              <button
                onClick={lockVault}
                className="text-[11px] font-bold text-red-500 hover:underline"
              >
                Lock
              </button>
            ) : role === 'owner' ? (
              <Link
                href="/lock"
                className="text-[11px] font-bold text-amber-600 hover:underline"
              >
                Unlock
              </Link>
            ) : (
              <span className="text-[11px] text-slate-400">Owner only</span>
            )}
          </div>
          <div className="flex items-center justify-between px-2 text-[10px] text-slate-400">
            <span>Air-Gapped Sovereign RAM</span>
            <span className={`flex items-center gap-1 ${apiStatus === 'offline' ? 'text-amber-500' : 'text-emerald-500'}`}>
              <Wifi className="h-3 w-3" />
              {apiStatus === 'offline' ? 'API offline' : 'Online'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navigation Bar */}
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 px-4 sm:px-6 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="relative hidden sm:block w-72">
              <Search className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search ledger, invoice, customer (⌘K)..."
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300">
              <span className="hidden sm:inline">Viewing as</span>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as 'owner' | 'accountant')}
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2 py-1 text-xs"
              >
                <option value="owner">Owner</option>
                <option value="accountant">Accountant</option>
              </select>
            </label>
            <div className="flex items-center gap-2 rounded-full bg-slate-100 dark:bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-700 dark:text-slate-300">
              <span
                className={`h-2 w-2 rounded-full ${
                  apiStatus === 'online' ? 'bg-emerald-500' : apiStatus === 'offline' ? 'bg-amber-500' : 'bg-slate-400'
                }`}
              />
              <span>
                FastAPI Bridge: {apiStatus === 'online' ? 'Connected' : apiStatus === 'offline' ? 'Unreachable (sample data)' : 'Checking…'}
              </span>
            </div>
            <Link
              href="/copilot"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition"
            >
              <Bot className="h-3.5 w-3.5" />
              <span>Ask Copilot</span>
            </Link>
          </div>
        </header>

        {/* View Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
