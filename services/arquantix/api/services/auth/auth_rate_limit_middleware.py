"""Middleware HTTP — rate limit ciblé sur /auth/login, /auth/refresh, /auth/revoke."""
from __future__ import annotations

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from services.auth.auth_rate_limit import build_auth_rate_limiter, client_ip_for_rl


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        if method != "POST":
            return await call_next(request)

        limiter = build_auth_rate_limiter()
        try:
            if path == "/auth/login":
                limiter.check_login(client_ip_for_rl(request))
            elif path in ("/auth/login/email-otp/start", "/auth/login/email-otp/verify"):
                limiter.check_login(client_ip_for_rl(request))
            elif path in (
                "/auth/login/start",
                "/auth/login/verify",
                "/auth/login/sms/start",
                "/auth/login/sms/verify",
                "/auth/signup/sms/start",
                "/auth/signup/sms/verify",
            ):
                limiter.check_login(client_ip_for_rl(request))
            elif path == "/auth/refresh":
                did = (request.headers.get("x-device-id") or "").strip() or "__missing__"
                limiter.check_refresh(did[:128])
            elif path == "/auth/revoke":
                did = (request.headers.get("x-device-id") or "").strip() or "__missing__"
                limiter.check_revoke(did[:128])
            elif path in ("/auth/passkeys/login/start", "/auth/passkeys/login/finish"):
                limiter.check_login(client_ip_for_rl(request))
            elif path in ("/auth/passkeys/register/start", "/auth/passkeys/register/finish"):
                limiter.check_login(client_ip_for_rl(request))
            elif path == "/auth/passkeys/prompt":
                limiter.check_login(client_ip_for_rl(request))
        except HTTPException as exc:
            if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                body = exc.detail
                if isinstance(body, dict):
                    return JSONResponse(status_code=429, content=body)
                return JSONResponse(status_code=429, content={"detail": body})
            raise

        return await call_next(request)
