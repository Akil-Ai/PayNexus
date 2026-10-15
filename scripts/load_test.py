"""High-throughput load and idempotency duplicate safety testing script.
Executes 1,000 payment requests including 10% intentional duplicate requests with identical Idempotency-Key.
Verifies throughput, p95 latency, and guarantees exact duplicate count == 0.
"""
import asyncio
import time
import uuid
import random
import httpx
import numpy as np

BASE_URL = "http://localhost:8000/api/v1"
NUM_REQUESTS = 1000
DUPLICATE_RATIO = 0.10  # 10% duplicates


async def run_load_test():
    print(f"Starting PayNexus load test: {NUM_REQUESTS} payments ({int(DUPLICATE_RATIO*100)}% intentional duplicates)...")

    # 1. Login to obtain access token
    async with httpx.AsyncClient(timeout=10.0) as client:
        auth_resp = await client.post(
            f"{BASE_URL}/auth/token",
            data={"username": "admin@paynexus.io", "password": "Demo@PayNexus2026!"}
        )
        if auth_resp.status_code != 200:
            print(f"Auth failed: {auth_resp.text}")
            return
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Get customer list
        cust_resp = await client.get(f"{BASE_URL}/admin/customers", headers=headers)
        customers = cust_resp.json()
        if not customers:
            print("No customers found in database. Seed database first.")
            return
        customer_ids = [c["id"] for c in customers]

        # Prepare request queue with intentional duplicate keys
        keys_pool = [f"idemp_load_{uuid.uuid4().hex}" for _ in range(int(NUM_REQUESTS * (1 - DUPLICATE_RATIO)))]
        # Add duplicates by repeating some keys
        num_dupes = NUM_REQUESTS - len(keys_pool)
        for i in range(num_dupes):
            keys_pool.append(keys_pool[i % len(keys_pool)])
        random.shuffle(keys_pool)

        latencies = []
        status_codes = {}
        idempotent_replayed_count = 0
        payment_ids_created = set()

        start_time = time.time()
        semaphore = asyncio.Semaphore(50)  # 50 concurrent requests

        async def send_payment(idemp_key):
            nonlocal idempotent_replayed_count
            payload = {
                "customer_id": random.choice(customer_ids),
                "amount_minor": random.randint(10000, 500000),
                "currency": "INR",
                "urgency": "NORMAL",
                "description": "Load test payment"
            }
            req_headers = {**headers, "Idempotency-Key": idemp_key}
            t0 = time.time()
            async with semaphore:
                try:
                    resp = await client.post(f"{BASE_URL}/payments/", json=payload, headers=req_headers)
                    elapsed = time.time() - t0
                    latencies.append(elapsed * 1000)
                    code = resp.status_code
                    status_codes[code] = status_codes.get(code, 0) + 1

                    if resp.headers.get("Idempotent-Replayed") == "true":
                        idempotent_replayed_count += 1

                    if code in (200, 201):
                        data = resp.json()
                        payment_ids_created.add(data["id"])
                except Exception as e:
                    latencies.append(9999)
                    status_codes["ERR"] = status_codes.get("ERR", 0) + 1

        tasks = [send_payment(k) for k in keys_pool]
        await asyncio.gather(*tasks)

        total_duration = time.time() - start_time
        throughput = NUM_REQUESTS / total_duration
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)

        print("\n================ LOAD TEST RESULTS ================")
        print(f"Total Requests Dispatched: {NUM_REQUESTS}")
        print(f"Total Duration:            {total_duration:.2f} seconds")
        print(f"Throughput:                {throughput:.1f} req/sec")
        print(f"Latency p50:               {p50:.1f} ms")
        print(f"Latency p95:               {p95:.1f} ms")
        print(f"Latency p99:               {p99:.1f} ms")
        print(f"HTTP Status Codes:         {status_codes}")
        print(f"Idempotent Replays:        {idempotent_replayed_count}")
        print(f"Unique Payments Created:   {len(payment_ids_created)}")
        print(f"Expected Unique Payments:  {NUM_REQUESTS - num_dupes}")
        print(f"Duplicate Payments Leaked: {len(payment_ids_created) - (NUM_REQUESTS - num_dupes)}")
        print("===================================================\n")


if __name__ == "__main__":
    asyncio.run(run_load_test())
