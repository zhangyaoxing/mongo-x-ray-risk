"""
Copyright (c) 2025 MongoDB Inc.

DISCLAIMER: THESE CODE SAMPLES ARE PROVIDED FOR EDUCATIONAL AND ILLUSTRATIVE PURPOSES ONLY,
TO DEMONSTRATE THE FUNCTIONALITY OF SPECIFIC MONGODB FEATURES.
THEY ARE NOT PRODUCTION-READY AND MAY LACK THE SECURITY HARDENING, ERROR HANDLING, AND TESTING REQUIRED FOR A LIVE ENVIRONMENT.
YOU ARE RESPONSIBLE FOR TESTING, VALIDATING, AND SECURING THIS CODE WITHIN YOUR OWN ENVIRONMENT BEFORE IMPLEMENTATION.
THIS MATERIAL IS PROVIDED "AS IS" WITHOUT WARRANTY OR LIABILITY.
"""

import logging
from pathlib import Path

from mongo_x_ray.plugin import Plugin

from mongo_x_ray_risk import clear_risks, ingest_risks, load_risks_from_csv

logger = logging.getLogger(__name__)


class IngestPlugin(Plugin):
    name = "ingest"
    distribution = "mongo-x-ray-risk"
    help = "Ingest a risk register CSV into the risk knowledge base"
    description = """
Ingest a risk register CSV into the ChromaDB-backed risk knowledge base used
by the analysis plugins (healthcheck, log, gmd) to match findings against
known risks.

The CSV must have the following columns:
  ID, Risk level, Impact, Name, Risk description

Header names are matched case-insensitively; any other columns (e.g.
Other Notes) are ignored. Rows without an ID or a Name are skipped. Existing
entries with the same ID are replaced; use --clear to start from an empty
register.

Run 'x-ray ingest --clear' alone to clear the register without a CSV.
"""
    epilog = """
Examples:
  x-ray ingest risk_register.csv
  x-ray ingest --clear risk_register.csv   # clear, then ingest
  x-ray ingest --clear                      # clear only
"""

    def add_arguments(self, parser):
        parser.add_argument("csv", nargs="?", help="Path to the risk register CSV file.")
        parser.add_argument(
            "--clear",
            help="Clear the existing risk register before ingesting.",
            action="store_true",
            default=False,
        )

    def run(self, args) -> int:
        """Clear the risk register and/or ingest a CSV, reporting what was done."""
        if not args.csv:
            if args.clear:
                clear_risks()
                logger.info("Cleared the existing risk register")
                return 0
            logger.error(
                "No CSV file given. Use 'x-ray ingest <csv>' to ingest, "
                "or 'x-ray ingest --clear' to clear the register."
            )
            return 1
        csv_path = Path(args.csv)
        if not csv_path.is_file():
            logger.error("CSV file not found: %s", csv_path)
            return 1
        try:
            risks = load_risks_from_csv(csv_path)
        except Exception as exc:
            logger.error("Failed to read CSV %s: %s", csv_path, exc)
            return 1
        if not risks:
            logger.error(
                "No valid risk rows found in %s (expected columns: ID, Risk level, Impact, Name, Risk description)",
                csv_path,
            )
            return 1
        if args.clear:
            clear_risks()
            logger.info("Cleared the existing risk register")
        count = ingest_risks(risks)
        logger.info("Ingested %d risks into the risk register", count)
        return 0
