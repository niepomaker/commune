import os 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from requests import request
import commune as c
from dotenv import load_dotenv
import uvicorn
import base64
import requests
load_dotenv()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.post("/")
def speech2text(input_data: str):
    URL=os.getenv("URL") or 'https://speech2text-agentartificial.ngrok.app/speech2text'
    API_KEY=os.getenv("API_KEY")
    payload = {
        'data': input_data,
        }
    
    payload = {'data': input_data}
    
    result = requests.post(
        url=URL,
        json=payload,
        timeout=6000, 
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        )
    with open("output.text", "w", encoding="utf-8") as f:
        f.writelines(result.text)

    return result.text


def main(input_path='in/actionplan-commune-manager.wav'):
    with open(input_path, "rb") as f:
        base64_data =base64.b64encode(f.read()).decode("utf-8")
        speech2text(base64_data)


def run():
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
if __name__ == "__main__":
    run()
