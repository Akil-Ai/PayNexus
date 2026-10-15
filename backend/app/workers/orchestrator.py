"""Entry point for orchestrator worker."""
import asyncio
from app.workers.orchestrator_worker import main

if __name__ == "__main__":
    asyncio.run(main())
