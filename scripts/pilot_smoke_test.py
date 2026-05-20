#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import sys
import time
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar


def build_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def request(opener: urllib.request.OpenerDirector, url: str, data: dict[str, str] | None = None) -> str:
    encoded = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=encoded)
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with opener.open(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_value(page: str, label: str) -> str:
    pattern = rf"<strong>{re.escape(label)}:</strong>\s*<span>([^<]+)</span>"
    match = re.search(pattern, page)
    if not match:
        raise RuntimeError(f"não foi possível extrair {label}")
    return html.unescape(match.group(1)).strip()


def extract_csrf(page: str) -> str:
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', page)
    if not match:
        raise RuntimeError("csrf_token não encontrado")
    return html.unescape(match.group(1))


def extract_report_url(page: str, protocol: str) -> str:
    pattern = rf'href="(/empresa/denuncias/[0-9a-fA-F-]+)"[^>]*>{re.escape(protocol)}</a>'
    match = re.search(pattern, page)
    if not match:
        raise RuntimeError("denúncia criada não apareceu na listagem da empresa")
    return html.unescape(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test piloto do fluxo denúncia -> empresa -> acompanhamento.")
    parser.add_argument("--base-url", default="https://denuncia.canaldenunciaonline.com.br")
    parser.add_argument("--tenant", default="triton")
    parser.add_argument("--company-email", default="admin@triton.local")
    parser.add_argument("--company-password", default="Admin123!")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    public = build_opener()
    company = build_opener()

    description = f"Smoke piloto {int(time.time())}"
    success = request(
        public,
        f"{base_url}/{args.tenant}/denuncias",
        {
            "report_type": "anonima",
            "category": "outros",
            "description": description,
            "website": "",
        },
    )
    protocol = extract_value(success, "Protocolo")
    login = extract_value(success, "Login")
    password = extract_value(success, "Senha")

    login_page = request(company, f"{base_url}/auth/login")
    if "csrf_token" in login_page:
        raise RuntimeError("login da empresa não deve exigir CSRF antes da sessão")
    empresa_home = request(company, f"{base_url}/auth/login", {"email": args.company_email, "password": args.company_password})
    if "Denúncias" not in empresa_home and "Denuncias" not in empresa_home:
        raise RuntimeError("login da empresa não chegou ao painel")

    listing = request(company, f"{base_url}/empresa/denuncias?protocol={urllib.parse.quote(protocol)}")
    report_url = extract_report_url(listing, protocol)
    detail = request(company, f"{base_url}{report_url}")
    csrf = extract_csrf(detail)
    response_text = "Resposta operacional do smoke test piloto."
    detail_after_response = request(company, f"{base_url}{report_url}/responder", {"csrf_token": csrf, "message": response_text})
    if response_text not in detail_after_response:
        raise RuntimeError("resposta da empresa não apareceu no detalhe")

    complainant = build_opener()
    painel = request(
        complainant,
        f"{base_url}/acompanhar/login",
        {"protocol": protocol, "login": login, "password": password},
    )
    if response_text not in painel:
        raise RuntimeError("resposta da empresa não apareceu no acompanhamento do denunciante")

    print("pilot_smoke_test=ok")
    print(f"tenant={args.tenant}")
    print(f"protocol={protocol}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"pilot_smoke_test=failed error={exc}", file=sys.stderr)
        raise SystemExit(1)
