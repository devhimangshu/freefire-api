import httpx
import json
import base64
from typing import Tuple
from google.protobuf import json_format, message
from Crypto.Cipher import AES
from ff_proto import freefire_pb2

MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASEVERSION = "OB50"
USERAGENT = "Dalvik/2.1.0 (Linux; Android 13)"


async def json_to_proto(json_data: str, proto_message: message.Message) -> bytes:
    json_format.ParseDict(json.loads(json_data), proto_message)
    return proto_message.SerializeToString()


def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    return text + bytes([padding_length] * padding_length)


def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    aes = AES.new(key, AES.MODE_CBC, iv)
    return aes.encrypt(pad(plaintext))


def decode_protobuf(encoded_data: bytes, message_type: message.Message):
    msg = message_type()
    msg.ParseFromString(encoded_data)
    return msg


async def getAccess_Token(uid: str, password: str):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"

    payload = f"uid={uid}&password={password}&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"

    headers = {
        'User-Agent': USERAGENT,
        'Content-Type': "application/x-www-form-urlencoded"
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, data=payload, headers=headers)

        if response.status_code != 200:
            raise ValueError("OAuth failed")

        data = response.json()

    return data.get("access_token", "0"), data.get("open_id", "0")


async def create_jwt(uid: str, password: str) -> Tuple[str, str, str]:
    access_token, open_id = await getAccess_Token(uid, password)

    if access_token == "0":
        raise ValueError("Failed to get access token")

    json_data = json.dumps({
        "open_id": open_id,
        "open_id_type": "4",
        "login_token": access_token,
        "orign_platform_type": "4"
    })

    proto = await json_to_proto(json_data, freefire_pb2.LoginReq())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, proto)

    url = "https://loginbp.ggblueshark.com/MajorLogin"

    headers = {
        'User-Agent': USERAGENT,
        'Content-Type': "application/octet-stream",
        'X-Unity-Version': "2018.4.11f1",
        'ReleaseVersion': RELEASEVERSION
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, data=payload, headers=headers)

        msg = json.loads(json_format.MessageToJson(
            decode_protobuf(response.content, freefire_pb2.LoginRes)
        ))

    token = msg.get("token", "0")
    region = msg.get("lockRegion", "0")
    server = msg.get("serverUrl", "0")

    if token == "0":
        raise ValueError("JWT failed")

    return f"Bearer {token}", region, server
