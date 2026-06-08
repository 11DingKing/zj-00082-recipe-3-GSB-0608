from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class IngredientCategory(str, enum.Enum):
    VEGETABLE = "蔬菜"
    FRUIT = "水果"
    MEAT = "肉类"
    SEAFOOD = "海鲜"
    EGG_DAIRY = "蛋奶"
    GRAIN = "谷物"
    SEASONING = "调味料"
    NUT = "坚果"


class Allergen(str, enum.Enum):
    GLUTEN = "含麸质"
    DAIRY = "含乳制品"
    NUT = "含坚果"
    SEAFOOD = "含海鲜"
    EGG = "含蛋"
    SOY = "含大豆"
    NONE = "无"


class RecipeCategory(str, enum.Enum):
    BREAKFAST = "早餐"
    LUNCH = "午餐"
    DINNER = "晚餐"
    SNACK = "加餐"
    DESSERT = "甜品"
    SOUP = "汤品"


class Difficulty(str, enum.Enum):
    EASY = "简单"
    MEDIUM = "中等"
    HARD = "困难"


class Goal(str, enum.Enum):
    FAT_LOSS = "减脂"
    MUSCLE_GAIN = "增肌"
    MAINTENANCE = "维持"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(200), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    favorites = relationship("Favorite", back_populates="user")
    ratings = relationship("Rating", back_populates="user")
    meal_plans = relationship("MealPlan", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    diet_logs = relationship("DietLog", back_populates="user")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(Enum(IngredientCategory), nullable=False)
    calories = Column(Float, nullable=False, comment="每100g热量 kcal")
    protein = Column(Float, nullable=False, comment="每100g蛋白质 g")
    fat = Column(Float, nullable=False, comment="每100g脂肪 g")
    carbs = Column(Float, nullable=False, comment="每100g碳水 g")
    fiber = Column(Float, default=0, comment="每100g膳食纤维 g")
    sodium = Column(Float, default=0, comment="每100g钠 mg")
    vitamin_a = Column(Float, default=0, comment="每100g维生素 A μg")
    vitamin_c = Column(Float, default=0, comment="每100g维生素 C mg")
    calcium = Column(Float, default=0, comment="每100g钙 mg")
    iron = Column(Float, default=0, comment="每100g铁 mg")
    allergens = Column(JSON, default=list, comment="过敏原列表")
    unit_price = Column(Float, nullable=False, comment="每100g单位价格 元")
    created_at = Column(DateTime, default=datetime.utcnow)

    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, index=True, nullable=False)
    category = Column(Enum(RecipeCategory), nullable=False)
    cook_time = Column(Integer, nullable=False, comment="烹饪时长 分钟")
    difficulty = Column(Enum(Difficulty), nullable=False)
    steps = Column(JSON, nullable=False, comment="步骤：[{order, description, duration}]")
    tags = Column(JSON, default=list, comment="标签列表")
    servings = Column(Integer, default=1, comment="份量")
    created_at = Column(DateTime, default=datetime.utcnow)

    recipe_ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="recipe")
    ratings = relationship("Rating", back_populates="recipe")
    meal_plan_items = relationship("MealPlanItem", back_populates="recipe")
    comments = relationship("Comment", back_populates="recipe")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    amount = Column(Float, nullable=False, comment="用量 g")

    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    recipe = relationship("Recipe", back_populates="favorites")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    score = Column(Integer, nullable=False, comment="评分 1-5")
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ratings")
    recipe = relationship("Recipe", back_populates="ratings")


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    goal = Column(Enum(Goal), nullable=False)
    target_calories = Column(Float, nullable=False)
    target_protein = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="meal_plans")
    items = relationship("MealPlanItem", back_populates="meal_plan", cascade="all, delete-orphan")


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id = Column(Integer, primary_key=True, index=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    meal_type = Column(String(50), nullable=False, comment="早餐/午餐/晚餐/加餐")
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

    meal_plan = relationship("MealPlan", back_populates="items")
    recipe = relationship("Recipe", back_populates="meal_plan_items")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    content = Column(Text, nullable=False, comment="评论内容")
    like_count = Column(Integer, default=0, comment="点赞数")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="comments")
    recipe = relationship("Recipe", back_populates="comments")


class MealType(str, enum.Enum):
    BREAKFAST = "早餐"
    LUNCH = "午餐"
    DINNER = "晚餐"
    SNACK = "加餐"


class DietLog(Base):
    __tablename__ = "diet_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False, comment="日期")
    meal_type = Column(Enum(MealType), nullable=False, comment="餐次")
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True, comment="食谱ID（可选）")
    custom_food = Column(String(200), nullable=True, comment="自定义食物名称")
    actual_calories = Column(Float, nullable=False, comment="实际摄入热量 kcal")
    actual_protein = Column(Float, nullable=False, comment="实际摄入蛋白质 g")
    actual_fat = Column(Float, nullable=False, comment="实际摄入脂肪 g")
    actual_carbs = Column(Float, nullable=False, comment="实际摄入碳水 g")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="diet_logs")
    recipe = relationship("Recipe")
