# app.py

print("STEP 1: Starting app import...")

from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json
import random

print("STEP 2: Imports basic done")

from get_jwt import create_jwt
print("STEP 3: get_jwt loaded")

from encrypt_like_body import create_like_payload
print("STEP 4: encrypt_like_body loaded")

app = FastAPI()

print("STEP 5: FastAPI app created")


# -------- Request Model --------
class LikeRequest(BaseModel):
    region: str
    target_uid: str


# -------- Helpers --------
def get_base_url(region: str):
    if region == "IND":
        return "https://client.ind.freefiremobile.com"
    elif region in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com"
    return "https://clientbp.ggblueshark.com"


def get_random_guest():
    with open("guests.json") as f:
        guests = json.load(f)
    return random.choice(guests)


# -------- Routes --------
@app.get("/")
def home():
    return {"status": "running"}


@app.post("/send-like")
async def send_like(data: LikeRequest):
    try:
        guest = get_random_guest()

        print(f"Using guest: {guest['uid']}")

        # Step 1 → JWT
        jwt, guest_region, _ = await create_jwt(
            guest["uid"],
            guest["password"]
        )

        # Step 2 → payload
        payload = create_like_payload(data.target_uid, guest_region)

        headers = {
            "User-Agent": "Dalvik/2.1.0",
            "Content-Type": "application/octet-stream",
            "Authorization": jwt,  # fixed
            "X-Unity-Version": "2018.4.11f1",
            "ReleaseVersion": "OB50",
        }

        url = f"{get_base_url(data.region)}/LikeProfile"

        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(url, data=payload, headers=headers)

        return {
            "status": res.status_code,
            "guest_uid": guest["uid"],
            "message": "like sent"
        }

    except Exception as e:
        print("ERROR:", str(e))
        return {"error": str(e)}


@app.get("/guest-count")
def guest_count():
    with open("guests.json") as f:
        guests = json.load(f)
    return {"total_guests": len(guests)}
