"""Record schema shared by the parser and the writers."""

RECORD_FIELDS = ("id", "value")


def check_record(record):
    return all(field in record for field in RECORD_FIELDS)
