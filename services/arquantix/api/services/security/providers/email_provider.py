"""Email delivery via AWS SES (boto3)."""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    @property
    def is_noop(self) -> bool:
        return False

    @abstractmethod
    def send_otp(self, to_email: str, code: str) -> None:
        """Send OTP email. Raises on failure."""


class NoopEmailProvider(EmailProvider):
    @property
    def is_noop(self) -> bool:
        return True

    def send_otp(self, to_email: str, code: str) -> None:
        logger.warning("Email provider noop: OTP email suppressed (code not logged)")


class SesEmailProvider(EmailProvider):
    def __init__(self) -> None:
        self.sender = os.getenv("SES_FROM_EMAIL") or os.getenv("AWS_SES_FROM", "")
        self.region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "eu-west-1")

    def send_otp(self, to_email: str, code: str) -> None:
        if not self.sender:
            raise RuntimeError("SES_FROM_EMAIL (or AWS_SES_FROM) not set")
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as e:
            raise RuntimeError("boto3 required for SES") from e
        client = boto3.client("ses", region_name=self.region)
        subject = "Security code"
        body_text = (
            f"Your security code is {code}.\n"
            f"It expires in 5 minutes. If you did not request this, ignore this message."
        )
        try:
            client.send_email(
                Source=self.sender,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
                },
            )
        except ClientError as e:
            err = (e.response or {}).get("Error") or {}
            logger.warning("SES send failed code=%s", err.get("Code"))
            raise RuntimeError("ses_send_failed") from e


def get_email_provider() -> EmailProvider:
    if os.getenv("SES_FROM_EMAIL") or os.getenv("AWS_SES_FROM"):
        return SesEmailProvider()
    return NoopEmailProvider()
