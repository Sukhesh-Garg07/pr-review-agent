"""Parsing of incoming record payloads."""

import json


def parse_record(raw):
    """Parse one JSON record and return it as a dict."""
    data = json.loads(raw)
    return {"id": data["id"], "value": data["value"]}


def parse_batch(raw_records):
    return [parse_record(raw) for raw in raw_records]
