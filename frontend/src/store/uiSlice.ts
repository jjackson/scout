import type { StateCreator } from "zustand"

export interface UiSlice {
  threadId: string
  activeArtifactId: string | null
  uiActions: {
    newThread: () => void
    openArtifact: (id: string) => void
    closeArtifact: () => void
  }
}

export const createUiSlice: StateCreator<UiSlice, [], [], UiSlice> = (set) => ({
  threadId: crypto.randomUUID(),
  activeArtifactId: null,
  uiActions: {
    newThread: () => {
      set({ threadId: crypto.randomUUID(), activeArtifactId: null })
    },
    openArtifact: (id: string) => {
      set({ activeArtifactId: id })
    },
    closeArtifact: () => {
      set({ activeArtifactId: null })
    },
  },
})
