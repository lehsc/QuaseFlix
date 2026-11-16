"""Run with python -m backend.billing_worker [--once]. Local simulation only."""
import argparse
import logging
import os
from pathlib import Path
import time
from backend.database.connection import get_db_connection
from backend.services.subscription_services import run_billing


def deliver_outbox():
    directory = Path(os.environ.get('QUASEFLIX_OUTBOX', '/tmp/quaseflix-outbox'))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id,recipient,body FROM public.billing_outbox WHERE delivered_at IS NULL FOR UPDATE SKIP LOCKED')
            for outbox_id, email, body in cur.fetchall():
                # Deterministic file names avoid duplicate delivery on a retry.
                import json
                (directory / f'billing-{outbox_id}.json').write_text(json.dumps({'to':email,'body':body}))
                cur.execute('UPDATE public.billing_outbox SET delivered_at=LOCALTIMESTAMP WHERE id=%s', (outbox_id,))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    while True:
        try:
            run_billing()
            deliver_outbox()
        except Exception:
            logging.exception('Billing worker failed')
            if args.once:
                raise
        if args.once:
            return
        time.sleep(60)


if __name__ == '__main__':
    main()
