"""Single runner to start all mock simulators (UPI, NEFT, SWIFT, CARD, Sanctions, KYC) in one process."""
import asyncio
import importlib.util
import os
import sys
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_DIR = os.path.join(BASE_DIR, "mock-services")

def load_app(subdir: str):
    file_path = os.path.join(MOCK_DIR, subdir, "main.py")
    spec = importlib.util.spec_from_file_location(f"mock_{subdir.replace('-', '_')}", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.app

upi_app = load_app("rail-upi")
neft_app = load_app("rail-neft")
swift_app = load_app("rail-swift")
card_app = load_app("rail-card")
sanctions_app = load_app("sanctions")
kyc_app = load_app("kyc")

async def main():
    servers = [
        uvicorn.Server(uvicorn.Config(upi_app, host="127.0.0.1", port=8101, log_level="warning")),
        uvicorn.Server(uvicorn.Config(neft_app, host="127.0.0.1", port=8102, log_level="warning")),
        uvicorn.Server(uvicorn.Config(swift_app, host="127.0.0.1", port=8103, log_level="warning")),
        uvicorn.Server(uvicorn.Config(card_app, host="127.0.0.1", port=8104, log_level="warning")),
        uvicorn.Server(uvicorn.Config(sanctions_app, host="127.0.0.1", port=8201, log_level="warning")),
        uvicorn.Server(uvicorn.Config(kyc_app, host="127.0.0.1", port=8202, log_level="warning")),
    ]
    print("Starting all 6 mock services on ports 8101-8104, 8201, 8202...")
    await asyncio.gather(*(s.serve() for s in servers))

if __name__ == "__main__":
    asyncio.run(main())
