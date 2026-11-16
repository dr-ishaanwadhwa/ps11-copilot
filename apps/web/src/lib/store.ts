import { create } from 'zustand';
import type { GallaEntry, CollectionSlip } from './types';
import { decryptPayload, encryptPayload } from './crypto';

// Default initial state for local drawer (sovereign plane)
const initialGalla: GallaEntry = {
  id: 'GL-9024',
  date: '2026-09-30',
  openingCash: 10000,
  cashIn: 25000,
  cashOut: 2500,
  cashBanked: 20000,
  countedCash: 420000, // ₹4.20L drawer holding
  expectedCash: 12500,
  drift: 0,
  isBalanced: true,
  notes: 'Godown main till balanced',
};

const initialSlips: CollectionSlip[] = [
  {
    slipId: 'SLP-1092',
    date: '2026-09-30',
    salesman: 'Ramesh Kumar',
    shopName: 'Laxmi Mart',
    amount: 15000,
    paymentMode: 'CASH',
    status: 'IN_TILL',
  },
  {
    slipId: 'SLP-1093',
    date: '2026-09-30',
    salesman: 'Vijay Patil',
    shopName: 'Balaji Gen',
    amount: 8500,
    paymentMode: 'UPI',
    status: 'BANKED',
  },
  {
    slipId: 'SLP-1094',
    date: '2026-09-30',
    salesman: 'Ramesh Kumar',
    shopName: 'Om Super',
    amount: 22000,
    paymentMode: 'CHEQUE',
    status: 'IN_TRANSIT',
  },
];

interface VaultStoreState {
  isUnlocked: boolean;
  pin: string | null;
  gallaEntry: GallaEntry | null;
  collectionSlips: CollectionSlip[];
  encryptedEnvelope: ArrayBuffer | null;
  unlockVault: (pin: string) => Promise<boolean>;
  lockVault: () => void;
  updateGalla: (entry: Partial<GallaEntry>) => void;
  addCollectionSlip: (slip: CollectionSlip) => void;
  reset: () => void;
}

export const useVaultStore = create<VaultStoreState>((set, get) => ({
  isUnlocked: true, // Default unlocked in development for demonstration
  pin: '1234',
  gallaEntry: initialGalla,
  collectionSlips: initialSlips,
  encryptedEnvelope: null,

  unlockVault: async (pin: string) => {
    const { encryptedEnvelope } = get();
    if (encryptedEnvelope) {
      try {
        const decrypted = await decryptPayload<{ galla: GallaEntry; slips: CollectionSlip[] }>(
          encryptedEnvelope,
          pin
        );
        set({
          isUnlocked: true,
          pin,
          gallaEntry: decrypted.galla,
          collectionSlips: decrypted.slips,
        });
        return true;
      } catch {
        return false;
      }
    } else {
      // First unlock / demo unlock
      if (pin.length >= 4) {
        set({ isUnlocked: true, pin, gallaEntry: initialGalla, collectionSlips: initialSlips });
        return true;
      }
      return false;
    }
  },

  lockVault: async () => {
    const { pin, gallaEntry, collectionSlips } = get();
    if (pin && gallaEntry) {
      try {
        const envelope = await encryptPayload(
          { galla: gallaEntry, slips: collectionSlips },
          pin
        );
        set({
          isUnlocked: false,
          pin: null,
          gallaEntry: null,
          collectionSlips: [],
          encryptedEnvelope: envelope,
        });
        return;
      } catch {
        // Fallback lock
      }
    }
    set({
      isUnlocked: false,
      pin: null,
      gallaEntry: null,
      collectionSlips: [],
    });
  },

  updateGalla: (updatedFields) => {
    set((state) => ({
      gallaEntry: state.gallaEntry ? { ...state.gallaEntry, ...updatedFields } : null,
    }));
  },

  addCollectionSlip: (slip) => {
    set((state) => ({
      collectionSlips: [slip, ...state.collectionSlips],
    }));
  },

  reset: () => {
    set({
      isUnlocked: false,
      pin: null,
      gallaEntry: null,
      collectionSlips: [],
      encryptedEnvelope: null,
    });
  },
}));

export type ArchetypeId = 'SME-1' | 'SME-2' | 'SME-3';
export type ActiveRole = 'owner' | 'accountant';

export const ARCHETYPES: { id: ArchetypeId; label: string; businessName: string; blurb: string }[] = [
  { id: 'SME-1', label: 'FMCG wholesale', businessName: 'Kaveri Distributors', blurb: 'Distributor with salesmen, route slips and a cash drawer' },
  { id: 'SME-2', label: 'Dental clinic', businessName: 'SmileArc Dental', blurb: 'Clinic with daily patient receipts and supplier bills' },
  { id: 'SME-3', label: 'Creative agency', businessName: 'Northlight Creative', blurb: 'Agency with milestone invoices and retainers' },
];

interface CockpitStoreState {
  businessId: string;
  businessName: string;
  role: ActiveRole;
  shareWithAccountant: boolean;
  setRole: (role: ActiveRole) => void;
  setArchetype: (id: ArchetypeId) => void;
  asOfDate: string;
  locale: 'hi' | 'en';
  viewMode: '3D' | '2D';
  khataAlpha: number;
  setLocale: (locale: 'hi' | 'en') => void;
  setViewMode: (mode: '3D' | '2D') => void;
  setKhataAlpha: (alpha: number) => void;
}

export const useCockpitStore = create<CockpitStoreState>((set) => ({
  businessId: 'SME-1',
  businessName: 'Kaveri Distributors',
  asOfDate: '2026-09-30',
  locale: 'hi',
  viewMode: '3D',
  khataAlpha: 0.85,
  role: 'owner',
  shareWithAccountant: false,
  setRole: (role) => {
    // Leaving the Owner role immediately relocks the sovereign vault (ADR-001/004).
    if (role !== 'owner') void useVaultStore.getState().lockVault();
    set({ role });
  },
  setArchetype: (id) => {
    const a = ARCHETYPES.find((x) => x.id === id);
    if (a) set({ businessId: a.id, businessName: a.businessName });
  },
  setLocale: (locale) => set({ locale }),
  setViewMode: (viewMode) => set({ viewMode }),
  setKhataAlpha: (khataAlpha) => set({ khataAlpha }),
}));
