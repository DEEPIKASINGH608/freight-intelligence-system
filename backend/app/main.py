from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router

app = FastAPI(
    title="Freight Intelligence System",
    version="1.0.0",
    description="AI-powered maritime freight and chartering decision system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "https://freight-intelligence-system-2qyh7ooz5-deepikasingh608s-projects.vercel.app",
        "https://freight-intelligence-system-5kf4zw6hf-deepikasingh608s-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Freight Intelligence System"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }