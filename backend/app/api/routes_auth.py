import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from app.models.schemas import UserRegisterRequest, UserLoginRequest, AuthResponse, UserResponse
from app.storage.repository import Repository
from app.core.security import hash_password, verify_password, generate_session_token

router = APIRouter(prefix="/auth", tags=["auth"])

def get_current_user_from_header(authorization: Optional[str] = Header(None)) -> Optional[UserResponse]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    return Repository.get_session_user(token)

@router.post("/register", response_model=AuthResponse)
def register_user(req: UserRegisterRequest):
    clean_username = req.username.strip().lower().replace(" ", "_")
    clean_email = req.email.strip().lower()

    if not clean_username or len(clean_username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters long.")
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="Valid email address is required.")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    # Check for duplicate username or email
    if Repository.get_user_by_username(clean_username):
        raise HTTPException(status_code=400, detail=f"Username '{clean_username}' is already registered.")
    if Repository.get_user_by_email(clean_email):
        raise HTTPException(status_code=400, detail=f"Email '{clean_email}' is already registered.")

    pw_hash, pw_salt = hash_password(req.password)
    user_id = f"user_{uuid.uuid4().hex[:10]}"

    user = Repository.create_user(
        user_id=user_id,
        username=clean_username,
        display_name=req.display_name.strip() or clean_username,
        email=clean_email,
        password_hash=pw_hash,
        password_salt=pw_salt,
        avatar_color=req.avatar_color or "#38bdf8",
        bio=req.bio.strip() if req.bio else "Personal Memory Lane Archive"
    )

    token = generate_session_token()
    Repository.create_session(token=token, user_id=user.id)

    return AuthResponse(token=token, user=user)

@router.post("/login", response_model=AuthResponse)
def login_user(req: UserLoginRequest):
    identifier = req.username_or_email.strip()
    raw_user = Repository.get_raw_user_for_auth(identifier)

    if not raw_user:
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    stored_hash = raw_user.get("password_hash")
    stored_salt = raw_user.get("password_salt")

    # If demo seed user didn't have password set, allow 'password123' or set it
    if not stored_hash or not stored_salt:
        if req.password == "password123":
            # auto-upgrade seed user password
            new_hash, new_salt = hash_password(req.password)
            from app.core.database import get_db
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?;",
                    (new_hash, new_salt, raw_user["id"])
                )
            stored_hash, stored_salt = new_hash, new_salt
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials. Use 'password123' for seeded accounts.")

    if not verify_password(req.password, stored_hash, stored_salt):
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    user = Repository.get_user(raw_user["id"])
    if not user:
        raise HTTPException(status_code=500, detail="Failed to load user profile.")

    token = generate_session_token()
    Repository.create_session(token=token, user_id=user.id)

    return AuthResponse(token=token, user=user)

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication token required.")
    token = authorization.replace("Bearer ", "").strip()
    user = Repository.get_session_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")
    return user

@router.post("/logout")
def logout_user(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        Repository.delete_session(token)
    return {"status": "logged_out"}
