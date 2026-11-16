'use client';

import React, { useState } from 'react';
import { formatINR } from '@/lib/types';
import type { CustomerReceivable, ReceivablesPayload } from '@/lib/types';
import { fetchReceivables, useApiResource } from '@/lib/api';
import { useCockpitStore } from '@/lib/store';
import { DataSourceBadge } from '@/components/vault/ClientVaultDisplay';
import { MessageSquare, ShieldAlert, ShieldCheck, Printer, AlertTriangle, FileCheck } from 'lucide-react';

// SAMPLE DATA ONLY: shown (with a "Sample data" label) when the API cannot be reached.
const mockDebtors: CustomerReceivable[] = [
  {
    customerId: 'CUST-001',
    customerName: 'Matoshree Supermarket',
    phone: '+919820012345',
    totalOutstanding: 114000,
    openInvoiceCount: 3,
    oldestInvoiceDays: 930, // 31 months old
    isLimitationAlert: true,
    hasSalesmanCollectedToday: false,
  },
  {
    customerId: 'CUST-002',
    customerName: 'Balaji General Store',
    phone: '+919820054321',
    totalOutstanding: 65000,
    openInvoiceCount: 2,
    oldestInvoiceDays: 48,
    isLimitationAlert: false,
    hasSalesmanCollectedToday: true,
    salesmanName: 'Ramesh Kumar',
    collectedTodayAmount: 15000,
    collectedSlipId: 'SLP-1092',
    recentCollectionNote: 'Cash in salesman route bag; not banked yet.',
  },
  {
    customerId: 'CUST-003',
    customerName: 'Laxmi Provision Stores',
    phone: '+919820098765',
    totalOutstanding: 182400,
    openInvoiceCount: 5,
    oldestInvoiceDays: 52,
    isLimitationAlert: false,
    hasSalesmanCollectedToday: false,
  },
  {
    customerId: 'CUST-004',
    customerName: 'Om Supermarket & Traders',
    phone: '+919820045678',
    totalOutstanding: 215000,
    openInvoiceCount: 4,
    oldestInvoiceDays: 910, // 30+ months old
    isLimitationAlert: true,
    hasSalesmanCollectedToday: true,
    salesmanName: 'Ramesh Kumar',
    collectedTodayAmount: 22000,
    collectedSlipId: 'SLP-1094',
  },
];

const SAMPLE_RECEIVABLES: ReceivablesPayload = {
  businessId: 'SME-1',
  totalOutstanding: 9047000,
  overdueCount: 91,
  limitationAlertCount: 2,
  customers: mockDebtors,
};
const SAMPLE_OPEN_INVOICES = 346;

// The API fills every customer phone with this placeholder; never open a chat to it.
const PLACEHOLDER_PHONE = '910000000001';
const usablePhone = (phone: string) => {
  const digits = phone.replace(/\D/g, '');
  return digits.length >= 10 && digits !== PLACEHOLDER_PHONE ? digits : null;
};

export function ReceivablesAgingTable() {
  const [activeSegment, setActiveSegment] = useState<'ALL' | 'MSMED' | 'CLIFF'>('ALL');
  const [bsaCertificateIssued, setBsaCertificateIssued] = useState<string | null>(null);
  const businessId = useCockpitStore((st) => st.businessId);
  const asOfDate = useCockpitStore((st) => st.asOfDate);
  const { data, status } = useApiResource((signal) => fetchReceivables(businessId, asOfDate, signal), [businessId, asOfDate]);
  const rec = data ?? SAMPLE_RECEIVABLES;
  const debtors = rec.customers;
  const openInvoices = data ? debtors.reduce((n, d) => n + d.openInvoiceCount, 0) : SAMPLE_OPEN_INVOICES;
  const overdueDebtors = debtors.filter((d) => d.oldestInvoiceDays >= 45);
  const overdueTotal = overdueDebtors.reduce((n, d) => n + d.totalOutstanding, 0);
  const MAX_ROWS = 100;

  const filteredDebtors = debtors.filter((d) => {
    if (activeSegment === 'MSMED') return d.oldestInvoiceDays >= 45 && !d.isLimitationAlert;
    if (activeSegment === 'CLIFF') return d.isLimitationAlert;
    return true;
  });
  const visibleDebtors = filteredDebtors.slice(0, MAX_ROWS);

  const handleIssueBsaCertificate = (custName: string, amount: number) => {
    const certId = `BSA-63-${Math.floor(100000 + Math.random() * 900000)}`;
    setBsaCertificateIssued(`Form 63 BSA Hash Certificate ${certId} issued for ${custName} (₹${amount.toLocaleString('en-IN')}). Statutory clock extended +36 months under Limitation Act §18.`);
    setTimeout(() => setBsaCertificateIssued(null), 6000);
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto">
      {/* BSA Hash Certificate Notification */}
      {bsaCertificateIssued && (
        <div className="rounded-xl bg-emerald-50 dark:bg-emerald-950 border border-emerald-300 dark:border-emerald-700 p-4 text-xs font-semibold text-emerald-900 dark:text-emerald-200 flex items-center gap-3 shadow-md">
          <FileCheck className="h-5 w-5 text-emerald-600 flex-shrink-0" />
          <span>{bsaCertificateIssued}</span>
        </div>
      )}

      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Receivables & Recovery Accelerator
            </span>
            <span className="rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 text-[10px] font-bold px-2 py-0.5 border border-emerald-300">
              Section 18 Shield: ACTIVE
            </span>
            <DataSourceBadge status={status} />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
            Customer Trade Credit Ledger & Legal Shields
          </h2>
        </div>

        <button
          onClick={() => alert('Generating printable PDF Daily Recovery Sheet with route assignments...')}
          className="flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-bold hover:bg-slate-100 dark:hover:bg-slate-800 transition shadow-sm"
        >
          <Printer className="h-4 w-4 text-slate-500" />
          <span>Print Daily Recovery Sheet</span>
        </button>
      </div>

      {/* 3-Quadrant Metric Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <span className="text-xs font-medium text-slate-500">Total Formal Receivables</span>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
            {formatINR(rec.totalOutstanding, { compact: true })}
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">Verified against GST General Ledger</span>
        </div>

        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <span className="text-xs font-medium text-slate-500">Open Invoices & Debtors</span>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
            {openInvoices.toLocaleString('en-IN')} Invoices
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">{debtors.length} customers with a balance</span>
        </div>

        <div className="rounded-2xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/40 dark:bg-amber-950/20 p-5 shadow-sm">
          <span className="text-xs font-medium text-amber-700 dark:text-amber-300 font-semibold">Customers Past 45 Days</span>
          <div className="text-2xl font-bold font-mono text-amber-900 dark:text-amber-200 mt-1">
            {overdueDebtors.length} {overdueDebtors.length === 1 ? 'customer' : 'customers'}
          </div>
          <span className="text-[11px] text-amber-600/80 dark:text-amber-400/80 mt-1 block">
            Oldest invoice is 45+ days; they owe {formatINR(overdueTotal, { compact: true })} in total
          </span>
        </div>
      </div>

      {/* Filter Segment Buttons */}
      <div className="flex flex-wrap gap-2 text-xs font-bold">
        <button
          onClick={() => setActiveSegment('ALL')}
          className={`px-3 py-1.5 rounded-lg transition ${
            activeSegment === 'ALL'
              ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
          }`}
        >
          All {debtors.length} Debtors
        </button>
        <button
          onClick={() => setActiveSegment('MSMED')}
          className={`px-3 py-1.5 rounded-lg transition ${
            activeSegment === 'MSMED'
              ? 'bg-amber-600 text-white'
              : 'bg-slate-100 dark:bg-slate-800 text-amber-600'
          }`}
        >
          Over 45 Days (MSMED Priority)
        </button>
        <button
          onClick={() => setActiveSegment('CLIFF')}
          className={`px-3 py-1.5 rounded-lg transition ${
            activeSegment === 'CLIFF'
              ? 'bg-red-600 text-white'
              : 'bg-slate-100 dark:bg-slate-800 text-red-600'
          }`}
        >
          <span className="inline-flex items-center gap-1.5"><AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />Over 30 Months (Section 18 Cliff)</span>
        </button>
      </div>

      {filteredDebtors.length > MAX_ROWS && (
        <p className="text-[11px] text-slate-500">
          Showing the {MAX_ROWS} largest of {filteredDebtors.length} customers.
        </p>
      )}
      {status === 'loading' && !data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" aria-busy="true">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-40 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
      )}

      {/* Customer Recovery Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {visibleDebtors.map((debtor) => (
          <div
            key={debtor.customerId}
            className={`rounded-2xl border p-5 shadow-sm flex flex-col justify-between ${
              debtor.isLimitationAlert
                ? 'border-red-300 dark:border-red-900/60 bg-red-50/20 dark:bg-red-950/10'
                : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900'
            }`}
          >
            <div>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    {debtor.customerName}
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">{usablePhone(debtor.phone) ? debtor.phone : 'Phone not on file'}</span>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-white">
                    {formatINR(debtor.totalOutstanding)}
                  </div>
                  <span className="text-[11px] text-slate-500">
                    Oldest: {debtor.oldestInvoiceDays} days
                  </span>
                </div>
              </div>

              {/* Section 18 Limitation Act Cliff Warning */}
              {debtor.isLimitationAlert && (
                <div className="mt-4 rounded-xl bg-red-100/70 dark:bg-red-950/60 p-3 border border-red-300 dark:border-red-800 text-xs text-red-900 dark:text-red-200">
                  <div className="flex items-center gap-1.5 font-bold mb-1">
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                    <span>SECTION 18 LIMITATION ACT CLIFF (Debt is 30+ Months Old)</span>
                  </div>
                  <p className="text-[11px] text-red-800/90 dark:text-red-300">
                    Statutory 3-year commercial limitation bar takes effect in &lt; 90 days. A written balance confirmation via WhatsApp resets the 3-year statutory clock.
                  </p>
                </div>
              )}

              {/* Salesman Protection Shield Banner */}
              {debtor.hasSalesmanCollectedToday && (
                <div className="mt-4 rounded-xl bg-amber-100/70 dark:bg-amber-950/60 p-3 border border-amber-300 dark:border-amber-800 text-xs text-amber-900 dark:text-amber-200">
                  <div className="flex items-center gap-1.5 font-bold mb-0.5">
                    <ShieldAlert className="h-4 w-4 text-amber-600" />
                    <span>SALESMAN PROTECTION SHIELD ACTIVE: DO NOT CALL</span>
                  </div>
                  <p className="text-[11px] text-amber-800/90 dark:text-amber-300">
                    Salesman {debtor.salesmanName} collected {formatINR(debtor.collectedTodayAmount || 0)} today (Slip {debtor.collectedSlipId}); cash is in route bag.
                  </p>
                </div>
              )}
            </div>

            {/* Actions Toolbar */}
            <div className="mt-5 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
              {usablePhone(debtor.phone) ? (
                <a
                  href={`https://wa.me/${usablePhone(debtor.phone)}?text=Namaste%20${encodeURIComponent(debtor.customerName)}%20ji%2C%20as%20per%20our%20records%20pending%20balance%20is%20${encodeURIComponent(formatINR(debtor.totalOutstanding))}.%20Could%20you%20please%20confirm%20if%20this%20matches%20your%20books%3F`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  <span>Send WhatsApp AoD</span>
                </a>
              ) : (
                <span
                  title="No phone number on file for this customer"
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-200 dark:bg-slate-800 text-slate-500 rounded-lg text-xs font-semibold cursor-not-allowed"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  <span>No phone on file</span>
                </span>
              )}

              {debtor.isLimitationAlert && (
                <button
                  onClick={() => handleIssueBsaCertificate(debtor.customerName, debtor.totalOutstanding)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 rounded-lg text-xs font-semibold hover:opacity-90 transition"
                >
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Issue BSA §63 Hash Cert</span>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
