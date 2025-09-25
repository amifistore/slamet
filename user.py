from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
import jwt
from passlib.context import CryptContext

from db import get_db, User, Transaction  # sesuaikan import sesuai struktur Anda

SECRET_KEY = "YOUR_SECRET_KEY"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(
    prefix="/user",
    tags=["user"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ========== SCHEMAS ==========
class UserOut(BaseModel):
    id: int
    username: str
    saldo: int
    email: Optional[str]

    class Config:
        orm_mode = True

class TopUpRequest(BaseModel):
    amount: int

class TransactionOut(BaseModel):
    id: int
    user_id: int
    type: str
    amount: int
    timestamp: str

    class Config:
        orm_mode = True

class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

# ========== HELPER FUNCTIONS ==========

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def is_user_in_group(user: User) -> bool:
    # TODO: Ganti dengan cek API Telegram/WhatsApp yang sebenarnya
    # Misal: cek user.telegram_id pada group tertentu
    # Untuk contoh, di sini selalu True (anggap user sudah join group)
    return True

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# ========== DEPENDENCY: GROUP VALIDATION ==========

def group_required(current_user: User = Depends(get_current_user)):
    if not is_user_in_group(current_user):
        raise HTTPException(
            status_code=403,
            detail="Kamu harus join channel/group terlebih dahulu untuk memakai bot ini!"
        )
    return current_user

# ========== ENDPOINTS ==========

@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(group_required)):
    return current_user

@router.post("/topup", response_model=UserOut)
def topup(request: TopUpRequest, db: Session = Depends(get_db), current_user: User = Depends(group_required)):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Nominal harus lebih dari 0")
    current_user.saldo += request.amount
    db.add(current_user)
    trx = Transaction(user_id=current_user.id, type="topup", amount=request.amount)
    db.add(trx)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/riwayat", response_model=List[TransactionOut])
def riwayat(db: Session = Depends(get_db), current_user: User = Depends(group_required)):
    transaksi = db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(Transaction.timestamp.desc()).all()
    return transaksi

@router.put("/update_profile", response_model=UserOut)
def update_profile(
    request: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(group_required)
):
    if request.username:
        current_user.username = request.username
    if request.email:
        current_user.email = request.email
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/change_password")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(group_required)
):
    if not verify_password(request.old_password, current_user.password):
        raise HTTPException(status_code=400, detail="Password lama salah!")
    current_user.password = get_password_hash(request.new_password)
    db.add(current_user)
    db.commit()
    return {"msg": "Password berhasil diubah"}
