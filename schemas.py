from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from models import UserRole, IngredientCategory, RecipeCategory, Difficulty, Goal, Allergen, MealType


class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class User(UserBase):
    id: int
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


class IngredientBase(BaseModel):
    name: str = Field(..., max_length=100)
    category: IngredientCategory
    calories: float = Field(..., ge=0, description="每100g热量 kcal")
    protein: float = Field(..., ge=0, description="每100g蛋白质 g")
    fat: float = Field(..., ge=0, description="每100g脂肪 g")
    carbs: float = Field(..., ge=0, description="每100g碳水 g")
    fiber: Optional[float] = Field(0, ge=0, description="每100g膳食纤维 g")
    sodium: Optional[float] = Field(0, ge=0, description="每100g钠 mg")
    vitamin_a: Optional[float] = Field(0, ge=0, description="每100g维生素 A μg")
    vitamin_c: Optional[float] = Field(0, ge=0, description="每100g维生素 C mg")
    calcium: Optional[float] = Field(0, ge=0, description="每100g钙 mg")
    iron: Optional[float] = Field(0, ge=0, description="每100g铁 mg")
    allergens: List[Allergen] = Field(default_factory=list)
    unit_price: float = Field(..., ge=0, description="每100g单位价格 元")


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(IngredientBase):
    pass


class Ingredient(IngredientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecipeIngredientBase(BaseModel):
    ingredient_id: int
    amount: float = Field(..., gt=0, description="用量 g")


class RecipeIngredientCreate(RecipeIngredientBase):
    pass


class RecipeIngredient(RecipeIngredientBase):
    id: int
    ingredient: Ingredient

    class Config:
        from_attributes = True


class RecipeStep(BaseModel):
    order: int
    description: str
    duration: Optional[int] = Field(0, description="时长 分钟")


class RecipeBase(BaseModel):
    name: str = Field(..., max_length=200)
    category: RecipeCategory
    cook_time: int = Field(..., gt=0, description="烹饪时长 分钟")
    difficulty: Difficulty
    steps: List[RecipeStep]
    tags: List[str] = Field(default_factory=list)
    servings: int = Field(1, ge=1, description="份量")


class RecipeCreate(RecipeBase):
    recipe_ingredients: List[RecipeIngredientCreate]


class RecipeUpdate(RecipeBase):
    recipe_ingredients: List[RecipeIngredientCreate]


class RecipeSummary(BaseModel):
    id: int
    name: str
    category: RecipeCategory
    cook_time: int
    difficulty: Difficulty
    tags: List[str]
    average_rating: Optional[float] = None
    favorite_count: int = 0

    class Config:
        from_attributes = True


class Recipe(RecipeBase):
    id: int
    created_at: datetime
    recipe_ingredients: List[RecipeIngredient]
    average_rating: Optional[float] = None
    favorite_count: int = 0

    class Config:
        from_attributes = True


class NutritionSummary(BaseModel):
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
    total_fiber: float
    total_sodium: float
    total_vitamin_a: float
    total_vitamin_c: float
    total_calcium: float
    total_iron: float
    per_serving: dict


class FavoriteBase(BaseModel):
    recipe_id: int


class FavoriteCreate(FavoriteBase):
    pass


class Favorite(FavoriteBase):
    id: int
    user_id: int
    created_at: datetime
    recipe: RecipeSummary

    class Config:
        from_attributes = True


class RatingBase(BaseModel):
    recipe_id: int
    score: int = Field(..., ge=1, le=5, description="评分 1-5")
    comment: Optional[str] = None


class RatingCreate(RatingBase):
    pass


class Rating(RatingBase):
    id: int
    user_id: int
    created_at: datetime
    user: User

    class Config:
        from_attributes = True


class MealPlanItemBase(BaseModel):
    date: datetime
    meal_type: str = Field(..., description="早餐/午餐/晚餐/加餐")
    recipe_id: int


class MealPlanItemCreate(MealPlanItemBase):
    pass


class MealPlanItem(MealPlanItemBase):
    id: int
    recipe: RecipeSummary

    class Config:
        from_attributes = True


class MealPlanBase(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    start_date: datetime
    end_date: datetime
    goal: Goal
    target_calories: float = Field(..., gt=0)
    target_protein: float = Field(..., gt=0)


class MealPlanCreate(MealPlanBase):
    items: List[MealPlanItemCreate]


class MealPlanGenerate(BaseModel):
    goal: Goal
    target_calories: float = Field(..., gt=0)
    target_protein: float = Field(..., gt=0)
    days: int = Field(7, ge=1, le=30)


class MealPlan(MealPlanBase):
    id: int
    user_id: int
    created_at: datetime
    items: List[MealPlanItem]

    class Config:
        from_attributes = True


class AllergenCheckRequest(BaseModel):
    recipe_id: int
    user_allergens: List[Allergen]


class AllergenCheckResponse(BaseModel):
    has_allergen: bool
    triggering_ingredients: List[dict]
    recipe_id: int
    recipe_name: str


class ShoppingListItem(BaseModel):
    ingredient_id: int
    ingredient_name: str
    category: IngredientCategory
    total_amount: float
    unit: str = "g"
    estimated_price: float


class ShoppingListResponse(BaseModel):
    items_by_category: dict
    total_estimated_price: float
    meal_plan_id: int
    meal_plan_name: Optional[str]


class RecommendedNutrition(BaseModel):
    calories: float = 2000
    protein: float = 60
    fat: float = 65
    carbs: float = 300


class StatisticsResponse(BaseModel):
    top_recipes: List[dict]
    recipes_by_category: dict
    user_nutrition_comparison: Optional[dict] = None
    recommended_nutrition: RecommendedNutrition
    comparison_with_recommended: Optional[dict] = None


class Message(BaseModel):
    message: str


class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class CommentCreate(CommentBase):
    recipe_id: int


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class Comment(CommentBase):
    id: int
    user_id: int
    recipe_id: int
    like_count: int
    created_at: datetime
    user: User

    class Config:
        from_attributes = True


class IngredientSubstitute(BaseModel):
    id: int
    name: str
    category: IngredientCategory
    calories: float
    protein: float
    fat: float
    carbs: float
    similarity_score: float

    class Config:
        from_attributes = True


class DietLogBase(BaseModel):
    date: datetime
    meal_type: MealType
    recipe_id: Optional[int] = None
    custom_food: Optional[str] = Field(None, max_length=200)
    actual_calories: float = Field(..., ge=0)
    actual_protein: float = Field(..., ge=0)
    actual_fat: float = Field(..., ge=0)
    actual_carbs: float = Field(..., ge=0)


class DietLogCreate(DietLogBase):
    pass


class DietLogUpdate(DietLogBase):
    pass


class DietLog(DietLogBase):
    id: int
    user_id: int
    created_at: datetime
    recipe: Optional[RecipeSummary] = None

    class Config:
        from_attributes = True


class DailyNutrition(BaseModel):
    date: str
    actual_calories: float
    actual_protein: float
    actual_fat: float
    actual_carbs: float
    target_calories: float
    target_protein: float
    target_fat: float
    target_carbs: float
    calories_diff_percent: float
    protein_diff_percent: float


class WeeklySummary(BaseModel):
    daily_data: List[DailyNutrition]
    week_start_date: str
    week_end_date: str
    avg_actual_calories: float
    avg_target_calories: float
    total_actual_calories: float
    total_target_calories: float
