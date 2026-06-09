import pytest
from models import IngredientCategory, RecipeCategory, Difficulty
import schemas
import crud


class TestCalculateRecipeNutrition:
    
    def test_basic_calculation_single_ingredient(self, db, create_test_ingredient, create_test_recipe):
        """测试单配料基础计算：100g 配料直接对应数值"""
        chicken = create_test_ingredient(
            name="鸡胸肉",
            category=IngredientCategory.MEAT,
            calories=165.0,
            protein=31.0,
            fat=3.6,
            carbs=0.0,
            fiber=0,
            sodium=74,
            vitamin_a=6,
            vitamin_c=0,
            calcium=11,
            iron=0.7,
            unit_price=20.0
        )
        
        steps = [schemas.RecipeStep(order=1, description="煮熟", duration=10)]
        recipe_ingredients = [schemas.RecipeIngredientCreate(ingredient_id=chicken.id, amount=100.0)]
        recipe = create_test_recipe(
            name="白煮鸡胸",
            category=RecipeCategory.LUNCH,
            cook_time=15,
            difficulty=Difficulty.EASY,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            servings=1
        )
        
        result = crud.calculate_recipe_nutrition(db, recipe.id)
        
        assert result is not None
        assert result.total_calories == 165.0
        assert result.total_protein == 31.0
        assert result.total_fat == 3.6
        assert result.total_carbs == 0.0
        assert result.per_serving["calories"] == 165.0
        assert result.per_serving["protein"] == 31.0
    
    def test_weighted_sum_multiple_ingredients(self, db, create_test_ingredient, create_test_recipe):
        """测试多配料加权求和"""
        rice = create_test_ingredient("米饭", IngredientCategory.GRAIN, 116, 2.6, 0.3, 25.6, unit_price=3.0)
        egg = create_test_ingredient("鸡蛋", IngredientCategory.EGG_DAIRY, 155, 13.0, 10.1, 1.1, unit_price=5.0)
        
        steps = [schemas.RecipeStep(order=1, description="炒制", duration=5)]
        recipe_ingredients = [
            schemas.RecipeIngredientCreate(ingredient_id=rice.id, amount=200.0),
            schemas.RecipeIngredientCreate(ingredient_id=egg.id, amount=50.0)
        ]
        recipe = create_test_recipe(
            name="蛋炒饭",
            category=RecipeCategory.LUNCH,
            cook_time=10,
            difficulty=Difficulty.EASY,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            servings=1
        )
        
        result = crud.calculate_recipe_nutrition(db, recipe.id)
        
        expected_calories = 116 * 2 + 155 * 0.5
        expected_protein = 2.6 * 2 + 13.0 * 0.5
        assert abs(result.total_calories - expected_calories) < 0.01
        assert abs(result.total_protein - expected_protein) < 0.01
    
    def test_servings_zero_fallback_to_one(self, db, create_test_ingredient, create_test_recipe):
        """BUG 测试：servings 为 0 时是否正确兜底为 1"""
        chicken = create_test_ingredient("鸡胸肉", IngredientCategory.MEAT, 165, 31, 3.6, 0, unit_price=20)
        
        steps = [schemas.RecipeStep(order=1, description="煮熟", duration=10)]
        recipe_ingredients = [schemas.RecipeIngredientCreate(ingredient_id=chicken.id, amount=100.0)]
        
        from sqlalchemy.orm import Session
        recipe_obj = create_test_recipe(
            name="test",
            category=RecipeCategory.LUNCH,
            cook_time=10,
            difficulty=Difficulty.EASY,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            servings=2
        )
        
        db_recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_obj.id).first()
        db_recipe.servings = 0
        db.commit()
        db.refresh(db_recipe)
        
        result = crud.calculate_recipe_nutrition(db, recipe_obj.id)
        
        assert result is not None
        assert result.per_serving["calories"] == 165.0
    
    def test_servings_negative_fallback_to_one(self, db, create_test_ingredient, create_test_recipe):
        """BUG 测试：servings 为负数时是否正确兜底为 1"""
        chicken = create_test_ingredient("鸡胸肉", IngredientCategory.MEAT, 165, 31, 3.6, 0, unit_price=20)
        
        steps = [schemas.RecipeStep(order=1, description="煮熟", duration=10)]
        recipe_ingredients = [schemas.RecipeIngredientCreate(ingredient_id=chicken.id, amount=100.0)]
        
        recipe_obj = create_test_recipe(
            name="test",
            category=RecipeCategory.LUNCH,
            cook_time=10,
            difficulty=Difficulty.EASY,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            servings=2
        )
        
        db_recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_obj.id).first()
        db_recipe.servings = -5
        db.commit()
        db.refresh(db_recipe)
        
        result = crud.calculate_recipe_nutrition(db, recipe_obj.id)
        
        assert result is not None
        assert result.per_serving["calories"] == 165.0
    
    def test_multiple_servings_division(self, db, create_test_ingredient, create_test_recipe):
        """测试多份时正确按份数均分"""
        chicken = create_test_ingredient("鸡胸肉", IngredientCategory.MEAT, 165, 31, 3.6, 0, unit_price=20)
        
        steps = [schemas.RecipeStep(order=1, description="煮熟", duration=10)]
        recipe_ingredients = [schemas.RecipeIngredientCreate(ingredient_id=chicken.id, amount=200.0)]
        recipe = create_test_recipe(
            name="双份鸡胸",
            category=RecipeCategory.LUNCH,
            cook_time=15,
            difficulty=Difficulty.EASY,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            servings=2
        )
        
        result = crud.calculate_recipe_nutrition(db, recipe.id)
        
        assert result.total_calories == 330.0
        assert result.per_serving["calories"] == 165.0
    
    def test_empty_ingredients_list(self, db, create_test_ingredient, create_test_recipe):
        """测试配料表为空的情况 - 绕过 pydantic 直接操作数据库"""
        chicken = create_test_ingredient("鸡胸肉", IngredientCategory.MEAT, 165, 31, 3.6, 0, unit_price=20)
        
        steps = [schemas.RecipeStep(order=1, description="test", duration=1)]
        recipe_ingredients = [schemas.RecipeIngredientCreate(ingredient_id=chicken.id, amount=100.0)]
        recipe_obj = create_test_recipe(
            name="临时食谱",
            category=RecipeCategory.LUNCH,
            cook_time=1,
            difficulty=Difficulty.EASY,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            servings=1
        )
        
        db.query(models.RecipeIngredient).filter(
            models.RecipeIngredient.recipe_id == recipe_obj.id
        ).delete()
        db.commit()
        
        result = crud.calculate_recipe_nutrition(db, recipe_obj.id)
        
        assert result is not None
        assert result.total_calories == 0
        assert result.total_protein == 0
        assert result.total_fat == 0
        assert result.total_carbs == 0
        assert result.per_serving["calories"] == 0
    
    def test_recipe_not_found_returns_none(self, db):
        """测试不存在的食谱返回 None"""
        result = crud.calculate_recipe_nutrition(db, 99999)
        assert result is None
    
    def test_rounding_precision_accumulation(self, db, create_test_ingredient, create_test_recipe):
        """测试四舍五入累积误差：确保每轮 round 后误差可控"""
        ingredients_data = [
            ("a", 100.333, 10.333, 1.333, 5.333),
            ("b", 100.333, 10.333, 1.333, 5.333),
            ("c", 100.333, 10.333, 1.333, 5.333),
        ]
        
        created_ingredients = []
        for i, (name, cal, prot, fat, carb) in enumerate(ingredients_data):
            ing = create_test_ingredient(
                name=f"ing_{name}",
                category=IngredientCategory.GRAIN,
                calories=cal,
                protein=prot,
                fat=fat,
                carbs=carb,
                unit_price=1.0
            )
            created_ingredients.append(ing)
        
        steps = [schemas.RecipeStep(order=1, description="混合", duration=1)]
        recipe_ingredients = [
            schemas.RecipeIngredientCreate(ingredient_id=ing.id, amount=100.0)
            for ing in created_ingredients
        ]
        recipe = create_test_recipe(
            name="误差测试",
            category=RecipeCategory.LUNCH,
            cook_time=1,
            difficulty=Difficulty.EASY,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            servings=1
        )
        
        result = crud.calculate_recipe_nutrition(db, recipe.id)
        
        expected_total_cal = 100.333 * 3
        expected_rounded = round(expected_total_cal, 2)
        assert result.total_calories == expected_rounded
        
        assert isinstance(result.total_calories, float)
        assert len(str(result.total_calories).split('.')[-1]) <= 2
    
    def test_zero_amount_ingredient(self, db, create_test_ingredient, create_test_recipe):
        """测试配料用量为 0 时不报错 - 绕过 pydantic 直接操作数据库"""
        chicken = create_test_ingredient("鸡胸肉", IngredientCategory.MEAT, 165, 31, 3.6, 0, unit_price=20)
        
        steps = [schemas.RecipeStep(order=1, description="test", duration=1)]
        recipe_ingredients = [schemas.RecipeIngredientCreate(ingredient_id=chicken.id, amount=100.0)]
        
        recipe_obj = create_test_recipe(
            name="zero_test",
            category=RecipeCategory.LUNCH,
            cook_time=1,
            difficulty=Difficulty.EASY,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            servings=1
        )
        
        ri = db.query(models.RecipeIngredient).filter(
            models.RecipeIngredient.recipe_id == recipe_obj.id
        ).first()
        ri.amount = 0.0
        db.commit()
        db.refresh(ri)
        
        result = crud.calculate_recipe_nutrition(db, recipe_obj.id)
        
        assert result is not None
        assert result.total_calories == 0.0
    
    def test_all_nutrient_fields_calculated(self, db, create_test_ingredient, create_test_recipe):
        """测试所有营养字段都被正确计算"""
        ing = create_test_ingredient(
            name="全能食材",
            category=IngredientCategory.VEGETABLE,
            calories=50,
            protein=5,
            fat=2,
            carbs=10,
            fiber=3,
            sodium=100,
            vitamin_a=200,
            vitamin_c=50,
            calcium=150,
            iron=2.5,
            unit_price=5.0
        )
        
        steps = [schemas.RecipeStep(order=1, description="test", duration=1)]
        recipe_ingredients = [schemas.RecipeIngredientCreate(ingredient_id=ing.id, amount=200.0)]
        recipe = create_test_recipe(
            name="全能测试",
            category=RecipeCategory.LUNCH,
            cook_time=1,
            difficulty=Difficulty.EASY,
            steps=steps,
            recipe_ingredients=recipe_ingredients,
            servings=2
        )
        
        result = crud.calculate_recipe_nutrition(db, recipe.id)
        
        assert result.total_calories == 100.0
        assert result.total_protein == 10.0
        assert result.total_fat == 4.0
        assert result.total_carbs == 20.0
        assert result.total_fiber == 6.0
        assert result.total_sodium == 200.0
        assert result.total_vitamin_a == 400.0
        assert result.total_vitamin_c == 100.0
        assert result.total_calcium == 300.0
        assert result.total_iron == 5.0
        
        assert result.per_serving["calories"] == 50.0
        assert result.per_serving["protein"] == 5.0
        assert result.per_serving["fat"] == 2.0
        assert result.per_serving["carbs"] == 10.0
        assert result.per_serving["fiber"] == 3.0
        assert result.per_serving["sodium"] == 100.0
        assert result.per_serving["vitamin_a"] == 200.0
        assert result.per_serving["vitamin_c"] == 50.0
        assert result.per_serving["calcium"] == 150.0
        assert result.per_serving["iron"] == 2.5


import models
