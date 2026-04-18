import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.websockets import websocket_router
import uvicorn

app = FastAPI(
    title="AI Dungeon Master API",
    description="FastAPI Backend for the AI Dungeon Master Web Application",
    version="1.0.0"
)

# Enable CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",       # local dev
        "https://*.vercel.app",        # Vercel preview deployments
        "https://ai-dungeon-master-coral.vercel.app",  # production Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.api.routes import api_router

app.include_router(websocket_router)
app.include_router(api_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "The AI Dungeon Master is breathing."}

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
