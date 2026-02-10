import { create } from "zustand"
import { createAuthSlice, type AuthSlice } from "./authSlice"
import { createProjectSlice, type ProjectSlice } from "./projectSlice"
import { createUiSlice, type UiSlice } from "./uiSlice"

export type AppStore = AuthSlice & ProjectSlice & UiSlice

export const useAppStore = create<AppStore>()((...a) => ({
  ...createAuthSlice(...a),
  ...createProjectSlice(...a),
  ...createUiSlice(...a),
}))
