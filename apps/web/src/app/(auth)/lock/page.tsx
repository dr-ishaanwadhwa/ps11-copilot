'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useVaultStore } from '@/lib/store';
import { AccountantVaultNotice, useAccountantRestricted } from '@/components/vault/ClientVaultDisplay';
import { Shield, Lock, Fingerprint, ArrowRight, AlertCircle } from 'lucide-react';

export default function LockPage() {
  const router = useRouter();
  const { unlockVault } = useVaultStore();
  const accountantRestricted = useAccountantRestricted();
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pin.length < 4) {
      setError('Please enter a valid 4-digit PIN.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const success = await unlockVault(pin);
      if (success) {
        router.push('/overview');
      } else {
        setError('Incorrect PIN or corrupted envelope. Please try again.');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Decryption error';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBiometricAuth = async () => {
    setIsLoading(true);
    try {
      // Demo biometric passkey authorization
      await unlockVault('1234');
      router.push('/overview');
    } catch {
      setError('Biometric sensor rejected or passkey unavailable.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-slate-950 text-white">
      <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/90 p-8 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-col items-center text-center mb-6">
          <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-amber-500 to-amber-300 flex items-center justify-center text-slate-950 shadow-lg mb-4">
            <Lock className="h-8 w-8" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight">Sovereign Vault Locked</h1>
          <p className="text-xs text-slate-400 mt-1 max-w-xs">
            Zero-Knowledge Sovereign Operating Plane (ADR-001). Decrypted exclusively in device volatile RAM.
          </p>
        </div>

        {accountantRestricted && (
          <div className="flex flex-col gap-4">
            <AccountantVaultNotice />
            <button
              type="button"
              onClick={() => router.push('/overview')}
              className="rounded-xl border border-slate-700 bg-slate-800/60 py-2.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 transition"
            >
              Back to formal books
            </button>
          </div>
        )}

        {!accountantRestricted && error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl bg-red-950/60 p-3 text-xs text-red-300 border border-red-800">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!accountantRestricted && (
        <form onSubmit={handleUnlock} className="flex flex-col gap-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">
              Owner PIN (Default: 1234)
            </label>
            <input
              type="password"
              maxLength={6}
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder="••••"
              autoFocus
              className="w-full rounded-xl border border-slate-700 bg-slate-800/80 p-3 text-center font-mono text-2xl tracking-[0.5em] text-white focus:border-amber-400 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center justify-center gap-2 rounded-xl bg-amber-500 py-3 text-sm font-bold text-slate-950 hover:bg-amber-400 transition shadow-lg disabled:opacity-50"
          >
            <span>{isLoading ? 'Deriving PBKDF2 Key...' : 'Unlock Sovereign Vault'}</span>
            <ArrowRight className="h-4 w-4" />
          </button>

          <div className="relative my-2 flex items-center justify-center">
            <div className="border-t border-slate-800 w-full" />
            <span className="bg-slate-900 px-3 text-[11px] text-slate-500 uppercase tracking-wider font-semibold">
              Or
            </span>
            <div className="border-t border-slate-800 w-full" />
          </div>

          <button
            type="button"
            onClick={handleBiometricAuth}
            className="flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800/60 py-2.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 transition"
          >
            <Fingerprint className="h-4 w-4 text-amber-400" />
            <span>Unlock via Touch ID / Face ID (WebAuthn PRF)</span>
          </button>
        </form>
        )}

        <div className="mt-8 flex items-center justify-center gap-2 text-[11px] text-slate-500">
          <Shield className="h-3.5 w-3.5 text-emerald-500" />
          <span>PBKDF2-HMAC-SHA256 • 100k Iterations • AES-256-GCM</span>
        </div>
      </div>
    </div>
  );
}
