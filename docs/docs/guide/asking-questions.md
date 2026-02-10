# Asking questions

Scout translates natural language questions into SQL queries. The quality of the results depends on how you phrase your questions and the knowledge available to the agent.

## Tips for good questions

### Be specific about what you want

Instead of "show me some data", ask "show me the top 10 customers by total order amount in the last 30 days". The more specific your question, the more accurate the SQL will be.

### Name tables and columns when you know them

If you know the table or column names, include them: "What is the average `order_total` from the `orders` table?" This reduces ambiguity and helps the agent generate correct SQL on the first try.

### Specify time ranges explicitly

"Last month's revenue" is ambiguous -- does it mean the last 30 days, or the previous calendar month? Be explicit: "Total revenue for January 2026" or "Total revenue for the last 30 days".

### Ask follow-up questions

Conversations are persistent. After getting an initial result, you can ask follow-ups:

- "Break that down by region"
- "Now show only the top 5"
- "Can you chart that?"
- "Exclude cancelled orders"

The agent remembers the context from earlier in the conversation.

### Request specific output formats

You can ask for specific formats:

- "Show me a bar chart of monthly revenue"
- "Create a dashboard comparing this quarter to last quarter"
- "Give me a table sorted by date descending"

## What the agent knows

The agent has access to:

- **Data dictionary** -- auto-generated schema documentation listing all visible tables, columns, and their types.
- **Table knowledge** -- human-written descriptions of what tables mean, use cases, and data quality notes.
- **Canonical metrics** -- agreed-upon definitions for metrics like MRR, DAU, or churn rate.
- **Verified queries** -- query patterns known to produce correct results.
- **Business rules** -- institutional knowledge and gotchas (e.g., "amounts are in cents, not dollars").
- **Agent learnings** -- corrections the agent has discovered from previous errors.

The more knowledge you add to a project, the better the agent's answers become.

## Limitations

- The agent can only run **SELECT** queries. It cannot insert, update, or delete data.
- Results are limited to a configurable maximum number of rows (default: 500).
- Queries have a timeout (default: 30 seconds).
- Some PostgreSQL functions are blocked for security reasons (file access, remote connections, etc.).
