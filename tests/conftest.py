"""共享 fixture 与数据构造器。

此处使用纯内存 SQLite，避免污染项目 ``data/`` 目录下的真实数据库；
也不依赖 ``seed.py`` 已经写入的现成数据。
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 让测试可以直接 import 项目根目录下的模块
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database import Base  # noqa: E402
import models  # noqa: E402


@pytest.fixture()
def db() -> Session:
    """每个测试一个独立的内存 SQLite 会话。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# ---------- 数据构造器 ----------

def make_ingredient(
    db: Session,
    name: str = "测试食材",
    category: models.IngredientCategory = models.IngredientCategory.VEGETABLE,
    calories: float = 100.0,
    protein: float = 10.0,
    fat: float = 5.0,
    carbs: float = 15.0,
    fiber: float = 1.0,
    sodium: float = 10.0,
    vitamin_a: float = 5.0,
    vitamin_c: float = 5.0,
    calcium: float = 20.0,
    iron: float = 1.0,
    allergens: Optional[List[models.Allergen]] = None,
    unit_price: float = 5.0,
) -> models.Ingredient:
    ing = models.Ingredient(
        name=name,
        category=category,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        fiber=fiber,
        sodium=sodium,
        vitamin_a=vitamin_a,
        vitamin_c=vitamin_c,
        calcium=calcium,
        iron=iron,
        allergens=[a.value for a in (allergens or [])],
        unit_price=unit_price,
    )
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


def make_recipe(
    db: Session,
    name: str,
    ingredients: List[tuple],  # [(Ingredient, amount_g), ...]
    servings: int = 1,
    category: models.RecipeCategory = models.RecipeCategory.LUNCH,
    cook_time: int = 30,
    difficulty: models.Difficulty = models.Difficulty.EASY,
) -> models.Recipe:
    """Servings 通过 ORM 直接写入，可绕过 schema 校验，用于测试 0/负数兜底。"""
    recipe = models.Recipe(
        name=name,
        category=category,
        cook_time=cook_time,
        difficulty=difficulty,
        steps=[{"order": 1, "description": "step", "duration": 0}],
        tags=[],
        servings=servings,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    for ing, amount in ingredients:
        ri = models.RecipeIngredient(
            recipe_id=recipe.id, ingredient_id=ing.id, amount=amount
        )
        db.add(ri)
    db.commit()
    db.refresh(recipe)
    return recipe


def make_user(db: Session, username: str = "tester") -> models.User:
    user = models.User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="x",
        role=models.UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
