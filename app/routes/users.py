from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.users import UserCreate, UserResponse
from app.services.users_service import UserService
from app.core.database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    try:
        user = await service.create_user(user_data.username, user_data.email, user_data.password)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

