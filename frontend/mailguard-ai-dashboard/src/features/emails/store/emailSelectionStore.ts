import { create } from "zustand";

interface EmailSelectionState {
  selectedId: string | null;
  select: (id: string | null) => void;
}

export const useEmailSelection = create<EmailSelectionState>((set) => ({
  selectedId: null,
  select: (id) => set({ selectedId: id }),
}));
