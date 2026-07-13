from fastapi import FastAPI, Query, HTTPException
import httpx
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/info")
async def get_info(
    uid: str = Query(..., description="Account UID"),
    password: str = Query(..., description="Account Password")
):
    # 1. Call JWT API
    jwt_url = f"https://jwtguest.up.railway.app/semy?uid={uid}&password={password}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            jwt_resp = await client.get(jwt_url)
            jwt_resp.raise_for_status()
            jwt_data = jwt_resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=400, detail=f"JWT API returned {e.response.status_code}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"JWT API request failed: {str(e)}")

    if not jwt_data.get("success", False):
        raise HTTPException(status_code=400, detail="Account was ban or wrong uid password")

    account_uid = jwt_data.get("account_uid")
    if not account_uid:
        payload = jwt_data.get("jwt_decoded", {}).get("payload", {})
        account_uid = payload.get("account_id")
        if account_uid is not None:
            account_uid = str(account_uid)

    if not account_uid:
        raise HTTPException(status_code=400, detail="Could not extract account ID from JWT response")

    # 2. Call new Info API (updated endpoint)
    info_url = f"https://ff-info.up.railway.app/info?uid={account_uid}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            info_resp = await client.get(info_url)
            info_resp.raise_for_status()
            info_data = info_resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=400, detail=f"Info API returned {e.response.status_code}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Info API request failed: {str(e)}")

    # Extract fields from the new API response structure
    # The data is nested under "basicInfo" key
    if "basicInfo" not in info_data:
        raise HTTPException(status_code=400, detail="Invalid response structure from Info API")
    
    basic_info = info_data["basicInfo"]
    
    # Extract the required fields
    account_id = basic_info.get("accountId")
    level = basic_info.get("level")
    nickname = basic_info.get("nickname")
    region = basic_info.get("region")

    if not account_id:
        raise HTTPException(status_code=400, detail="Info API did not return accountId")

    # Return final response - only the requested fields
    return {
        "accountId": account_id,
        "level": level,
        "nickname": nickname,
        "region": region
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
