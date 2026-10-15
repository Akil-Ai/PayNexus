"""Reconciliation worker.
Periodically queries rail simulator settlement endpoints, ingests statement files,
and executes automated reconciliation matching and exception classification.
"""
import asyncio
import uuid
import httpx
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.database import AsyncSessionLocal
from app.models import ReconRun, ReconFile
from app.services.recon_service import parse_csv_statement, run_reconciliation

logger = get_logger(__name__)
settings = get_settings()


async def poll_rail_statements():
    """Polls rail simulators for daily settlement files and triggers reconciliation."""
    rails = [
        {"code": "UPI", "url": settings.RAIL_UPI_URL},
        {"code": "NEFT", "url": settings.RAIL_NEFT_URL},
    ]

    for r in rails:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"{r['url']}/settlement-file")
                if resp.status_code == 200:
                    csv_content = resp.text
                    records = parse_csv_statement(csv_content)
                    if records:
                        logger.info(f"Ingested {len(records)} records from {r['code']} statement endpoint")
                        async with AsyncSessionLocal() as db:
                            run_id = str(uuid.uuid4())
                            recon_run = ReconRun(
                                id=run_id,
                                rail=r["code"],
                                status="RUNNING",
                                total_records=len(records),
                                created_at=datetime.now(timezone.utc)
                            )
                            db.add(recon_run)
                            await db.commit()

                            await run_reconciliation(
                                db=db,
                                recon_run_id=run_id,
                                rail_code=r["code"],
                                statement_records=records,
                                auto_resolve=True,
                                actor_id="RECON_CRON_WORKER"
                            )
                            await db.commit()
        except Exception as exc:
            logger.debug(f"Could not poll settlement file for {r['code']}: {exc}")


async def main():
    setup_logging()
    logger.info("Reconciliation worker started.")
    poll_interval = 60  # Poll every 60 seconds

    while True:
        try:
            await poll_rail_statements()
            await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            break
        except Exception as err:
            logger.error(f"Reconciliation worker loop error: {err}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
