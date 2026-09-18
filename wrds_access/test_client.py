"""Offline contracts for bounded WRDS access; all transports are stubbed.

Inputs: hand-written API fixtures. Outputs: refusal and replay assertions.
Identity: one fixture row means n=1; replay preserves exactly those bytes.
Tier: 1
Run: .venv/bin/python -m unittest discover -s wrds_access -p 'test_*.py'
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from client import MAX_BYTES, AccessError, Client, load_token

FIELDS = {
    "permno": {"type": "integer", "filter_field": True},
    "date": {"type": "date", "filter_field": True},
    "ret": {"type": "decimal", "filter_field": False},
}
FILTERS = {"permno": "14593", "date": "2024-01-03"}
ROW = {"permno": 14593, "date": "2024-01-03", "ret": None}


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cache = Path(self.directory.name)
        # Assignment and transport interception happen before any client operation.
        self.env = patch.dict(os.environ, {"WRDS_API_KEY": "test-placeholder"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.transport = patch("client.requests.Session")
        self.session = self.transport.start().return_value.__enter__.return_value
        self.addCleanup(self.transport.stop)

    def responses(self, *payloads, status=200):
        responses = []
        for payload in payloads:
            response = MagicMock()
            response.__enter__.return_value = response
            response.status_code = status
            raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            response.iter_content.return_value = [raw]
            responses.append(response)
        self.session.request.side_effect = responses

    def test_live_contract_and_offline_replay(self):
        self.responses(
            {"fields": FIELDS}, {"results": [ROW], "next": "http://untrusted.invalid/", "count": 99}
        )
        client = Client(self.cache, online=True)
        rows, provenance = client.sample("crsp.dsf", FILTERS)
        self.assertEqual(rows, [ROW])
        self.assertEqual(self.session.request.call_count, 2)  # OPTIONS + GET, no next.
        call = self.session.request.call_args
        self.assertEqual(call.args, ("GET", "https://wrds-api.wharton.upenn.edu/data/crsp.dsf/"))
        self.assertEqual(call.kwargs["params"], {**FILTERS, "limit": 1})
        self.assertFalse(call.kwargs["allow_redirects"])
        self.session.request.side_effect = AssertionError("offline must not use network")
        with patch(
            "client.load_token", side_effect=AssertionError("offline must not read secrets")
        ):
            self.assertEqual(Client(self.cache).sample("crsp.dsf", FILTERS), (rows, provenance))
        self.assertNotIn(
            "test-placeholder", "".join(p.read_text() for p in self.cache.glob("*.json"))
        )

    def test_missing_scope_limits_and_table_refused_before_network(self):
        client = Client(self.cache, online=True)
        for table, filters, limit in [
            ("comp.fundq", FILTERS, 1),
            ("crsp.dsf", {}, 1),
            ("crsp.dsf", FILTERS, 6),
            ("crsp.dsf", FILTERS, True),
        ]:
            with (
                self.subTest(table=table, filters=filters, limit=limit),
                self.assertRaises(AccessError),
            ):
                client.sample(table, filters, limit=limit)
        self.session.request.assert_not_called()
        with self.assertRaises(AccessError):
            Client(self.cache).schema("crsp.dsf")
        self.session.request.assert_not_called()

    def test_unsupported_filter_and_out_of_scope_rows_refused(self):
        self.responses({"fields": FIELDS}, {"results": [{**ROW, "date": "1980-01-01"}]})
        client = Client(self.cache, online=True)
        with self.assertRaisesRegex(AccessError, "Unsupported filter"):
            client.sample("crsp.dsf", {**FILTERS, "ret": "0"})
        self.assertEqual(self.session.request.call_count, 1)
        with self.assertRaisesRegex(AccessError, "outside"):
            client.sample("crsp.dsf", FILTERS)
        # Invalid vendor responses stay frozen but cannot pass offline validation.
        with self.assertRaisesRegex(AccessError, "outside"):
            Client(self.cache).sample("crsp.dsf", FILTERS)

    def test_row_cap_and_cache_corruption(self):
        self.responses({"fields": FIELDS}, {"results": [ROW, ROW]})
        with self.assertRaisesRegex(AccessError, "row limit"):
            Client(self.cache, online=True).sample("crsp.dsf", FILTERS)
        for path in self.cache.glob("*.json"):
            envelope = json.loads(path.read_text())
            if envelope["request"]["method"] == "OPTIONS":
                envelope["raw_response"] = "{}"
                path.write_text(json.dumps(envelope))
        with self.assertRaisesRegex(AccessError, "integrity"):
            Client(self.cache).schema("crsp.dsf")

    def test_redirect_secret_echo_and_byte_cap(self):
        self.responses({}, status=302)
        with self.assertRaisesRegex(AccessError, "HTTP 302"):
            Client(self.cache, online=True).schema("crsp.dsf")
        self.responses({"secret": "test-placeholder"})
        with self.assertRaisesRegex(AccessError, "Credential appeared"):
            Client(self.cache, online=True).schema("crsp.dsf")
        self.responses(b"x" * (MAX_BYTES + 1))
        with self.assertRaisesRegex(AccessError, "byte cap"):
            Client(self.cache, online=True).schema("crsp.dsf")
        self.assertEqual(list(self.cache.glob("*.json")), [])

    def test_empty_environment_disables_dotenv(self):
        with (
            patch.dict(os.environ, {"WRDS_API_KEY": ""}),
            patch("client.Path.read_text", side_effect=AssertionError("must not read .env")),
            self.assertRaises(AccessError),
        ):
            load_token()


if __name__ == "__main__":
    unittest.main()
