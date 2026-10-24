"""JSON lines on stderr: one event per line, never personal data or request bodies."""

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        try:
            data = json.loads(message)
            if not isinstance(data, dict):
                data = {'message': message}
        except ValueError:
            data = {'message': message}
        line = {'time': datetime.fromtimestamp(record.created, UTC).isoformat(timespec='milliseconds'),
                'level': record.levelname.lower(), 'logger': record.name, **data}
        if record.exc_info:
            line['exception'] = self.formatException(record.exc_info)
        return json.dumps(line, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    if any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers):
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def event(logger: logging.Logger, name: str, level: int = logging.INFO, **fields: object) -> None:
    logger.log(level, json.dumps({'event': name, **fields}, ensure_ascii=False, default=str))
