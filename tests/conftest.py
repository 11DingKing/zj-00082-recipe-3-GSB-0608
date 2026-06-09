import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import models
import schemas
import crud


@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def create_test_ingredient(db):
    def _create_ingredient(name, category, calories, protein, fat, carbs, **kwargs):
        ingredient_data = schemas.IngredientCreate(
            name=name,
            category=category,
            calories=calories,
            protein=protein,
            fat=fat,
            carbs=carbs,
            unit_price=kwargs.get("unit_price", 1.0),
            fiber=kwargs.get("fiber", 0),
            sodium=kwargs.get("sodium", 0),
            vitamin_a=kwargs.get("vitamin_a", 0),
            vitamin_c=kwargs.get("vitamin_c", 0),
            calcium=kwargs.get("calcium", 0),
            iron=kwargs.get("iron", 0),
            allergens=kwargs.get("allergens", [])
        )
        return crud.create_ingredient(db, ingredient_data)
    return _create_ingredient


@pytest.fixture
def create_test_recipe(db):
    def _create_recipe(name, category, cook_time, difficulty, steps, recipe_ingredients, **kwargs):
        recipe_data = schemas.RecipeCreate(
            name=name,
            category=category,
            cook_time=cook_time,
            difficulty=difficulty,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            tags=kwargs.get("tags", []),
            servings=kwargs.get("servings", 1)
        )
        return crud.create_recipe(db, recipe_data)
    return _create_recipe


@pytest.fixture
def create_test_user(db):
    def _create_user(username="testuser", password="testpass123", email="test@example.com"):
        user_data = schemas.UserCreate(
            username=username,
            password=password,
            email=email
        )
        return crud.create_user(db, user_data)
    return _create_user
