"""Entry point for reconciliation worker."""
import asyncio
from app.workers.recon_worker import main

if __name__ == "__main__":
    asyncio.run(main())
