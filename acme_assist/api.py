"""Thin client for the ACME Systems API."""

import logging

import httpx

from acme_assist import config

log = logging.getLogger("acme.api")


class AcmeAPI:
    def __init__(self, base_url: str | None = None):
        url = base_url or config.API_URL or "inprocess"  # an empty ACME_API_URL counts as unset
        if url == "inprocess":
            try:
                from fastapi.testclient import TestClient

                from acme_api.main import app, ensure_db
            except ImportError:
                raise RuntimeError("ACME_API_URL is not set. Put the ACME Systems API URL in your .env file.") from None

            ensure_db()
            self.http = TestClient(app, base_url="http://acme-api.inprocess")
        else:
            self.http = httpx.Client(base_url=url, timeout=None)

    def _call(self, method: str, path: str, **kwargs):
        try:
            r = self.http.request(method, path, **kwargs)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # never crash the chat over a backend hiccup
            log.warning("ACME API %s %s failed: %s", method, path, e)
            return {}

    def get(self, path: str, **params):
        return self._call("GET", path, params={k: v for k, v in params.items() if v is not None})

    def post(self, path: str, json: dict | None = None):
        return self._call("POST", path, json=json or {})

    def patch(self, path: str, json: dict | None = None):
        return self._call("PATCH", path, json=json or {})


_client: AcmeAPI | None = None


def get_api() -> AcmeAPI:
    global _client
    if _client is None:
        _client = AcmeAPI()
    return _client


def reset_api():
    global _client
    _client = None
