import type { StateCreator } from "zustand"
import { api } from "@/api/client"

export interface Project {
  id: string
  name: string
  slug: string
  description: string
  role: string
}

export type ProjectsStatus = "idle" | "loading" | "loaded" | "error"

export interface ProjectSlice {
  projects: Project[]
  activeProjectId: string | null
  projectsStatus: ProjectsStatus
  projectActions: {
    fetchProjects: () => Promise<void>
    setActiveProject: (id: string) => void
  }
}

export const createProjectSlice: StateCreator<ProjectSlice, [], [], ProjectSlice> = (set, get) => ({
  projects: [],
  activeProjectId: null,
  projectsStatus: "idle",
  projectActions: {
    fetchProjects: async () => {
      set({ projectsStatus: "loading" })
      try {
        const projects = await api.get<Project[]>("/api/projects/")
        const activeProjectId = get().activeProjectId
        set({
          projects,
          projectsStatus: "loaded",
          // Auto-select first project if none selected
          activeProjectId: activeProjectId ?? (projects[0]?.id ?? null),
        })
      } catch {
        set({ projectsStatus: "error" })
      }
    },

    setActiveProject: (id: string) => {
      set({ activeProjectId: id })
    },
  },
})
