from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
import jwt

from db import get_db, User, Transaction  # sesuaikan dengan project Anda

SECRET_KEY = "YOUR_SECRET_KEY"
ALGORITHM = "HS256"

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ========== SCHEMAS ==========
class UserAdminOut(BaseModel):
    id: int
    username: str
    email: Optional[str]
    saldo: int
    kuota: Optional[int]
    is_active: bool
    role: Optional[str]

    class Config:
        orm_mode = True

class EditUserRequest(BaseModel):
    username: Optional[str]
    email: Optional[str]
    saldo: Optional[int]
    kuota: Optional[int]
    is_active: Optional[bool]
    role: Optional[str]

class CreateUserRequest(BaseModel):
    username: str
    email: Optional[str]
    password: str
    saldo: Optional[int] = 0
    kuota: Optional[int] = 0
    role: Optional[str] = "user"
    is_active: Optional[bool] = True

class KuotaRequest(BaseModel):
    kuota: int

class TransactionAdminOut(BaseModel):
    id: int
    user_id: int
    type: str
    amount: int
    timestamp: str

    class Config:
        orm_mode = True

# ========== AUTH ADMIN ONLY ==========
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

def admin_required(current_user: User = Depends(get_current_user)):
    if getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=403, detail="Hanya admin yang boleh mengakses menu ini.")
    return current_user

# ========== ENDPOINTS ADMIN ==========

# List all users
@router.get("/users", response_model=List[UserAdminOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    return db.query(User).all()

# Create user
@router.post("/users", response_model=UserAdminOut)
def create_user(request: CreateUserRequest, db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    if db.query(User).filter_by(username=request.username).first():
        raise HTTPException(status_code=400, detail="Username sudah terdaftar")
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_pw = pwd_context.hash(request.password)
    new_user = User(
        username=request.username,
        email=request.email,
        password=hashed_pw,
        saldo=request.saldo,
        kuota=request.kuota,
        role=request.role,
        is_active=request.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Edit user (by id)
@router.put("/users/{user_id}", response_model=UserAdminOut)
def edit_user(
    user_id: int,
    request: EditUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    for attr, value in request.dict(exclude_unset=True).items():
        setattr(user, attr, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Hapus user
@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    db.delete(user)
    db.commit()
    return {"msg": "User berhasil dihapus"}

# Edit kuota user (by id, endpoint khusus)
@router.put("/users/{user_id}/kuota", response_model=UserAdminOut)
def edit_kuota(
    user_id: int,
    req: KuotaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    user.kuota = req.kuota
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# List transaksi semua user / per user
@router.get("/transaksi", response_model=List[TransactionAdminOut])
def list_all_transaction(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    q = db.query(Transaction)
    if user_id:
        q = q.filter(Transaction.user_id == user_id)
    return q.order_by(Transaction.timestamp.desc()).all()

# (Optional) Aktif/nonaktifkan user
@router.put("/users/{user_id}/aktifkan", response_model=UserAdminOut)
def aktifkan_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.put("/users/{user_id}/nonaktifkan", response_model=UserAdminOut)
def nonaktifkan_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
