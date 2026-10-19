from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine
from .routers import auth, materials, chat,attendance

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="College Management API")

# --- Add this CORS block ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------

app.include_router(auth.router)
app.include_router(materials.router)
app.include_router(chat.router)
app.include_router(attendance.router)
@app.get("/")
def read_root():
    return {"message": "Welcome to the API! The server is running."}