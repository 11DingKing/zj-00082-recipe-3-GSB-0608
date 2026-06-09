import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import models


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def make_ingredient(db_session):
    def _make(name, category=models.IngredientCategory.VEGETABLE,
              calories=0.0, protein=0.0, fat=0.0, carbs=0.0,
              fiber=0.0, sodium=0.0, vitamin_a=0.0, vitamin_c=0.0,
              calcium=0.0, iron=0.0, allergens=None, unit_price=0.0):
        ing = models.Ingredient(
            name=name, category=category,
            calories=calories, protein=protein, fat=fat, carbs=carbs,
            fiber=fiber, sodium=sodium, vitamin_a=vitamin_a, vitamin_c=vitamin_c,
            calcium=calcium, iron=iron,
            allergens=allergens if allergens is not None else [],
            unit_price=unit_price
        )
        db_session.add(ing)
        db_session.commit()
        db_session.refresh(ing)
        return ing
    return _make


@pytest.fixture
def make_recipe(db_session):
    def _make(name, category=models.RecipeCategory.LUNCH, cook_time=30,
              difficulty=models.Difficulty.EASY, steps=None, tags=None,
              servings=1, recipe_ingredients=None):
        if steps is None:
            steps = [{"order": 1, "description": "test", "duration": 10}]
        if tags is None:
            tags = []
        recipe = models.Recipe(
            name=name, category=category, cook_time=cook_time,
            difficulty=difficulty, steps=steps, tags=tags, servings=servings
        )
        db_session.add(recipe)
        db_session.commit()
        db_session.refresh(recipe)

        if recipe_ingredients:
            for ing_data in recipe_ingredients:
                ri = models.RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ing_data["ingredient"].id,
                    amount=ing_data["amount"]
                )
                db_session.add(ri)
            db_session.commit()
            db_session.refresh(recipe)

        return recipe
    return _make


@pytest.fixture
def make_user(db_session):
    def _make(username="testuser", email="test@example.com", password="password123",
              role=models.UserRole.USER):
        from crud import get_password_hash
        user = models.User(
            username=username, email=email,
            hashed_password=get_password_hash(password),
            role=role
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _make
