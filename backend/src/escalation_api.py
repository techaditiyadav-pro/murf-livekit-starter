"""Small local HTTP API for the KrishiMitra human-support dashboard."""

from __future__ import annotations

import json
import logging
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlparse

from database import FarmerRepository

logger = logging.getLogger("krishimitra.escalation_api")


class EscalationHandler(BaseHTTPRequestHandler):
    repository = FarmerRepository()

    def _send(self, status: HTTPStatus, payload: object) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
<<<<<<< HEAD
        path = urlparse(self.path).path
        if path == "/api/escalations":
            try:
                self._send(
                    HTTPStatus.OK, {"escalations": self.repository.list_escalations()}
                )
            except Exception:
                logger.exception("Could not list escalations")
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "Could not load requests"},
                )
        elif path == "/api/analytics":
            try:
                summary = self.repository.get_analytics_summary()
                recent = self.repository.get_recent_calls(20)
                total = summary["total_calls"]
                success_rate = (
                    round(summary["successful_calls"] / total * 100, 1)
                    if total > 0
                    else 0.0
                )
                self._send(
                    HTTPStatus.OK,
                    {**summary, "success_rate": success_rate, "recent_calls": recent},
                )
            except Exception:
                logger.exception("Could not load analytics")
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "Could not load analytics"},
                )
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})
=======
        if urlparse(self.path).path != "/api/escalations":
            self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            self._send(
                HTTPStatus.OK, {"escalations": self.repository.list_escalations()}
            )
        except Exception:
            logger.exception("Could not list escalations")
            self._send(
                HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Could not load requests"}
            )
>>>>>>> 2a9f9107e479b9131be5e3a35ba520a32f06820c

    def do_PATCH(self) -> None:
        reference_id = urlparse(self.path).path.removeprefix("/api/escalations/")
        if not reference_id or "/" in reference_id:
            self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            status = json.loads(self.rfile.read(length)).get("status")
            record = self.repository.update_escalation_status(reference_id, status)
            if record is None:
                self._send(HTTPStatus.NOT_FOUND, {"error": "Request not found"})
            else:
                self._send(HTTPStatus.OK, record)
        except (ValueError, json.JSONDecodeError):
            self._send(
                HTTPStatus.BAD_REQUEST, {"error": "Use OPEN, IN_PROGRESS, or RESOLVED"}
            )
        except Exception:
            logger.exception("Could not update escalation")
            self._send(
                HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Could not update request"}
            )

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/escalations":
            self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
            record, duplicate = self.repository.create_escalation(
                farmer_name=body.get("farmer_name"),
                farmer_identifier=body.get("farmer_identifier"),
                reason=body.get("reason", "SERIOUS_CROP_PROBLEM"),
                problem_summary=body.get("problem_summary", ""),
                what_agent_checked=body.get(
                    "what_agent_checked", "User requested human support directly."
                ),
                urgency=body.get("urgency", "medium"),
                language=body.get("language", "Hindi"),
                preferred_follow_up_method=body.get(
                    "preferred_follow_up_method", "Phone Call"
                ),
            )
            status_code = HTTPStatus.OK if duplicate else HTTPStatus.CREATED
            self._send(status_code, {**record, "duplicate": duplicate})
        except ValueError as err:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(err)})
        except Exception:
            logger.exception("Could not create escalation")
            self._send(
                HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Could not create request"}
            )

    def log_message(self, message_format: str, *args: object) -> None:
        logger.debug(message_format, *args)


def start_escalation_api() -> None:
    """Start the local dashboard API once per worker process."""
    port = int(os.getenv("ESCALATION_API_PORT", "8001"))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), EscalationHandler)
    except OSError as error:
        logger.warning("Escalation API was not started: %s", error)
        return
    Thread(target=server.serve_forever, daemon=True, name="escalation-api").start()
    logger.info("Escalation API listening at http://127.0.0.1:%s/api/escalations", port)
