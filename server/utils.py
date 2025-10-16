# server/utils.py
import os
import requests
from flask import jsonify
import time

def verify_secret(provided_secret: str):
    secret = os.getenv("SECRET_KEY")
    if not secret:
        return "SECRET_KEY not set in environment", 500
    return provided_secret == secret

def post_evaluation(evaluation_url: str, payload: dict, max_retries: int=6):
    """
    POST to evaluation_url. On failure, retry with exponential backoff (1,2,4,8...).
    Returns response code or raises.
    """
    headers = {"Content-Type": "application/json"}
    delay = 1
    for attempt in range(max_retries):
        try:
            r = requests.post(evaluation_url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                return r
            # else retry
        except Exception as e:
            # continue to retry
            pass
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"Failed to POST evaluation after {max_retries} attempts")
