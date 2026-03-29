import hashlib
import hmac
import json
import logging
import subprocess

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _verify_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


@router.post("/github")
async def github_push_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
):
    if not settings.github_webhook_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint is disabled",
        )

    if x_github_event != "push":
        return {"status": "ignored", "reason": "only push events are processed"}

    raw_body = await request.body()
    if settings.github_webhook_secret and not _verify_signature(
        raw_body,
        x_hub_signature_256,
        settings.github_webhook_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    payload = json.loads(raw_body.decode("utf-8") or "{}")
    pushed_ref = payload.get("ref", "")
    expected_ref = f"refs/heads/{settings.github_webhook_branch}"
    if pushed_ref and pushed_ref != expected_ref:
        return {
            "status": "ignored",
            "reason": f"branch mismatch: got {pushed_ref}, expected {expected_ref}",
        }

    cmd = [
        "git",
        "-C",
        settings.github_webhook_repo_path,
        "pull",
        "origin",
        settings.github_webhook_branch,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    if result.returncode != 0:
        logger.error("git pull failed: %s", result.stderr.strip())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "git pull failed",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            },
        )

    return {
        "status": "ok",
        "message": "Repository updated",
        "stdout": result.stdout.strip(),
        "branch": settings.github_webhook_branch,
    }
