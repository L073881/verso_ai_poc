from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/process")
async def process_webhook(request: Request):
    data = await request.json()

    print("\n🔥 JIRA WEBHOOK RECEIVED 🔥")
    print(data)

    # Always respond so Jira doesn't retry
    return {"status": "received", "ok": True}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
