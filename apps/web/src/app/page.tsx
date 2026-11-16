'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ARCHETYPES, useCockpitStore } from '@/lib/store';
import { ArrowRight, FileSpreadsheet, Landmark, Database } from 'lucide-react';

function ComingSoon() {
  return (
    <span className="rounded-full bg-slate-200 dark:bg-slate-700 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
      Coming soon
    </span>
  );
}

export default function HomePage() {
  const router = useRouter();
  const businessId = useCockpitStore((s) => s.businessId);
  const setArchetype = useCockpitStore((s) => s.setArchetype);

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto flex max-w-3xl flex-col gap-10 px-5 py-14 sm:py-20">
        <header className="flex flex-col gap-4">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-emerald-400 flex items-center justify-center text-white font-extrabold shadow-md">
              ₹
            </div>
            <span className="font-extrabold text-sm tracking-tight">SME Cashflow Copilot</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Explain every rupee between your bank and your books
          </h1>
          <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 max-w-xl">
            See what is in your bank, what your books say, who owes you, and how low your cash could go in the next 90 days, in plain language.
          </p>
        </header>

        <section aria-labelledby="archetype-title" className="flex flex-col gap-3">
          <h2 id="archetype-title" className="text-sm font-bold">
            Which business are you?
          </h2>
          <div role="radiogroup" aria-labelledby="archetype-title" className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {ARCHETYPES.map((a) => {
              const selected = businessId === a.id;
              return (
                <button
                  key={a.id}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => setArchetype(a.id)}
                  className={`min-w-0 rounded-xl border p-4 text-left transition ${
                    selected
                      ? 'border-emerald-600 bg-emerald-50 dark:bg-emerald-950/30 ring-1 ring-emerald-600'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-emerald-500'
                  }`}
                >
                  <span className="block text-sm font-bold">{a.label}</span>
                  <span className="mt-1 block text-[11px] text-slate-500">{a.blurb}</span>
                  <span className="mt-2 block font-mono text-[10px] text-slate-400">{a.id}</span>
                </button>
              );
            })}
          </div>
        </section>

        <section aria-labelledby="start-title" className="flex flex-col gap-3">
          <h2 id="start-title" className="text-sm font-bold">
            How do you want to start?
          </h2>

          <button
            type="button"
            onClick={() => router.push('/overview')}
            className="flex items-center justify-between gap-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white p-4 text-left shadow-sm transition"
          >
            <span className="flex items-center gap-3 min-w-0">
              <Database className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
              <span className="text-sm font-bold">Use the demo data pack</span>
            </span>
            <ArrowRight className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
          </button>

          <button
            type="button"
            disabled
            aria-disabled="true"
            className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 p-4 text-left opacity-70 cursor-not-allowed"
          >
            <span className="flex items-center gap-3 min-w-0">
              <FileSpreadsheet className="h-5 w-5 flex-shrink-0 text-slate-500" aria-hidden="true" />
              <span className="text-sm font-bold">Upload a bank statement (CSV or Excel)</span>
            </span>
            <ComingSoon />
          </button>

          <button
            type="button"
            disabled
            aria-disabled="true"
            className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 p-4 text-left opacity-70 cursor-not-allowed"
          >
            <span className="flex items-center gap-3 min-w-0">
              <Landmark className="h-5 w-5 flex-shrink-0 text-slate-500" aria-hidden="true" />
              <span className="text-sm font-bold">Connect via Account Aggregator (sandbox)</span>
            </span>
            <ComingSoon />
          </button>
        </section>

        <footer className="flex flex-col gap-3 border-t border-slate-200 dark:border-slate-800 pt-6">
          <button
            type="button"
            disabled
            aria-disabled="true"
            className="flex items-center justify-center gap-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-2.5 text-sm font-semibold opacity-60 cursor-not-allowed"
          >
            <span>Continue with Google</span>
            <ComingSoon />
          </button>
          <p className="text-[11px] text-slate-500">
            Sign-in, uploads and bank connections are not available yet. The demo data pack is sample data for the selected business.{' '}
            <Link href="/overview" className="font-semibold text-emerald-700 dark:text-emerald-400 hover:underline">
              Skip to the cockpit
            </Link>
          </p>
        </footer>
      </div>
    </main>
  );
}
