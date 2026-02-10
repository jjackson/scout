"""
CommCare Connect data connector.

Implements the connector interface for CommCare Connect's export API.
Uses OAuth 2.0 for authentication.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

import psycopg2
import requests

from apps.datasources.models import DataSourceType

from .base import BaseConnector, DatasetInfo, SyncResult, TokenResult
from .registry import register_connector

if TYPE_CHECKING:
    from apps.datasources.models import DataSourceCredential

logger = logging.getLogger(__name__)


@register_connector(DataSourceType.COMMCARE_CONNECT)
@dataclass
class CommCareConnectConnector(BaseConnector):
    """
    Connector for CommCare Connect export API.

    CommCare Connect provides CSV exports for various data types including:
    - Opportunities
    - User data
    - Completed works
    - Payments
    - Assessments
    - Completed modules
    """

    base_url: str
    client_id: str
    client_secret: str

    # OAuth endpoints (relative to base_url)
    AUTHORIZE_PATH = "/o/authorize/"
    TOKEN_PATH = "/o/token/"

    # Export API endpoints
    OPPORTUNITIES_LIST_PATH = "/export/opp_org_program_list/"
    OPPORTUNITY_PATH = "/export/opportunity/{opp_id}/"
    USER_DATA_PATH = "/export/opportunity/{opp_id}/user_data/"
    COMPLETED_WORKS_PATH = "/export/opportunity/{opp_id}/completed_works/"
    PAYMENTS_PATH = "/export/opportunity/{opp_id}/payment/"
    ASSESSMENTS_PATH = "/export/opportunity/{opp_id}/assessment/"
    COMPLETED_MODULES_PATH = "/export/opportunity/{opp_id}/completed_module/"
    USER_VISITS_PATH = "/export/opportunity/{opp_id}/user_visits/"

    def get_oauth_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        scopes: list[str] | None = None,
    ) -> str:
        """Generate OAuth authorization URL for CommCare Connect."""
        if scopes is None:
            scopes = ["export"]  # Default scope for export API

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(scopes),
        }

        return f"{self.base_url}{self.AUTHORIZE_PATH}?{urlencode(params)}"

    def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> TokenResult:
        """Exchange authorization code for access and refresh tokens."""
        response = requests.post(
            f"{self.base_url}{self.TOKEN_PATH}",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        # Calculate expiration time
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        return TokenResult(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expires_at=expires_at,
            scopes=data.get("scope", "export").split(),
        )

    def refresh_access_token(self, refresh_token: str) -> TokenResult:
        """Refresh an expired access token."""
        response = requests.post(
            f"{self.base_url}{self.TOKEN_PATH}",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        return TokenResult(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_at=expires_at,
            scopes=data.get("scope", "export").split(),
        )

    def get_available_datasets(
        self,
        credential: DataSourceCredential,
        config: dict[str, Any] | None = None,
    ) -> list[DatasetInfo]:
        """
        Get available datasets from CommCare Connect.

        Returns datasets for each opportunity the user has access to.
        """
        access_token = credential.access_token

        # Get list of opportunities, organizations, and programs
        response = requests.get(
            f"{self.base_url}{self.OPPORTUNITIES_LIST_PATH}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60,
        )
        response.raise_for_status()

        data = response.json()
        datasets = []

        # Add program/org summary datasets
        datasets.append(DatasetInfo(
            name="organizations",
            description="Organizations data",
            estimated_rows=None,
        ))
        datasets.append(DatasetInfo(
            name="programs",
            description="Programs data",
            estimated_rows=None,
        ))
        datasets.append(DatasetInfo(
            name="opportunities",
            description="Opportunities summary",
            estimated_rows=None,
        ))

        # For each opportunity, add the detailed export datasets
        opportunities = data.get("opportunities", [])
        if isinstance(opportunities, dict):
            opportunities = [opportunities]

        for opp in opportunities:
            opp_id = opp.get("id")
            opp_name = opp.get("name", f"Opportunity {opp_id}")

            datasets.extend([
                DatasetInfo(
                    name=f"opportunity_{opp_id}_user_data",
                    description=f"User data for {opp_name}",
                    estimated_rows=None,
                ),
                DatasetInfo(
                    name=f"opportunity_{opp_id}_completed_works",
                    description=f"Completed works for {opp_name}",
                    estimated_rows=None,
                ),
                DatasetInfo(
                    name=f"opportunity_{opp_id}_payments",
                    description=f"Payments for {opp_name}",
                    estimated_rows=None,
                ),
                DatasetInfo(
                    name=f"opportunity_{opp_id}_user_visits",
                    description=f"User visits for {opp_name}",
                    estimated_rows=None,
                ),
            ])

        return datasets

    def sync_dataset(
        self,
        credential: DataSourceCredential,
        dataset_name: str,
        schema_name: str,
        config: dict[str, Any] | None = None,
        progress_callback: Any | None = None,
        cursor: dict[str, Any] | None = None,
    ) -> SyncResult:
        """
        Sync data from CommCare Connect to local PostgreSQL.

        Syncs all available data for the configured opportunities.
        """
        access_token = credential.access_token
        rows_synced: dict[str, int] = {}
        db_config = config.get("database", {}) if config else {}

        try:
            # Connect to the database
            conn = psycopg2.connect(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", 5432),
                dbname=db_config.get("name", "scout"),
                user=db_config.get("user", "scout"),
                password=db_config.get("password", ""),
            )
            conn.autocommit = False
            cur = conn.cursor()

            # Create schema if it doesn't exist
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")

            # Fetch and sync the org/program/opportunity list
            list_response = requests.get(
                f"{self.base_url}{self.OPPORTUNITIES_LIST_PATH}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=60,
            )
            list_response.raise_for_status()
            list_data = list_response.json()

            # Sync organizations
            org_count = self._sync_organizations(cur, schema_name, list_data)
            rows_synced["organizations"] = org_count

            # Sync programs
            prog_count = self._sync_programs(cur, schema_name, list_data)
            rows_synced["programs"] = prog_count

            # Sync opportunities summary
            opp_count = self._sync_opportunities(cur, schema_name, list_data)
            rows_synced["opportunities"] = opp_count

            # Get opportunity IDs for detailed exports
            opportunities = list_data.get("opportunities", [])
            if isinstance(opportunities, dict):
                opportunities = [opportunities]

            # Sync detailed data for each opportunity
            for opp in opportunities:
                opp_id = opp.get("id")
                if not opp_id:
                    continue

                if progress_callback:
                    progress_callback(f"Syncing opportunity {opp_id}")

                # Sync user data
                try:
                    user_count = self._sync_csv_endpoint(
                        cur, schema_name, access_token,
                        self.USER_DATA_PATH.format(opp_id=opp_id),
                        f"opportunity_{opp_id}_user_data",
                        opp_id,
                    )
                    rows_synced[f"opportunity_{opp_id}_user_data"] = user_count
                except requests.HTTPError as e:
                    logger.warning(f"Failed to sync user data for opp {opp_id}: {e}")

                # Sync completed works
                try:
                    works_count = self._sync_csv_endpoint(
                        cur, schema_name, access_token,
                        self.COMPLETED_WORKS_PATH.format(opp_id=opp_id),
                        f"opportunity_{opp_id}_completed_works",
                        opp_id,
                    )
                    rows_synced[f"opportunity_{opp_id}_completed_works"] = works_count
                except requests.HTTPError as e:
                    logger.warning(f"Failed to sync completed works for opp {opp_id}: {e}")

                # Sync payments
                try:
                    payments_count = self._sync_csv_endpoint(
                        cur, schema_name, access_token,
                        self.PAYMENTS_PATH.format(opp_id=opp_id),
                        f"opportunity_{opp_id}_payments",
                        opp_id,
                    )
                    rows_synced[f"opportunity_{opp_id}_payments"] = payments_count
                except requests.HTTPError as e:
                    logger.warning(f"Failed to sync payments for opp {opp_id}: {e}")

                # Sync user visits
                try:
                    visits_count = self._sync_csv_endpoint(
                        cur, schema_name, access_token,
                        self.USER_VISITS_PATH.format(opp_id=opp_id),
                        f"opportunity_{opp_id}_user_visits",
                        opp_id,
                    )
                    rows_synced[f"opportunity_{opp_id}_user_visits"] = visits_count
                except requests.HTTPError as e:
                    logger.warning(f"Failed to sync user visits for opp {opp_id}: {e}")

            conn.commit()
            cur.close()
            conn.close()

            return SyncResult(
                success=True,
                rows_synced=rows_synced,
            )

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                # Rate limited - return pause cursor
                retry_after = int(e.response.headers.get("Retry-After", 60))
                return SyncResult(
                    success=False,
                    rows_synced=rows_synced,
                    error="Rate limited",
                    cursor={"retry_after": retry_after, "rows_synced": rows_synced},
                )
            return SyncResult(
                success=False,
                rows_synced=rows_synced,
                error=str(e),
            )
        except Exception as e:
            logger.exception("Error syncing CommCare Connect data")
            return SyncResult(
                success=False,
                rows_synced=rows_synced,
                error=str(e),
            )

    def _sync_organizations(
        self,
        cur: Any,
        schema_name: str,
        data: dict[str, Any],
    ) -> int:
        """Sync organizations data."""
        organizations = data.get("organizations", [])
        if isinstance(organizations, dict):
            organizations = [organizations]

        if not organizations:
            return 0

        # Create table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.organizations (
                id INTEGER PRIMARY KEY,
                slug TEXT,
                name TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Clear and insert
        cur.execute(f"DELETE FROM {schema_name}.organizations")

        for org in organizations:
            cur.execute(f"""
                INSERT INTO {schema_name}.organizations (id, slug, name)
                VALUES (%s, %s, %s)
            """, (org.get("id"), org.get("slug"), org.get("name")))

        return len(organizations)

    def _sync_programs(
        self,
        cur: Any,
        schema_name: str,
        data: dict[str, Any],
    ) -> int:
        """Sync programs data."""
        programs = data.get("programs", [])
        if isinstance(programs, dict):
            programs = [programs]

        if not programs:
            return 0

        # Create table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.programs (
                id INTEGER PRIMARY KEY,
                name TEXT,
                delivery_type TEXT,
                currency TEXT,
                organization TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Clear and insert
        cur.execute(f"DELETE FROM {schema_name}.programs")

        for prog in programs:
            cur.execute(f"""
                INSERT INTO {schema_name}.programs (id, name, delivery_type, currency, organization)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                prog.get("id"),
                prog.get("name"),
                prog.get("delivery_type"),
                prog.get("currency"),
                prog.get("organization"),
            ))

        return len(programs)

    def _sync_opportunities(
        self,
        cur: Any,
        schema_name: str,
        data: dict[str, Any],
    ) -> int:
        """Sync opportunities summary data."""
        opportunities = data.get("opportunities", [])
        if isinstance(opportunities, dict):
            opportunities = [opportunities]

        if not opportunities:
            return 0

        # Create table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.opportunities (
                id INTEGER PRIMARY KEY,
                name TEXT,
                organization TEXT,
                program INTEGER,
                end_date DATE,
                is_active TEXT,
                visit_count INTEGER,
                date_created TIMESTAMP,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Clear and insert
        cur.execute(f"DELETE FROM {schema_name}.opportunities")

        for opp in opportunities:
            cur.execute(f"""
                INSERT INTO {schema_name}.opportunities
                (id, name, organization, program, end_date, is_active, visit_count, date_created)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                opp.get("id"),
                opp.get("name"),
                opp.get("organization"),
                opp.get("program"),
                opp.get("end_date"),
                opp.get("is_active"),
                opp.get("visit_count"),
                opp.get("date_created"),
            ))

        return len(opportunities)

    def _sync_csv_endpoint(
        self,
        cur: Any,
        schema_name: str,
        access_token: str,
        endpoint_path: str,
        table_name: str,
        opp_id: int,
    ) -> int:
        """
        Sync a CSV endpoint to a database table.

        CommCare Connect export endpoints return CSV data.
        """
        response = requests.get(
            f"{self.base_url}{endpoint_path}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=120,
        )
        response.raise_for_status()

        # Parse CSV response
        csv_content = response.text
        if not csv_content.strip():
            return 0

        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        if not rows:
            return 0

        # Get column names from first row
        columns = list(rows[0].keys())

        # Sanitize column names for SQL
        safe_columns = [self._sanitize_column_name(col) for col in columns]

        # Create table with all columns as TEXT (simple approach)
        col_defs = ", ".join(f'"{col}" TEXT' for col in safe_columns)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}."{table_name}" (
                {col_defs},
                opportunity_id INTEGER,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Clear existing data for this opportunity
        cur.execute(
            f'DELETE FROM {schema_name}."{table_name}" WHERE opportunity_id = %s',
            (opp_id,)
        )

        # Insert rows
        col_names = ", ".join(f'"{col}"' for col in safe_columns)
        placeholders = ", ".join(["%s"] * len(safe_columns))

        for row in rows:
            values = [row.get(col, "") for col in columns]
            cur.execute(
                f'INSERT INTO {schema_name}."{table_name}" ({col_names}, opportunity_id) '
                f'VALUES ({placeholders}, %s)',
                values + [opp_id]
            )

        return len(rows)

    def _sanitize_column_name(self, name: str) -> str:
        """Sanitize column name for use in SQL."""
        # Replace spaces and special chars with underscores
        sanitized = name.lower().replace(" ", "_").replace("-", "_")
        # Remove any remaining non-alphanumeric chars (except underscore)
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"col_{sanitized}"
        return sanitized or "unnamed"
