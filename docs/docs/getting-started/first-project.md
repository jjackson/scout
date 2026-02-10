# Create your first project

A project in Scout represents a single database scope. Each project has its own database connection, agent configuration, table access controls, and knowledge base.

## Create a project

1. Open the Django admin at `http://localhost:8000/admin/`.
2. Navigate to **Projects > Projects** and click **Add Project**.
3. Fill in the required fields:

| Field | Description |
|-------|-------------|
| **Name** | Display name for the project (e.g., "Sales Analytics") |
| **Slug** | URL-safe identifier, auto-generated from name |
| **DB Host** | Hostname of the target PostgreSQL database |
| **DB Port** | Port number (default: 5432) |
| **DB Name** | Database name to connect to |
| **DB Schema** | Schema to query (default: `public`) |
| **DB User** | Username for the database connection (encrypted at rest) |
| **DB Password** | Password for the database connection (encrypted at rest) |

4. Click **Save**.

## Configure table access (optional)

By default, the agent can see all tables in the configured schema. To restrict access:

- **Allowed tables** -- JSON list of table names the agent can query. An empty list means all tables are visible.
- **Excluded tables** -- JSON list of table names to hide from the agent, even if they appear in the allowed list.

Example: to limit the agent to only `orders`, `customers`, and `products`:

```json
["orders", "customers", "products"]
```

## Generate the data dictionary

The data dictionary tells the agent what tables and columns exist. Generate it with:

```bash
uv run manage.py generate_data_dictionary --project-slug your-project-slug
```

This introspects the target database and stores the schema information on the project.

## Add team members

1. In the Django admin, navigate to **Projects > Project memberships**.
2. Click **Add Project Membership**.
3. Select the user, the project, and a role:

| Role | Permissions |
|------|-------------|
| **Viewer** | Chat with the agent and view results |
| **Analyst** | Chat, export data, create saved queries |
| **Admin** | Full project configuration access |

4. Click **Save**.

## Next step

[Start your first conversation](first-conversation.md) to ask the agent a question about your data.
