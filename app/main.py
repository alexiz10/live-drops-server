from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from supertokens_python import get_all_cors_headers
from supertokens_python.framework.fastapi import get_middleware

from app.core.config import settings
from app.core.supertokens import init_supertokens

init_supertokens()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(get_middleware())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type"] + get_all_cors_headers(),
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
