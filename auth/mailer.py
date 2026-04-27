# =============================================================================
# Pluggable mail backends (dev console + future SMTP)
# =============================================================================
from __future__ import annotations

import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage
import os


@dataclass
class OutgoingMessage:
    to_addr: str
    subject: str
    text_body: str
    html_body: str | None = None


class BaseMailer(ABC):
    @abstractmethod
    def send(self, msg: OutgoingMessage) -> None:
        raise NotImplementedError


class DevConsoleMailer(BaseMailer):
    """
    Local development and coursework demos: print the would-be message.

    In screenshots for markers, the team can show terminal output with the
    magic link, satisfying "we don't send real external mail" constraints.
    """

    def send(self, msg: OutgoingMessage) -> None:
        sep = "\n" + ("-" * 78) + "\n"
        print(f"{sep}[UWA Skill-Swap] OUTBOUND MAIL (dev console){sep}")
        print(f"To: {msg.to_addr!r}\nSubject: {msg.subject!r}\n\n{msg.text_body}")
        if msg.html_body:
            print(f"\n-- HTML (trunc) --\n{msg.html_body[:2000]!s}")


class SmtpMailer(BaseMailer):
    """
    Stub for future use — not called until SMTP credentials are provisioned.
    The implementation is intentionally simple; TLS policy must be revisited
    for production (STARTTLS, cert pinning, app passwords, etc.).
    """

    def __init__(self) -> None:
        self._host = os.environ.get("SMTP_HOST", "localhost")
        self._port = int(os.environ.get("SMTP_PORT", "587"))
        self._user = os.environ.get("SMTP_USER", "")
        self._password = os.environ.get("SMTP_PASSWORD", "")
        self._from = os.environ.get("EMAIL_FROM", "no-reply@uwa.local")

    def send(self, msg: OutgoingMessage) -> None:
        em = EmailMessage()
        em["From"] = self._from
        em["To"] = msg.to_addr
        em["Subject"] = msg.subject
        em.set_content(msg.text_body)
        if msg.html_body:
            em.add_alternative(msg.html_body, subtype="html")

        if self._host in ("", "none", "disabled"):
            raise RuntimeError("SMTP disabled but SmtpMailer was selected")
        with smtplib.SMTP(self._host, self._port) as s:
            s.ehlo()
            if self._user:
                s.starttls()
                s.login(self._user, self._password)
            s.send_message(em)


def get_mailer() -> BaseMailer:
    mode = os.environ.get("EMAIL_BACKEND", "console").lower()
    if mode == "smtp":
        return SmtpMailer()
    return DevConsoleMailer()
