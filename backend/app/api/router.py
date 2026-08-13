from fastapi import APIRouter

from app.api.admin.router import router as admin_router
from app.api.auth.router import router as auth_router
from app.api.auth.email_verification_router import router as email_verification_router
from app.api.auth.password_reset_router import router as password_reset_router
from app.api.auth.password_change_router import router as password_change_router
from app.api.auth.profile_router import router as profile_router
from app.api.auth.signup_router import router as signup_router
from app.api.consultation.router import router as consultation_router
from app.api.documents.router import router as documents_router
from app.api.evaluations.router import router as evaluations_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(signup_router, prefix="/auth", tags=["auth"])
api_router.include_router(email_verification_router, prefix="/auth", tags=["auth"])
api_router.include_router(password_reset_router, prefix="/auth", tags=["auth"])
api_router.include_router(password_change_router, prefix="/auth", tags=["auth"])
api_router.include_router(profile_router, prefix="/auth", tags=["auth"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(consultation_router, prefix="/consultation", tags=["consultation"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(evaluations_router, prefix="/evaluations", tags=["evaluations"])
