# Security

Scout implements multiple layers of security to protect data and prevent abuse.

## SQL validation

All queries pass through the `SQLValidator` before execution. The validator uses [sqlglot](https://github.com/tobymao/sqlglot) for AST-level analysis:

### SELECT only

Only `SELECT` statements are allowed. Any query containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, or other non-SELECT statements is rejected.

### Single statement

Only one SQL statement per request is allowed. Multi-statement queries (separated by semicolons) are blocked.

### Dangerous function blocking

PostgreSQL functions that could be used for data exfiltration or system access are blocked:

- **File system access** -- `pg_read_file`, `pg_read_binary_file`, `pg_ls_dir`, `pg_stat_file`, etc.
- **Large object manipulation** -- `lo_import`, `lo_export`, `lo_create`, etc.
- **Remote database access** -- `dblink` and related functions.
- **Command execution** -- any function that could execute system commands.
- **Copy operations** -- `COPY` statements are blocked.

### Table access enforcement

The validator checks that every table referenced in the query is allowed by the project's table access configuration (allowlist/blocklist). Queries referencing disallowed tables are rejected before execution.

### Automatic LIMIT injection

If a query does not include a `LIMIT` clause, one is automatically added based on the project's `max_rows_per_query` setting (default: 500).

## Database isolation

### Encrypted credentials

Project database credentials (username and password) are encrypted at rest using Fernet symmetric encryption. The encryption key is stored in the `DB_CREDENTIAL_KEY` environment variable, never in the database.

### Read-only connections

Database connections use a read-only role (when configured) and set the PostgreSQL `search_path` to the project's configured schema, preventing access to other schemas.

### Statement timeout

Each connection sets a `statement_timeout` based on the project's `max_query_timeout_seconds` setting (default: 30 seconds). Long-running queries are automatically terminated.

### Connection pooling

Database connections are pooled per-project with a configurable maximum (`MAX_CONNECTIONS_PER_PROJECT`, default: 5).

## Rate limiting

### Login rate limiting

Login attempts are rate-limited per email address: 5 attempts within 5 minutes triggers a lockout. The counter resets on successful login.

### Query rate limiting

Query execution is rate-limited per user at `MAX_QUERIES_PER_MINUTE` (default: 60 queries per minute).

## Session security

- **Session cookies** -- authentication uses HTTP-only session cookies (not JWT).
- **CSRF protection** -- all mutating requests require a valid CSRF token. The SPA reads the token from a non-HTTP-only CSRF cookie.
- **Allowed hosts** -- `DJANGO_ALLOWED_HOSTS` restricts which host headers are accepted.
- **Trusted origins** -- `CSRF_TRUSTED_ORIGINS` restricts which origins can make cross-origin requests.

## Schema name validation

Database schema names are validated with a regex pattern (`^[a-zA-Z_][a-zA-Z0-9_]*$`) to prevent SQL injection through schema names.
