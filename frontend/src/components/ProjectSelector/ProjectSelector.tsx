import { useEffect } from "react"
import { useAppStore } from "@/store/store"
import { Select } from "@/components/ui/select"

export function ProjectSelector() {
  const projects = useAppStore((s) => s.projects)
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const projectsStatus = useAppStore((s) => s.projectsStatus)
  const fetchProjects = useAppStore((s) => s.projectActions.fetchProjects)
  const setActiveProject = useAppStore((s) => s.projectActions.setActiveProject)
  const newThread = useAppStore((s) => s.uiActions.newThread)

  useEffect(() => {
    if (projectsStatus === "idle") {
      fetchProjects()
    }
  }, [projectsStatus, fetchProjects])

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setActiveProject(e.target.value)
    newThread() // Reset conversation on project switch
  }

  if (projectsStatus === "loading") {
    return <span className="text-sm text-muted-foreground">Loading projects...</span>
  }

  if (projects.length === 0) {
    return <span className="text-sm text-muted-foreground">No projects</span>
  }

  return (
    <Select
      options={projects.map((p) => ({ value: p.id, label: `${p.name} (${p.role})` }))}
      value={activeProjectId ?? ""}
      onChange={handleChange}
      className="w-56"
    />
  )
}
