from fastapi import FastAPI, Request


app = FastAPI(title="Backup Model Mock")


@app.post("/generate")
async def generate(request: Request):
    body = await request.json()

    prompt = body.get("prompt", "")

    return {
        "provider": "backup",
        "text": f"Backup response for: {prompt}",
    }