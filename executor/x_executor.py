from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import error, parse, request


class XExecutionError(RuntimeError):
    """Raised when BLACK ORIGIN cannot execute an X operation."""


@dataclass
class XCredentials:
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str
    bearer_token: str


class XExecutor:
    """Executes real X (Twitter) API operations for BLACK ORIGIN."""

    _BASE_URL = "https://api.x.com/2"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        operation = str(task.get("operation", "post_and_fetch_metrics")).lower()
        credentials = self._load_credentials()

        if operation == "post_tweet":
            post_result = self._post_tweet(task=task, credentials=credentials)
            return {"success": True, "summary": "x_posted", "operation": operation, "post": post_result}

        if operation == "fetch_metrics":
            tweet_id = str(task.get("tweet_id", "")).strip()
            if not tweet_id:
                raise XExecutionError("X fetch_metrics operation requires 'tweet_id'")
            metrics = self._fetch_metrics(tweet_id=tweet_id, credentials=credentials)
            return {"success": True, "summary": "x_metrics_fetched", "operation": operation, "metrics": metrics}

        if operation != "post_and_fetch_metrics":
            raise XExecutionError(f"Unsupported X operation: {operation}")

        post_result = self._post_tweet(task=task, credentials=credentials)
        tweet_id = str(post_result["data"]["id"])
        metrics = self._fetch_metrics(tweet_id=tweet_id, credentials=credentials)
        return {
            "success": True,
            "summary": "x_posted_and_measured",
            "operation": operation,
            "post": post_result,
            "metrics": metrics,
        }

    def _post_tweet(self, task: Dict[str, Any], credentials: XCredentials) -> Dict[str, Any]:
        text = str(task.get("text", "")).strip()
        if not text:
            raise XExecutionError("X post_tweet operation requires non-empty 'text'")

        payload: Dict[str, Any] = {"text": text}
        if task.get("reply_settings"):
            payload["reply_settings"] = task["reply_settings"]

        response = self._request(
            method="POST",
            path="/tweets",
            credentials=credentials,
            body=payload,
            auth_mode="oauth1",
        )
        return response

    def _fetch_metrics(self, tweet_id: str, credentials: XCredentials) -> Dict[str, Any]:
        query = {
            "tweet.fields": "public_metrics,created_at,non_public_metrics",
        }
        response = self._request(
            method="GET",
            path=f"/tweets/{parse.quote(tweet_id)}",
            credentials=credentials,
            query=query,
            auth_mode="bearer",
        )
        return response

    def _request(
        self,
        method: str,
        path: str,
        credentials: XCredentials,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        auth_mode: str = "bearer",
    ) -> Dict[str, Any]:
        url = f"{self._BASE_URL}{path}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"

        headers = {"Accept": "application/json"}
        body_bytes: Optional[bytes] = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            body_bytes = json.dumps(body).encode("utf-8")

        if auth_mode == "oauth1":
            headers["Authorization"] = self._build_oauth1_header(
                method=method,
                url=url,
                credentials=credentials,
                body=body,
            )
        else:
            headers["Authorization"] = f"Bearer {credentials.bearer_token}"

        req = request.Request(url=url, data=body_bytes, method=method)
        for key, value in headers.items():
            req.add_header(key, value)

        try:
            with request.urlopen(req, timeout=12) as response:
                raw = response.read().decode("utf-8", errors="replace")
                parsed = json.loads(raw) if raw else {}
                return {
                    "status_code": int(getattr(response, "status", 200)),
                    "headers": dict(response.headers.items()),
                    "data": parsed,
                }
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            detail = raw or str(exc)
            raise XExecutionError(f"X API HTTP error ({exc.code}): {detail}") from exc
        except error.URLError as exc:
            raise XExecutionError(f"X API connection error: {exc.reason}") from exc

    def _load_credentials(self) -> XCredentials:
        api_key = os.getenv("X_API_KEY", "")
        api_secret = os.getenv("X_API_SECRET", "")
        access_token = os.getenv("X_ACCESS_TOKEN", "")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET", "")
        bearer_token = os.getenv("X_BEARER_TOKEN", "")

        if not all([api_key, api_secret, access_token, access_token_secret, bearer_token]):
            raise XExecutionError(
                "Missing X credentials. Required env vars: X_API_KEY, X_API_SECRET, "
                "X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_BEARER_TOKEN"
            )

        return XCredentials(
            api_key=api_key,
            api_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            bearer_token=bearer_token,
        )

    def _build_oauth1_header(
        self,
        method: str,
        url: str,
        credentials: XCredentials,
        body: Optional[Dict[str, Any]],
    ) -> str:
        nonce = uuid.uuid4().hex
        timestamp = str(int(time.time()))
        oauth_params = {
            "oauth_consumer_key": credentials.api_key,
            "oauth_nonce": nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_token": credentials.access_token,
            "oauth_version": "1.0",
        }

        signed_params = dict(oauth_params)
        parsed = parse.urlparse(url)
        query_pairs = parse.parse_qsl(parsed.query, keep_blank_values=True)
        for key, value in query_pairs:
            signed_params[key] = value

        if body:
            for key, value in body.items():
                if isinstance(value, (str, int, float, bool)):
                    signed_params[str(key)] = str(value)

        encoded = [(self._pct_encode(k), self._pct_encode(v)) for k, v in signed_params.items()]
        encoded.sort(key=lambda item: (item[0], item[1]))
        parameter_string = "&".join(f"{k}={v}" for k, v in encoded)

        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        signature_base = "&".join(
            [
                method.upper(),
                self._pct_encode(base_url),
                self._pct_encode(parameter_string),
            ]
        )

        signing_key = f"{self._pct_encode(credentials.api_secret)}&{self._pct_encode(credentials.access_token_secret)}"
        digest = hmac.new(signing_key.encode("utf-8"), signature_base.encode("utf-8"), hashlib.sha1).digest()
        signature = base64.b64encode(digest).decode("utf-8")
        oauth_params["oauth_signature"] = signature

        header_value = ", ".join(
            f'{self._pct_encode(k)}="{self._pct_encode(v)}"' for k, v in sorted(oauth_params.items())
        )
        return f"OAuth {header_value}"

    @staticmethod
    def _pct_encode(value: Any) -> str:
        return parse.quote(str(value), safe="~-._")
