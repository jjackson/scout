# Admin UI Design: Projects, Knowledge, Recipes, and Data Dictionary

## Overview

This design adds a comprehensive admin interface for power users to manage projects, knowledge, recipes, and data dictionary. The UI is accessed via a new sidebar navigation that scopes all management features under the selected project.

## Target Users

Admin/power users who set up and configure projects for others. The interface prioritizes power and flexibility over simplicity.

## Navigation Structure

### Sidebar Layout

```
┌─────────────────────────┐
│ [Scout Logo]            │
├─────────────────────────┤
│ Project: [Dropdown ▼]   │
│ ─────────────────────── │
│ + Manage Projects       │
├─────────────────────────┤
│ ● Chat                  │
│ ○ Knowledge             │
│ ○ Recipes               │
│ ○ Data Dictionary       │
├─────────────────────────┤
│                         │
│ [spacer]                │
│                         │
├─────────────────────────┤
│ user@email.com          │
│ Logout                  │
└─────────────────────────┘
```

### Behavior

- Sidebar is always visible (collapsible on mobile)
- Project dropdown at top for quick switching
- "Manage Projects" link opens full project management page
- Active section highlighted
- Chat remains the default/home view
- User info and logout at bottom

---

## Projects Management

**Access:** "Manage Projects" link in sidebar

### Projects List View

- Table/card list of all projects user has access to
- Columns: name, description (truncated), your role, member count, last activity
- Actions: Edit, Delete (with confirmation)
- "New Project" button at top

### Project Create/Edit Form

Organized into collapsible sections:

#### 1. Basic Info
- Name (required)
- Slug (auto-generated from name, editable)
- Description (textarea)

#### 2. Database Connection
- Host, Port, Database name, Username, Password
- "Test Connection" button
- Success shows: connection status + detected schema/tables

#### 3. Access Control
- Allowed schemas (multi-select from detected)
- Allowed tables (multi-select, filtered by schema)
- Blocked tables (for exclusions)

#### 4. AI Configuration
- System prompt (textarea with placeholder/example)
- LLM model selector (dropdown of available models)
- Model parameters (temperature, etc.)

#### 5. Team Members
- List current members with roles
- Add member (email + role selector)
- Remove/change role for existing members

---

## Knowledge Management

**Access:** "Knowledge" in sidebar

### Unified Knowledge View

Single searchable, filterable list of all knowledge items for the project.

#### Header Controls
- Search bar (searches across names, descriptions, content)
- Filter chips/dropdown for type: All, Metrics, Business Rules, Verified Queries, Agent Learnings
- "New" button with type selector dropdown

#### List Item Display

Each item shows:
- Type badge (color-coded)
  - Blue: Canonical Metric
  - Green: Business Rule
  - Purple: Verified Query
  - Yellow: Agent Learning
- Name/title
- Description (truncated)
- Related tables (as tags)
- Last updated
- For Agent Learnings: confidence score + "Promote" action

### Create/Edit Forms

Form fields vary by knowledge type:

| Type | Fields |
|------|--------|
| Canonical Metric | Name, description, SQL template, related tables |
| Business Rule | Name, rule text, context/examples, related tables |
| Verified Query | Name, description, SQL, tags, related tables |
| Agent Learning | (view/edit only) description, correction, confidence, promote action |

### Promote Flow (Agent Learnings)

1. Click "Promote" on an Agent Learning
2. Choose target type: Business Rule or Verified Query
3. Form pre-fills with learning content
4. On save: creates new knowledge item, marks learning as promoted

---

## Recipes Management

**Access:** "Recipes" in sidebar

### Recipes List View

- Cards or table showing all recipes for the project
- Columns: name, description, number of steps, variable count, last run date
- Actions: View/Edit, Run, Delete

### Recipe Detail/Edit View

#### Header Section
- Name (editable)
- Description (editable textarea)

#### Variables Section
- List of defined variables:
  - Name
  - Type (string, number, date, boolean, select)
  - Required flag
  - For select type: options list
  - Default value (optional)
- Add/remove/reorder variables

#### Steps Section
- Ordered list of steps (drag to reorder)
- Each step shows:
  - Step number
  - Prompt template (editable textarea)
  - Variables used (highlighted `{{variable}}` syntax)
  - Click variable name to insert at cursor
  - Remove step button
- Add step button at bottom

#### Run History Section (collapsible)
- Table of past runs: date, status (success/failed/running), duration, who ran it
- Click to expand: variable values used, step-by-step results

### Run Recipe Flow

1. Click "Run" button
2. Modal/slide-out appears with:
   - Form fields for each variable (type-appropriate inputs)
   - "Run" button
3. Shows progress as steps execute
4. Results displayed inline or links to chat thread

---

## Data Dictionary

**Access:** "Data Dictionary" in sidebar

### Layout

- Left panel: tree/list of schemas and tables
- Right panel: detail view for selected table

### Left Panel (Schema Browser)

```
[Search tables...]        [Refresh Schema]

▼ public
  ● users
    orders
    products
▼ analytics
    events
  ● sessions
```

- Expandable schema folders
- Tables listed alphabetically under each
- Search/filter box at top
- "Refresh Schema" button (re-syncs from database)
- Visual indicator (●) for tables with annotations

### Right Panel (Table Detail)

#### Header
- Table name + schema
- Row count (if available)
- "Annotated" badge if has custom metadata

#### Columns Table

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | no | Primary key *(auto)* |
| email | varchar(255) | no | *Click to add description* |
| created_at | timestamp | no | When the user signed up |

- Type and nullable from auto-generated schema
- Description is editable inline (click to edit)
- Italicized placeholder for unannotated columns

#### Table-Level Annotations

Below the columns table:

- **Description** - What this table represents (textarea)
- **Use Cases** - When to query this table (textarea)
- **Data Quality Notes** - Known issues, caveats (textarea)
- **Refresh Frequency** - How often data updates (text input)
- **Owner** - Team/person responsible (text input)
- **Related Tables** - Multi-select of other tables

All annotations auto-save (debounced) and create/update TableKnowledge records behind the scenes.

---

## Technical Implementation

### Backend API Endpoints

#### Projects

```
GET    /api/projects/                      - List user's projects
POST   /api/projects/                      - Create project
GET    /api/projects/{id}/                 - Get project detail
PUT    /api/projects/{id}/                 - Update project
DELETE /api/projects/{id}/                 - Delete project
POST   /api/projects/{id}/test-connection/ - Test DB connection
POST   /api/projects/{id}/refresh-schema/  - Refresh data dictionary
GET    /api/projects/{id}/members/         - List project members
POST   /api/projects/{id}/members/         - Add member
DELETE /api/projects/{id}/members/{uid}/   - Remove member
```

#### Knowledge

```
GET    /api/projects/{pid}/knowledge/              - List all knowledge (filterable)
POST   /api/projects/{pid}/knowledge/              - Create knowledge item
GET    /api/projects/{pid}/knowledge/{id}/         - Get knowledge detail
PUT    /api/projects/{pid}/knowledge/{id}/         - Update knowledge
DELETE /api/projects/{pid}/knowledge/{id}/         - Delete knowledge
POST   /api/projects/{pid}/knowledge/{id}/promote/ - Promote AgentLearning
```

#### Recipes

```
GET    /api/projects/{pid}/recipes/          - List recipes
POST   /api/projects/{pid}/recipes/          - Create recipe
GET    /api/projects/{pid}/recipes/{id}/     - Get recipe with steps
PUT    /api/projects/{pid}/recipes/{id}/     - Update recipe & steps
DELETE /api/projects/{pid}/recipes/{id}/     - Delete recipe
POST   /api/projects/{pid}/recipes/{id}/run/ - Execute recipe
GET    /api/projects/{pid}/recipes/{id}/runs/- List run history
```

#### Data Dictionary

```
GET    /api/projects/{pid}/data-dictionary/              - Get full schema with annotations
GET    /api/projects/{pid}/data-dictionary/tables/{t}/   - Get single table detail
PUT    /api/projects/{pid}/data-dictionary/tables/{t}/   - Update table annotations
```

### Frontend Components

#### New Components

```
src/components/
├── Sidebar/
│   ├── Sidebar.tsx
│   ├── ProjectSelector.tsx
│   └── NavItem.tsx
├── ProjectsPage/
│   ├── ProjectsList.tsx
│   ├── ProjectCard.tsx
│   └── ProjectForm.tsx
├── KnowledgePage/
│   ├── KnowledgeList.tsx
│   ├── KnowledgeFilters.tsx
│   ├── KnowledgeCard.tsx
│   └── KnowledgeForm.tsx
├── RecipesPage/
│   ├── RecipesList.tsx
│   ├── RecipeDetail.tsx
│   ├── RecipeStepEditor.tsx
│   ├── RecipeVariables.tsx
│   ├── RecipeRunner.tsx
│   └── RunHistory.tsx
└── DataDictionaryPage/
    ├── SchemaTree.tsx
    ├── TableDetail.tsx
    ├── ColumnsTable.tsx
    └── TableAnnotations.tsx
```

#### Zustand Store Extensions

```
src/store/
├── projectSlice.ts    - Extend with CRUD actions
├── knowledgeSlice.ts  - New: knowledge items state
├── recipeSlice.ts     - New: recipes state
└── dictionarySlice.ts - New: schema/annotations state
```

### Frontend Routes

```
/                           → Chat (default)
/projects                   → Projects list
/projects/new               → Create project
/projects/:id/edit          → Edit project
/knowledge                  → Knowledge list
/knowledge/new              → Create knowledge
/knowledge/:id              → Edit knowledge
/recipes                    → Recipes list
/recipes/:id                → Recipe detail/edit
/data-dictionary            → Data dictionary browser
```

---

## Implementation Order

Recommended phased approach:

### Phase 1: Navigation & Projects
1. Add sidebar navigation component
2. Implement React Router setup
3. Build projects list and CRUD
4. Add database connection testing

### Phase 2: Data Dictionary
1. Build schema browser UI
2. Implement refresh schema endpoint
3. Add inline column annotation
4. Add table-level annotations (creates TableKnowledge)

### Phase 3: Knowledge Management
1. Build unified knowledge list with filters
2. Implement type-specific forms
3. Add Agent Learning promotion flow

### Phase 4: Recipes
1. Build recipes list
2. Implement recipe detail/edit with step editor
3. Add recipe runner UI
4. Implement run history view
