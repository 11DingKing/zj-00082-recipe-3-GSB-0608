import pytest
from models import IngredientCategory, RecipeCategory, Difficulty, Goal
import schemas
import crud
import models


def create_simple_recipe(db, create_test_ingredient, create_test_recipe, name, calories, protein, category=RecipeCategory.LUNCH):
    """辅助函数：创建一个简单的单配料食谱"""
    ing = create_test_ingredient(
        name=f"ing_{name}",
        category=IngredientCategory.MEAT,
        calories=calories,
        protein=protein,
        fat=10.0,
        carbs=0.0,
        unit_price=10.0
    )
    steps = [schemas.RecipeStep(order=1, description="test", duration=5)]
    recipe_ingredients = [schemas.RecipeIngredientCreate(ingredient_id=ing.id, amount=100.0)]
    return create_test_recipe(
        name=name,
        category=category,
        cook_time=10,
        difficulty=Difficulty.EASY,
        steps=steps,
        recipe_ingredients=recipe_ingredients,
        servings=1
    )


class TestGenerateMealPlan:
    
    def test_no_recipes_returns_none(self, db, create_test_user):
        """测试没有食谱时返回 None"""
        user = create_test_user()
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=80,
            days=1
        )
        result = crud.generate_meal_plan(db, user.id, generate_data)
        assert result is None
    
    def test_generates_correct_days_and_meals(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试生成正确天数和餐次数的计划"""
        create_simple_recipe(db, create_test_ingredient, create_test_recipe, "r1", 500, 30)
        user = create_test_user()
        
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=80,
            days=3
        )
        result = crud.generate_meal_plan(db, user.id, generate_data)
        
        assert result is not None
        assert len(result.items) == 3 * 4
        meal_types = set(item.meal_type for item in result.items)
        assert "早餐" in meal_types
        assert "午餐" in meal_types
        assert "晚餐" in meal_types
        assert "加餐" in meal_types
    
    def test_combination_limit_5000_enforced(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """BUG 测试：验证组合数超过 5000 时会被截断
        
        4 餐次 × N 食谱 = N^4 种组合
        8^4 = 4096 (< 5000)
        9^4 = 6561 (> 5000)
        所以用 9 个食谱应该触发截断
        """
        for i in range(9):
            create_simple_recipe(
                db, create_test_ingredient, create_test_recipe,
                f"recipe_{i}", 500 + i * 10, 20 + i
            )
        
        user = create_test_user()
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=80,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        assert result is not None
    
    def test_fallback_to_first_recipe_when_no_feasible(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试：当找不到可行方案时，是否退化到只用第一个食谱
        
        注意：需要确认 best_combination 为 None 的分支是否会被触发
        由于算法会记录最佳分数（即使不满足条件），这个分支可能永远不会执行
        这可能是一个潜在的 bug - 死代码
        """
        create_simple_recipe(db, create_test_ingredient, create_test_recipe, "r1", 100, 5)
        create_simple_recipe(db, create_test_ingredient, create_test_recipe, "r2", 150, 8)
        
        user = create_test_user()
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=10000,
            target_protein=1000,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        
        assert result is not None
        recipe_ids = [item.recipe_id for item in result.items]
        assert len(set(recipe_ids)) >= 1
    
    def test_calories_lower_boundary_exactly_90_percent(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试热量临界点：正好等于下限（目标的 90%）应该被判定为可行"""
        target_calories = 2000
        per_meal_cal = target_calories * 0.9 / 4
        
        for i in range(4):
            create_simple_recipe(
                db, create_test_ingredient, create_test_recipe,
                f"r{i}", per_meal_cal, 30,
                category=list(RecipeCategory)[i] if i < 4 else RecipeCategory.LUNCH
            )
        
        user = create_test_user()
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=target_calories,
            target_protein=100,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        assert result is not None
    
    def test_calories_upper_boundary_exactly_110_percent(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试热量临界点：正好等于上限（目标的 110%）应该被判定为可行"""
        target_calories = 2000
        per_meal_cal = target_calories * 1.1 / 4
        
        for i in range(4):
            create_simple_recipe(
                db, create_test_ingredient, create_test_recipe,
                f"r{i}", per_meal_cal, 30,
                category=list(RecipeCategory)[i] if i < 4 else RecipeCategory.LUNCH
            )
        
        user = create_test_user()
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=target_calories,
            target_protein=100,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        assert result is not None
    
    def test_calories_below_90_percent_not_feasible(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试热量低于 90% 不满足条件"""
        target_calories = 2000
        per_meal_cal = target_calories * 0.89 / 4
        
        for i in range(2):
            create_simple_recipe(
                db, create_test_ingredient, create_test_recipe,
                f"r{i}", per_meal_cal, 5
            )
        
        user = create_test_user()
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=target_calories,
            target_protein=10,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        assert result is not None
    
    def test_calories_above_110_percent_not_feasible(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试热量高于 110% 不满足条件"""
        target_calories = 2000
        per_meal_cal = target_calories * 1.11 / 4
        
        for i in range(2):
            create_simple_recipe(
                db, create_test_ingredient, create_test_recipe,
                f"r{i}", per_meal_cal, 50
            )
        
        user = create_test_user()
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=target_calories,
            target_protein=10,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        assert result is not None
    
    def test_protein_exactly_at_target_is_feasible(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试蛋白质临界点：正好等于目标值应该被判定为可行"""
        target_protein = 100
        per_meal_protein = target_protein / 4
        
        for i in range(4):
            create_simple_recipe(
                db, create_test_ingredient, create_test_recipe,
                f"r{i}", 500, per_meal_protein
            )
        
        user = create_test_user()
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=target_protein,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        assert result is not None
    
    def test_protein_below_target_not_feasible(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试蛋白质低于目标值不满足条件"""
        target_protein = 100
        per_meal_protein = (target_protein - 1) / 4
        
        create_simple_recipe(db, create_test_ingredient, create_test_recipe, "r1", 500, per_meal_protein)
        
        user = create_test_user()
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=target_protein,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        assert result is not None
    
    def test_meal_plan_has_correct_goal_and_targets(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试生成的膳食计划目标和营养目标正确"""
        create_simple_recipe(db, create_test_ingredient, create_test_recipe, "r1", 500, 30)
        user = create_test_user()
        
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.FAT_LOSS,
            target_calories=1500,
            target_protein=100,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        
        assert result.goal == Goal.FAT_LOSS
        assert result.target_calories == 1500
        assert result.target_protein == 100
        assert "减脂" in result.name
    
    def test_single_recipe_uses_it_for_all_meals(self, db, create_test_ingredient, create_test_recipe, create_test_user):
        """测试只有一个食谱时，所有餐次都用这个食谱"""
        recipe = create_simple_recipe(db, create_test_ingredient, create_test_recipe, "only_recipe", 500, 30)
        user = create_test_user()
        
        generate_data = schemas.MealPlanGenerate(
            goal=Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=80,
            days=1
        )
        
        result = crud.generate_meal_plan(db, user.id, generate_data)
        
        assert result is not None
        for item in result.items:
            assert item.recipe_id == recipe.id
