from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json
import asyncio

app = FastAPI()


class LikeRequest(BaseModel):
    region: str
    target_uid: str


def get_base_url(region: str):
    if region == "IND":
        return "https://client.ind.freefiremobile.com"
    elif region in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com"
    return "https://clientbp.ggblueshark.com"


@app.get("/")
def home():
    return {"status": "API running"}


@app.get("/guest-count")
def guest_count():
    with open("guests.json") as f:
        guests = json.load(f)
    return {"total_guests": len(guests)}


@app.post("/send-like")
async def send_like(data: LikeRequest):
    try:
        from get_jwt import create_jwt
        from encrypt_like_body import create_like_payload

        with open("guests.json") as f:
            guests = json.load(f)

        max_likes = min(220, len(guests))

        success = 0
        failed = 0

        async with httpx.AsyncClient(timeout=10) as client:
            for i in range(max_likes):
                guest = guests[i]

                try:
                    jwt, guest_region, _ = await create_jwt(
                        guest["uid"],
                        guest["password"]
                    )

                    payload = create_like_payload(
                        data.target_uid,
                        guest_region
                    )

                    headers = {
                        "User-Agent": "Dalvik/2.1.0",
                        "Content-Type": "application/octet-stream",
                        "Authorization": jwt,
                        "X-Unity-Version": "2018.4.11f1",
                        "ReleaseVersion": "OB50",
                    }

                    url = f"{get_base_url(data.region)}/LikeProfile"

                    res = await client.post(url, data=payload, headers=headers)

                    if res.status_code == 200:
                        success += 1
                    else:
                        failed += 1

                    await asyncio.sleep(0.3)

                except:
                    failed += 1

        return {
            "requested": max_likes,
            "success": success,
            "failed": failed
        }

    except Exception as e:
        return {"error": str(e)}
