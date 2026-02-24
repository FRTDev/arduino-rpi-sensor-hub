#!/usr/bin/env python3
"""
Genere des mesures aleatoires et les envoie a l'API /api/data.

Exemple:
    python generate_random_measures.py --count 100 --delay 0.2
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import datetime
from urllib import error, request


def build_payload() -> dict[str, str]:
    arduino_id = random.choice(["arduino1", "arduino2"])
    if arduino_id == "arduino1":
        valeur = str(random.randint(0, 1023))  # LDR
    else:
        valeur = f"{random.uniform(15.0, 35.0):.1f}"  # TMP36 en degC
    return {
        "arduino_id": arduino_id,
        "valeur": valeur,
        "timestamp": datetime.now().isoformat(),
    }


def send_measure(url: str, api_key: str, payload: dict[str, str]) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
    )
    with request.urlopen(req, timeout=5) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Injecte des mesures aleatoires dans le serveur IoT."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:5000/api/data",
        help="URL complete de l'endpoint API (defaut: %(default)s)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GATEWAY_API_KEY", "gateway2026"),
        help="Cle API gateway (defaut: env GATEWAY_API_KEY ou gateway2026)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=40,
        help="Nombre total de mesures a envoyer (defaut: %(default)s)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Pause en secondes entre envois (defaut: %(default)s)",
    )
    args = parser.parse_args()

    ok = 0
    fail = 0
    for i in range(1, args.count + 1):
        payload = build_payload()
        try:
            status, body = send_measure(args.url, args.api_key, payload)
            print(
                f"[{i}/{args.count}] OK status={status} "
                f"{payload['arduino_id']}={payload['valeur']} body={body}"
            )
            ok += 1
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"[{i}/{args.count}] HTTP {exc.code}: {body}")
            fail += 1
        except Exception as exc:
            print(f"[{i}/{args.count}] ERREUR: {exc}")
            fail += 1

        if i < args.count and args.delay > 0:
            time.sleep(args.delay)

    print(f"\nTermine. Succes={ok}, Echecs={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
