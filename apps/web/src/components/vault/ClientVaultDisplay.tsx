'use client';

import React, { useSyncExternalStore } from 'react';
import { useVaultStore, useCockpitStore } from '@/lib/store';
import { formatINR } from '@/lib/types';
import Link from 'next/link';

export const ACCOUNTANT_VAULT_MESSAGE =
  "You are viewing as Accountant. Sovereign cash is restricted to Owner unless 'Share with Accountant' is enabled by the Owner.";

/** True when the active role cannot decrypt sovereign cash, so no PIN prompt should be offered. */
export function useAccountantRestricted(): boolean {
  const role = useCockpitStore((s) => s.role);
  const share = useCockpitStore((s) => s.shareWithAccountant);
  return role === 'accountant' && !share;
}

export function AccountantVaultNotice({ className = '' }: { className?: string }) {
  return (
    <div
      role="status"
      className={`flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-800 p-3 text-xs text-amber-900 dark:text-amber-200 ${className}`}
    >
      <svg viewBox="0 0 24 24" className="h-4 w-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </svg>
      <span>{ACCOUNTANT_VAULT_MESSAGE}</span>
    </div>
  );
}

/** Shared status chip for views that fall back to sample data (same look as the forecast page). */
export function DataSourceBadge({ status, className = '' }: { status: 'loading' | 'live' | 'sample'; className?: string }) {
  if (status === 'live') return null;
  const label = status === 'loading' ? 'Loading…' : 'Sample data';
  return (
    <span
      role="status"
      className={`inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-2 py-0.5 text-[10px] font-bold text-slate-600 dark:text-slate-300 ${className}`}
    >
      <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4M12 8h.01" />
      </svg>
      {label}
    </span>
  );
}

interface ClientVaultDisplayProps {
  bankBalance: number;
  commitments: number;
  className?: string;
}

export function ClientVaultDisplay({
  bankBalance,
  commitments,
  className = '',
}: ClientVaultDisplayProps) {
  const isHydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  const { isUnlocked, gallaEntry } = useVaultStore();
  const accountantRestricted = useAccountantRestricted();

  if (!isHydrated) {
    return (
      <div className={`h-16 w-full animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800 ${className}`} />
    );
  }

  const drawerCash = isUnlocked ? (gallaEntry?.countedCash ?? 0) : 0;
  const netUsable = bankBalance + drawerCash - commitments;

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-extrabold font-mono tracking-tight text-slate-900 dark:text-white">
          {formatINR(netUsable, { compact: true })}
        </span>
        {isUnlocked ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-300">
            True Solvency
          </span>
        ) : accountantRestricted ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-300">
            Formal Only (Owner access)
          </span>
        ) : (
          <Link
            href="/lock"
            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border border-amber-300 hover:underline"
          >
            Formal Only (Unlock)
          </Link>
        )}
      </div>

      <div className="text-xs text-slate-500 dark:text-slate-400">
        {isUnlocked ? (
          <span>
            Bank: <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{formatINR(bankBalance, { compact: true })}</span> + Drawer Till: <span className="font-mono font-medium text-amber-600 dark:text-amber-400">{formatINR(drawerCash, { compact: true })}</span> − Due: <span className="font-mono font-medium text-red-500">{formatINR(commitments, { compact: true })}</span>
          </span>
        ) : (
          <span>
            Bank: <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{formatINR(bankBalance, { compact: true })}</span> · Sovereign Vault Locked
          </span>
        )}
      </div>
      {!isUnlocked && accountantRestricted && <AccountantVaultNotice className="mt-1" />}
    </div>
  );
}
