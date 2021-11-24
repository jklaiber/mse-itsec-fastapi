import html
from typing import List, Optional
from sqlalchemy.orm import Session

from passlib.hash import argon2
from .models import Item, User
from .schemas import ItemCreate, UserCreate


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def get_users_encoded(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    users = []
    for user in db.query(User).offset(skip).limit(limit).all():
        user.name = html.escape(user.name)
        user.email = html.escape(user.email)
        users.append(user)
    return users


def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        name=user.name, email=user.email, hashed_password=argon2.hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_items(db: Session, skip: int = 0, limit: int = 100) -> List[Item]:
    return db.query(Item).offset(skip).limit(limit).all()


def create_user_item(db: Session, item: ItemCreate, user_id: int) -> Item:
    db_item = Item(**item.dict(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_user_by_name_safe1(db: Session, name: str) -> Optional[User]:
    return db.query(User).filter(User.name == name).first()


def get_user_by_name_safe2(db: Session, name: str) -> Optional[User]:
    sql_statement: str = "SELECT * FROM users WHERE name = :name "
    return db.execute(sql_statement, {"name": name}).first()


def get_user_by_name_unsafe(db: Session, name: str) -> Optional[User]:
    return db.execute(f"SELECT * FROM users WHERE name = '{name}'").all()


def delete_user_by_id(db: Session, id: int) -> None:
    db.query(User).filter(User.id == id).delete()
    db.commit()


def _verify_password(user: User, password: str) -> bool:
    # Take a look for more information of passlib and why we have choosen Argon2 -> https://passlib.readthedocs.io/en/stable/narr/quickstart.html#the-options
    return argon2.verify(password, user.hashed_password)


def authenticate_user(username: str, password: str, db: Session) -> Optional[User]:
    user: Optional[User] = get_user_by_name_safe1(db, username)
    if user and _verify_password(user, password):
        return user
