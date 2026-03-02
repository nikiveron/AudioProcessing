from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import torch
from model import GRUSeparator
from utils import process_single_file

app = FastAPI(title="ML Audio Processor")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = GRUSeparator().to(device)

try:
    model.load_state_dict(torch.load("model_weights.pth", map_location=device))
    print("Model weights loaded.")
except FileNotFoundError:
    print("Model weights not found. Run 'python train_model.py' first.")


@app.post("/process")
async def process_audio(file: UploadFile = File(...)):
    try:
        print(f"Processing file: {file.filename}")

        input_bytes = await file.read()
        result_buf = process_single_file(model, input_bytes, device)

        result_buf.seek(0)

        return StreamingResponse(
            result_buf,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=processed_{file.filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except Exception as e:
        print(f"Processing error: {e}")
        return {"error": f"Processing failed: {str(e)}"}