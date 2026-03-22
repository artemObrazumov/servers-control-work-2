from fastapi import FastAPI, HTTPException, Query, Request, Response, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import uuid
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from datetime import datetime, timedelta
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = Field(None, gt=0)
    is_subscribed: Optional[bool] = None

@app.post("/create_user")
def create_user(user: UserCreate):
    return user

sample_products = [
    {"product_id": 123, "name": "Smartphone", "category": "Electronics", "price": 599.99},
    {"product_id": 456, "name": "Phone Case", "category": "Accessories", "price": 19.99},
    {"product_id": 789, "name": "Iphone", "category": "Electronics", "price": 1299.99},
    {"product_id": 101, "name": "Headphones", "category": "Accessories", "price": 99.99},
    {"product_id": 202, "name": "Smartwatch", "category": "Electronics", "price": 299.99}
]

@app.get("/product/{product_id}")
def get_product(product_id: int):
    for product in sample_products:
        if product["product_id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")

@app.get("/products/search")
def search_products(keyword: str, category: Optional[str] = None, limit: int = 10):
    results = [p for p in sample_products if keyword.lower() in p['name'].lower() and (category is None or p['category'].lower() == category.lower())]
    return results[:limit]

SECRET_KEY = "your-secret-key"
serializer = URLSafeTimedSerializer(SECRET_KEY)

class LoginData(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(data: LoginData, response: Response):
    if data.username == "artem" and data.password == "123456":
        user_id = str(uuid.uuid4())
        session_data = {"user_id": user_id, "timestamp": time.time()}
        session_token = serializer.dumps(session_data)
        response.set_cookie(key="session_token", value=session_token, httponly=True, max_age=300, secure=False)
        return {"message": "Logged in successfully"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

def get_current_user(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        session_data = serializer.loads(session_token, max_age=300)
        now = time.time()
        last_activity = session_data.get("timestamp", 0)

        if now - last_activity >= 180 and now - last_activity < 300:
             session_data["timestamp"] = now
             new_token = serializer.dumps(session_data)
             response.set_cookie(key="session_token", value=new_token, httponly=True, max_age=300, secure=False)

        return session_data
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired")
    except BadTimeSignature:
        raise HTTPException(status_code=401, detail="Invalid session")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")


@app.get("/user")
def get_user(current_user: dict = Depends(get_current_user)):
    return {"user_id": current_user.get("user_id"), "message": "This is a protected route"}

@app.get("/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    return {"user_id": current_user.get("user_id"), "message": "User profile information"}


@app.get("/headers")
def read_headers(user_agent: str = Header(None), accept_language: str = Header(None)):
    if not user_agent or not accept_language:
        raise HTTPException(status_code=400, detail="Missing required headers")
    return {"User-Agent": user_agent, "Accept-Language": accept_language}


class CommonHeaders(BaseModel):
    user_agent: str = Field(..., alias="User-Agent")
    accept_language: str = Field(..., alias="Accept-Language")


@app.get("/info")
def info(response: Response, headers: CommonHeaders = Depends()):
    response.headers["X-Server-Time"] = str(datetime.now())
    return {
        "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
        "headers": headers.dict(by_alias=True)
    }

@app.get("/headers_model")
def read_headers_model(headers: CommonHeaders = Depends()):
    return headers.dict(by_alias=True)
