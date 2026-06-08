from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
import schemas
from crud import create_user, create_ingredient, create_recipe, create_meal_plan, create_rating, create_favorite
from models import UserRole, IngredientCategory, RecipeCategory, Difficulty, Goal, Allergen


def seed_all(db: Session):
    if db.query(models.User).count() > 0:
        return False
    
    print("开始填充种子数据...")
    
    users = seed_users(db)
    print(f"已创建 {len(users)} 个用户")
    
    ingredients = seed_ingredients(db)
    print(f"已创建 {len(ingredients)} 种食材")
    
    recipes = seed_recipes(db, ingredients)
    print(f"已创建 {len(recipes)} 个食谱")
    
    meal_plans = seed_meal_plans(db, users[1], recipes)
    print(f"已创建 {len(meal_plans)} 个膳食计划")
    
    seed_ratings_favorites(db, users, recipes)
    print("已创建评分和收藏数据")
    
    print("种子数据填充完成！")
    return True


def seed_users(db: Session):
    admin = create_user(
        db,
        schemas.UserCreate(username="admin", email="admin@example.com", password="admin123456"),
        role=UserRole.ADMIN
    )
    
    user1 = create_user(
        db,
        schemas.UserCreate(username="user1", email="user1@example.com", password="user123456"),
        role=UserRole.USER
    )
    
    return [admin, user1]


def seed_ingredients(db: Session):
    ingredients_data = [
        {"name": "鸡胸肉", "category": IngredientCategory.MEAT, "calories": 165, "protein": 31, "fat": 3.6, "carbs": 0, "fiber": 0, "sodium": 74, "vitamin_a": 0, "vitamin_c": 0, "calcium": 11, "iron": 0.9, "allergens": [Allergen.NONE], "unit_price": 3.5},
        {"name": "猪瘦肉", "category": IngredientCategory.MEAT, "calories": 143, "protein": 20.5, "fat": 6.2, "carbs": 0, "fiber": 0, "sodium": 57, "vitamin_a": 0, "vitamin_c": 0, "calcium": 6, "iron": 1.1, "allergens": [Allergen.NONE], "unit_price": 4.0},
        {"name": "牛肉", "category": IngredientCategory.MEAT, "calories": 250, "protein": 26, "fat": 15, "carbs": 0, "fiber": 0, "sodium": 72, "vitamin_a": 0, "vitamin_c": 0, "calcium": 9, "iron": 2.2, "allergens": [Allergen.NONE], "unit_price": 8.0},
        {"name": "三文鱼", "category": IngredientCategory.SEAFOOD, "calories": 208, "protein": 20, "fat": 13, "carbs": 0, "fiber": 0, "sodium": 59, "vitamin_a": 40, "vitamin_c": 0, "calcium": 9, "iron": 0.5, "allergens": [Allergen.SEAFOOD], "unit_price": 12.0},
        {"name": "虾", "category": IngredientCategory.SEAFOOD, "calories": 99, "protein": 24, "fat": 0.3, "carbs": 0.2, "fiber": 0, "sodium": 111, "vitamin_a": 54, "vitamin_c": 0, "calcium": 53, "iron": 0.5, "allergens": [Allergen.SEAFOOD], "unit_price": 6.0},
        {"name": "鸡蛋", "category": IngredientCategory.EGG_DAIRY, "calories": 155, "protein": 13, "fat": 11, "carbs": 1.1, "fiber": 0, "sodium": 124, "vitamin_a": 140, "vitamin_c": 0, "calcium": 50, "iron": 1.2, "allergens": [Allergen.EGG], "unit_price": 0.8},
        {"name": "牛奶", "category": IngredientCategory.EGG_DAIRY, "calories": 61, "protein": 3.2, "fat": 3.2, "carbs": 4.8, "fiber": 0, "sodium": 43, "vitamin_a": 28, "vitamin_c": 0, "calcium": 113, "iron": 0.1, "allergens": [Allergen.DAIRY], "unit_price": 0.6},
        {"name": "酸奶", "category": IngredientCategory.EGG_DAIRY, "calories": 59, "protein": 10, "fat": 0.7, "carbs": 3.6, "fiber": 0, "sodium": 40, "vitamin_a": 27, "vitamin_c": 0, "calcium": 110, "iron": 0.1, "allergens": [Allergen.DAIRY], "unit_price": 1.5},
        {"name": "奶酪", "category": IngredientCategory.EGG_DAIRY, "calories": 402, "protein": 25, "fat": 33, "carbs": 1.3, "fiber": 0, "sodium": 621, "vitamin_a": 198, "vitamin_c": 0, "calcium": 721, "iron": 0.4, "allergens": [Allergen.DAIRY], "unit_price": 5.0},
        {"name": "西兰花", "category": IngredientCategory.VEGETABLE, "calories": 34, "protein": 2.8, "fat": 0.4, "carbs": 7, "fiber": 2.6, "sodium": 33, "vitamin_a": 31, "vitamin_c": 51, "calcium": 47, "iron": 0.7, "allergens": [Allergen.NONE], "unit_price": 2.0},
        {"name": "胡萝卜", "category": IngredientCategory.VEGETABLE, "calories": 41, "protein": 0.9, "fat": 0.2, "carbs": 10, "fiber": 2.8, "sodium": 69, "vitamin_a": 835, "vitamin_c": 5.9, "calcium": 33, "iron": 0.3, "allergens": [Allergen.NONE], "unit_price": 1.0},
        {"name": "菠菜", "category": IngredientCategory.VEGETABLE, "calories": 23, "protein": 2.9, "fat": 0.4, "carbs": 3.6, "fiber": 2.2, "sodium": 79, "vitamin_a": 469, "vitamin_c": 28, "calcium": 99, "iron": 2.7, "allergens": [Allergen.NONE], "unit_price": 1.5},
        {"name": "番茄", "category": IngredientCategory.VEGETABLE, "calories": 18, "protein": 0.9, "fat": 0.2, "carbs": 3.9, "fiber": 1.2, "sodium": 5, "vitamin_a": 42, "vitamin_c": 13.7, "calcium": 10, "iron": 0.3, "allergens": [Allergen.NONE], "unit_price": 1.2},
        {"name": "黄瓜", "category": IngredientCategory.VEGETABLE, "calories": 16, "protein": 0.6, "fat": 0.1, "carbs": 3.6, "fiber": 0.5, "sodium": 2, "vitamin_a": 5, "vitamin_c": 2.8, "calcium": 16, "iron": 0.3, "allergens": [Allergen.NONE], "unit_price": 0.8},
        {"name": "生菜", "category": IngredientCategory.VEGETABLE, "calories": 15, "protein": 1.4, "fat": 0.2, "carbs": 2.9, "fiber": 1.2, "sodium": 10, "vitamin_a": 166, "vitamin_c": 3.7, "calcium": 36, "iron": 0.9, "allergens": [Allergen.NONE], "unit_price": 1.0},
        {"name": "苹果", "category": IngredientCategory.FRUIT, "calories": 52, "protein": 0.3, "fat": 0.2, "carbs": 14, "fiber": 2.4, "sodium": 1, "vitamin_a": 3, "vitamin_c": 4.6, "calcium": 6, "iron": 0.1, "allergens": [Allergen.NONE], "unit_price": 1.5},
        {"name": "香蕉", "category": IngredientCategory.FRUIT, "calories": 89, "protein": 1.1, "fat": 0.3, "carbs": 23, "fiber": 2.6, "sodium": 1, "vitamin_a": 3, "vitamin_c": 8.7, "calcium": 5, "iron": 0.3, "allergens": [Allergen.NONE], "unit_price": 1.2},
        {"name": "橙子", "category": IngredientCategory.FRUIT, "calories": 47, "protein": 0.9, "fat": 0.1, "carbs": 12, "fiber": 2.4, "sodium": 0, "vitamin_a": 11, "vitamin_c": 53.2, "calcium": 40, "iron": 0.1, "allergens": [Allergen.NONE], "unit_price": 2.0},
        {"name": "蓝莓", "category": IngredientCategory.FRUIT, "calories": 57, "protein": 0.7, "fat": 0.3, "carbs": 14, "fiber": 2.4, "sodium": 1, "vitamin_a": 3, "vitamin_c": 9.7, "calcium": 6, "iron": 0.3, "allergens": [Allergen.NONE], "unit_price": 8.0},
        {"name": "燕麦", "category": IngredientCategory.GRAIN, "calories": 389, "protein": 16.9, "fat": 6.9, "carbs": 66, "fiber": 11, "sodium": 2, "vitamin_a": 0, "vitamin_c": 0, "calcium": 54, "iron": 5, "allergens": [Allergen.GLUTEN], "unit_price": 2.5},
        {"name": "糙米", "category": IngredientCategory.GRAIN, "calories": 362, "protein": 7.5, "fat": 2.7, "carbs": 76, "fiber": 3.5, "sodium": 5, "vitamin_a": 0, "vitamin_c": 0, "calcium": 33, "iron": 2, "allergens": [Allergen.NONE], "unit_price": 2.0},
        {"name": "全麦面包", "category": IngredientCategory.GRAIN, "calories": 247, "protein": 13, "fat": 3.4, "carbs": 41, "fiber": 7, "sodium": 459, "vitamin_a": 0, "vitamin_c": 0, "calcium": 121, "iron": 3.6, "allergens": [Allergen.GLUTEN], "unit_price": 1.5},
        {"name": "意大利面", "category": IngredientCategory.GRAIN, "calories": 371, "protein": 13, "fat": 1.5, "carbs": 75, "fiber": 2.5, "sodium": 6, "vitamin_a": 0, "vitamin_c": 0, "calcium": 21, "iron": 2.5, "allergens": [Allergen.GLUTEN], "unit_price": 2.0},
        {"name": "橄榄油", "category": IngredientCategory.SEASONING, "calories": 884, "protein": 0, "fat": 100, "carbs": 0, "fiber": 0, "sodium": 1, "vitamin_a": 0, "vitamin_c": 0, "calcium": 0, "iron": 0, "allergens": [Allergen.NONE], "unit_price": 10.0},
        {"name": "酱油", "category": IngredientCategory.SEASONING, "calories": 53, "protein": 8, "fat": 0.1, "carbs": 4.9, "fiber": 0.1, "sodium": 5605, "vitamin_a": 0, "vitamin_c": 0, "calcium": 18, "iron": 2.2, "allergens": [Allergen.SOY], "unit_price": 0.5},
        {"name": "盐", "category": IngredientCategory.SEASONING, "calories": 0, "protein": 0, "fat": 0, "carbs": 0, "fiber": 0, "sodium": 38758, "vitamin_a": 0, "vitamin_c": 0, "calcium": 24, "iron": 0.3, "allergens": [Allergen.NONE], "unit_price": 0.1},
        {"name": "黑胡椒", "category": IngredientCategory.SEASONING, "calories": 251, "protein": 10, "fat": 3.3, "carbs": 64, "fiber": 25, "sodium": 27, "vitamin_a": 15, "vitamin_c": 0, "calcium": 443, "iron": 14.3, "allergens": [Allergen.NONE], "unit_price": 1.0},
        {"name": "杏仁", "category": IngredientCategory.NUT, "calories": 579, "protein": 21, "fat": 50, "carbs": 22, "fiber": 12, "sodium": 1, "vitamin_a": 1, "vitamin_c": 0, "calcium": 264, "iron": 3.7, "allergens": [Allergen.NUT], "unit_price": 8.0},
        {"name": "核桃", "category": IngredientCategory.NUT, "calories": 654, "protein": 15, "fat": 65, "carbs": 14, "fiber": 7, "sodium": 2, "vitamin_a": 1, "vitamin_c": 1.3, "calcium": 98, "iron": 2.9, "allergens": [Allergen.NUT], "unit_price": 10.0},
        {"name": "花生", "category": IngredientCategory.NUT, "calories": 567, "protein": 25.8, "fat": 49.2, "carbs": 16.1, "fiber": 8.5, "sodium": 18, "vitamin_a": 0, "vitamin_c": 0, "calcium": 92, "iron": 4.6, "allergens": [Allergen.NUT], "unit_price": 5.0},
        {"name": "南瓜", "category": IngredientCategory.VEGETABLE, "calories": 26, "protein": 1, "fat": 0.1, "carbs": 6.5, "fiber": 0.5, "sodium": 1, "vitamin_a": 148, "vitamin_c": 9, "calcium": 16, "iron": 0.4, "allergens": [Allergen.NONE], "unit_price": 1.5},
        {"name": "草莓", "category": IngredientCategory.FRUIT, "calories": 32, "protein": 0.7, "fat": 0.3, "carbs": 7.7, "fiber": 2, "sodium": 1, "vitamin_a": 1, "vitamin_c": 58.8, "calcium": 16, "iron": 0.4, "allergens": [Allergen.NONE], "unit_price": 6.0},
    ]
    
    ingredients = []
    for data in ingredients_data:
        ingredient = create_ingredient(db, schemas.IngredientCreate(**data))
        ingredients.append(ingredient)
    
    return ingredients


def seed_recipes(db: Session, ingredients):
    ing_map = {ing.name: ing for ing in ingredients}
    
    recipes_data = [
        {
            "name": "香煎鸡胸肉沙拉",
            "category": RecipeCategory.LUNCH,
            "cook_time": 25,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "鸡胸肉切片，用盐和黑胡椒腌制10分钟", "duration": 10},
                {"order": 2, "description": "平底锅加橄榄油，中火煎鸡胸肉至两面金黄", "duration": 8},
                {"order": 3, "description": "西兰花焯水，生菜、番茄、黄瓜洗净切好", "duration": 5},
                {"order": 4, "description": "所有食材摆盘，淋上少许橄榄油即可", "duration": 2}
            ],
            "tags": ["高蛋白", "低脂", "健身餐"],
            "servings": 1,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["鸡胸肉"].id, "amount": 150},
                {"ingredient_id": ing_map["西兰花"].id, "amount": 100},
                {"ingredient_id": ing_map["生菜"].id, "amount": 50},
                {"ingredient_id": ing_map["番茄"].id, "amount": 80},
                {"ingredient_id": ing_map["黄瓜"].id, "amount": 60},
                {"ingredient_id": ing_map["橄榄油"].id, "amount": 10},
                {"ingredient_id": ing_map["盐"].id, "amount": 2},
                {"ingredient_id": ing_map["黑胡椒"].id, "amount": 1}
            ]
        },
        {
            "name": "燕麦牛奶粥",
            "category": RecipeCategory.BREAKFAST,
            "cook_time": 15,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "燕麦片倒入碗中，加入牛奶", "duration": 2},
                {"order": 2, "description": "微波炉加热2-3分钟或小火煮沸", "duration": 5},
                {"order": 3, "description": "加入蓝莓和切片香蕉搅拌均匀", "duration": 3},
                {"order": 4, "description": "可根据口味加入少许蜂蜜", "duration": 2}
            ],
            "tags": ["健康", "早餐", "快手"],
            "servings": 1,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["燕麦"].id, "amount": 50},
                {"ingredient_id": ing_map["牛奶"].id, "amount": 200},
                {"ingredient_id": ing_map["蓝莓"].id, "amount": 30},
                {"ingredient_id": ing_map["香蕉"].id, "amount": 50}
            ]
        },
        {
            "name": "三文鱼蔬菜卷",
            "category": RecipeCategory.DINNER,
            "cook_time": 30,
            "difficulty": Difficulty.MEDIUM,
            "steps": [
                {"order": 1, "description": "三文鱼切片，用盐和黑胡椒腌制", "duration": 10},
                {"order": 2, "description": "胡萝卜、黄瓜切条，菠菜焯水", "duration": 8},
                {"order": 3, "description": "用三文鱼片卷起蔬菜条", "duration": 7},
                {"order": 4, "description": "平底锅刷少许橄榄油，煎至鱼卷变色", "duration": 5}
            ],
            "tags": ["高蛋白", "低碳水", "减脂"],
            "servings": 1,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["三文鱼"].id, "amount": 120},
                {"ingredient_id": ing_map["胡萝卜"].id, "amount": 40},
                {"ingredient_id": ing_map["黄瓜"].id, "amount": 40},
                {"ingredient_id": ing_map["菠菜"].id, "amount": 30},
                {"ingredient_id": ing_map["橄榄油"].id, "amount": 5},
                {"ingredient_id": ing_map["盐"].id, "amount": 1},
                {"ingredient_id": ing_map["黑胡椒"].id, "amount": 1}
            ]
        },
        {
            "name": "番茄鸡蛋意面",
            "category": RecipeCategory.LUNCH,
            "cook_time": 35,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "烧水煮意大利面至八分熟", "duration": 12},
                {"order": 2, "description": "鸡蛋打散，番茄切块", "duration": 5},
                {"order": 3, "description": "热锅下油，炒熟鸡蛋盛出", "duration": 3},
                {"order": 4, "description": "炒番茄出汁，加入少许水和酱油", "duration": 5},
                {"order": 5, "description": "倒入意面和鸡蛋，翻炒均匀", "duration": 5}
            ],
            "tags": ["经典", "快手", "家常菜"],
            "servings": 2,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["意大利面"].id, "amount": 100},
                {"ingredient_id": ing_map["鸡蛋"].id, "amount": 100},
                {"ingredient_id": ing_map["番茄"].id, "amount": 150},
                {"ingredient_id": ing_map["橄榄油"].id, "amount": 10},
                {"ingredient_id": ing_map["酱油"].id, "amount": 5},
                {"ingredient_id": ing_map["盐"].id, "amount": 2}
            ]
        },
        {
            "name": "希腊酸奶水果碗",
            "category": RecipeCategory.SNACK,
            "cook_time": 10,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "酸奶倒入碗中", "duration": 1},
                {"order": 2, "description": "苹果、香蕉、蓝莓洗净切好", "duration": 5},
                {"order": 3, "description": "水果摆放在酸奶上", "duration": 2},
                {"order": 4, "description": "撒上少许杏仁片", "duration": 2}
            ],
            "tags": ["健康", "零食", "甜点"],
            "servings": 1,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["酸奶"].id, "amount": 150},
                {"ingredient_id": ing_map["苹果"].id, "amount": 50},
                {"ingredient_id": ing_map["香蕉"].id, "amount": 50},
                {"ingredient_id": ing_map["蓝莓"].id, "amount": 20},
                {"ingredient_id": ing_map["杏仁"].id, "amount": 15}
            ]
        },
        {
            "name": "菠菜奶酪煎蛋卷",
            "category": RecipeCategory.BREAKFAST,
            "cook_time": 20,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "菠菜焯水挤干水分切碎", "duration": 5},
                {"order": 2, "description": "鸡蛋打散，加入盐和黑胡椒", "duration": 3},
                {"order": 3, "description": "奶酪切碎", "duration": 2},
                {"order": 4, "description": "平底锅倒油，倒入蛋液", "duration": 3},
                {"order": 5, "description": "蛋液半凝固时撒上菠菜和奶酪", "duration": 2},
                {"order": 6, "description": "卷起蛋卷，煎至两面金黄", "duration": 3}
            ],
            "tags": ["高蛋白", "早餐", "芝士"],
            "servings": 1,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["鸡蛋"].id, "amount": 100},
                {"ingredient_id": ing_map["菠菜"].id, "amount": 50},
                {"ingredient_id": ing_map["奶酪"].id, "amount": 30},
                {"ingredient_id": ing_map["橄榄油"].id, "amount": 5},
                {"ingredient_id": ing_map["盐"].id, "amount": 1},
                {"ingredient_id": ing_map["黑胡椒"].id, "amount": 1}
            ]
        },
        {
            "name": "糙米鸡胸肉炒饭",
            "category": RecipeCategory.DINNER,
            "cook_time": 40,
            "difficulty": Difficulty.MEDIUM,
            "steps": [
                {"order": 1, "description": "糙米提前浸泡，蒸熟备用", "duration": 25},
                {"order": 2, "description": "鸡胸肉切丁，用盐和黑胡椒腌制", "duration": 5},
                {"order": 3, "description": "胡萝卜、西兰花切小丁", "duration": 5},
                {"order": 4, "description": "热锅下油，炒鸡胸肉至变色", "duration": 3},
                {"order": 5, "description": "加入蔬菜丁翻炒，再加入糙米饭", "duration": 3},
                {"order": 6, "description": "加少许酱油调味，翻炒均匀", "duration": 2}
            ],
            "tags": ["高蛋白", "健身", "低碳水"],
            "servings": 2,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["糙米"].id, "amount": 100},
                {"ingredient_id": ing_map["鸡胸肉"].id, "amount": 120},
                {"ingredient_id": ing_map["胡萝卜"].id, "amount": 50},
                {"ingredient_id": ing_map["西兰花"].id, "amount": 50},
                {"ingredient_id": ing_map["橄榄油"].id, "amount": 8},
                {"ingredient_id": ing_map["酱油"].id, "amount": 5},
                {"ingredient_id": ing_map["盐"].id, "amount": 1},
                {"ingredient_id": ing_map["黑胡椒"].id, "amount": 1}
            ]
        },
        {
            "name": "鲜橙虾仁沙拉",
            "category": RecipeCategory.LUNCH,
            "cook_time": 20,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "虾仁去壳去虾线，用盐腌制", "duration": 5},
                {"order": 2, "description": "橙子去皮切块", "duration": 3},
                {"order": 3, "description": "生菜、黄瓜洗净切好", "duration": 4},
                {"order": 4, "description": "虾仁焯水至变红捞出", "duration": 3},
                {"order": 5, "description": "所有食材混合，淋上少许橄榄油", "duration": 3}
            ],
            "tags": ["低卡", "清爽", "海鲜"],
            "servings": 1,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["虾"].id, "amount": 100},
                {"ingredient_id": ing_map["橙子"].id, "amount": 100},
                {"ingredient_id": ing_map["生菜"].id, "amount": 50},
                {"ingredient_id": ing_map["黄瓜"].id, "amount": 50},
                {"ingredient_id": ing_map["橄榄油"].id, "amount": 5},
                {"ingredient_id": ing_map["盐"].id, "amount": 1}
            ]
        },
        {
            "name": "坚果能量棒",
            "category": RecipeCategory.SNACK,
            "cook_time": 45,
            "difficulty": Difficulty.MEDIUM,
            "steps": [
                {"order": 1, "description": "杏仁、核桃、花生切碎", "duration": 5},
                {"order": 2, "description": "燕麦与坚果混合", "duration": 3},
                {"order": 3, "description": "加入香蕉泥搅拌均匀", "duration": 5},
                {"order": 4, "description": "倒入烤盘中压实", "duration": 5},
                {"order": 5, "description": "烤箱180度烤25分钟", "duration": 25},
                {"order": 6, "description": "冷却后切条", "duration": 2}
            ],
            "tags": ["能量", "零食", "无麸质"],
            "servings": 4,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["燕麦"].id, "amount": 80},
                {"ingredient_id": ing_map["杏仁"].id, "amount": 30},
                {"ingredient_id": ing_map["核桃"].id, "amount": 30},
                {"ingredient_id": ing_map["花生"].id, "amount": 30},
                {"ingredient_id": ing_map["香蕉"].id, "amount": 100}
            ]
        },
        {
            "name": "牛肉西兰花",
            "category": RecipeCategory.DINNER,
            "cook_time": 30,
            "difficulty": Difficulty.MEDIUM,
            "steps": [
                {"order": 1, "description": "牛肉切片，用酱油、黑胡椒腌制", "duration": 10},
                {"order": 2, "description": "西兰花切小朵，焯水备用", "duration": 5},
                {"order": 3, "description": "热锅下油，大火快炒牛肉至变色", "duration": 3},
                {"order": 4, "description": "加入西兰花快速翻炒", "duration": 3},
                {"order": 5, "description": "加少许盐调味即可", "duration": 2}
            ],
            "tags": ["高蛋白", "增肌", "低碳水"],
            "servings": 2,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["牛肉"].id, "amount": 150},
                {"ingredient_id": ing_map["西兰花"].id, "amount": 150},
                {"ingredient_id": ing_map["橄榄油"].id, "amount": 10},
                {"ingredient_id": ing_map["酱油"].id, "amount": 8},
                {"ingredient_id": ing_map["盐"].id, "amount": 2},
                {"ingredient_id": ing_map["黑胡椒"].id, "amount": 2}
            ]
        },
        {
            "name": "全麦三明治",
            "category": RecipeCategory.BREAKFAST,
            "cook_time": 15,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "全麦面包烤至表面微焦", "duration": 3},
                {"order": 2, "description": "煎一个荷包蛋", "duration": 3},
                {"order": 3, "description": "番茄、生菜洗净切片", "duration": 4},
                {"order": 4, "description": "面包上依次铺生菜、番茄、鸡蛋、奶酪", "duration": 3},
                {"order": 5, "description": "盖上另一片面包，对角切开", "duration": 2}
            ],
            "tags": ["快手", "早餐", "便携"],
            "servings": 1,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["全麦面包"].id, "amount": 60},
                {"ingredient_id": ing_map["鸡蛋"].id, "amount": 50},
                {"ingredient_id": ing_map["番茄"].id, "amount": 40},
                {"ingredient_id": ing_map["生菜"].id, "amount": 20},
                {"ingredient_id": ing_map["奶酪"].id, "amount": 20},
                {"ingredient_id": ing_map["橄榄油"].id, "amount": 3}
            ]
        },
        {
            "name": "南瓜胡萝卜汤",
            "category": RecipeCategory.SOUP,
            "cook_time": 40,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "南瓜、胡萝卜去皮切块", "duration": 8},
                {"order": 2, "description": "加水煮至软烂", "duration": 20},
                {"order": 3, "description": "用搅拌机打成泥", "duration": 5},
                {"order": 4, "description": "加盐和黑胡椒调味", "duration": 3},
                {"order": 5, "description": "撒上少许杏仁片装饰", "duration": 2}
            ],
            "tags": ["素食", "暖身", "低卡"],
            "servings": 2,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["南瓜"].id, "amount": 200},
                {"ingredient_id": ing_map["胡萝卜"].id, "amount": 100},
                {"ingredient_id": ing_map["杏仁"].id, "amount": 10},
                {"ingredient_id": ing_map["盐"].id, "amount": 2},
                {"ingredient_id": ing_map["黑胡椒"].id, "amount": 1}
            ]
        },
        {
            "name": "蓝莓酸奶冰淇淋",
            "category": RecipeCategory.DESSERT,
            "cook_time": 240,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "蓝莓洗净沥干", "duration": 5},
                {"order": 2, "description": "酸奶与蓝莓混合搅拌", "duration": 5},
                {"order": 3, "description": "倒入容器，放入冰箱冷冻", "duration": 210},
                {"order": 4, "description": "每隔30分钟搅拌一次，共搅拌3次", "duration": 15}
            ],
            "tags": ["健康", "甜点", "低卡"],
            "servings": 2,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["酸奶"].id, "amount": 200},
                {"ingredient_id": ing_map["蓝莓"].id, "amount": 50}
            ]
        },
        {
            "name": "香煎猪排配蔬菜",
            "category": RecipeCategory.DINNER,
            "cook_time": 35,
            "difficulty": Difficulty.MEDIUM,
            "steps": [
                {"order": 1, "description": "猪瘦肉用刀背拍松，用盐和黑胡椒腌制", "duration": 15},
                {"order": 2, "description": "西兰花、胡萝卜切好焯水", "duration": 8},
                {"order": 3, "description": "平底锅加油，中火煎猪排至两面金黄", "duration": 8},
                {"order": 4, "description": "猪排出锅静置3分钟后切片", "duration": 3},
                {"order": 5, "description": "摆盘配上蔬菜即可", "duration": 1}
            ],
            "tags": ["高蛋白", "增肌", "主食"],
            "servings": 1,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["猪瘦肉"].id, "amount": 150},
                {"ingredient_id": ing_map["西兰花"].id, "amount": 100},
                {"ingredient_id": ing_map["胡萝卜"].id, "amount": 50},
                {"ingredient_id": ing_map["橄榄油"].id, "amount": 8},
                {"ingredient_id": ing_map["盐"].id, "amount": 2},
                {"ingredient_id": ing_map["黑胡椒"].id, "amount": 2}
            ]
        },
        {
            "name": "苹果核桃燕麦杯",
            "category": RecipeCategory.SNACK,
            "cook_time": 10,
            "difficulty": Difficulty.EASY,
            "steps": [
                {"order": 1, "description": "燕麦片用少许牛奶泡软", "duration": 3},
                {"order": 2, "description": "苹果切丁，核桃压碎", "duration": 4},
                {"order": 3, "description": "杯底铺一层燕麦", "duration": 1},
                {"order": 4, "description": "交替铺上酸奶、苹果丁、核桃碎", "duration": 2}
            ],
            "tags": ["健康", "零食", "分层"],
            "servings": 1,
            "recipe_ingredients": [
                {"ingredient_id": ing_map["燕麦"].id, "amount": 30},
                {"ingredient_id": ing_map["酸奶"].id, "amount": 100},
                {"ingredient_id": ing_map["苹果"].id, "amount": 80},
                {"ingredient_id": ing_map["核桃"].id, "amount": 15},
                {"ingredient_id": ing_map["牛奶"].id, "amount": 30}
            ]
        }
    ]
    
    recipes = []
    for data in recipes_data:
        recipe = create_recipe(db, schemas.RecipeCreate(**data))
        recipes.append(recipe)
    
    return recipes


def seed_meal_plans(db: Session, user, recipes):
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=6)
    
    recipe_categories = {}
    for recipe in recipes:
        if recipe.category not in recipe_categories:
            recipe_categories[recipe.category] = []
        recipe_categories[recipe.category].append(recipe)
    
    meal_type_map = {
        "早餐": RecipeCategory.BREAKFAST,
        "午餐": RecipeCategory.LUNCH,
        "晚餐": RecipeCategory.DINNER,
        "加餐": RecipeCategory.SNACK
    }
    
    items = []
    for day in range(7):
        current_date = start_date + timedelta(days=day)
        for meal_type, category in meal_type_map.items():
            if category in recipe_categories and recipe_categories[category]:
                recipe_idx = (day * 4 + len(items)) % len(recipe_categories[category])
                items.append(schemas.MealPlanItemCreate(
                    date=current_date,
                    meal_type=meal_type,
                    recipe_id=recipe_categories[category][recipe_idx].id
                ))
    
    mp_create = schemas.MealPlanCreate(
        name="示例一周减脂计划",
        start_date=start_date,
        end_date=end_date,
        goal=Goal.FAT_LOSS,
        target_calories=1800,
        target_protein=120,
        items=items
    )
    
    meal_plan = create_meal_plan(db, mp_create, user.id)
    return [meal_plan]


def seed_ratings_favorites(db: Session, users, recipes):
    ratings_data = [
        (1, 0, 5, "非常健康美味！"),
        (1, 1, 5, "早餐首选，简单又营养"),
        (1, 2, 4, "味道不错，稍微有点复杂"),
        (1, 3, 5, "经典口味，全家都爱"),
        (1, 4, 4, "小零食很健康"),
        (1, 5, 5, "芝士蛋卷超级香！"),
        (1, 6, 4, "健身必备餐"),
        (1, 7, 5, "清爽解腻，夏天吃正好"),
        (1, 8, 4, "能量棒很顶饿"),
        (1, 9, 5, "牛肉超嫩"),
        (1, 10, 4, "快手早餐"),
        (1, 11, 5, "暖乎乎的超舒服"),
        (1, 12, 4, "健康甜点"),
        (1, 13, 5, "猪排外焦里嫩"),
        (1, 14, 4, "颜值很高"),
    ]
    
    for user_idx, recipe_idx, score, comment in ratings_data:
        create_rating(db, schemas.RatingCreate(
            recipe_id=recipes[recipe_idx].id,
            score=score,
            comment=comment
        ), users[user_idx].id)
    
    favorite_recipes = [0, 1, 3, 5, 9, 13]
    for recipe_idx in favorite_recipes:
        create_favorite(db, schemas.FavoriteCreate(
            recipe_id=recipes[recipe_idx].id
        ), users[1].id)
