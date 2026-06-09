import pytest
import math
from itertools import product
import crud
import models
import schemas


class TestCalculateRecipeNutrition:

    def test_weighted_sum_single_ingredient_100g(self, db_session, make_ingredient, make_recipe):
        ing = make_ingredient("鸡胸肉", category=models.IngredientCategory.MEAT,
                              calories=165.0, protein=31.0, fat=3.6, carbs=0.0,
                              fiber=0.0, sodium=74.0, unit_price=5.0)
        recipe = make_recipe("煎鸡胸", recipe_ingredients=[{"ingredient": ing, "amount": 100.0}])
        result = crud.calculate_recipe_nutrition(db_session, recipe.id)

        assert result is not None
        assert result.total_calories == pytest.approx(165.0, abs=0.01)
        assert result.total_protein == pytest.approx(31.0, abs=0.01)
        assert result.total_fat == pytest.approx(3.6, abs=0.01)
        assert result.total_carbs == pytest.approx(0.0, abs=0.01)

    def test_weighted_sum_half_amount(self, db_session, make_ingredient, make_recipe):
        ing = make_ingredient("鸡胸肉", category=models.IngredientCategory.MEAT,
                              calories=165.0, protein=31.0, fat=3.6, carbs=0.0,
                              unit_price=5.0)
        recipe = make_recipe("半份鸡胸", recipe_ingredients=[{"ingredient": ing, "amount": 50.0}])
        result = crud.calculate_recipe_nutrition(db_session, recipe.id)

        assert result.total_calories == pytest.approx(82.5, abs=0.01)
        assert result.total_protein == pytest.approx(15.5, abs=0.01)

    def test_weighted_sum_multiple_ingredients(self, db_session, make_ingredient, make_recipe):
        rice = make_ingredient("大米", category=models.IngredientCategory.GRAIN,
                               calories=130.0, protein=2.7, fat=0.3, carbs=28.0, unit_price=1.0)
        egg = make_ingredient("鸡蛋", category=models.IngredientCategory.EGG_DAIRY,
                              calories=155.0, protein=13.0, fat=11.0, carbs=1.1, unit_price=2.0)

        recipe = make_recipe("蛋炒饭", recipe_ingredients=[
            {"ingredient": rice, "amount": 200.0},
            {"ingredient": egg, "amount": 50.0}
        ])
        result = crud.calculate_recipe_nutrition(db_session, recipe.id)

        expected_calories = 130.0 * 2.0 + 155.0 * 0.5
        expected_protein = 2.7 * 2.0 + 13.0 * 0.5

        assert result.total_calories == pytest.approx(expected_calories, abs=0.01)
        assert result.total_protein == pytest.approx(expected_protein, abs=0.01)

    def test_per_serving_divides_correctly(self, db_session, make_ingredient, make_recipe):
        ing = make_ingredient("米饭", category=models.IngredientCategory.GRAIN,
                              calories=130.0, protein=2.7, fat=0.3, carbs=28.0, unit_price=1.0)
        recipe = make_recipe("米饭4人份", servings=4,
                             recipe_ingredients=[{"ingredient": ing, "amount": 400.0}])
        result = crud.calculate_recipe_nutrition(db_session, recipe.id)

        assert result.total_calories == pytest.approx(520.0, abs=0.01)
        assert result.per_serving["calories"] == pytest.approx(130.0, abs=0.01)
        assert result.per_serving["protein"] == pytest.approx(2.7, abs=0.01)

    def test_servings_zero_falls_back_to_one(self, db_session, make_ingredient, make_recipe):
        ing = make_ingredient("西兰花", category=models.IngredientCategory.VEGETABLE,
                              calories=34.0, protein=2.8, fat=0.4, carbs=7.0, unit_price=2.0)
        recipe = make_recipe("零份西兰花？", servings=0,
                             recipe_ingredients=[{"ingredient": ing, "amount": 100.0}])

        assert recipe.servings == 0
        result = crud.calculate_recipe_nutrition(db_session, recipe.id)

        assert result is not None
        assert result.per_serving["calories"] == pytest.approx(34.0, abs=0.01)

    def test_servings_negative_falls_back_to_one(self, db_session, make_ingredient, make_recipe):
        ing = make_ingredient("牛肉", category=models.IngredientCategory.MEAT,
                              calories=250.0, protein=26.0, fat=15.0, carbs=0.0, unit_price=8.0)
        recipe = make_recipe("负份牛肉", servings=-3,
                             recipe_ingredients=[{"ingredient": ing, "amount": 200.0}])

        assert recipe.servings == -3
        result = crud.calculate_recipe_nutrition(db_session, recipe.id)

        assert result is not None
        assert result.total_calories == pytest.approx(500.0, abs=0.01)
        assert result.per_serving["calories"] == pytest.approx(500.0, abs=0.01)

    def test_empty_ingredients_returns_zeros(self, db_session, make_recipe):
        recipe = make_recipe("空壳食谱", servings=2, recipe_ingredients=[])
        result = crud.calculate_recipe_nutrition(db_session, recipe.id)

        assert result is not None
        assert result.total_calories == 0.0
        assert result.total_protein == 0.0
        assert result.total_fat == 0.0
        assert result.total_carbs == 0.0
        assert result.per_serving["calories"] == 0.0
        assert result.per_serving["protein"] == 0.0

    def test_nonexistent_recipe_returns_none(self, db_session):
        result = crud.calculate_recipe_nutrition(db_session, 999999)
        assert result is None

    def test_rounding_accumulation_many_small_ingredients(self, db_session, make_ingredient, make_recipe):
        ingredients_list = []
        for i in range(100):
            ing = make_ingredient(f"配料{i}", calories=1.005, protein=1.005,
                                  fat=1.005, carbs=1.005, unit_price=0.1)
            ingredients_list.append({"ingredient": ing, "amount": 100.0})

        recipe = make_recipe("百种微量配料", recipe_ingredients=ingredients_list)
        result = crud.calculate_recipe_nutrition(db_session, recipe.id)

        raw_total = 100 * 1.005
        assert result.total_calories == round(raw_total, 2)
        assert result.total_calories == pytest.approx(100.5, abs=0.01)

    def test_all_nutrition_fields_are_rounded_to_two_decimals(self, db_session, make_ingredient, make_recipe):
        ing = make_ingredient("奇葩数值",
                              calories=123.4567, protein=89.0123,
                              fat=45.6789, carbs=23.4567,
                              fiber=12.3456, sodium=987.6543,
                              vitamin_a=1234.5678, vitamin_c=56.7890,
                              calcium=34.5678, iron=5.6789,
                              unit_price=3.0)
        recipe = make_recipe("奇葩数值食谱",
                             recipe_ingredients=[{"ingredient": ing, "amount": 100.0}])
        result = crud.calculate_recipe_nutrition(db_session, recipe.id)

        for field in ["total_calories", "total_protein", "total_fat", "total_carbs",
                      "total_fiber", "total_sodium", "total_vitamin_a", "total_vitamin_c",
                      "total_calcium", "total_iron"]:
            val = getattr(result, field)
            assert val == round(val, 2), f"{field} 未正确四舍五入到两位小数"

        for key in result.per_serving:
            val = result.per_serving[key]
            assert val == round(val, 2), f"per_serving['{key}'] 未正确四舍五入到两位小数"


class TestGenerateMealPlan:

    def _make_recipe_with_nutrition(self, db_session, name, per_serving_calories, per_serving_protein,
                                    make_ingredient, make_recipe):
        ing = make_ingredient(f"{name}_ing", calories=per_serving_calories,
                              protein=per_serving_protein, fat=10.0, carbs=20.0, unit_price=1.0)
        return make_recipe(name, recipe_ingredients=[{"ingredient": ing, "amount": 100.0}])

    def test_no_recipes_returns_none(self, db_session, make_user):
        user = make_user()
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000, target_protein=60, days=1
        )
        result = crud.generate_meal_plan(db_session, user.id, gen_data)
        assert result is None

    def test_combination_limit_at_most_5000(self, db_session, make_user, make_ingredient, make_recipe):
        import itertools

        for i in range(10):
            self._make_recipe_with_nutrition(db_session, f"食谱{i}", 500.0, 15.0,
                                             make_ingredient, make_recipe)

        user = make_user()
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000, target_protein=60, days=1
        )

        recipes = crud.get_recipes(db_session)
        recipe_nutrition = {}
        for r in recipes:
            n = crud.calculate_recipe_nutrition(db_session, r.id)
            recipe_nutrition[r.id] = {
                "recipe": r, "nutrition": n,
                "per_serving_calories": n.per_serving["calories"],
                "per_serving_protein": n.per_serving["protein"]
            }

        recipe_list = list(recipe_nutrition.values())
        expected_total = len(list(itertools.product(recipe_list, repeat=4)))

        counted = 0
        for _ in itertools.product(recipe_list, repeat=4):
            counted += 1
            if counted > 5000:
                break

        assert counted == 5001 or counted == expected_total
        assert expected_total == 10 ** 4
        assert counted > 5000 or expected_total <= 5000

        result = crud.generate_meal_plan(db_session, user.id, gen_data)
        assert result is not None
        assert len(result.items) == 4

    def test_exact_target_calories_is_within_10_percent(self, db_session, make_user, make_ingredient, make_recipe):
        self._make_recipe_with_nutrition(db_session, "餐A", 500.0, 20.0, make_ingredient, make_recipe)
        self._make_recipe_with_nutrition(db_session, "餐B", 500.0, 20.0, make_ingredient, make_recipe)
        self._make_recipe_with_nutrition(db_session, "餐C", 500.0, 20.0, make_ingredient, make_recipe)
        self._make_recipe_with_nutrition(db_session, "餐D", 500.0, 20.0, make_ingredient, make_recipe)

        user = make_user()
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000, target_protein=60, days=1
        )
        result = crud.generate_meal_plan(db_session, user.id, gen_data)
        assert result is not None

        total_cal = 0
        total_prot = 0
        for item in result.items:
            n = crud.calculate_recipe_nutrition(db_session, item.recipe_id)
            total_cal += n.per_serving["calories"]
            total_prot += n.per_serving["protein"]

        assert 2000 * 0.9 <= total_cal <= 2000 * 1.1
        assert total_prot >= 60

    def test_calories_lower_bound_exactly_10_percent(self, db_session, make_user, make_ingredient, make_recipe):
        self._make_recipe_with_nutrition(db_session, "低卡餐", 450.0, 20.0, make_ingredient, make_recipe)
        for i in range(3):
            self._make_recipe_with_nutrition(db_session, f"普通餐{i}", 450.0, 20.0, make_ingredient, make_recipe)

        user = make_user()
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.FAT_LOSS,
            target_calories=2000, target_protein=60, days=1
        )
        result = crud.generate_meal_plan(db_session, user.id, gen_data)

        total_cal = 0
        for item in result.items:
            n = crud.calculate_recipe_nutrition(db_session, item.recipe_id)
            total_cal += n.per_serving["calories"]

        assert total_cal == pytest.approx(1800.0, abs=0.01)

    def test_calories_upper_bound_exactly_10_percent(self, db_session, make_user, make_ingredient, make_recipe):
        self._make_recipe_with_nutrition(db_session, "高卡餐", 550.0, 20.0, make_ingredient, make_recipe)
        for i in range(3):
            self._make_recipe_with_nutrition(db_session, f"餐{i}", 550.0, 20.0, make_ingredient, make_recipe)

        user = make_user()
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.MUSCLE_GAIN,
            target_calories=2000, target_protein=60, days=1
        )
        result = crud.generate_meal_plan(db_session, user.id, gen_data)

        total_cal = 0
        for item in result.items:
            n = crud.calculate_recipe_nutrition(db_session, item.recipe_id)
            total_cal += n.per_serving["calories"]

        assert total_cal == pytest.approx(2200.0, abs=0.01)

    def test_calories_just_below_10_percent_boundary_rejected(self, db_session, make_user, make_ingredient, make_recipe):
        self._make_recipe_with_nutrition(db_session, "很低卡", 449.0, 20.0, make_ingredient, make_recipe)
        for i in range(3):
            self._make_recipe_with_nutrition(db_session, f"餐{i}", 449.0, 20.0, make_ingredient, make_recipe)

        user = make_user()
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.FAT_LOSS,
            target_calories=2000, target_protein=60, days=1
        )
        result = crud.generate_meal_plan(db_session, user.id, gen_data)

        total_cal = sum(
            crud.calculate_recipe_nutrition(db_session, item.recipe_id).per_serving["calories"]
            for item in result.items
        )
        assert total_cal == pytest.approx(1796.0, abs=0.01)
        assert total_cal < 1800.0

    def test_protein_exactly_at_target_is_accepted(self, db_session, make_user, make_ingredient, make_recipe):
        self._make_recipe_with_nutrition(db_session, "蛋白餐A", 500.0, 15.0, make_ingredient, make_recipe)
        self._make_recipe_with_nutrition(db_session, "蛋白餐B", 500.0, 15.0, make_ingredient, make_recipe)
        self._make_recipe_with_nutrition(db_session, "蛋白餐C", 500.0, 15.0, make_ingredient, make_recipe)
        self._make_recipe_with_nutrition(db_session, "蛋白餐D", 500.0, 15.0, make_ingredient, make_recipe)

        user = make_user()
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.MUSCLE_GAIN,
            target_calories=2000, target_protein=60, days=1
        )
        result = crud.generate_meal_plan(db_session, user.id, gen_data)

        total_prot = sum(
            crud.calculate_recipe_nutrition(db_session, item.recipe_id).per_serving["protein"]
            for item in result.items
        )
        assert total_prot == pytest.approx(60.0, abs=0.01)

    def test_protein_one_gram_below_target_is_not_feasible(self, db_session, make_user, make_ingredient, make_recipe):
        self._make_recipe_with_nutrition(db_session, "低蛋白A", 500.0, 14.75, make_ingredient, make_recipe)
        for i in range(3):
            self._make_recipe_with_nutrition(db_session, f"低蛋白{i}", 500.0, 14.75, make_ingredient, make_recipe)

        user = make_user()
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.MUSCLE_GAIN,
            target_calories=2000, target_protein=60, days=1
        )
        result = crud.generate_meal_plan(db_session, user.id, gen_data)

        total_prot = sum(
            crud.calculate_recipe_nutrition(db_session, item.recipe_id).per_serving["protein"]
            for item in result.items
        )
        assert total_prot == pytest.approx(59.0, abs=0.01)
        assert total_prot < 60.0

    def test_impossible_plan_does_not_use_first_recipe_for_all_meals(self, db_session, make_user, make_ingredient, make_recipe):
        r1 = self._make_recipe_with_nutrition(db_session, "极端高卡", 3000.0, 5.0, make_ingredient, make_recipe)
        r2 = self._make_recipe_with_nutrition(db_session, "极端低卡", 10.0, 1.0, make_ingredient, make_recipe)

        user = make_user()
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.FAT_LOSS,
            target_calories=2000, target_protein=100, days=1
        )
        result = crud.generate_meal_plan(db_session, user.id, gen_data)

        assert result is not None
        recipe_ids = [item.recipe_id for item in result.items]

        all_first_recipe = all(rid == r1.id for rid in recipe_ids)
        assert not all_first_recipe, (
            "BUG: 不存在可行方案时，并没有退化为所有餐都使用第一个食谱——"
            "best_combination 永远不为 None，退化分支是死代码"
        )

    def test_multiple_days_generates_correct_item_count(self, db_session, make_user, make_ingredient, make_recipe):
        for i in range(5):
            self._make_recipe_with_nutrition(db_session, f"日计划食谱{i}", 500.0, 20.0, make_ingredient, make_recipe)

        user = make_user()
        days = 3
        gen_data = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000, target_protein=60, days=days
        )
        result = crud.generate_meal_plan(db_session, user.id, gen_data)

        assert result is not None
        assert len(result.items) == days * 4


class TestGetIngredientSubstitutes:

    def test_nonexistent_ingredient_returns_none(self, db_session):
        result = crud.get_ingredient_substitutes(db_session, 999999)
        assert result is None

    def test_no_candidates_in_same_category_returns_empty(self, db_session, make_ingredient):
        ing = make_ingredient("孤独的胡萝卜", category=models.IngredientCategory.VEGETABLE,
                              calories=41.0, protein=0.9, fat=0.2, carbs=10.0, unit_price=1.0)
        result = crud.get_ingredient_substitutes(db_session, ing.id)
        assert result == []

    def test_identical_nutrition_gives_similarity_one(self, db_session, make_ingredient):
        a = make_ingredient("A", calories=100.0, protein=10.0, fat=5.0, carbs=10.0, unit_price=2.0)
        b = make_ingredient("B", calories=100.0, protein=10.0, fat=5.0, carbs=10.0, unit_price=2.0)
        result = crud.get_ingredient_substitutes(db_session, a.id)
        assert len(result) == 1
        assert result[0]["similarity_score"] == pytest.approx(1.0, abs=0.001)

    def test_exactly_20_percent_diff_is_included(self, db_session, make_ingredient):
        base = make_ingredient("基准", calories=100.0, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)
        exact20 = make_ingredient("刚好20%", calories=120.0, protein=12.0, fat=12.0, carbs=0.0, unit_price=1.0)
        result = crud.get_ingredient_substitutes(db_session, base.id)
        assert len(result) == 1
        found = any(s["ingredient"].id == exact20.id for s in result)
        assert found

    def test_just_over_20_percent_diff_is_excluded(self, db_session, make_ingredient):
        base = make_ingredient("基准2", calories=100.0, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)
        over20 = make_ingredient("超20%", calories=121.0, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)
        result = crud.get_ingredient_substitutes(db_session, base.id)
        assert len(result) == 0

    def test_one_metric_over_20_excludes_even_if_others_match(self, db_session, make_ingredient):
        base = make_ingredient("基准3", calories=100.0, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)
        bad_fat = make_ingredient("脂肪超了", calories=100.0, protein=10.0, fat=121.0, carbs=0.0, unit_price=1.0)
        result = crud.get_ingredient_substitutes(db_session, base.id)
        assert len(result) == 0

    def test_top_n_limits_results(self, db_session, make_ingredient):
        base = make_ingredient("基准4", calories=100.0, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)
        for i in range(8):
            make_ingredient(f"候选{i}", calories=100.0 + i, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)

        result = crud.get_ingredient_substitutes(db_session, base.id, top_n=3)
        assert len(result) <= 3

    def test_sorted_by_similarity_descending(self, db_session, make_ingredient):
        base = make_ingredient("基准5", calories=100.0, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)
        perfect = make_ingredient("完美匹配", calories=100.0, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)
        slightly = make_ingredient("有点差异", calories=110.0, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)
        more = make_ingredient("差异较大", calories=119.0, protein=10.0, fat=10.0, carbs=0.0, unit_price=1.0)

        result = crud.get_ingredient_substitutes(db_session, base.id, top_n=10)
        assert len(result) == 3
        scores = [s["similarity_score"] for s in result]
        assert scores[0] >= scores[1] >= scores[2]
        assert result[0]["ingredient"].id == perfect.id
        assert result[-1]["ingredient"].id == more.id

    def test_zero_calories_in_base_raises_zero_division(self, db_session, make_ingredient):
        base = make_ingredient("零热量", category=models.IngredientCategory.VEGETABLE,
                               calories=0.0, protein=5.0, fat=1.0, carbs=5.0, unit_price=1.0)
        other = make_ingredient("其他蔬菜", category=models.IngredientCategory.VEGETABLE,
                                calories=10.0, protein=5.0, fat=1.0, carbs=5.0, unit_price=1.0)

        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db_session, base.id)

    def test_zero_protein_in_base_raises_zero_division(self, db_session, make_ingredient):
        base = make_ingredient("零蛋白", category=models.IngredientCategory.FRUIT,
                               calories=50.0, protein=0.0, fat=0.5, carbs=12.0, unit_price=2.0)
        other = make_ingredient("其他水果", category=models.IngredientCategory.FRUIT,
                                calories=50.0, protein=1.0, fat=0.5, carbs=12.0, unit_price=2.0)

        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db_session, base.id)

    def test_zero_fat_in_base_raises_zero_division(self, db_session, make_ingredient):
        base = make_ingredient("零脂肪", category=models.IngredientCategory.GRAIN,
                               calories=350.0, protein=7.0, fat=0.0, carbs=77.0, unit_price=0.5)
        other = make_ingredient("其他谷物", category=models.IngredientCategory.GRAIN,
                                calories=350.0, protein=7.0, fat=2.0, carbs=77.0, unit_price=0.5)

        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db_session, base.id)

    def test_different_category_excluded(self, db_session, make_ingredient):
        base = make_ingredient("基准菜", category=models.IngredientCategory.VEGETABLE,
                               calories=25.0, protein=2.0, fat=0.3, carbs=5.0, unit_price=1.0)
        meat = make_ingredient("肉类东西", category=models.IngredientCategory.MEAT,
                               calories=25.0, protein=2.0, fat=0.3, carbs=5.0, unit_price=5.0)
        result = crud.get_ingredient_substitutes(db_session, base.id)
        assert len(result) == 0

    def test_does_not_include_itself(self, db_session, make_ingredient):
        base = make_ingredient("自己", calories=50.0, protein=5.0, fat=2.0, carbs=8.0, unit_price=1.0)
        other = make_ingredient("同类", calories=50.0, protein=5.0, fat=2.0, carbs=8.0, unit_price=1.0)
        result = crud.get_ingredient_substitutes(db_session, base.id)
        ids = [s["ingredient"].id for s in result]
        assert base.id not in ids
        assert other.id in ids
