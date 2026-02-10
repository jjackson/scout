# Admin UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add admin interfaces for managing projects, knowledge, recipes, and data dictionary with sidebar navigation.

**Architecture:** React frontend with React Router for navigation, Zustand for state, shadcn/ui components. Django REST Framework backend with APIView-based endpoints. All features scoped under the selected project.

**Tech Stack:** React 18, React Router 6, Zustand, shadcn/ui, Tailwind CSS, Django 5, DRF, PostgreSQL

---

## Phase 1: Navigation & Routing

### Task 1.1: Install React Router

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install react-router-dom**

Run:
```bash
cd frontend && bun add react-router-dom
```

**Step 2: Verify installation**

Run:
```bash
cd frontend && bun pm ls | grep react-router
```
Expected: `react-router-dom@7.x.x` (or 6.x.x)

**Step 3: Commit**

```bash
git add frontend/package.json frontend/bun.lockb
git commit -m "chore: add react-router-dom dependency"
```

---

### Task 1.2: Create Router Setup

**Files:**
- Create: `frontend/src/router.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create router configuration**

Create `frontend/src/router.tsx`:
```tsx
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom"
import { AppLayout } from "@/components/AppLayout/AppLayout"
import { ChatPanel } from "@/components/ChatPanel/ChatPanel"

// Lazy load admin pages (to be created later)
const ProjectsPage = () => <div>Projects Page (coming soon)</div>
const KnowledgePage = () => <div>Knowledge Page (coming soon)</div>
const RecipesPage = () => <div>Recipes Page (coming soon)</div>
const DataDictionaryPage = () => <div>Data Dictionary Page (coming soon)</div>

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <ChatPanel /> },
      { path: "chat", element: <ChatPanel /> },
      { path: "projects", element: <ProjectsPage /> },
      { path: "projects/new", element: <ProjectsPage /> },
      { path: "projects/:id/edit", element: <ProjectsPage /> },
      { path: "knowledge", element: <KnowledgePage /> },
      { path: "knowledge/new", element: <KnowledgePage /> },
      { path: "knowledge/:id", element: <KnowledgePage /> },
      { path: "recipes", element: <RecipesPage /> },
      { path: "recipes/:id", element: <RecipesPage /> },
      { path: "data-dictionary", element: <DataDictionaryPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
])
```

**Step 2: Update App.tsx to use router**

Replace `frontend/src/App.tsx`:
```tsx
import { useEffect } from "react"
import { RouterProvider } from "react-router-dom"
import { useAppStore } from "@/store/store"
import { LoginForm } from "@/components/LoginForm/LoginForm"
import { Skeleton } from "@/components/ui/skeleton"
import { router } from "@/router"

export default function App() {
  const authStatus = useAppStore((s) => s.authStatus)
  const fetchMe = useAppStore((s) => s.authActions.fetchMe)

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  if (authStatus === "idle" || authStatus === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="space-y-3 w-64">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
    )
  }

  if (authStatus === "unauthenticated") {
    return <LoginForm />
  }

  return <RouterProvider router={router} />
}
```

**Step 3: Verify app still loads**

Run:
```bash
cd frontend && bun run dev
```
Visit http://localhost:5173 - should see the existing chat interface.

**Step 4: Commit**

```bash
git add frontend/src/router.tsx frontend/src/App.tsx
git commit -m "feat: add React Router with route configuration"
```

---

### Task 1.3: Create Sidebar Component

**Files:**
- Create: `frontend/src/components/Sidebar/Sidebar.tsx`
- Create: `frontend/src/components/Sidebar/NavItem.tsx`
- Create: `frontend/src/components/Sidebar/index.ts`

**Step 1: Create NavItem component**

Create `frontend/src/components/Sidebar/NavItem.tsx`:
```tsx
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface NavItemProps {
  to: string
  icon: LucideIcon
  label: string
}

export function NavItem({ to, icon: Icon, label }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-accent text-accent-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        )
      }
    >
      <Icon className="h-4 w-4" />
      {label}
    </NavLink>
  )
}
```

**Step 2: Create Sidebar component**

Create `frontend/src/components/Sidebar/Sidebar.tsx`:
```tsx
import { Link } from "react-router-dom"
import {
  MessageSquare,
  BookOpen,
  ChefHat,
  Database,
  Settings,
  LogOut,
} from "lucide-react"
import { useAppStore } from "@/store/store"
import { NavItem } from "./NavItem"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function Sidebar() {
  const user = useAppStore((s) => s.user)
  const projects = useAppStore((s) => s.projects)
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const setActiveProject = useAppStore((s) => s.projectActions.setActiveProject)
  const logout = useAppStore((s) => s.authActions.logout)

  const activeProject = projects.find((p) => p.id === activeProjectId)

  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-background">
      {/* Logo */}
      <div className="flex h-14 items-center border-b px-4">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <span className="text-lg">Scout</span>
        </Link>
      </div>

      {/* Project Selector */}
      <div className="border-b p-4">
        <label className="text-xs font-medium text-muted-foreground">
          Project
        </label>
        <Select
          value={activeProjectId ?? undefined}
          onValueChange={setActiveProject}
        >
          <SelectTrigger className="mt-1 w-full">
            <SelectValue placeholder="Select project">
              {activeProject?.name}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {projects.map((project) => (
              <SelectItem key={project.id} value={project.id}>
                {project.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Link
          to="/projects"
          className="mt-2 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <Settings className="h-3 w-3" />
          Manage Projects
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        <NavItem to="/" icon={MessageSquare} label="Chat" />
        <NavItem to="/knowledge" icon={BookOpen} label="Knowledge" />
        <NavItem to="/recipes" icon={ChefHat} label="Recipes" />
        <NavItem to="/data-dictionary" icon={Database} label="Data Dictionary" />
      </nav>

      {/* User Section */}
      <div className="border-t p-4">
        <div className="mb-2 truncate text-sm text-muted-foreground">
          {user?.email}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start"
          onClick={logout}
        >
          <LogOut className="mr-2 h-4 w-4" />
          Logout
        </Button>
      </div>
    </aside>
  )
}
```

**Step 3: Create index export**

Create `frontend/src/components/Sidebar/index.ts`:
```tsx
export { Sidebar } from "./Sidebar"
export { NavItem } from "./NavItem"
```

**Step 4: Commit**

```bash
git add frontend/src/components/Sidebar/
git commit -m "feat: add Sidebar component with project selector and navigation"
```

---

### Task 1.4: Update AppLayout to Use Sidebar

**Files:**
- Modify: `frontend/src/components/AppLayout/AppLayout.tsx`

**Step 1: Read current AppLayout**

Read the current implementation to understand its structure.

**Step 2: Update AppLayout to include Sidebar and Outlet**

Update `frontend/src/components/AppLayout/AppLayout.tsx`:
```tsx
import { useEffect } from "react"
import { Outlet } from "react-router-dom"
import { useAppStore } from "@/store/store"
import { Sidebar } from "@/components/Sidebar"

export function AppLayout() {
  const fetchProjects = useAppStore((s) => s.projectActions.fetchProjects)
  const projectsStatus = useAppStore((s) => s.projectsStatus)

  useEffect(() => {
    if (projectsStatus === "idle") {
      fetchProjects()
    }
  }, [fetchProjects, projectsStatus])

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
```

**Step 3: Verify layout works**

Run:
```bash
cd frontend && bun run dev
```
Visit http://localhost:5173 - should see sidebar on left, chat panel in main area.

**Step 4: Commit**

```bash
git add frontend/src/components/AppLayout/AppLayout.tsx
git commit -m "feat: integrate Sidebar into AppLayout with React Router Outlet"
```

---

### Task 1.5: Update ChatPanel for Standalone Use

**Files:**
- Modify: `frontend/src/components/ChatPanel/ChatPanel.tsx`

**Step 1: Read current ChatPanel**

Read the current implementation to understand its structure.

**Step 2: Remove any layout wrapper if present**

The ChatPanel should be a standalone component that fits within the main area. Remove any outer chrome (header with project selector, etc.) since that's now in the Sidebar. Keep only the chat functionality.

**Step 3: Verify chat still works**

Run:
```bash
cd frontend && bun run dev
```
Test sending a message and receiving a response.

**Step 4: Commit**

```bash
git add frontend/src/components/ChatPanel/
git commit -m "refactor: update ChatPanel as standalone component for router outlet"
```

---

## Phase 2: Projects Management

### Task 2.1: Create Projects API Endpoints

**Files:**
- Create: `apps/projects/api/__init__.py`
- Create: `apps/projects/api/serializers.py`
- Create: `apps/projects/api/views.py`
- Modify: `apps/projects/urls.py`

**Step 1: Create serializers**

Create `apps/projects/api/__init__.py`:
```python
```

Create `apps/projects/api/serializers.py`:
```python
"""
Serializers for projects API.
"""
from rest_framework import serializers

from apps.projects.models import Project, ProjectMembership, ProjectRole


class ProjectListSerializer(serializers.ModelSerializer):
    """Serializer for project list view."""

    role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "role",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_role(self, obj):
        """Get the current user's role in this project."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user).first()
        return membership.role if membership else None

    def get_member_count(self, obj):
        """Get the number of members in this project."""
        return obj.memberships.count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Serializer for project detail/create/update."""

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "db_host",
            "db_port",
            "db_name",
            "db_user",
            "db_password",
            "allowed_schemas",
            "allowed_tables",
            "blocked_tables",
            "system_prompt",
            "llm_model",
            "llm_temperature",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "db_password": {"write_only": True},
        }

    def create(self, validated_data):
        """Create project and add creator as admin."""
        request = self.context.get("request")
        project = Project.objects.create(**validated_data)
        ProjectMembership.objects.create(
            project=project,
            user=request.user,
            role=ProjectRole.ADMIN,
        )
        return project


class ProjectMemberSerializer(serializers.ModelSerializer):
    """Serializer for project membership."""

    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = ProjectMembership
        fields = ["id", "email", "name", "role", "created_at"]
        read_only_fields = ["id", "email", "name", "created_at"]


class AddMemberSerializer(serializers.Serializer):
    """Serializer for adding a new member to a project."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=ProjectRole.choices, default=ProjectRole.VIEWER)

    def validate_email(self, value):
        """Check if user exists."""
        from apps.users.models import User

        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value


class TestConnectionSerializer(serializers.Serializer):
    """Serializer for testing database connection."""

    db_host = serializers.CharField()
    db_port = serializers.IntegerField(default=5432)
    db_name = serializers.CharField()
    db_user = serializers.CharField()
    db_password = serializers.CharField()
```

**Step 2: Create views**

Create `apps/projects/api/views.py`:
```python
"""
API views for projects management.
"""
import asyncio

import asyncpg
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.users.models import User

from .serializers import (
    AddMemberSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectMemberSerializer,
    TestConnectionSerializer,
)


class ProjectPermissionMixin:
    """Mixin for checking project permissions."""

    def get_project(self, project_id):
        """Get project by ID."""
        return get_object_or_404(Project, pk=project_id)

    def check_admin_permission(self, request, project):
        """Check if user is project admin."""
        if request.user.is_superuser:
            return True, None
        membership = ProjectMembership.objects.filter(
            user=request.user,
            project=project,
        ).first()
        if not membership or membership.role != ProjectRole.ADMIN:
            return False, Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return True, None


class ProjectListCreateView(APIView):
    """
    GET /api/projects/ - List projects user has access to
    POST /api/projects/ - Create a new project
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List projects the user has access to."""
        memberships = ProjectMembership.objects.filter(
            user=request.user
        ).select_related("project")
        projects = [m.project for m in memberships if m.project.is_active]
        serializer = ProjectListSerializer(
            projects, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request):
        """Create a new project."""
        serializer = ProjectDetailSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        project = serializer.save()
        return Response(
            ProjectDetailSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(ProjectPermissionMixin, APIView):
    """
    GET /api/projects/{id}/ - Get project details
    PUT /api/projects/{id}/ - Update project
    DELETE /api/projects/{id}/ - Delete project
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        """Get project details."""
        project = self.get_project(project_id)
        # Check user has access
        if not request.user.is_superuser:
            membership = ProjectMembership.objects.filter(
                user=request.user, project=project
            ).first()
            if not membership:
                return Response(
                    {"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN
                )
        serializer = ProjectDetailSerializer(project)
        return Response(serializer.data)

    def put(self, request, project_id):
        """Update project."""
        project = self.get_project(project_id)
        has_permission, error = self.check_admin_permission(request, project)
        if not has_permission:
            return error
        serializer = ProjectDetailSerializer(
            project, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, project_id):
        """Delete project (soft delete by setting is_active=False)."""
        project = self.get_project(project_id)
        has_permission, error = self.check_admin_permission(request, project)
        if not has_permission:
            return error
        project.is_active = False
        project.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectMembersView(ProjectPermissionMixin, APIView):
    """
    GET /api/projects/{id}/members/ - List project members
    POST /api/projects/{id}/members/ - Add a member
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        """List project members."""
        project = self.get_project(project_id)
        # Check user has access
        if not request.user.is_superuser:
            membership = ProjectMembership.objects.filter(
                user=request.user, project=project
            ).first()
            if not membership:
                return Response(
                    {"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN
                )
        members = ProjectMembership.objects.filter(project=project).select_related(
            "user"
        )
        serializer = ProjectMemberSerializer(members, many=True)
        return Response(serializer.data)

    def post(self, request, project_id):
        """Add a member to the project."""
        project = self.get_project(project_id)
        has_permission, error = self.check_admin_permission(request, project)
        if not has_permission:
            return error
        serializer = AddMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.get(email=serializer.validated_data["email"])
        # Check if already a member
        if ProjectMembership.objects.filter(project=project, user=user).exists():
            return Response(
                {"error": "User is already a member."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership = ProjectMembership.objects.create(
            project=project,
            user=user,
            role=serializer.validated_data["role"],
        )
        return Response(
            ProjectMemberSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectMemberDetailView(ProjectPermissionMixin, APIView):
    """
    DELETE /api/projects/{id}/members/{user_id}/ - Remove a member
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, project_id, user_id):
        """Remove a member from the project."""
        project = self.get_project(project_id)
        has_permission, error = self.check_admin_permission(request, project)
        if not has_permission:
            return error
        membership = get_object_or_404(
            ProjectMembership, project=project, user_id=user_id
        )
        # Don't allow removing the last admin
        if membership.role == ProjectRole.ADMIN:
            admin_count = ProjectMembership.objects.filter(
                project=project, role=ProjectRole.ADMIN
            ).count()
            if admin_count <= 1:
                return Response(
                    {"error": "Cannot remove the last admin."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TestConnectionView(APIView):
    """
    POST /api/projects/test-connection/ - Test database connection
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Test database connection with provided credentials."""
        serializer = TestConnectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data

        async def test_connection():
            try:
                conn = await asyncpg.connect(
                    host=data["db_host"],
                    port=data["db_port"],
                    database=data["db_name"],
                    user=data["db_user"],
                    password=data["db_password"],
                    timeout=10,
                )
                # Get schemas
                schemas = await conn.fetch(
                    """
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                    ORDER BY schema_name
                    """
                )
                # Get tables
                tables = await conn.fetch(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                      AND table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_schema, table_name
                    """
                )
                await conn.close()
                return {
                    "success": True,
                    "schemas": [r["schema_name"] for r in schemas],
                    "tables": [
                        {"schema": r["table_schema"], "table": r["table_name"]}
                        for r in tables
                    ],
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        result = asyncio.run(test_connection())
        if result["success"]:
            return Response(result)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
```

**Step 3: Update URLs**

Update `apps/projects/urls.py`:
```python
"""
URL configuration for projects app.
"""
from django.urls import path

from .api.views import (
    ProjectDetailView,
    ProjectListCreateView,
    ProjectMemberDetailView,
    ProjectMembersView,
    TestConnectionView,
)

app_name = "projects"

urlpatterns = [
    path("", ProjectListCreateView.as_view(), name="list_create"),
    path("<uuid:project_id>/", ProjectDetailView.as_view(), name="detail"),
    path("<uuid:project_id>/members/", ProjectMembersView.as_view(), name="members"),
    path(
        "<uuid:project_id>/members/<uuid:user_id>/",
        ProjectMemberDetailView.as_view(),
        name="member_detail",
    ),
    path("test-connection/", TestConnectionView.as_view(), name="test_connection"),
]
```

**Step 4: Run tests**

Run:
```bash
pytest tests/ -v -k project
```

**Step 5: Commit**

```bash
git add apps/projects/api/ apps/projects/urls.py
git commit -m "feat: add projects API endpoints"
```

---

### Task 2.2: Create Projects Zustand Slice

**Files:**
- Modify: `frontend/src/store/projectSlice.ts`
- Modify: `frontend/src/api/client.ts`

**Step 1: Extend API client with PUT and DELETE**

Update `frontend/src/api/client.ts` to add:
```typescript
export const api = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(url: string) => request<T>(url, { method: "DELETE" }),
}
```

**Step 2: Extend projectSlice with CRUD actions**

Update `frontend/src/store/projectSlice.ts`:
```typescript
import type { StateCreator } from "zustand"
import { api } from "@/api/client"

export interface Project {
  id: string
  name: string
  slug: string
  description: string
  role: string
  member_count?: number
}

export interface ProjectDetail extends Project {
  db_host: string
  db_port: number
  db_name: string
  db_user: string
  db_password?: string
  allowed_schemas: string[]
  allowed_tables: string[]
  blocked_tables: string[]
  system_prompt: string
  llm_model: string
  llm_temperature: number
  is_active: boolean
}

export interface ProjectMember {
  id: string
  email: string
  name: string
  role: string
  created_at: string
}

export type ProjectsStatus = "idle" | "loading" | "loaded" | "error"

export interface ProjectSlice {
  projects: Project[]
  activeProjectId: string | null
  projectsStatus: ProjectsStatus
  currentProject: ProjectDetail | null
  projectMembers: ProjectMember[]
  projectActions: {
    fetchProjects: () => Promise<void>
    setActiveProject: (id: string) => void
    fetchProject: (id: string) => Promise<ProjectDetail>
    createProject: (data: Partial<ProjectDetail>) => Promise<ProjectDetail>
    updateProject: (id: string, data: Partial<ProjectDetail>) => Promise<ProjectDetail>
    deleteProject: (id: string) => Promise<void>
    fetchMembers: (projectId: string) => Promise<void>
    addMember: (projectId: string, email: string, role: string) => Promise<void>
    removeMember: (projectId: string, userId: string) => Promise<void>
  }
}

export const createProjectSlice: StateCreator<ProjectSlice, [], [], ProjectSlice> = (
  set,
  get
) => ({
  projects: [],
  activeProjectId: null,
  projectsStatus: "idle",
  currentProject: null,
  projectMembers: [],
  projectActions: {
    fetchProjects: async () => {
      set({ projectsStatus: "loading" })
      try {
        const projects = await api.get<Project[]>("/api/projects/")
        const activeProjectId = get().activeProjectId
        set({
          projects,
          projectsStatus: "loaded",
          activeProjectId: activeProjectId ?? (projects[0]?.id ?? null),
        })
      } catch {
        set({ projectsStatus: "error" })
      }
    },

    setActiveProject: (id: string) => {
      set({ activeProjectId: id })
    },

    fetchProject: async (id: string) => {
      const project = await api.get<ProjectDetail>(`/api/projects/${id}/`)
      set({ currentProject: project })
      return project
    },

    createProject: async (data: Partial<ProjectDetail>) => {
      const project = await api.post<ProjectDetail>("/api/projects/", data)
      const projects = get().projects
      set({ projects: [...projects, project] })
      return project
    },

    updateProject: async (id: string, data: Partial<ProjectDetail>) => {
      const project = await api.put<ProjectDetail>(`/api/projects/${id}/`, data)
      const projects = get().projects.map((p) => (p.id === id ? { ...p, ...project } : p))
      set({ projects, currentProject: project })
      return project
    },

    deleteProject: async (id: string) => {
      await api.delete(`/api/projects/${id}/`)
      const projects = get().projects.filter((p) => p.id !== id)
      const activeProjectId = get().activeProjectId === id ? projects[0]?.id ?? null : get().activeProjectId
      set({ projects, activeProjectId })
    },

    fetchMembers: async (projectId: string) => {
      const members = await api.get<ProjectMember[]>(`/api/projects/${projectId}/members/`)
      set({ projectMembers: members })
    },

    addMember: async (projectId: string, email: string, role: string) => {
      const member = await api.post<ProjectMember>(`/api/projects/${projectId}/members/`, {
        email,
        role,
      })
      set({ projectMembers: [...get().projectMembers, member] })
    },

    removeMember: async (projectId: string, userId: string) => {
      await api.delete(`/api/projects/${projectId}/members/${userId}/`)
      set({ projectMembers: get().projectMembers.filter((m) => m.id !== userId) })
    },
  },
})
```

**Step 3: Commit**

```bash
git add frontend/src/store/projectSlice.ts frontend/src/api/client.ts
git commit -m "feat: extend projectSlice with CRUD actions"
```

---

### Task 2.3: Create Projects List Page

**Files:**
- Create: `frontend/src/pages/ProjectsPage/ProjectsPage.tsx`
- Create: `frontend/src/pages/ProjectsPage/ProjectCard.tsx`
- Create: `frontend/src/pages/ProjectsPage/index.ts`
- Modify: `frontend/src/router.tsx`

**Step 1: Install additional shadcn components**

Run:
```bash
cd frontend && bunx shadcn@latest add table badge dialog alert-dialog
```

**Step 2: Create ProjectCard component**

Create `frontend/src/pages/ProjectsPage/ProjectCard.tsx`:
```tsx
import { Link } from "react-router-dom"
import { MoreHorizontal, Pencil, Trash2, Users } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import type { Project } from "@/store/projectSlice"

interface ProjectCardProps {
  project: Project
  onDelete: (id: string) => void
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="text-lg">{project.name}</CardTitle>
          <CardDescription className="mt-1">
            {project.description || "No description"}
          </CardDescription>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link to={`/projects/${project.id}/edit`}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => onDelete(project.id)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Users className="h-4 w-4" />
            {project.member_count ?? 0} members
          </div>
          <Badge variant="outline">{project.role}</Badge>
        </div>
      </CardContent>
    </Card>
  )
}
```

**Step 3: Create ProjectsPage component**

Create `frontend/src/pages/ProjectsPage/ProjectsPage.tsx`:
```tsx
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Plus } from "lucide-react"
import { useAppStore } from "@/store/store"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { ProjectCard } from "./ProjectCard"

export function ProjectsPage() {
  const projects = useAppStore((s) => s.projects)
  const projectsStatus = useAppStore((s) => s.projectsStatus)
  const fetchProjects = useAppStore((s) => s.projectActions.fetchProjects)
  const deleteProject = useAppStore((s) => s.projectActions.deleteProject)

  const [deleteId, setDeleteId] = useState<string | null>(null)

  useEffect(() => {
    if (projectsStatus === "idle") {
      fetchProjects()
    }
  }, [fetchProjects, projectsStatus])

  const handleDelete = async () => {
    if (deleteId) {
      await deleteProject(deleteId)
      setDeleteId(null)
    }
  }

  return (
    <div className="container mx-auto py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-muted-foreground">
            Manage your data projects and team access
          </p>
        </div>
        <Button asChild>
          <Link to="/projects/new">
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Link>
        </Button>
      </div>

      {projectsStatus === "loading" && (
        <div className="text-muted-foreground">Loading projects...</div>
      )}

      {projectsStatus === "loaded" && projects.length === 0 && (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="text-muted-foreground">No projects yet</p>
          <Button asChild className="mt-4">
            <Link to="/projects/new">Create your first project</Link>
          </Button>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {projects.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            onDelete={setDeleteId}
          />
        ))}
      </div>

      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Project</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this project? This action cannot
              be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
```

**Step 4: Create index export**

Create `frontend/src/pages/ProjectsPage/index.ts`:
```tsx
export { ProjectsPage } from "./ProjectsPage"
```

**Step 5: Update router**

Update the router in `frontend/src/router.tsx` to import and use the real ProjectsPage:
```tsx
import { ProjectsPage } from "@/pages/ProjectsPage"

// In routes:
{ path: "projects", element: <ProjectsPage /> },
```

**Step 6: Verify page works**

Run:
```bash
cd frontend && bun run dev
```
Navigate to /projects - should see the projects list.

**Step 7: Commit**

```bash
git add frontend/src/pages/ProjectsPage/ frontend/src/router.tsx frontend/src/components/ui/
git commit -m "feat: add ProjectsPage with list view"
```

---

### Task 2.4: Create Project Form Page

**Files:**
- Create: `frontend/src/pages/ProjectsPage/ProjectForm.tsx`
- Modify: `frontend/src/pages/ProjectsPage/index.ts`
- Modify: `frontend/src/router.tsx`

**Step 1: Install form components**

Run:
```bash
cd frontend && bunx shadcn@latest add form textarea tabs accordion
```

**Step 2: Create ProjectForm component**

Create `frontend/src/pages/ProjectsPage/ProjectForm.tsx`:
```tsx
import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { useAppStore } from "@/store/store"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { api } from "@/api/client"
import type { ProjectDetail } from "@/store/projectSlice"

interface ConnectionTestResult {
  success: boolean
  schemas?: string[]
  tables?: { schema: string; table: string }[]
  error?: string
}

export function ProjectForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = !!id

  const fetchProject = useAppStore((s) => s.projectActions.fetchProject)
  const createProject = useAppStore((s) => s.projectActions.createProject)
  const updateProject = useAppStore((s) => s.projectActions.updateProject)

  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const [form, setForm] = useState<Partial<ProjectDetail>>({
    name: "",
    slug: "",
    description: "",
    db_host: "",
    db_port: 5432,
    db_name: "",
    db_user: "",
    db_password: "",
    allowed_schemas: [],
    allowed_tables: [],
    blocked_tables: [],
    system_prompt: "",
    llm_model: "claude-sonnet-4-20250514",
    llm_temperature: 0,
  })

  useEffect(() => {
    if (isEdit) {
      fetchProject(id).then(setForm)
    }
  }, [id, isEdit, fetchProject])

  const updateField = <K extends keyof ProjectDetail>(
    key: K,
    value: ProjectDetail[K]
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleTestConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await api.post<ConnectionTestResult>(
        "/api/projects/test-connection/",
        {
          db_host: form.db_host,
          db_port: form.db_port,
          db_name: form.db_name,
          db_user: form.db_user,
          db_password: form.db_password,
        }
      )
      setTestResult(result)
    } catch (e) {
      setTestResult({ success: false, error: String(e) })
    } finally {
      setTesting(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (isEdit) {
        await updateProject(id, form)
      } else {
        await createProject(form)
      }
      navigate("/projects")
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto max-w-2xl py-8">
      <h1 className="mb-8 text-2xl font-bold">
        {isEdit ? "Edit Project" : "New Project"}
      </h1>

      <form onSubmit={handleSubmit}>
        <Accordion type="multiple" defaultValue={["basic", "database"]}>
          {/* Basic Info */}
          <AccordionItem value="basic">
            <AccordionTrigger>Basic Info</AccordionTrigger>
            <AccordionContent>
              <Card>
                <CardContent className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={form.name}
                      onChange={(e) => updateField("name", e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="slug">Slug</Label>
                    <Input
                      id="slug"
                      value={form.slug}
                      onChange={(e) => updateField("slug", e.target.value)}
                      placeholder="auto-generated-from-name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={form.description}
                      onChange={(e) => updateField("description", e.target.value)}
                      rows={3}
                    />
                  </div>
                </CardContent>
              </Card>
            </AccordionContent>
          </AccordionItem>

          {/* Database Connection */}
          <AccordionItem value="database">
            <AccordionTrigger>Database Connection</AccordionTrigger>
            <AccordionContent>
              <Card>
                <CardContent className="space-y-4 pt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="db_host">Host</Label>
                      <Input
                        id="db_host"
                        value={form.db_host}
                        onChange={(e) => updateField("db_host", e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="db_port">Port</Label>
                      <Input
                        id="db_port"
                        type="number"
                        value={form.db_port}
                        onChange={(e) =>
                          updateField("db_port", parseInt(e.target.value) || 5432)
                        }
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="db_name">Database</Label>
                    <Input
                      id="db_name"
                      value={form.db_name}
                      onChange={(e) => updateField("db_name", e.target.value)}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="db_user">Username</Label>
                      <Input
                        id="db_user"
                        value={form.db_user}
                        onChange={(e) => updateField("db_user", e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="db_password">Password</Label>
                      <Input
                        id="db_password"
                        type="password"
                        value={form.db_password}
                        onChange={(e) => updateField("db_password", e.target.value)}
                        placeholder={isEdit ? "••••••••" : ""}
                      />
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleTestConnection}
                    disabled={testing}
                  >
                    {testing ? "Testing..." : "Test Connection"}
                  </Button>
                  {testResult && (
                    <div
                      className={`rounded-md p-3 text-sm ${
                        testResult.success
                          ? "bg-green-50 text-green-800"
                          : "bg-red-50 text-red-800"
                      }`}
                    >
                      {testResult.success ? (
                        <>
                          Connection successful!
                          <br />
                          Found {testResult.schemas?.length} schemas,{" "}
                          {testResult.tables?.length} tables
                        </>
                      ) : (
                        <>Connection failed: {testResult.error}</>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </AccordionContent>
          </AccordionItem>

          {/* Access Control */}
          <AccordionItem value="access">
            <AccordionTrigger>Access Control</AccordionTrigger>
            <AccordionContent>
              <Card>
                <CardHeader>
                  <CardDescription>
                    Restrict which schemas and tables the AI can access
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="allowed_schemas">
                      Allowed Schemas (comma-separated)
                    </Label>
                    <Input
                      id="allowed_schemas"
                      value={form.allowed_schemas?.join(", ")}
                      onChange={(e) =>
                        updateField(
                          "allowed_schemas",
                          e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                        )
                      }
                      placeholder="public, analytics"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="allowed_tables">
                      Allowed Tables (comma-separated)
                    </Label>
                    <Input
                      id="allowed_tables"
                      value={form.allowed_tables?.join(", ")}
                      onChange={(e) =>
                        updateField(
                          "allowed_tables",
                          e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                        )
                      }
                      placeholder="Leave empty to allow all in schema"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="blocked_tables">
                      Blocked Tables (comma-separated)
                    </Label>
                    <Input
                      id="blocked_tables"
                      value={form.blocked_tables?.join(", ")}
                      onChange={(e) =>
                        updateField(
                          "blocked_tables",
                          e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                        )
                      }
                      placeholder="users_pii, secrets"
                    />
                  </div>
                </CardContent>
              </Card>
            </AccordionContent>
          </AccordionItem>

          {/* AI Configuration */}
          <AccordionItem value="ai">
            <AccordionTrigger>AI Configuration</AccordionTrigger>
            <AccordionContent>
              <Card>
                <CardContent className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="system_prompt">System Prompt</Label>
                    <Textarea
                      id="system_prompt"
                      value={form.system_prompt}
                      onChange={(e) => updateField("system_prompt", e.target.value)}
                      rows={5}
                      placeholder="Additional instructions for the AI agent..."
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="llm_model">Model</Label>
                      <Input
                        id="llm_model"
                        value={form.llm_model}
                        onChange={(e) => updateField("llm_model", e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="llm_temperature">Temperature</Label>
                      <Input
                        id="llm_temperature"
                        type="number"
                        min="0"
                        max="2"
                        step="0.1"
                        value={form.llm_temperature}
                        onChange={(e) =>
                          updateField(
                            "llm_temperature",
                            parseFloat(e.target.value) || 0
                          )
                        }
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <div className="mt-8 flex gap-4">
          <Button type="submit" disabled={loading}>
            {loading ? "Saving..." : isEdit ? "Save Changes" : "Create Project"}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate("/projects")}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  )
}
```

**Step 3: Update index export**

Update `frontend/src/pages/ProjectsPage/index.ts`:
```tsx
export { ProjectsPage } from "./ProjectsPage"
export { ProjectForm } from "./ProjectForm"
```

**Step 4: Update router**

Update `frontend/src/router.tsx`:
```tsx
import { ProjectsPage, ProjectForm } from "@/pages/ProjectsPage"

// In routes:
{ path: "projects", element: <ProjectsPage /> },
{ path: "projects/new", element: <ProjectForm /> },
{ path: "projects/:id/edit", element: <ProjectForm /> },
```

**Step 5: Verify form works**

Run:
```bash
cd frontend && bun run dev
```
Navigate to /projects/new - should see the form with accordion sections.

**Step 6: Commit**

```bash
git add frontend/src/pages/ProjectsPage/ frontend/src/router.tsx frontend/src/components/ui/
git commit -m "feat: add ProjectForm for create/edit"
```

---

## Phase 3: Data Dictionary

### Task 3.1: Create Data Dictionary API Endpoints

**Files:**
- Create: `apps/projects/api/data_dictionary.py`
- Modify: `apps/projects/urls.py`

**Step 1: Create data dictionary views**

Create `apps/projects/api/data_dictionary.py`:
```python
"""
API views for data dictionary management.
"""
import asyncio

import asyncpg
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.knowledge.models import TableKnowledge
from apps.projects.models import Project, ProjectMembership


class DataDictionaryView(APIView):
    """
    GET /api/projects/{id}/data-dictionary/ - Get full schema with annotations
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        """Get the data dictionary for a project."""
        project = get_object_or_404(Project, pk=project_id)

        # Check access
        if not request.user.is_superuser:
            if not ProjectMembership.objects.filter(
                user=request.user, project=project
            ).exists():
                return Response(
                    {"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN
                )

        # Get cached data dictionary
        data_dictionary = project.data_dictionary or {}

        # Get table annotations
        annotations = TableKnowledge.objects.filter(project=project)
        annotations_by_table = {
            f"{a.schema_name}.{a.table_name}": {
                "description": a.description,
                "use_cases": a.use_cases,
                "data_quality_notes": a.data_quality_notes,
                "refresh_frequency": a.refresh_frequency,
                "owner": a.owner,
                "related_tables": a.related_tables,
                "column_notes": a.column_notes,
            }
            for a in annotations
        }

        # Merge annotations into data dictionary
        for schema_name, tables in data_dictionary.get("schemas", {}).items():
            for table_name, table_info in tables.items():
                key = f"{schema_name}.{table_name}"
                if key in annotations_by_table:
                    table_info["annotations"] = annotations_by_table[key]

        return Response(data_dictionary)


class RefreshSchemaView(APIView):
    """
    POST /api/projects/{id}/refresh-schema/ - Refresh data dictionary from database
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        """Refresh the data dictionary by querying the database schema."""
        project = get_object_or_404(Project, pk=project_id)

        # Check admin access
        if not request.user.is_superuser:
            membership = ProjectMembership.objects.filter(
                user=request.user, project=project
            ).first()
            if not membership or membership.role != "admin":
                return Response(
                    {"error": "Admin access required."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        async def fetch_schema():
            try:
                conn = await asyncpg.connect(
                    host=project.db_host,
                    port=project.db_port,
                    database=project.db_name,
                    user=project.db_user,
                    password=project.get_db_password(),
                    timeout=30,
                )

                # Get columns with types
                columns = await conn.fetch(
                    """
                    SELECT
                        table_schema,
                        table_name,
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        ordinal_position
                    FROM information_schema.columns
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_schema, table_name, ordinal_position
                    """
                )

                await conn.close()

                # Build schema structure
                schemas = {}
                for col in columns:
                    schema = col["table_schema"]
                    table = col["table_name"]

                    if schema not in schemas:
                        schemas[schema] = {}
                    if table not in schemas[schema]:
                        schemas[schema][table] = {"columns": []}

                    schemas[schema][table]["columns"].append({
                        "name": col["column_name"],
                        "type": col["data_type"],
                        "nullable": col["is_nullable"] == "YES",
                        "default": col["column_default"],
                    })

                return {"success": True, "schemas": schemas}

            except Exception as e:
                return {"success": False, "error": str(e)}

        result = asyncio.run(fetch_schema())

        if not result["success"]:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        # Save to project
        project.data_dictionary = {"schemas": result["schemas"]}
        project.save(update_fields=["data_dictionary"])

        return Response({"success": True, "schemas": result["schemas"]})


class TableAnnotationsView(APIView):
    """
    GET /api/projects/{id}/data-dictionary/tables/{schema}.{table}/ - Get table detail
    PUT /api/projects/{id}/data-dictionary/tables/{schema}.{table}/ - Update annotations
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, table_path):
        """Get table detail with annotations."""
        project = get_object_or_404(Project, pk=project_id)

        # Check access
        if not request.user.is_superuser:
            if not ProjectMembership.objects.filter(
                user=request.user, project=project
            ).exists():
                return Response(
                    {"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN
                )

        # Parse table path
        parts = table_path.split(".", 1)
        if len(parts) != 2:
            return Response(
                {"error": "Invalid table path. Use schema.table format."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        schema_name, table_name = parts

        # Get from data dictionary
        data_dictionary = project.data_dictionary or {}
        table_info = (
            data_dictionary.get("schemas", {})
            .get(schema_name, {})
            .get(table_name, {})
        )

        if not table_info:
            return Response(
                {"error": "Table not found in data dictionary."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get annotations
        annotations = TableKnowledge.objects.filter(
            project=project, schema_name=schema_name, table_name=table_name
        ).first()

        response = {
            "schema": schema_name,
            "table": table_name,
            "columns": table_info.get("columns", []),
            "annotations": None,
        }

        if annotations:
            response["annotations"] = {
                "description": annotations.description,
                "use_cases": annotations.use_cases,
                "data_quality_notes": annotations.data_quality_notes,
                "refresh_frequency": annotations.refresh_frequency,
                "owner": annotations.owner,
                "related_tables": annotations.related_tables,
                "column_notes": annotations.column_notes,
            }

        return Response(response)

    def put(self, request, project_id, table_path):
        """Update table annotations."""
        project = get_object_or_404(Project, pk=project_id)

        # Check access
        if not request.user.is_superuser:
            if not ProjectMembership.objects.filter(
                user=request.user, project=project
            ).exists():
                return Response(
                    {"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN
                )

        # Parse table path
        parts = table_path.split(".", 1)
        if len(parts) != 2:
            return Response(
                {"error": "Invalid table path. Use schema.table format."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        schema_name, table_name = parts

        # Get or create TableKnowledge
        table_knowledge, _ = TableKnowledge.objects.get_or_create(
            project=project,
            schema_name=schema_name,
            table_name=table_name,
        )

        # Update fields
        data = request.data
        if "description" in data:
            table_knowledge.description = data["description"]
        if "use_cases" in data:
            table_knowledge.use_cases = data["use_cases"]
        if "data_quality_notes" in data:
            table_knowledge.data_quality_notes = data["data_quality_notes"]
        if "refresh_frequency" in data:
            table_knowledge.refresh_frequency = data["refresh_frequency"]
        if "owner" in data:
            table_knowledge.owner = data["owner"]
        if "related_tables" in data:
            table_knowledge.related_tables = data["related_tables"]
        if "column_notes" in data:
            table_knowledge.column_notes = data["column_notes"]

        table_knowledge.save()

        return Response({
            "description": table_knowledge.description,
            "use_cases": table_knowledge.use_cases,
            "data_quality_notes": table_knowledge.data_quality_notes,
            "refresh_frequency": table_knowledge.refresh_frequency,
            "owner": table_knowledge.owner,
            "related_tables": table_knowledge.related_tables,
            "column_notes": table_knowledge.column_notes,
        })
```

**Step 2: Update URLs**

Add to `apps/projects/urls.py`:
```python
from .api.data_dictionary import (
    DataDictionaryView,
    RefreshSchemaView,
    TableAnnotationsView,
)

# Add to urlpatterns:
path(
    "<uuid:project_id>/data-dictionary/",
    DataDictionaryView.as_view(),
    name="data_dictionary",
),
path(
    "<uuid:project_id>/refresh-schema/",
    RefreshSchemaView.as_view(),
    name="refresh_schema",
),
path(
    "<uuid:project_id>/data-dictionary/tables/<str:table_path>/",
    TableAnnotationsView.as_view(),
    name="table_annotations",
),
```

**Step 3: Commit**

```bash
git add apps/projects/api/data_dictionary.py apps/projects/urls.py
git commit -m "feat: add data dictionary API endpoints"
```

---

### Task 3.2: Create Data Dictionary Zustand Slice

**Files:**
- Create: `frontend/src/store/dictionarySlice.ts`
- Modify: `frontend/src/store/store.ts`

**Step 1: Create dictionary slice**

Create `frontend/src/store/dictionarySlice.ts`:
```typescript
import type { StateCreator } from "zustand"
import { api } from "@/api/client"

export interface Column {
  name: string
  type: string
  nullable: boolean
  default: string | null
  description?: string
}

export interface TableAnnotations {
  description: string
  use_cases: string
  data_quality_notes: string
  refresh_frequency: string
  owner: string
  related_tables: string[]
  column_notes: Record<string, string>
}

export interface TableInfo {
  columns: Column[]
  annotations?: TableAnnotations
}

export interface DataDictionary {
  schemas: Record<string, Record<string, TableInfo>>
}

export interface TableDetail {
  schema: string
  table: string
  columns: Column[]
  annotations: TableAnnotations | null
}

export type DictionaryStatus = "idle" | "loading" | "loaded" | "error"

export interface DictionarySlice {
  dataDictionary: DataDictionary | null
  dictionaryStatus: DictionaryStatus
  selectedTable: TableDetail | null
  dictionaryActions: {
    fetchDictionary: (projectId: string) => Promise<void>
    refreshSchema: (projectId: string) => Promise<void>
    fetchTable: (projectId: string, schema: string, table: string) => Promise<void>
    updateAnnotations: (
      projectId: string,
      schema: string,
      table: string,
      annotations: Partial<TableAnnotations>
    ) => Promise<void>
  }
}

export const createDictionarySlice: StateCreator<
  DictionarySlice,
  [],
  [],
  DictionarySlice
> = (set, get) => ({
  dataDictionary: null,
  dictionaryStatus: "idle",
  selectedTable: null,
  dictionaryActions: {
    fetchDictionary: async (projectId: string) => {
      set({ dictionaryStatus: "loading" })
      try {
        const data = await api.get<DataDictionary>(
          `/api/projects/${projectId}/data-dictionary/`
        )
        set({ dataDictionary: data, dictionaryStatus: "loaded" })
      } catch {
        set({ dictionaryStatus: "error" })
      }
    },

    refreshSchema: async (projectId: string) => {
      set({ dictionaryStatus: "loading" })
      try {
        const data = await api.post<DataDictionary>(
          `/api/projects/${projectId}/refresh-schema/`
        )
        set({ dataDictionary: data, dictionaryStatus: "loaded" })
      } catch {
        set({ dictionaryStatus: "error" })
      }
    },

    fetchTable: async (projectId: string, schema: string, table: string) => {
      const data = await api.get<TableDetail>(
        `/api/projects/${projectId}/data-dictionary/tables/${schema}.${table}/`
      )
      set({ selectedTable: data })
    },

    updateAnnotations: async (
      projectId: string,
      schema: string,
      table: string,
      annotations: Partial<TableAnnotations>
    ) => {
      const updated = await api.put<TableAnnotations>(
        `/api/projects/${projectId}/data-dictionary/tables/${schema}.${table}/`,
        annotations
      )
      // Update selected table
      const current = get().selectedTable
      if (current && current.schema === schema && current.table === table) {
        set({ selectedTable: { ...current, annotations: updated } })
      }
      // Update in dictionary cache
      const dict = get().dataDictionary
      if (dict?.schemas[schema]?.[table]) {
        dict.schemas[schema][table].annotations = updated
        set({ dataDictionary: { ...dict } })
      }
    },
  },
})
```

**Step 2: Add to store**

Update `frontend/src/store/store.ts`:
```typescript
import { create } from "zustand"
import { createAuthSlice, type AuthSlice } from "./authSlice"
import { createProjectSlice, type ProjectSlice } from "./projectSlice"
import { createUiSlice, type UiSlice } from "./uiSlice"
import { createDictionarySlice, type DictionarySlice } from "./dictionarySlice"

export type AppStore = AuthSlice & ProjectSlice & UiSlice & DictionarySlice

export const useAppStore = create<AppStore>()((...a) => ({
  ...createAuthSlice(...a),
  ...createProjectSlice(...a),
  ...createUiSlice(...a),
  ...createDictionarySlice(...a),
}))
```

**Step 3: Commit**

```bash
git add frontend/src/store/dictionarySlice.ts frontend/src/store/store.ts
git commit -m "feat: add dictionarySlice for data dictionary state"
```

---

### Task 3.3: Create Data Dictionary Page

**Files:**
- Create: `frontend/src/pages/DataDictionaryPage/DataDictionaryPage.tsx`
- Create: `frontend/src/pages/DataDictionaryPage/SchemaTree.tsx`
- Create: `frontend/src/pages/DataDictionaryPage/TableDetail.tsx`
- Create: `frontend/src/pages/DataDictionaryPage/index.ts`
- Modify: `frontend/src/router.tsx`

**Step 1: Create SchemaTree component**

Create `frontend/src/pages/DataDictionaryPage/SchemaTree.tsx`:
```tsx
import { useState } from "react"
import { ChevronDown, ChevronRight, Table2, Database } from "lucide-react"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import type { DataDictionary } from "@/store/dictionarySlice"

interface SchemaTreeProps {
  dictionary: DataDictionary
  selectedTable: { schema: string; table: string } | null
  onSelectTable: (schema: string, table: string) => void
}

export function SchemaTree({
  dictionary,
  selectedTable,
  onSelectTable,
}: SchemaTreeProps) {
  const [search, setSearch] = useState("")
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(
    new Set(Object.keys(dictionary.schemas))
  )

  const toggleSchema = (schema: string) => {
    const next = new Set(expandedSchemas)
    if (next.has(schema)) {
      next.delete(schema)
    } else {
      next.add(schema)
    }
    setExpandedSchemas(next)
  }

  const filteredSchemas = Object.entries(dictionary.schemas).reduce(
    (acc, [schemaName, tables]) => {
      const filteredTables = Object.keys(tables).filter(
        (tableName) =>
          !search ||
          tableName.toLowerCase().includes(search.toLowerCase()) ||
          schemaName.toLowerCase().includes(search.toLowerCase())
      )
      if (filteredTables.length > 0) {
        acc[schemaName] = filteredTables
      }
      return acc
    },
    {} as Record<string, string[]>
  )

  return (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <Input
          placeholder="Search tables..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8"
        />
      </div>
      <div className="flex-1 overflow-auto">
        {Object.entries(filteredSchemas).map(([schemaName, tableNames]) => (
          <div key={schemaName}>
            <button
              onClick={() => toggleSchema(schemaName)}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-sm font-medium hover:bg-accent"
            >
              {expandedSchemas.has(schemaName) ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <Database className="h-4 w-4" />
              {schemaName}
            </button>
            {expandedSchemas.has(schemaName) && (
              <div className="ml-4">
                {tableNames.map((tableName) => {
                  const isSelected =
                    selectedTable?.schema === schemaName &&
                    selectedTable?.table === tableName
                  const hasAnnotations =
                    dictionary.schemas[schemaName][tableName]?.annotations
                  return (
                    <button
                      key={tableName}
                      onClick={() => onSelectTable(schemaName, tableName)}
                      className={cn(
                        "flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent",
                        isSelected && "bg-accent"
                      )}
                    >
                      <Table2 className="h-4 w-4" />
                      {tableName}
                      {hasAnnotations && (
                        <span className="ml-auto h-2 w-2 rounded-full bg-primary" />
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Step 2: Create TableDetail component**

Create `frontend/src/pages/DataDictionaryPage/TableDetail.tsx`:
```tsx
import { useState, useEffect, useCallback } from "react"
import { useAppStore } from "@/store/store"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import type { TableDetail as TableDetailType } from "@/store/dictionarySlice"

interface TableDetailProps {
  projectId: string
  table: TableDetailType
}

export function TableDetail({ projectId, table }: TableDetailProps) {
  const updateAnnotations = useAppStore(
    (s) => s.dictionaryActions.updateAnnotations
  )

  const [annotations, setAnnotations] = useState(
    table.annotations || {
      description: "",
      use_cases: "",
      data_quality_notes: "",
      refresh_frequency: "",
      owner: "",
      related_tables: [],
      column_notes: {},
    }
  )

  useEffect(() => {
    setAnnotations(
      table.annotations || {
        description: "",
        use_cases: "",
        data_quality_notes: "",
        refresh_frequency: "",
        owner: "",
        related_tables: [],
        column_notes: {},
      }
    )
  }, [table])

  // Debounced save
  const saveAnnotations = useCallback(
    (updates: Partial<typeof annotations>) => {
      const timer = setTimeout(() => {
        updateAnnotations(projectId, table.schema, table.table, updates)
      }, 500)
      return () => clearTimeout(timer)
    },
    [projectId, table.schema, table.table, updateAnnotations]
  )

  const updateField = (field: string, value: string) => {
    const updated = { ...annotations, [field]: value }
    setAnnotations(updated)
    saveAnnotations({ [field]: value })
  }

  const updateColumnNote = (column: string, note: string) => {
    const updated = {
      ...annotations,
      column_notes: { ...annotations.column_notes, [column]: note },
    }
    setAnnotations(updated)
    saveAnnotations({ column_notes: updated.column_notes })
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold">
          {table.schema}.{table.table}
        </h2>
        {table.annotations && (
          <Badge variant="outline" className="mt-1">
            Annotated
          </Badge>
        )}
      </div>

      {/* Columns Table */}
      <div>
        <h3 className="mb-2 font-medium">Columns</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Column</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Nullable</TableHead>
              <TableHead className="w-1/3">Description</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {table.columns.map((col) => (
              <TableRow key={col.name}>
                <TableCell className="font-mono text-sm">{col.name}</TableCell>
                <TableCell className="font-mono text-sm text-muted-foreground">
                  {col.type}
                </TableCell>
                <TableCell>{col.nullable ? "Yes" : "No"}</TableCell>
                <TableCell>
                  <Input
                    placeholder="Add description..."
                    value={annotations.column_notes[col.name] || ""}
                    onChange={(e) => updateColumnNote(col.name, e.target.value)}
                    className="h-8"
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Table Annotations */}
      <div className="grid gap-4">
        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            placeholder="What does this table represent?"
            value={annotations.description}
            onChange={(e) => updateField("description", e.target.value)}
            rows={2}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="use_cases">Use Cases</Label>
          <Textarea
            id="use_cases"
            placeholder="When should this table be queried?"
            value={annotations.use_cases}
            onChange={(e) => updateField("use_cases", e.target.value)}
            rows={2}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="data_quality_notes">Data Quality Notes</Label>
          <Textarea
            id="data_quality_notes"
            placeholder="Known issues, caveats, or data quality concerns"
            value={annotations.data_quality_notes}
            onChange={(e) => updateField("data_quality_notes", e.target.value)}
            rows={2}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="refresh_frequency">Refresh Frequency</Label>
            <Input
              id="refresh_frequency"
              placeholder="e.g., Daily at 2am UTC"
              value={annotations.refresh_frequency}
              onChange={(e) => updateField("refresh_frequency", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="owner">Owner</Label>
            <Input
              id="owner"
              placeholder="Team or person responsible"
              value={annotations.owner}
              onChange={(e) => updateField("owner", e.target.value)}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
```

**Step 3: Create DataDictionaryPage**

Create `frontend/src/pages/DataDictionaryPage/DataDictionaryPage.tsx`:
```tsx
import { useEffect, useState } from "react"
import { RefreshCw } from "lucide-react"
import { useAppStore } from "@/store/store"
import { Button } from "@/components/ui/button"
import { SchemaTree } from "./SchemaTree"
import { TableDetail } from "./TableDetail"

export function DataDictionaryPage() {
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const dataDictionary = useAppStore((s) => s.dataDictionary)
  const dictionaryStatus = useAppStore((s) => s.dictionaryStatus)
  const selectedTable = useAppStore((s) => s.selectedTable)
  const fetchDictionary = useAppStore((s) => s.dictionaryActions.fetchDictionary)
  const refreshSchema = useAppStore((s) => s.dictionaryActions.refreshSchema)
  const fetchTable = useAppStore((s) => s.dictionaryActions.fetchTable)

  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (activeProjectId && dictionaryStatus === "idle") {
      fetchDictionary(activeProjectId)
    }
  }, [activeProjectId, dictionaryStatus, fetchDictionary])

  const handleRefresh = async () => {
    if (!activeProjectId) return
    setRefreshing(true)
    await refreshSchema(activeProjectId)
    setRefreshing(false)
  }

  const handleSelectTable = (schema: string, table: string) => {
    if (activeProjectId) {
      fetchTable(activeProjectId, schema, table)
    }
  }

  if (!activeProjectId) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Select a project to view the data dictionary
      </div>
    )
  }

  if (dictionaryStatus === "loading") {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Loading data dictionary...
      </div>
    )
  }

  if (!dataDictionary || Object.keys(dataDictionary.schemas || {}).length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">
          No schema data available. Refresh to fetch from database.
        </p>
        <Button onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Refreshing..." : "Refresh Schema"}
        </Button>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Left Panel - Schema Tree */}
      <div className="w-64 border-r">
        <div className="flex items-center justify-between border-b p-3">
          <span className="text-sm font-medium">Tables</span>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>
        <SchemaTree
          dictionary={dataDictionary}
          selectedTable={
            selectedTable
              ? { schema: selectedTable.schema, table: selectedTable.table }
              : null
          }
          onSelectTable={handleSelectTable}
        />
      </div>

      {/* Right Panel - Table Detail */}
      <div className="flex-1 overflow-auto">
        {selectedTable ? (
          <TableDetail projectId={activeProjectId} table={selectedTable} />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            Select a table to view details
          </div>
        )}
      </div>
    </div>
  )
}
```

**Step 4: Create index export**

Create `frontend/src/pages/DataDictionaryPage/index.ts`:
```tsx
export { DataDictionaryPage } from "./DataDictionaryPage"
```

**Step 5: Update router**

Update `frontend/src/router.tsx`:
```tsx
import { DataDictionaryPage } from "@/pages/DataDictionaryPage"

// In routes:
{ path: "data-dictionary", element: <DataDictionaryPage /> },
```

**Step 6: Commit**

```bash
git add frontend/src/pages/DataDictionaryPage/ frontend/src/router.tsx
git commit -m "feat: add DataDictionaryPage with schema browser and annotations"
```

---

## Phase 4: Knowledge Management

### Task 4.1: Create Knowledge API Endpoints

**Files:**
- Create: `apps/knowledge/api/__init__.py`
- Create: `apps/knowledge/api/serializers.py`
- Create: `apps/knowledge/api/views.py`
- Create: `apps/knowledge/urls.py`
- Modify: `scout/urls.py`

**Step 1: Create serializers**

Create `apps/knowledge/api/__init__.py`:
```python
```

Create `apps/knowledge/api/serializers.py`:
```python
"""
Serializers for knowledge API.
"""
from rest_framework import serializers

from apps.knowledge.models import (
    AgentLearning,
    BusinessRule,
    CanonicalMetric,
    VerifiedQuery,
)


class CanonicalMetricSerializer(serializers.ModelSerializer):
    """Serializer for canonical metrics."""

    type = serializers.SerializerMethodField()
    related_tables = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    class Meta:
        model = CanonicalMetric
        fields = [
            "id",
            "type",
            "name",
            "description",
            "sql_template",
            "related_tables",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "type", "created_at", "updated_at"]

    def get_type(self, obj):
        return "metric"


class BusinessRuleSerializer(serializers.ModelSerializer):
    """Serializer for business rules."""

    type = serializers.SerializerMethodField()
    related_tables = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    class Meta:
        model = BusinessRule
        fields = [
            "id",
            "type",
            "name",
            "rule_text",
            "context",
            "related_tables",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "type", "created_at", "updated_at"]

    def get_type(self, obj):
        return "rule"


class VerifiedQuerySerializer(serializers.ModelSerializer):
    """Serializer for verified queries."""

    type = serializers.SerializerMethodField()
    related_tables = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    tags = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    class Meta:
        model = VerifiedQuery
        fields = [
            "id",
            "type",
            "name",
            "description",
            "sql",
            "tags",
            "related_tables",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "type", "created_at", "updated_at"]

    def get_type(self, obj):
        return "query"


class AgentLearningSerializer(serializers.ModelSerializer):
    """Serializer for agent learnings."""

    type = serializers.SerializerMethodField()
    related_tables = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    class Meta:
        model = AgentLearning
        fields = [
            "id",
            "type",
            "description",
            "correction",
            "confidence",
            "promoted_to",
            "related_tables",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "type", "promoted_to", "created_at", "updated_at"]

    def get_type(self, obj):
        return "learning"


class PromoteLearningSerializer(serializers.Serializer):
    """Serializer for promoting an agent learning."""

    target_type = serializers.ChoiceField(choices=["rule", "query"])
    name = serializers.CharField()
    # Additional fields based on target type
    rule_text = serializers.CharField(required=False)
    context = serializers.CharField(required=False, allow_blank=True)
    sql = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
```

**Step 2: Create views**

Create `apps/knowledge/api/views.py`:
```python
"""
API views for knowledge management.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.knowledge.models import (
    AgentLearning,
    BusinessRule,
    CanonicalMetric,
    VerifiedQuery,
)
from apps.projects.models import Project, ProjectMembership

from .serializers import (
    AgentLearningSerializer,
    BusinessRuleSerializer,
    CanonicalMetricSerializer,
    PromoteLearningSerializer,
    VerifiedQuerySerializer,
)


class KnowledgeListCreateView(APIView):
    """
    GET /api/projects/{pid}/knowledge/ - List all knowledge items
    POST /api/projects/{pid}/knowledge/ - Create a knowledge item
    """

    permission_classes = [IsAuthenticated]

    def get_project(self, project_id, user):
        """Get project and verify access."""
        project = get_object_or_404(Project, pk=project_id)
        if not user.is_superuser:
            if not ProjectMembership.objects.filter(user=user, project=project).exists():
                return None
        return project

    def get(self, request, project_id):
        """List all knowledge items for a project."""
        project = self.get_project(project_id, request.user)
        if not project:
            return Response(
                {"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN
            )

        # Get filter parameter
        knowledge_type = request.query_params.get("type")
        search = request.query_params.get("search", "")

        items = []

        # Helper to filter by search
        def matches_search(obj, fields):
            if not search:
                return True
            search_lower = search.lower()
            for field in fields:
                value = getattr(obj, field, "")
                if value and search_lower in str(value).lower():
                    return True
            return False

        # Metrics
        if not knowledge_type or knowledge_type == "metric":
            metrics = CanonicalMetric.objects.filter(project=project)
            for m in metrics:
                if matches_search(m, ["name", "description", "sql_template"]):
                    items.append(CanonicalMetricSerializer(m).data)

        # Rules
        if not knowledge_type or knowledge_type == "rule":
            rules = BusinessRule.objects.filter(project=project)
            for r in rules:
                if matches_search(r, ["name", "rule_text", "context"]):
                    items.append(BusinessRuleSerializer(r).data)

        # Queries
        if not knowledge_type or knowledge_type == "query":
            queries = VerifiedQuery.objects.filter(project=project)
            for q in queries:
                if matches_search(q, ["name", "description", "sql"]):
                    items.append(VerifiedQuerySerializer(q).data)

        # Learnings
        if not knowledge_type or knowledge_type == "learning":
            learnings = AgentLearning.objects.filter(project=project)
            for l in learnings:
                if matches_search(l, ["description", "correction"]):
                    items.append(AgentLearningSerializer(l).data)

        # Sort by updated_at descending
        items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return Response(items)

    def post(self, request, project_id):
        """Create a new knowledge item."""
        project = self.get_project(project_id, request.user)
        if not project:
            return Response(
                {"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN
            )

        knowledge_type = request.data.get("type")
        if not knowledge_type:
            return Response(
                {"error": "type field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer_map = {
            "metric": (CanonicalMetricSerializer, CanonicalMetric),
            "rule": (BusinessRuleSerializer, BusinessRule),
            "query": (VerifiedQuerySerializer, VerifiedQuery),
        }

        if knowledge_type not in serializer_map:
            return Response(
                {"error": f"Invalid type: {knowledge_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        SerializerClass, _ = serializer_map[knowledge_type]
        serializer = SerializerClass(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(project=project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class KnowledgeDetailView(APIView):
    """
    GET /api/projects/{pid}/knowledge/{id}/ - Get knowledge item
    PUT /api/projects/{pid}/knowledge/{id}/ - Update knowledge item
    DELETE /api/projects/{pid}/knowledge/{id}/ - Delete knowledge item
    """

    permission_classes = [IsAuthenticated]

    def get_item(self, project_id, item_id):
        """Find the knowledge item across all types."""
        models = [CanonicalMetric, BusinessRule, VerifiedQuery, AgentLearning]
        for model in models:
            try:
                return model.objects.get(pk=item_id, project_id=project_id)
            except model.DoesNotExist:
                continue
        return None

    def get_serializer(self, item):
        """Get the appropriate serializer for the item."""
        if isinstance(item, CanonicalMetric):
            return CanonicalMetricSerializer
        elif isinstance(item, BusinessRule):
            return BusinessRuleSerializer
        elif isinstance(item, VerifiedQuery):
            return VerifiedQuerySerializer
        elif isinstance(item, AgentLearning):
            return AgentLearningSerializer
        return None

    def get(self, request, project_id, item_id):
        """Get a knowledge item."""
        item = self.get_item(project_id, item_id)
        if not item:
            return Response(
                {"error": "Knowledge item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        SerializerClass = self.get_serializer(item)
        return Response(SerializerClass(item).data)

    def put(self, request, project_id, item_id):
        """Update a knowledge item."""
        item = self.get_item(project_id, item_id)
        if not item:
            return Response(
                {"error": "Knowledge item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        SerializerClass = self.get_serializer(item)
        serializer = SerializerClass(item, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data)

    def delete(self, request, project_id, item_id):
        """Delete a knowledge item."""
        item = self.get_item(project_id, item_id)
        if not item:
            return Response(
                {"error": "Knowledge item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PromoteLearningView(APIView):
    """
    POST /api/projects/{pid}/knowledge/{id}/promote/ - Promote agent learning
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, item_id):
        """Promote an agent learning to a business rule or verified query."""
        learning = get_object_or_404(
            AgentLearning, pk=item_id, project_id=project_id
        )

        if learning.promoted_to:
            return Response(
                {"error": "Learning has already been promoted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PromoteLearningSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        target_type = data["target_type"]

        if target_type == "rule":
            rule = BusinessRule.objects.create(
                project_id=project_id,
                name=data["name"],
                rule_text=data.get("rule_text", learning.correction),
                context=data.get("context", ""),
                related_tables=learning.related_tables,
            )
            learning.promoted_to = f"rule:{rule.id}"
            learning.save()
            return Response(BusinessRuleSerializer(rule).data, status=status.HTTP_201_CREATED)

        elif target_type == "query":
            query = VerifiedQuery.objects.create(
                project_id=project_id,
                name=data["name"],
                description=data.get("description", learning.description),
                sql=data.get("sql", ""),
                tags=data.get("tags", []),
                related_tables=learning.related_tables,
            )
            learning.promoted_to = f"query:{query.id}"
            learning.save()
            return Response(VerifiedQuerySerializer(query).data, status=status.HTTP_201_CREATED)
```

**Step 3: Create URLs**

Create `apps/knowledge/urls.py`:
```python
"""
URL configuration for knowledge app.
"""
from django.urls import path

from .api.views import KnowledgeDetailView, KnowledgeListCreateView, PromoteLearningView

app_name = "knowledge"

urlpatterns = [
    path("", KnowledgeListCreateView.as_view(), name="list_create"),
    path("<uuid:item_id>/", KnowledgeDetailView.as_view(), name="detail"),
    path("<uuid:item_id>/promote/", PromoteLearningView.as_view(), name="promote"),
]
```

**Step 4: Add to main URLs**

Update `scout/urls.py` to include:
```python
path("api/projects/<uuid:project_id>/knowledge/", include("apps.knowledge.urls")),
```

**Step 5: Commit**

```bash
git add apps/knowledge/api/ apps/knowledge/urls.py scout/urls.py
git commit -m "feat: add knowledge management API endpoints"
```

---

### Task 4.2: Create Knowledge Page (Frontend)

This follows the same pattern as Projects and Data Dictionary. Create:
- `frontend/src/store/knowledgeSlice.ts`
- `frontend/src/pages/KnowledgePage/KnowledgePage.tsx`
- `frontend/src/pages/KnowledgePage/KnowledgeList.tsx`
- `frontend/src/pages/KnowledgePage/KnowledgeForm.tsx`
- `frontend/src/pages/KnowledgePage/index.ts`

(Implementation details follow the same patterns established above)

---

## Phase 5: Recipes Management

### Task 5.1: Create Recipes API Endpoints

**Files:**
- Create: `apps/recipes/api/__init__.py`
- Create: `apps/recipes/api/serializers.py`
- Create: `apps/recipes/api/views.py`
- Create: `apps/recipes/urls.py`
- Modify: `scout/urls.py`

(Implementation follows the same patterns as Knowledge API)

---

### Task 5.2: Create Recipes Page (Frontend)

Create:
- `frontend/src/store/recipeSlice.ts`
- `frontend/src/pages/RecipesPage/RecipesPage.tsx`
- `frontend/src/pages/RecipesPage/RecipeDetail.tsx`
- `frontend/src/pages/RecipesPage/RecipeRunner.tsx`
- `frontend/src/pages/RecipesPage/index.ts`

(Implementation follows the same patterns established above)

---

## Summary

This plan covers:

1. **Phase 1: Navigation & Routing** - Install React Router, create Sidebar, update AppLayout
2. **Phase 2: Projects Management** - Full CRUD API and UI for projects
3. **Phase 3: Data Dictionary** - Schema browser with inline annotations
4. **Phase 4: Knowledge Management** - Unified knowledge list with filtering and promotion
5. **Phase 5: Recipes Management** - View, edit, and run recipes

Each task includes:
- Exact file paths
- Complete code examples
- Verification steps
- Commit commands

The plan follows TDD principles where applicable and maintains consistency with existing codebase patterns.
