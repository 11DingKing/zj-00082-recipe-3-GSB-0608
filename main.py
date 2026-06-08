from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import List, Optional
import uvicorn

from database import engine, get_db, Base
from models import User, UserRole, Ingredient, Recipe, RecipeIngredient, MealPlan, Favorite, Rating, Goal, Allergen, Comment, DietLog
import schemas
from crud import (
    get_user_by_username, authenticate_user,
    get_ingredient, get_ingredients, create_ingredient, update_ingredient, delete_ingredient,
    get_recipe, get_recipes, create_recipe, update_recipe, delete_recipe,
    calculate_recipe_nutrition, check_allergens,
    get_user_favorites, create_favorite, delete_favorite,
    get_recipe_ratings, create_rating,
    get_meal_plan, get_user_meal_plans, create_meal_plan, delete_meal_plan, generate_meal_plan,
    generate_shopping_list, get_statistics,
    get_comment, get_recipe_comments, create_comment, update_comment, delete_comment, like_comment,
    get_ingredient_substitutes,
    get_diet_log, get_user_diet_logs, create_diet_log, update_diet_log, delete_diet_log, get_weekly_summary
)
from seed import seed_all

SECRET_KEY = "your-secret-key-keep-it-in-env-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

Base.metadata.create_all(bind=engine)

with Session(engine) as db:
    seed_all(db)

app = FastAPI(title="食谱与营养计算服务", version="1.0.0")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user


async def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can perform this action")
    return current_user


@app.post("/token", response_model=schemas.Token, tags=["认证"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@app.get("/users/me", response_model=schemas.User, tags=["用户"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/ingredients", response_model=List[schemas.Ingredient], tags=["食材"])
def read_ingredients(
    skip: int = 0, 
    limit: int = 100, 
    category: Optional[schemas.IngredientCategory] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ingredients = get_ingredients(db, skip=skip, limit=limit, category=category)
    return ingredients


@app.get("/ingredients/{ingredient_id}", response_model=schemas.Ingredient, tags=["食材"])
def read_ingredient(ingredient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_ingredient = get_ingredient(db, ingredient_id=ingredient_id)
    if db_ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return db_ingredient


@app.post("/ingredients", response_model=schemas.Ingredient, tags=["食材"])
def create_new_ingredient(
    ingredient: schemas.IngredientCreate, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    return create_ingredient(db=db, ingredient=ingredient)


@app.put("/ingredients/{ingredient_id}", response_model=schemas.Ingredient, tags=["食材"])
def update_existing_ingredient(
    ingredient_id: int, 
    ingredient: schemas.IngredientUpdate, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    db_ingredient = update_ingredient(db, ingredient_id=ingredient_id, ingredient=ingredient)
    if db_ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return db_ingredient


@app.delete("/ingredients/{ingredient_id}", response_model=schemas.Message, tags=["食材"])
def delete_existing_ingredient(
    ingredient_id: int, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    db_ingredient = delete_ingredient(db, ingredient_id=ingredient_id)
    if db_ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return {"message": "Ingredient deleted successfully"}


@app.get("/recipes", response_model=List[schemas.Recipe], tags=["食谱"])
def read_recipes(
    skip: int = 0, 
    limit: int = 100, 
    category: Optional[schemas.RecipeCategory] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recipes = get_recipes(db, skip=skip, limit=limit, category=category, tag=tag)
    return recipes


@app.get("/recipes/{recipe_id}", response_model=schemas.Recipe, tags=["食谱"])
def read_recipe(recipe_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_recipe = get_recipe(db, recipe_id=recipe_id)
    if db_recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return db_recipe


@app.post("/recipes", response_model=schemas.Recipe, tags=["食谱"])
def create_new_recipe(
    recipe: schemas.RecipeCreate, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    return create_recipe(db=db, recipe=recipe)


@app.put("/recipes/{recipe_id}", response_model=schemas.Recipe, tags=["食谱"])
def update_existing_recipe(
    recipe_id: int, 
    recipe: schemas.RecipeUpdate, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    db_recipe = update_recipe(db, recipe_id=recipe_id, recipe=recipe)
    if db_recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return db_recipe


@app.delete("/recipes/{recipe_id}", response_model=schemas.Message, tags=["食谱"])
def delete_existing_recipe(
    recipe_id: int, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    db_recipe = delete_recipe(db, recipe_id=recipe_id)
    if db_recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"message": "Recipe deleted successfully"}


@app.get("/recipes/{recipe_id}/nutrition", response_model=schemas.NutritionSummary, tags=["营养计算"])
def get_recipe_nutrition(
    recipe_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    nutrition = calculate_recipe_nutrition(db, recipe_id=recipe_id)
    if nutrition is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return nutrition


@app.get("/recipes/{recipe_id}/allergens", response_model=schemas.AllergenCheckResponse, tags=["过敏原检测"])
def check_recipe_allergens_get(
    recipe_id: int,
    allergens: Optional[List[Allergen]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = check_allergens(db, recipe_id=recipe_id, user_allergens=allergens)
    if result is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return result


@app.post("/recipes/check-allergens", response_model=schemas.AllergenCheckResponse, tags=["过敏原检测"])
def check_recipe_allergens_post(
    request: schemas.AllergenCheckRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = check_allergens(db, recipe_id=request.recipe_id, user_allergens=request.user_allergens)
    if result is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return result


@app.get("/favorites", response_model=List[schemas.Favorite], tags=["收藏"])
def read_favorites(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_user_favorites(db, user_id=current_user.id, skip=skip, limit=limit)


@app.post("/favorites", response_model=schemas.Favorite, tags=["收藏"])
def add_favorite(
    favorite: schemas.FavoriteCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_favorite(db, favorite=favorite, user_id=current_user.id)


@app.delete("/favorites/{recipe_id}", response_model=schemas.Message, tags=["收藏"])
def remove_favorite(
    recipe_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_favorite = delete_favorite(db, user_id=current_user.id, recipe_id=recipe_id)
    if db_favorite is None:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"message": "Favorite deleted successfully"}


@app.get("/recipes/{recipe_id}/ratings", response_model=List[schemas.Rating], tags=["评分"])
def read_recipe_ratings(
    recipe_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_recipe_ratings(db, recipe_id=recipe_id, skip=skip, limit=limit)


@app.post("/ratings", response_model=schemas.Rating, tags=["评分"])
def add_rating(
    rating: schemas.RatingCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_rating(db, rating=rating, user_id=current_user.id)


@app.get("/meal-plans", response_model=List[schemas.MealPlan], tags=["膳食计划"])
def read_meal_plans(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_user_meal_plans(db, user_id=current_user.id, skip=skip, limit=limit)


@app.post("/meal-plans", response_model=schemas.MealPlan, tags=["膳食计划"])
def add_meal_plan(
    meal_plan: schemas.MealPlanCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_meal_plan(db, meal_plan=meal_plan, user_id=current_user.id)


@app.delete("/meal-plans/{meal_plan_id}", response_model=schemas.Message, tags=["膳食计划"])
def remove_meal_plan(
    meal_plan_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_mp = delete_meal_plan(db, meal_plan_id=meal_plan_id)
    if db_mp is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return {"message": "Meal plan deleted successfully"}


@app.post("/meal-plans/generate", response_model=schemas.MealPlan, tags=["膳食计划"])
def generate_new_meal_plan(
    generate_data: schemas.MealPlanGenerate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meal_plan = generate_meal_plan(db, user_id=current_user.id, generate_data=generate_data)
    if meal_plan is None:
        raise HTTPException(status_code=400, detail="Not enough recipes to generate meal plan")
    return meal_plan


@app.get("/meal-plans/{meal_plan_id}/shopping-list", response_model=schemas.ShoppingListResponse, tags=["购物清单"])
def get_meal_plan_shopping_list(
    meal_plan_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shopping_list = generate_shopping_list(db, meal_plan_id=meal_plan_id)
    if shopping_list is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return shopping_list


@app.get("/statistics", response_model=schemas.StatisticsResponse, tags=["统计"])
def get_system_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_statistics(db, user_id=current_user.id)


@app.get("/recipes/{recipe_id}/comments", response_model=List[schemas.Comment], tags=["评论"])
def read_recipe_comments(
    recipe_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_recipe_comments(db, recipe_id=recipe_id, skip=skip, limit=limit)


@app.post("/recipes/{recipe_id}/comments", response_model=schemas.Comment, tags=["评论"])
def add_recipe_comment(
    recipe_id: int,
    comment: schemas.CommentBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment_create = schemas.CommentCreate(recipe_id=recipe_id, content=comment.content)
    return create_comment(db, comment=comment_create, user_id=current_user.id)


@app.put("/comments/{comment_id}", response_model=schemas.Comment, tags=["评论"])
def update_recipe_comment(
    comment_id: int,
    comment: schemas.CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_comment = update_comment(db, comment_id=comment_id, comment=comment, user_id=current_user.id)
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found or not authorized")
    return db_comment


@app.delete("/comments/{comment_id}", response_model=schemas.Message, tags=["评论"])
def delete_recipe_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_comment = delete_comment(db, comment_id=comment_id, user_id=current_user.id)
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found or not authorized")
    return {"message": "Comment deleted successfully"}


@app.post("/comments/{comment_id}/like", response_model=schemas.Comment, tags=["评论"])
def like_recipe_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_comment = like_comment(db, comment_id=comment_id)
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return db_comment


@app.get("/ingredients/{ingredient_id}/substitutes", response_model=List[schemas.IngredientSubstitute], tags=["食材替换"])
def read_ingredient_substitutes(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    substitutes = get_ingredient_substitutes(db, ingredient_id=ingredient_id)
    if substitutes is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    result = []
    for sub in substitutes:
        ing = sub["ingredient"]
        result.append({
            "id": ing.id,
            "name": ing.name,
            "category": ing.category,
            "calories": ing.calories,
            "protein": ing.protein,
            "fat": ing.fat,
            "carbs": ing.carbs,
            "similarity_score": sub["similarity_score"]
        })
    return result


@app.get("/diet-logs", response_model=List[schemas.DietLog], tags=["饮食日记"])
def read_diet_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_user_diet_logs(db, user_id=current_user.id, skip=skip, limit=limit)


@app.get("/diet-logs/{diet_log_id}", response_model=schemas.DietLog, tags=["饮食日记"])
def read_diet_log(
    diet_log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_diet_log = get_diet_log(db, diet_log_id=diet_log_id)
    if db_diet_log is None or db_diet_log.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Diet log not found")
    return db_diet_log


@app.post("/diet-logs", response_model=schemas.DietLog, tags=["饮食日记"])
def add_diet_log(
    diet_log: schemas.DietLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_diet_log(db, diet_log=diet_log, user_id=current_user.id)


@app.put("/diet-logs/{diet_log_id}", response_model=schemas.DietLog, tags=["饮食日记"])
def update_diet_log_entry(
    diet_log_id: int,
    diet_log: schemas.DietLogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_diet_log = update_diet_log(db, diet_log_id=diet_log_id, diet_log=diet_log, user_id=current_user.id)
    if db_diet_log is None:
        raise HTTPException(status_code=404, detail="Diet log not found or not authorized")
    return db_diet_log


@app.delete("/diet-logs/{diet_log_id}", response_model=schemas.Message, tags=["饮食日记"])
def delete_diet_log_entry(
    diet_log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_diet_log = delete_diet_log(db, diet_log_id=diet_log_id, user_id=current_user.id)
    if db_diet_log is None:
        raise HTTPException(status_code=404, detail="Diet log not found or not authorized")
    return {"message": "Diet log deleted successfully"}


@app.get("/diet-logs/weekly-summary", response_model=schemas.WeeklySummary, tags=["饮食日记"])
def read_weekly_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_weekly_summary(db, user_id=current_user.id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
