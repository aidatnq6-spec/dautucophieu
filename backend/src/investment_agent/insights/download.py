"""Bounded report download: refuses files over max_bytes and downloads slower than max_seconds in total."""

import time


def fetch_pdf(client, url: str, *, max_bytes: int, max_seconds: float, clock=time.monotonic, chunk_size: int = 65536) -> bytes:
    start, parts, size = clock(), [], 0
    with client.stream("GET", url) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes(chunk_size):
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("report file too large")
            if clock() - start > max_seconds:
                raise TimeoutError("report download too slow")
            parts.append(chunk)
    return b"".join(parts)
