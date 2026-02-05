"""
Management command to bulk import knowledge from JSON/YAML files.

Directory structure expected:
    knowledge/
    ├── tables/*.json       # TableKnowledge
    ├── metrics/*.json      # CanonicalMetric
    ├── queries/*.json      # VerifiedQuery
    ├── business/*.json     # BusinessRule
    └── golden/*.json       # GoldenQuery

Usage:
    # Import all knowledge for a project from a directory
    python manage.py import_knowledge --project-slug my-project --dir ./knowledge

    # Import only specific types
    python manage.py import_knowledge --project-slug my-project --dir ./knowledge --type tables

    # Recreate (delete existing before import)
    python manage.py import_knowledge --project-slug my-project --dir ./knowledge --recreate
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.knowledge.models import (
    BusinessRule,
    CanonicalMetric,
    GoldenQuery,
    TableKnowledge,
    VerifiedQuery,
)
from apps.projects.models import Project


class Command(BaseCommand):
    help = "Bulk import knowledge from JSON/YAML files"

    KNOWLEDGE_TYPES = {
        "tables": {
            "model": TableKnowledge,
            "dir": "tables",
            "unique_field": "table_name",
        },
        "metrics": {
            "model": CanonicalMetric,
            "dir": "metrics",
            "unique_field": "name",
        },
        "queries": {
            "model": VerifiedQuery,
            "dir": "queries",
            "unique_field": "name",
        },
        "business": {
            "model": BusinessRule,
            "dir": "business",
            "unique_field": "title",
        },
        "golden": {
            "model": GoldenQuery,
            "dir": "golden",
            "unique_field": "question",
        },
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-slug",
            type=str,
            required=True,
            help="Project slug to import knowledge for",
        )
        parser.add_argument(
            "--dir",
            type=str,
            required=True,
            help="Directory containing knowledge files",
        )
        parser.add_argument(
            "--type",
            type=str,
            choices=list(self.KNOWLEDGE_TYPES.keys()),
            help="Import only a specific type of knowledge",
        )
        parser.add_argument(
            "--recreate",
            action="store_true",
            help="Delete existing knowledge before importing",
        )

    def handle(self, *args, **options):
        # Get project
        try:
            project = Project.objects.get(slug=options["project_slug"])
        except Project.DoesNotExist:
            raise CommandError(f"Project with slug '{options['project_slug']}' not found")

        knowledge_dir = Path(options["dir"])
        if not knowledge_dir.exists():
            raise CommandError(f"Directory '{knowledge_dir}' does not exist")

        # Determine which types to import
        if options["type"]:
            types_to_import = {options["type"]: self.KNOWLEDGE_TYPES[options["type"]]}
        else:
            types_to_import = self.KNOWLEDGE_TYPES

        # Import each type
        for type_name, config in types_to_import.items():
            type_dir = knowledge_dir / config["dir"]
            if not type_dir.exists():
                self.stdout.write(f"  Skipping {type_name}: directory not found")
                continue

            model = config["model"]
            unique_field = config["unique_field"]

            # Delete existing if --recreate
            if options["recreate"]:
                deleted, _ = model.objects.filter(project=project).delete()
                self.stdout.write(f"  Deleted {deleted} existing {type_name}")

            # Import files
            created = 0
            updated = 0
            for json_file in type_dir.glob("*.json"):
                try:
                    with open(json_file) as f:
                        data = json.load(f)

                    # Handle both single object and list of objects
                    items = data if isinstance(data, list) else [data]

                    for item in items:
                        # Add project reference
                        item["project"] = project

                        # Set verified_at for queries if not present
                        if type_name == "queries" and "verified_at" not in item:
                            item["verified_at"] = timezone.now()

                        # Upsert
                        unique_value = item.get(unique_field)
                        if unique_value:
                            obj, was_created = model.objects.update_or_create(
                                project=project,
                                **{unique_field: unique_value},
                                defaults={
                                    k: v
                                    for k, v in item.items()
                                    if k != unique_field and k != "project"
                                },
                            )
                            if was_created:
                                created += 1
                            else:
                                updated += 1
                        else:
                            model.objects.create(**item)
                            created += 1

                except json.JSONDecodeError as e:
                    self.stderr.write(
                        self.style.ERROR(f"    Invalid JSON in {json_file}: {e}")
                    )
                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f"    Error importing {json_file}: {e}")
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  {type_name}: created {created}, updated {updated}"
                )
            )
