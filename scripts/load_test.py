import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import URLError
from urllib.request import Request, urlopen


URL = "http://127.0.0.1:8000/bid"
TOTAL_REQUESTS = 100
CONCURRENCY = 10


def send_bid_request(index: int) -> dict:
    payload = {
        "impression_id": f"imp_load_{index}",
        "user_id": "user_sports_1" if index % 2 == 0 else "new_user_123",
        "placement": "mobile_feed",
        "country": "IL",
        "device": "mobile",
        "floor_price": 1.2 if index % 3 != 0 else 20.0,
        "context": "sports shoes sale" if index % 2 == 0 else "random article",
    }

    data = json.dumps(payload).encode("utf-8")

    request = Request(
        URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()

    try:
        with urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            latency_ms = (time.perf_counter() - start) * 1000

            return {
                "success": True,
                "status_code": response.status,
                "latency_ms": latency_ms,
                "decision": body.get("decision"),
            }
    except URLError as error:
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "success": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "decision": None,
            "error": str(error),
        }


def main() -> None:
    print(f"Sending {TOTAL_REQUESTS} requests with concurrency={CONCURRENCY}")

    results = []

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [
            executor.submit(send_bid_request, index)
            for index in range(TOTAL_REQUESTS)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    duration_seconds = time.perf_counter() - start

    successful_results = [result for result in results if result["success"]]
    latencies = [result["latency_ms"] for result in successful_results]

    bid_count = sum(1 for result in successful_results if result["decision"] == "BID")
    no_bid_count = sum(1 for result in successful_results if result["decision"] == "NO_BID")

    print()
    print("Load test summary")
    print("-----------------")
    print(f"Total requests: {TOTAL_REQUESTS}")
    print(f"Successful requests: {len(successful_results)}")
    print(f"Failed requests: {TOTAL_REQUESTS - len(successful_results)}")
    print(f"BID count: {bid_count}")
    print(f"NO_BID count: {no_bid_count}")
    print(f"Total duration seconds: {duration_seconds:.2f}")
    print(f"Approx requests per second: {TOTAL_REQUESTS / duration_seconds:.2f}")

    if latencies:
        print(f"Average latency ms: {statistics.mean(latencies):.2f}")
        print(f"Median latency ms: {statistics.median(latencies):.2f}")
        print(f"Max latency ms: {max(latencies):.2f}")


if __name__ == "__main__":
    main()
