"""Credential vault endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.infrastructure.vault import Vault, get_vault
from src.interfaces.web.schemas import CredentialIn

router = APIRouter()


@router.get("/api/credentials")
async def list_credentials(vault: Vault = Depends(get_vault)):
    services = vault.list_services()
    result = []
    for svc in services:
        creds = vault.list_credentials(svc)
        result.append({"service": svc, "usernames": [c["username"] for c in creds]})
    return result


@router.post("/api/credentials")
async def save_credential(data: CredentialIn, vault: Vault = Depends(get_vault)):
    vault.set_password(data.service, data.username, data.password)
    return {"status": "ok"}


@router.get("/api/credentials/{service}")
async def get_credential(service: str, username: str = "", vault: Vault = Depends(get_vault)):
    if not username:
        raise HTTPException(400, "username query param required")
    password = vault.get_password(service, username)
    if password is None:
        raise HTTPException(404, "credential not found")
    # Never return the raw password over HTTP — the UI never reads it, and
    # exposing it turns the API into a credential exfiltration vector.
    # The task runner fetches passwords directly from the OS keyring at
    # execution time using the service + username pair.
    return {"service": service, "username": username, "password": "***"}


@router.delete("/api/credentials/{service}")
async def delete_credential(service: str, vault: Vault = Depends(get_vault)):
    vault.delete_password(service)
    return {"status": "deleted"}
