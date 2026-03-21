from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib import error, parse, request


class APIExecutionError(RuntimeError):
    """Raised when an API task is malformed or cannot be executed."""


class APIExecutor:
    """Executes outbound HTTP API requests for BLACK ORIGIN."""

    _ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        method = str(task.get("method", "GET")).upper()
        if method not in self._ALLOWED_METHODS:
            raise APIExecutionError(f"Unsupported API method: {method}")

        url = str(task.get("url", "")).strip()
        if not url:
            raise APIExecutionError("API task missing 'url'")

        query = task.get("query") or {}
        headers = {str(k): str(v) for k, v in (task.get("headers") or {}).items()}
        timeout = float(task.get("timeout_seconds", 8))
        body = task.get("body")

        target_url = self._with_query(url, query)
        payload = self._serialize_body(body, headers)

        req = request.Request(url=target_url, data=payload, method=method)
        for key, value in headers.items():
            req.add_header(key, value)

        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                status = int(getattr(response, "status", 200))
                parsed = self._parse_body(raw, response.headers.get("Content-Type", ""))
                return {
                    "success": 200 <= status < 400,
                    "summary": "api_call_succeeded" if 200 <= status < 400 else "api_call_failed",
                    "status_code": status,
                    "method": method,
                    "url": target_url,
                    "headers": dict(response.headers.items()),
                    "body": parsed,
                    "raw_body": raw,
                }
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            return {
                "success": False,
                "summary": "api_call_failed",
                "status_code": int(exc.code),
                "method": method,
                "url": target_url,
                "headers": dict(getattr(exc, "headers", {}).items()),
                "body": self._parse_body(raw, ""),
                "raw_body": raw,
                "error": str(exc),
            }
        except error.URLError as exc:
            return {
                "success": False,
                "summary": "api_call_failed",
                "status_code": 0,
                "method": method,
                "url": target_url,
                "headers": {},
                "body": None,
                "raw_body": "",
                "error": str(exc.reason),
            }

    @staticmethod
    def _with_query(url: str, query: Dict[str, Any]) -> str:
        if not query:
            return url
        parsed = parse.urlparse(url)
        existing = parse.parse_qs(parsed.query)
        for key, value in query.items():
            existing[str(key)] = [str(value)]
        new_query = parse.urlencode(existing, doseq=True)
        return parse.urlunparse(parsed._replace(query=new_query))

    @staticmethod
    def _serialize_body(body: Optional[Any], headers: Dict[str, str]) -> Optional[bytes]:
        if body is None:
            return None
        if isinstance(body, (bytes, bytearray)):
            return bytes(body)
        if isinstance(body, str):
            return body.encode("utf-8")

        headers.setdefault("Content-Type", "application/json")
        return json.dumps(body).encode("utf-8")

    @staticmethod
    def _parse_body(raw: str, content_type: str) -> Any:
        if not raw:
            return None
        if "application/json" in content_type.lower():
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
