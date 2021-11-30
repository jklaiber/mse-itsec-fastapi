import os

from typing import List
from fastapi import Depends, FastAPI, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from jose import jwt
from . import crud, models, schemas
from .database import SessionLocal, engine
from pydantic import BaseModel

class CsrfSettings(BaseModel):
    secret_key:str = 'test_secret123' #put somewhere safe

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

JWT_SECRET = os.getenv("JWT_SECRET", "jwttoken")

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/token")
def generate_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = crud.authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    else:
        user = schemas.User.from_orm(user)
        return {
            "access_token": jwt.encode(user.dict(), JWT_SECRET),
            "token_type": "bearer",
        }

@app.get("/csrftoken/")
async def get_csrf_token(csrf_protect:CsrfProtect = Depends()):
    response = JSONResponse(status_code=200, content ={'csrf_token':'cookie'})
    csrf_protect.set_csrf_cookie(response)
    return response

@app.get("/users/myself", response_model=schemas.User)
def get_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db), csrf_protect:CsrfProtect = Depends()):
    csrf_protect.validate_csrf_in_cookies(request)
    payload = jwt.decode(token, JWT_SECRET)
    user = crud.get_user(db, payload.get("id"))
    return user

@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(status_code=exc.status_code, content = {'detail':exc.message})    


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)


@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


# Used to prevent stored XSS attack
# @app.get("/usersencoded/", response_model=List[schemas.User])
# def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     users = crud.get_users_encoded(db, skip=skip, limit=limit)
#     return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user_by_id(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


# Used for demo for SQLInjection
# @app.get("/users/safe1/{name}", response_model=schemas.User)
# def read_user_by_name_safe1(name: str, db: Session = Depends(get_db)):
#     db_user = crud.get_user_by_name_safe1(db=db, name=name)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user


# Used for demo for SQLInjection
# @app.get("/users/safe2/{name}", response_model=schemas.User)
# def read_user_by_name_safe2(name: str, db: Session = Depends(get_db)):
#     db_user = crud.get_user_by_name_safe2(db=db, name=name)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user


# Used for demo for SQLInjection
# @app.get("/users/unsafe/{name}")
# def read_user_by_name_unsafe(name: str, db: Session = Depends(get_db)):
#     db_user = crud.get_user_by_name_unsafe(db=db, name=name)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user


@app.delete("/user/{user_id}")
def delete_user_by_id(id: int, db: Session = Depends(get_db)):
    crud.delete_user_by_id(db, id)
    return f"User with id {id} successfully deleted"


@app.post("/users/{user_id}/items/", response_model=schemas.Item)
def create_item_for_user(
    user_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)
):
    return crud.create_user_item(db=db, item=item, user_id=user_id)


@app.get("/items/", response_model=List[schemas.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = crud.get_items(db, skip=skip, limit=limit)
    return items
