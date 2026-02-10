import type { StateCreator } from "zustand"

export interface UiSlice {
  threadId: string
  uiActions: {
    newThread: () => void
  }
}

export const createUiSlice: StateCreator<UiSlice, [], [], UiSlice> = (set) => ({
  threadId: crypto.randomUUID(),
  uiActions: {
    newThread: () => {
      set({ threadId: crypto.randomUUID() })
    },
  },
})
