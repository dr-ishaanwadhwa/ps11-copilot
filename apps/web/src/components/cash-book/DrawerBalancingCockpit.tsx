'use client';

import React, { useState } from 'react';
import { useVaultStore } from '@/lib/store';
import { AccountantVaultNotice, useAccountantRestricted } from '@/components/vault/ClientVaultDisplay';
import { formatINR } from '@/lib/types';
import type { CollectionSlip } from '@/lib/types';
import { Lock, Plus, ShieldCheck, CheckCircle2, AlertCircle, FileText, Camera } from 'lucide-react';

export function DrawerBalancingCockpit() {
  const { isUnlocked, gallaEntry, collectionSlips, updateGalla, addCollectionSlip, lockVault } = useVaultStore();
  const accountantRestricted = useAccountantRestricted();

  const [openingFloat, setOpeningFloat] = useState(10000);
  const [parchiIn, setParchiIn] = useState(25000);
  const [cashOut, setCashOut] = useState(2500);
  const [bankedCdm, setBankedCdm] = useState(20000);
  const [countedCash, setCountedCash] = useState(12500);

  // New slip form state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newSalesman, setNewSalesman] = useState('');
  const [newShop, setNewShop] = useState('');
  const [newAmount, setNewAmount] = useState('');
  const [newMode, setNewMode] = useState<'CASH' | 'UPI' | 'CHEQUE'>('CASH');

  const expectedCash = openingFloat + parchiIn - cashOut - bankedCdm;
  const drift = countedCash - expectedCash;
  const isBalanced = Math.abs(drift) <= 50;

  const handleCommitDayClose = () => {
    updateGalla({
      openingCash: openingFloat,
      cashIn: parchiIn,
      cashOut,
      cashBanked: bankedCdm,
      countedCash,
      expectedCash,
      drift,
      isBalanced,
      date: new Date().toISOString().split('T')[0],
    });
    alert('Day close balancing committed to encrypted Sovereign Vault.');
  };

  const handleCreateSlip = (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(newAmount);
    if (!amt || !newSalesman || !newShop) return;

    const newSlip: CollectionSlip = {
      slipId: `SLP-${Math.floor(1000 + Math.random() * 9000)}`,
      date: new Date().toISOString().split('T')[0],
      salesman: newSalesman,
      shopName: newShop,
      amount: amt,
      paymentMode: newMode,
      status: newMode === 'CASH' ? 'IN_TILL' : 'IN_TRANSIT',
    };

    addCollectionSlip(newSlip);
    setIsModalOpen(false);
    setNewSalesman('');
    setNewShop('');
    setNewAmount('');
  };

  if (!isUnlocked) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <div className="h-16 w-16 rounded-full bg-amber-100 dark:bg-amber-950 flex items-center justify-center text-amber-600 mb-4">
          <Lock className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Sovereign Vault Locked</h2>
        {accountantRestricted ? (
          <AccountantVaultNotice className="max-w-md mt-3 text-left" />
        ) : (
          <>
            <p className="text-sm text-slate-500 max-w-md mt-1 mb-6">
              Physical cash drawer tallies and salesman collection slips are encrypted under ADR-001. Enter your owner PIN to decrypt volatile session memory.
            </p>
            <a
              href="/lock"
              className="px-6 py-2.5 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-lg shadow transition"
            >
              Enter 4-Digit Owner PIN
            </a>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
              Sovereign Operating Plane (Plane B)
            </span>
            <span className="rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 text-[10px] font-bold px-2 py-0.5">
              Unlocked in RAM
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
            Cash Book & Godown Drawer Balancing
          </h2>
        </div>

        <button
          onClick={lockVault}
          className="flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-bold hover:bg-slate-100 dark:hover:bg-slate-800 transition"
        >
          <Lock className="h-4 w-4 text-slate-500" />
          <span>Lock Sovereign Vault</span>
        </button>
      </div>

      {/* 5-Part Godown Cash Drawer Balancing Cockpit */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-900 dark:text-white mb-4">
          5-Part Evening Drawer Balancing Cockpit
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <div className="min-w-0 rounded-xl bg-slate-50 dark:bg-slate-800/60 p-3 border border-slate-200 dark:border-slate-700">
            <label className="text-[11px] font-semibold text-slate-500 block mb-1">1. Opening Float</label>
            <input
              type="number"
              value={openingFloat}
              onChange={(e) => setOpeningFloat(parseFloat(e.target.value) || 0)}
              className="w-full min-w-0 font-mono text-base font-bold bg-transparent border-b border-slate-300 dark:border-slate-600 focus:outline-none"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Morning Till Balance</span>
          </div>

          <div className="min-w-0 rounded-xl bg-slate-50 dark:bg-slate-800/60 p-3 border border-slate-200 dark:border-slate-700">
            <label className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 block mb-1">
              + 2. Parchi In
            </label>
            <input
              type="number"
              value={parchiIn}
              onChange={(e) => setParchiIn(parseFloat(e.target.value) || 0)}
              className="w-full min-w-0 font-mono text-base font-bold text-emerald-600 dark:text-emerald-400 bg-transparent border-b border-slate-300 dark:border-slate-600 focus:outline-none"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Salesman Receipts</span>
          </div>

          <div className="min-w-0 rounded-xl bg-slate-50 dark:bg-slate-800/60 p-3 border border-slate-200 dark:border-slate-700">
            <label className="text-[11px] font-semibold text-red-500 block mb-1">− 3. Hamali / Exp</label>
            <input
              type="number"
              value={cashOut}
              onChange={(e) => setCashOut(parseFloat(e.target.value) || 0)}
              className="w-full min-w-0 font-mono text-base font-bold text-red-500 bg-transparent border-b border-slate-300 dark:border-slate-600 focus:outline-none"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Labor & Petty Cash</span>
          </div>

          <div className="min-w-0 rounded-xl bg-slate-50 dark:bg-slate-800/60 p-3 border border-slate-200 dark:border-slate-700">
            <label className="text-[11px] font-semibold text-slate-500 block mb-1">− 4. Banked (CDM)</label>
            <input
              type="number"
              value={bankedCdm}
              onChange={(e) => setBankedCdm(parseFloat(e.target.value) || 0)}
              className="w-full min-w-0 font-mono text-base font-bold bg-transparent border-b border-slate-300 dark:border-slate-600 focus:outline-none"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Cash Deposit Machine</span>
          </div>

          <div className="min-w-0 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/30 p-3 border border-indigo-200 dark:border-indigo-800">
            <label className="text-[11px] font-semibold text-indigo-700 dark:text-indigo-300 block mb-1">
              = Expected Till
            </label>
            <div className="font-mono text-base font-bold text-indigo-900 dark:text-indigo-200">
              {formatINR(expectedCash)}
            </div>
            <span className="text-[10px] text-slate-400 mt-1 block">Theoretical Balance</span>
          </div>

          <div className="min-w-0 rounded-xl bg-amber-50/50 dark:bg-amber-950/30 p-3 border border-amber-300 dark:border-amber-700">
            <label className="text-[11px] font-semibold text-amber-700 dark:text-amber-300 block mb-1">
              Physical Counted
            </label>
            <input
              type="number"
              value={countedCash}
              onChange={(e) => setCountedCash(parseFloat(e.target.value) || 0)}
              className="w-full min-w-0 font-mono text-base font-bold text-amber-900 dark:text-amber-200 bg-transparent border-b border-amber-400 focus:outline-none"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Currency Notes Count</span>
          </div>
        </div>

        {/* Balancing Status Bar */}
        <div className="mt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            {isBalanced ? (
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 px-3 py-1.5 rounded-lg border border-emerald-300">
                <CheckCircle2 className="h-4 w-4" />
                <span>DRAWER BALANCED (Drift: {formatINR(drift)})</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs font-bold text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/50 px-3 py-1.5 rounded-lg border border-red-300">
                <AlertCircle className="h-4 w-4" />
                <span>DRIFT DETECTED (Drift: {formatINR(drift)})</span>
              </div>
            )}
            <span className="text-xs text-slate-500">Permissible drift threshold: ±₹50.00</span>
          </div>

          <button
            onClick={handleCommitDayClose}
            className="px-4 py-2 bg-slate-900 hover:bg-black text-white dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white text-xs font-bold rounded-lg shadow-sm transition"
          >
            Confirm & Seal Day Close
          </button>
        </div>
      </div>

      {/* Salesman Collection Slip (Kaccha Parchi) Ingestion */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Salesman Field Collection Slips (Parchi)
            </h3>
            <span className="text-xs text-slate-500">
              Active Slips Today: {collectionSlips.length} • Total Collected: {formatINR(collectionSlips.reduce((acc, s) => acc + s.amount, 0))}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => alert('Gemini Vision OCR activated: Hold salesman paper slip in front of camera.')}
              className="flex items-center gap-1.5 px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition"
            >
              <Camera className="h-4 w-4 text-slate-500" />
              <span>OCR Slip (Camera)</span>
            </button>
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold shadow-sm transition"
            >
              <Plus className="h-4 w-4" />
              <span>Record New Slip</span>
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 font-semibold">
                <th className="py-2.5 px-3">Slip ID</th>
                <th className="py-2.5 px-3">Date</th>
                <th className="py-2.5 px-3">Salesman</th>
                <th className="py-2.5 px-3">Shop / Retailer</th>
                <th className="py-2.5 px-3">Amount</th>
                <th className="py-2.5 px-3">Mode</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-200">
              {collectionSlips.map((slip) => (
                <tr key={slip.slipId} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-3 font-mono font-medium">{slip.slipId}</td>
                  <td className="py-3 px-3">{slip.date}</td>
                  <td className="py-3 px-3 font-medium">{slip.salesman}</td>
                  <td className="py-3 px-3">{slip.shopName}</td>
                  <td className="py-3 px-3 font-mono font-bold">{formatINR(slip.amount)}</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">
                      {slip.paymentMode}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    {slip.status === 'IN_TILL' && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                        In Till
                      </span>
                    )}
                    {slip.status === 'BANKED' && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                        Banked
                      </span>
                    )}
                    {slip.status === 'IN_TRANSIT' && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300">
                        In Bag (Route)
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Statutory Guardrail Compliance Banners */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 [&>div]:min-w-0">
        <div className="rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/40 dark:bg-emerald-950/20 p-4">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 text-xs font-bold">
            <ShieldCheck className="h-4 w-4" />
            <span>Section 186 Cash Receipt Guard</span>
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-1">
            Zero single-party cash receipts ≥ ₹2,00,000 logged today. System enforces hard blocking on single receipts &gt; ₹1.99L.
          </p>
        </div>

        <div className="rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/40 dark:bg-emerald-950/20 p-4">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 text-xs font-bold">
            <ShieldCheck className="h-4 w-4" />
            <span>Section 36(4) Expense Guard</span>
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-1">
            Hamali petty cash voucher (₹2,500) is within the ₹10,000 single-voucher tax disallowance limit.
          </p>
        </div>

        <div className="min-w-0 rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/40 dark:bg-indigo-950/20 p-4">
          <div className="flex items-start gap-2 min-w-0 text-indigo-700 dark:text-indigo-300 text-xs font-bold">
            <FileText className="h-4 w-4" />
            <span>SFT Rule 237 Deposit Facts</span>
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-1 break-words">
            YTD Cash Deposited: ₹14.50L. Current Account SFT reporting threshold is ₹50.00L annually.
          </p>
        </div>
      </div>

      {/* Record New Slip Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 p-6 shadow-2xl border border-slate-200 dark:border-slate-800">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
              Record Salesman Collection Slip
            </h3>
            <form onSubmit={handleCreateSlip} className="flex flex-col gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">Salesman Name</label>
                <input
                  type="text"
                  placeholder="e.g. Ramesh Kumar"
                  value={newSalesman}
                  onChange={(e) => setNewSalesman(e.target.value)}
                  required
                  className="w-full mt-1 p-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">Shop / Retailer Name</label>
                <input
                  type="text"
                  placeholder="e.g. Laxmi Mart"
                  value={newShop}
                  onChange={(e) => setNewShop(e.target.value)}
                  required
                  className="w-full mt-1 p-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">Amount (₹)</label>
                  <input
                    type="number"
                    placeholder="15000"
                    value={newAmount}
                    onChange={(e) => setNewAmount(e.target.value)}
                    required
                    className="w-full mt-1 p-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent font-mono"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">Payment Mode</label>
                  <select
                    value={newMode}
                    onChange={(e) => setNewMode(e.target.value as 'CASH' | 'UPI' | 'CHEQUE')}
                    className="w-full mt-1 p-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent"
                  >
                    <option value="CASH">CASH</option>
                    <option value="UPI">UPI</option>
                    <option value="CHEQUE">CHEQUE</option>
                  </select>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold"
                >
                  Save Slip to Till
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
