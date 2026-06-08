from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
import models
import schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate, role: models.UserRole = models.UserRole.USER):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_ingredient(db: Session, ingredient_id: int):
    return db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()


def get_ingredient_by_name(db: Session, name: str):
    return db.query(models.Ingredient).filter(models.Ingredient.name == name).first()


def get_ingredients(db: Session, skip: int = 0, limit: int = 100, category: Optional[models.IngredientCategory] = None):
    query = db.query(models.Ingredient)
    if category:
        query = query.filter(models.Ingredient.category == category)
    return query.offset(skip).limit(limit).all()


def create_ingredient(db: Session, ingredient: schemas.IngredientCreate):
    db_ingredient = models.Ingredient(**ingredient.model_dump())
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    return db_ingredient


def update_ingredient(db: Session, ingredient_id: int, ingredient: schemas.IngredientUpdate):
    db_ingredient = get_ingredient(db, ingredient_id)
    if db_ingredient:
        for key, value in ingredient.model_dump().items():
            setattr(db_ingredient, key, value)
        db.commit()
        db.refresh(db_ingredient)
    return db_ingredient


def delete_ingredient(db: Session, ingredient_id: int):
    db_ingredient = get_ingredient(db, ingredient_id)
    if db_ingredient:
        db.delete(db_ingredient)
        db.commit()
    return db_ingredient


def get_recipe_avg_rating(db: Session, recipe_id: int):
    result = db.query(func.avg(models.Rating.score)).filter(models.Rating.recipe_id == recipe_id).scalar()
    return float(result) if result else None


def get_recipe_favorite_count(db: Session, recipe_id: int):
    return db.query(models.Favorite).filter(models.Favorite.recipe_id == recipe_id).count()


def get_recipe(db: Session, recipe_id: int):
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if recipe:
        recipe.average_rating = get_recipe_avg_rating(db, recipe_id)
        recipe.favorite_count = get_recipe_favorite_count(db, recipe_id)
    return recipe


def get_recipe_by_name(db: Session, name: str):
    return db.query(models.Recipe).filter(models.Recipe.name == name).first()


def get_recipes(db: Session, skip: int = 0, limit: int = 100, category: Optional[models.RecipeCategory] = None, tag: Optional[str] = None):
    query = db.query(models.Recipe)
    if category:
        query = query.filter(models.Recipe.category == category)
    if tag:
        query = query.filter(models.Recipe.tags.contains([tag]))
    recipes = query.offset(skip).limit(limit).all()
    for recipe in recipes:
        recipe.average_rating = get_recipe_avg_rating(db, recipe.id)
        recipe.favorite_count = get_recipe_favorite_count(db, recipe.id)
    return recipes


def create_recipe(db: Session, recipe: schemas.RecipeCreate):
    recipe_data = recipe.model_dump()
    recipe_ingredients_data = recipe_data.pop("recipe_ingredients")
    db_recipe = models.Recipe(**recipe_data)
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    
    for ri_data in recipe_ingredients_data:
        db_ri = models.RecipeIngredient(recipe_id=db_recipe.id, **ri_data)
        db.add(db_ri)
    
    db.commit()
    db.refresh(db_recipe)
    db_recipe.average_rating = None
    db_recipe.favorite_count = 0
    return db_recipe


def update_recipe(db: Session, recipe_id: int, recipe: schemas.RecipeUpdate):
    db_recipe = get_recipe(db, recipe_id)
    if db_recipe:
        recipe_data = recipe.model_dump()
        recipe_ingredients_data = recipe_data.pop("recipe_ingredients")
        
        for key, value in recipe_data.items():
            setattr(db_recipe, key, value)
        
        db.query(models.RecipeIngredient).filter(models.RecipeIngredient.recipe_id == recipe_id).delete()
        
        for ri_data in recipe_ingredients_data:
            db_ri = models.RecipeIngredient(recipe_id=recipe_id, **ri_data)
            db.add(db_ri)
        
        db.commit()
        db.refresh(db_recipe)
        db_recipe.average_rating = get_recipe_avg_rating(db, recipe_id)
        db_recipe.favorite_count = get_recipe_favorite_count(db, recipe_id)
    return db_recipe


def delete_recipe(db: Session, recipe_id: int):
    db_recipe = get_recipe(db, recipe_id)
    if db_recipe:
        db.delete(db_recipe)
        db.commit()
    return db_recipe


def calculate_recipe_nutrition(db: Session, recipe_id: int):
    db_recipe = get_recipe(db, recipe_id)
    if not db_recipe:
        return None
    
    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0
    total_fiber = 0
    total_sodium = 0
    total_vitamin_a = 0
    total_vitamin_c = 0
    total_calcium = 0
    total_iron = 0
    
    for ri in db_recipe.recipe_ingredients:
        ingredient = ri.ingredient
        factor = ri.amount / 100.0
        total_calories += ingredient.calories * factor
        total_protein += ingredient.protein * factor
        total_fat += ingredient.fat * factor
        total_carbs += ingredient.carbs * factor
        total_fiber += ingredient.fiber * factor
        total_sodium += ingredient.sodium * factor
        total_vitamin_a += ingredient.vitamin_a * factor
        total_vitamin_c += ingredient.vitamin_c * factor
        total_calcium += ingredient.calcium * factor
        total_iron += ingredient.iron * factor
    
    servings = db_recipe.servings if db_recipe.servings > 0 else 1
    
    return schemas.NutritionSummary(
        total_calories=round(total_calories, 2),
        total_protein=round(total_protein, 2),
        total_fat=round(total_fat, 2),
        total_carbs=round(total_carbs, 2),
        total_fiber=round(total_fiber, 2),
        total_sodium=round(total_sodium, 2),
        total_vitamin_a=round(total_vitamin_a, 2),
        total_vitamin_c=round(total_vitamin_c, 2),
        total_calcium=round(total_calcium, 2),
        total_iron=round(total_iron, 2),
        per_serving={
            "calories": round(total_calories / servings, 2),
            "protein": round(total_protein / servings, 2),
            "fat": round(total_fat / servings, 2),
            "carbs": round(total_carbs / servings, 2),
            "fiber": round(total_fiber / servings, 2),
            "sodium": round(total_sodium / servings, 2),
            "vitamin_a": round(total_vitamin_a / servings, 2),
            "vitamin_c": round(total_vitamin_c / servings, 2),
            "calcium": round(total_calcium / servings, 2),
            "iron": round(total_iron / servings, 2)
        }
    )


def check_allergens(db: Session, recipe_id: int, user_allergens: List[models.Allergen]):
    db_recipe = get_recipe(db, recipe_id)
    if not db_recipe:
        return None
    
    if not user_allergens or models.Allergen.NONE in user_allergens:
        return schemas.AllergenCheckResponse(
            has_allergen=False,
            triggering_ingredients=[],
            recipe_id=recipe_id,
            recipe_name=db_recipe.name
        )
    
    triggering = []
    for ri in db_recipe.recipe_ingredients:
        ingredient = ri.ingredient
        common_allergens = [a for a in ingredient.allergens if a in user_allergens and a != models.Allergen.NONE]
        if common_allergens:
            triggering.append({
                "ingredient_id": ingredient.id,
                "ingredient_name": ingredient.name,
                "allergens": common_allergens
            })
    
    return schemas.AllergenCheckResponse(
        has_allergen=len(triggering) > 0,
        triggering_ingredients=triggering,
        recipe_id=recipe_id,
        recipe_name=db_recipe.name
    )


def get_favorite(db: Session, user_id: int, recipe_id: int):
    return db.query(models.Favorite).filter(
        models.Favorite.user_id == user_id,
        models.Favorite.recipe_id == recipe_id
    ).first()


def get_user_favorites(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    favorites = db.query(models.Favorite).filter(models.Favorite.user_id == user_id).offset(skip).limit(limit).all()
    for fav in favorites:
        fav.recipe.average_rating = get_recipe_avg_rating(db, fav.recipe.id)
        fav.recipe.favorite_count = get_recipe_favorite_count(db, fav.recipe.id)
    return favorites


def create_favorite(db: Session, favorite: schemas.FavoriteCreate, user_id: int):
    existing = get_favorite(db, user_id, favorite.recipe_id)
    if existing:
        return existing
    db_favorite = models.Favorite(user_id=user_id, **favorite.model_dump())
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    db_favorite.recipe.average_rating = get_recipe_avg_rating(db, favorite.recipe_id)
    db_favorite.recipe.favorite_count = get_recipe_favorite_count(db, favorite.recipe_id)
    return db_favorite


def delete_favorite(db: Session, user_id: int, recipe_id: int):
    db_favorite = get_favorite(db, user_id, recipe_id)
    if db_favorite:
        db.delete(db_favorite)
        db.commit()
    return db_favorite


def get_rating(db: Session, user_id: int, recipe_id: int):
    return db.query(models.Rating).filter(
        models.Rating.user_id == user_id,
        models.Rating.recipe_id == recipe_id
    ).first()


def get_recipe_ratings(db: Session, recipe_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Rating).filter(models.Rating.recipe_id == recipe_id).offset(skip).limit(limit).all()


def create_rating(db: Session, rating: schemas.RatingCreate, user_id: int):
    existing = get_rating(db, user_id, rating.recipe_id)
    if existing:
        existing.score = rating.score
        existing.comment = rating.comment
        db.commit()
        db.refresh(existing)
        return existing
    db_rating = models.Rating(user_id=user_id, **rating.model_dump())
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating


def get_meal_plan(db: Session, meal_plan_id: int):
    return db.query(models.MealPlan).filter(models.MealPlan.id == meal_plan_id).first()


def get_user_meal_plans(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.MealPlan).filter(models.MealPlan.user_id == user_id).offset(skip).limit(limit).all()


def create_meal_plan(db: Session, meal_plan: schemas.MealPlanCreate, user_id: int):
    mp_data = meal_plan.model_dump()
    items_data = mp_data.pop("items")
    db_mp = models.MealPlan(user_id=user_id, **mp_data)
    db.add(db_mp)
    db.commit()
    db.refresh(db_mp)
    
    for item_data in items_data:
        db_item = models.MealPlanItem(meal_plan_id=db_mp.id, **item_data)
        db.add(db_item)
    
    db.commit()
    db.refresh(db_mp)
    return db_mp


def delete_meal_plan(db: Session, meal_plan_id: int):
    db_mp = get_meal_plan(db, meal_plan_id)
    if db_mp:
        db.delete(db_mp)
        db.commit()
    return db_mp


def generate_meal_plan(db: Session, user_id: int, generate_data: schemas.MealPlanGenerate):
    recipes = get_recipes(db)
    if not recipes:
        return None
    
    recipe_nutrition = {}
    for recipe in recipes:
        nutrition = calculate_recipe_nutrition(db, recipe.id)
        if nutrition:
            recipe_nutrition[recipe.id] = {
                "recipe": recipe,
                "nutrition": nutrition,
                "per_serving_calories": nutrition.per_serving["calories"],
                "per_serving_protein": nutrition.per_serving["protein"]
            }
    
    meal_types = ["早餐", "午餐", "晚餐", "加餐"]
    items = []
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    min_calories_range = generate_data.target_calories * 0.9
    max_calories_range = generate_data.target_calories * 1.1
    target_protein = generate_data.target_protein
    
    for day in range(generate_data.days):
        current_date = start_date + timedelta(days=day)
        
        best_combination = None
        best_score = float('inf')
        
        recipe_list = list(recipe_nutrition.values())
        
        from itertools import product
        
        max_combinations = 5000
        combination_count = 0
        
        for combo in product(recipe_list, repeat=len(meal_types)):
            combination_count += 1
            if combination_count > max_combinations:
                break
            
            total_calories = sum(r["per_serving_calories"] for r in combo)
            total_protein = sum(r["per_serving_protein"] for r in combo)
            
            calories_ok = min_calories_range <= total_calories <= max_calories_range
            protein_ok = total_protein >= target_protein
            
            calories_diff = abs(total_calories - generate_data.target_calories)
            protein_diff = max(0, target_protein - total_protein)
            
            score = calories_diff * 2 + protein_diff * 10
            
            if calories_ok and protein_ok:
                score -= 1000
            
            if score < best_score:
                best_score = score
                best_combination = combo
        
        if best_combination is None:
            for meal_type in meal_types:
                selected = recipe_list[0]
                items.append(schemas.MealPlanItemCreate(
                    date=current_date,
                    meal_type=meal_type,
                    recipe_id=selected["recipe"].id
                ))
        else:
            for i, meal_type in enumerate(meal_types):
                selected = best_combination[i]
                items.append(schemas.MealPlanItemCreate(
                    date=current_date,
                    meal_type=meal_type,
                    recipe_id=selected["recipe"].id
                ))
    
    end_date = start_date + timedelta(days=generate_data.days - 1)
    
    mp_create = schemas.MealPlanCreate(
        name=f"智能{generate_data.days}天{generate_data.goal.value}计划",
        start_date=start_date,
        end_date=end_date,
        goal=generate_data.goal,
        target_calories=generate_data.target_calories,
        target_protein=generate_data.target_protein,
        items=items
    )
    
    return create_meal_plan(db, mp_create, user_id)


def generate_shopping_list(db: Session, meal_plan_id: int):
    db_mp = get_meal_plan(db, meal_plan_id)
    if not db_mp:
        return None
    
    ingredient_amounts = {}
    
    for item in db_mp.items:
        recipe = get_recipe(db, item.recipe_id)
        if recipe:
            for ri in recipe.recipe_ingredients:
                ing_id = ri.ingredient.id
                if ing_id not in ingredient_amounts:
                    ingredient_amounts[ing_id] = {
                        "ingredient": ri.ingredient,
                        "amount": 0
                    }
                ingredient_amounts[ing_id]["amount"] += ri.amount
    
    items_by_category = {}
    total_price = 0
    
    for ing_data in ingredient_amounts.values():
        ingredient = ing_data["ingredient"]
        amount = ing_data["amount"]
        price = (amount / 100.0) * ingredient.unit_price
        total_price += price
        
        category = ingredient.category.value
        if category not in items_by_category:
            items_by_category[category] = []
        
        items_by_category[category].append(schemas.ShoppingListItem(
            ingredient_id=ingredient.id,
            ingredient_name=ingredient.name,
            category=ingredient.category,
            total_amount=round(amount, 2),
            estimated_price=round(price, 2)
        ))
    
    return schemas.ShoppingListResponse(
        items_by_category=items_by_category,
        total_estimated_price=round(total_price, 2),
        meal_plan_id=meal_plan_id,
        meal_plan_name=db_mp.name
    )


def get_statistics(db: Session, user_id: Optional[int] = None):
    top_recipes_subquery = db.query(
        models.Rating.recipe_id,
        func.avg(models.Rating.score).label('avg_rating'),
        func.count(models.Favorite.id).label('fav_count')
    ).join(models.Favorite, models.Favorite.recipe_id == models.Rating.recipe_id, isouter=True).group_by(models.Rating.recipe_id).order_by(func.avg(models.Rating.score).desc()).limit(10).subquery()
    
    top_recipes_query = db.query(
        models.Recipe,
        top_recipes_subquery.c.avg_rating,
        top_recipes_subquery.c.fav_count
    ).join(top_recipes_subquery, models.Recipe.id == top_recipes_subquery.c.recipe_id)
    
    top_recipes = []
    for recipe, avg_rating, fav_count in top_recipes_query.all():
        top_recipes.append({
            "id": recipe.id,
            "name": recipe.name,
            "category": recipe.category.value,
            "average_rating": round(float(avg_rating), 2) if avg_rating else None,
            "favorite_count": fav_count,
            "cook_time": recipe.cook_time
        })
    
    category_counts = db.query(
        models.Recipe.category,
        func.count(models.Recipe.id)
    ).group_by(models.Recipe.category).all()
    
    recipes_by_category = {cat.value: count for cat, count in category_counts}
    
    recommended = schemas.RecommendedNutrition()
    
    user_nutrition_comparison = None
    comparison_with_recommended = None
    
    if user_id:
        user_mps = get_user_meal_plans(db, user_id, limit=1)
        if user_mps:
            mp = user_mps[0]
            total_calories = 0
            total_protein = 0
            total_fat = 0
            total_carbs = 0
            count = 0
            
            for item in mp.items:
                nutrition = calculate_recipe_nutrition(db, item.recipe_id)
                if nutrition:
                    total_calories += nutrition.per_serving["calories"]
                    total_protein += nutrition.per_serving["protein"]
                    total_fat += nutrition.per_serving["fat"]
                    total_carbs += nutrition.per_serving["carbs"]
                    count += 1
            
            if count > 0:
                avg_calories = total_calories / count * 3
                avg_protein = total_protein / count * 3
                avg_fat = total_fat / count * 3
                avg_carbs = total_carbs / count * 3
                
                user_nutrition_comparison = {
                    "target_calories": mp.target_calories,
                    "target_protein": mp.target_protein,
                    "actual_average_calories": round(avg_calories, 2),
                    "actual_average_protein": round(avg_protein, 2),
                    "calories_diff_percent": round((avg_calories - mp.target_calories) / mp.target_calories * 100, 2),
                    "protein_diff_percent": round((avg_protein - mp.target_protein) / mp.target_protein * 100, 2)
                }
                
                comparison_with_recommended = {
                    "actual_average_calories": round(avg_calories, 2),
                    "actual_average_protein": round(avg_protein, 2),
                    "actual_average_fat": round(avg_fat, 2),
                    "actual_average_carbs": round(avg_carbs, 2),
                    "calories_diff_percent": round((avg_calories - recommended.calories) / recommended.calories * 100, 2),
                    "protein_diff_percent": round((avg_protein - recommended.protein) / recommended.protein * 100, 2),
                    "fat_diff_percent": round((avg_fat - recommended.fat) / recommended.fat * 100, 2),
                    "carbs_diff_percent": round((avg_carbs - recommended.carbs) / recommended.carbs * 100, 2)
                }
    
    return schemas.StatisticsResponse(
        top_recipes=top_recipes,
        recipes_by_category=recipes_by_category,
        user_nutrition_comparison=user_nutrition_comparison,
        recommended_nutrition=recommended,
        comparison_with_recommended=comparison_with_recommended
    )


def get_comment(db: Session, comment_id: int):
    return db.query(models.Comment).filter(models.Comment.id == comment_id).first()


def get_recipe_comments(db: Session, recipe_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Comment).filter(models.Comment.recipe_id == recipe_id).order_by(models.Comment.created_at.desc()).offset(skip).limit(limit).all()


def create_comment(db: Session, comment: schemas.CommentCreate, user_id: int):
    db_comment = models.Comment(
        user_id=user_id,
        recipe_id=comment.recipe_id,
        content=comment.content
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def update_comment(db: Session, comment_id: int, comment: schemas.CommentUpdate, user_id: int):
    db_comment = get_comment(db, comment_id)
    if db_comment and db_comment.user_id == user_id:
        db_comment.content = comment.content
        db.commit()
        db.refresh(db_comment)
        return db_comment
    return None


def delete_comment(db: Session, comment_id: int, user_id: int):
    db_comment = get_comment(db, comment_id)
    if db_comment and db_comment.user_id == user_id:
        db.delete(db_comment)
        db.commit()
        return db_comment
    return None


def like_comment(db: Session, comment_id: int):
    db_comment = get_comment(db, comment_id)
    if db_comment:
        db_comment.like_count += 1
        db.commit()
        db.refresh(db_comment)
        return db_comment
    return None


def get_ingredient_substitutes(db: Session, ingredient_id: int, top_n: int = 5):
    db_ingredient = get_ingredient(db, ingredient_id)
    if not db_ingredient:
        return None
    
    candidates = db.query(models.Ingredient).filter(
        models.Ingredient.category == db_ingredient.category,
        models.Ingredient.id != ingredient_id
    ).all()
    
    substitutes = []
    for candidate in candidates:
        calories_diff = abs(candidate.calories - db_ingredient.calories) / db_ingredient.calories
        protein_diff = abs(candidate.protein - db_ingredient.protein) / db_ingredient.protein
        fat_diff = abs(candidate.fat - db_ingredient.fat) / db_ingredient.fat
        
        if calories_diff <= 0.2 and protein_diff <= 0.2 and fat_diff <= 0.2:
            similarity_score = 1 - (calories_diff + protein_diff + fat_diff) / 3
            substitutes.append({
                "ingredient": candidate,
                "similarity_score": similarity_score
            })
    
    substitutes.sort(key=lambda x: x["similarity_score"], reverse=True)
    return substitutes[:top_n]


def get_diet_log(db: Session, diet_log_id: int):
    return db.query(models.DietLog).filter(models.DietLog.id == diet_log_id).first()


def get_user_diet_logs(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.DietLog).filter(models.DietLog.user_id == user_id).order_by(models.DietLog.date.desc()).offset(skip).limit(limit).all()


def create_diet_log(db: Session, diet_log: schemas.DietLogCreate, user_id: int):
    db_diet_log = models.DietLog(user_id=user_id, **diet_log.model_dump())
    db.add(db_diet_log)
    db.commit()
    db.refresh(db_diet_log)
    return db_diet_log


def update_diet_log(db: Session, diet_log_id: int, diet_log: schemas.DietLogUpdate, user_id: int):
    db_diet_log = get_diet_log(db, diet_log_id)
    if db_diet_log and db_diet_log.user_id == user_id:
        for key, value in diet_log.model_dump().items():
            setattr(db_diet_log, key, value)
        db.commit()
        db.refresh(db_diet_log)
        return db_diet_log
    return None


def delete_diet_log(db: Session, diet_log_id: int, user_id: int):
    db_diet_log = get_diet_log(db, diet_log_id)
    if db_diet_log and db_diet_log.user_id == user_id:
        db.delete(db_diet_log)
        db.commit()
        return db_diet_log
    return None


def get_weekly_summary(db: Session, user_id: int):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    user_mps = get_user_meal_plans(db, user_id, limit=1)
    target_calories = 2000.0
    target_protein = 60.0
    target_fat = 65.0
    target_carbs = 300.0
    
    if user_mps:
        target_calories = user_mps[0].target_calories
        target_protein = user_mps[0].target_protein
    
    diet_logs = db.query(models.DietLog).filter(
        models.DietLog.user_id == user_id,
        models.DietLog.date >= week_start,
        models.DietLog.date <= week_end
    ).all()
    
    daily_data = {}
    for i in range(7):
        current_date = week_start + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        daily_data[date_str] = {
            "actual_calories": 0,
            "actual_protein": 0,
            "actual_fat": 0,
            "actual_carbs": 0
        }
    
    for log in diet_logs:
        date_str = log.date.strftime("%Y-%m-%d")
        if date_str in daily_data:
            daily_data[date_str]["actual_calories"] += log.actual_calories
            daily_data[date_str]["actual_protein"] += log.actual_protein
            daily_data[date_str]["actual_fat"] += log.actual_fat
            daily_data[date_str]["actual_carbs"] += log.actual_carbs
    
    daily_nutrition_list = []
    for date_str, data in daily_data.items():
        actual_calories = data["actual_calories"]
        actual_protein = data["actual_protein"]
        actual_fat = data["actual_fat"]
        actual_carbs = data["actual_carbs"]
        
        calories_diff_percent = ((actual_calories - target_calories) / target_calories * 100) if target_calories > 0 else 0
        protein_diff_percent = ((actual_protein - target_protein) / target_protein * 100) if target_protein > 0 else 0
        
        daily_nutrition_list.append(schemas.DailyNutrition(
            date=date_str,
            actual_calories=round(actual_calories, 2),
            actual_protein=round(actual_protein, 2),
            actual_fat=round(actual_fat, 2),
            actual_carbs=round(actual_carbs, 2),
            target_calories=round(target_calories, 2),
            target_protein=round(target_protein, 2),
            target_fat=round(target_fat, 2),
            target_carbs=round(target_carbs, 2),
            calories_diff_percent=round(calories_diff_percent, 2),
            protein_diff_percent=round(protein_diff_percent, 2)
        ))
    
    total_actual_calories = sum(d["actual_calories"] for d in daily_data.values())
    total_target_calories = target_calories * 7
    avg_actual_calories = total_actual_calories / 7 if total_actual_calories > 0 else 0
    avg_target_calories = target_calories
    
    return schemas.WeeklySummary(
        daily_data=daily_nutrition_list,
        week_start_date=week_start.strftime("%Y-%m-%d"),
        week_end_date=week_end.strftime("%Y-%m-%d"),
        avg_actual_calories=round(avg_actual_calories, 2),
        avg_target_calories=round(avg_target_calories, 2),
        total_actual_calories=round(total_actual_calories, 2),
        total_target_calories=round(total_target_calories, 2)
    )
