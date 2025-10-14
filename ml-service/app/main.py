from fastapi import FastAPI
app = FastAPI()

@app.post("/process")
async def process_audio(file_url: str, genre: str):
    # TODO: загрузка файла, инференс, загрузка результата
    return {"status": "ok", "output_url": "https://..."}
