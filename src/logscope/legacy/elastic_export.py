"""Export parsed access-log records to Elasticsearch with the _bulk API.

Usage:

    logscope export access.log --es http://localhost:9200 --index nginx-access

Records are sent in batches of `batch_size` as NDJSON. Each document gets a
deterministic _id (hash of the raw line), so re-running an export over the
same file doesn't create duplicates.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from logscope.records import LogRecord

DEFAULT_INDEX = "nginx-access"
DEFAULT_BATCH_SIZE = 500
MAX_RETRIES = 3


@dataclass
class ExportResult:
    sent: int = 0
    failed: int = 0
    batches: int = 0


class ElasticExporter:
    def __init__(
        self,
        base_url: str,
        index: str = DEFAULT_INDEX,
        batch_size: int = DEFAULT_BATCH_SIZE,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.index = index
        self.batch_size = batch_size
        self.timeout = timeout
        self.headers = {"Content-Type": "application/x-ndjson"}
        if username and password:
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            self.headers["Authorization"] = f"Basic {token}"

    def export(self, records: Iterable[LogRecord]) -> ExportResult:
        result = ExportResult()
        for batch in self._batches(records):
            ok, failed = self._send(batch)
            result.sent += ok
            result.failed += failed
            result.batches += 1
        return result

    def _batches(self, records: Iterable[LogRecord]) -> Iterator[list[LogRecord]]:
        batch: list[LogRecord] = []
        for record in records:
            batch.append(record)
            if len(batch) >= self.batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _document(self, record: LogRecord) -> dict:
        return {
            "@timestamp": record.timestamp.isoformat(),
            "client.ip": record.ip,
            "http.request.method": record.method,
            "url.path": record.path,
            "http.response.status_code": record.status,
            "http.response.body.bytes": record.bytes_sent,
            "user_agent.original": record.agent,
            "event.duration": int(record.request_time * 1e9) if record.request_time else None,
        }

    def _body(self, batch: list[LogRecord]) -> bytes:
        lines = []
        for record in batch:
            doc_id = hashlib.sha1(record.raw.encode()).hexdigest()
            lines.append(json.dumps({"index": {"_index": self.index, "_id": doc_id}}))
            lines.append(json.dumps(self._document(record)))
        return ("\n".join(lines) + "\n").encode()

    def _send(self, batch: list[LogRecord]) -> tuple[int, int]:
        request = urllib.request.Request(
            f"{self.base_url}/_bulk", data=self._body(batch), headers=self.headers, method="POST"
        )
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                break
            except urllib.error.HTTPError as e:
                if e.code < 500 or attempt == MAX_RETRIES - 1:
                    return 0, len(batch)
            except urllib.error.URLError:
                if attempt == MAX_RETRIES - 1:
                    return 0, len(batch)
            time.sleep(2**attempt)

        if not payload.get("errors"):
            return len(batch), 0
        failed = sum(1 for item in payload["items"] if item["index"].get("error"))
        return len(batch) - failed, failed
