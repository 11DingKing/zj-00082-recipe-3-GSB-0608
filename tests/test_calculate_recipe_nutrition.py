"""calculate_recipe_nutrition 单元测试。

覆盖：加权求和正确性、servings=0/负数兜底、四舍五入误差累积、空配料表。
"""
from __future__ import annotations

import crud
import models

from .conftest import make_ingredient, make_recipe


class TestCalculateRecipeNutrition:
    def test_weighted_sum_two_ingredients(self, db):
        """100g + 50g 两种食材，应按 amount/100 加权求和。"""
        ing_a = make_ingredient(
            db, name="A", calories=100, protein=10, fat=5,
            carbs=15, fiber=1, sodium=10, vitamin_a=5, vitamin_c=5,
            calcium=20, iron=1,
        )
        ing_b = make_ingredient(
            db, name="B", calories=200, protein=20, fat=8,
            carbs=30, fiber=2, sodium=20, vitamin_a=10, vitamin_c=10,
            calcium=40, iron=2,
        )
        # A 100g（factor=1.0），B 50g（factor=0.5）
        recipe = make_recipe(db, "R1", [(ing_a, 100), (ing_b, 50)], servings=2)

        result = crud.calculate_recipe_nutrition(db, recipe.id)

        assert result is not None
        # total = A*1.0 + B*0.5
        assert result.total_calories == 200.0   # 100 + 100
        assert result.total_protein == 20.0     # 10 + 10
        assert result.total_fat == 9.0          # 5 + 4
        assert result.total_carbs == 30.0       # 15 + 15
        assert result.total_fiber == 2.0
        assert result.total_sodium == 20.0
        assert result.total_vitamin_a == 10.0
        assert result.total_vitamin_c == 10.0
        assert result.total_calcium == 40.0
        assert result.total_iron == 2.0

        # per_serving = total / 2
        assert result.per_serving["calories"] == 100.0
        assert result.per_serving["protein"] == 10.0
        assert result.per_serving["fat"] == 4.5

    def test_servings_zero_falls_back_to_one(self, db):
        """servings=0 应当回退为 1，不应除零。"""
        ing = make_ingredient(db, name="A", calories=400, protein=20, fat=10, carbs=50)
        recipe = make_recipe(db, "R-zero", [(ing, 100)], servings=0)

        result = crud.calculate_recipe_nutrition(db, recipe.id)

        assert result is not None
        assert result.per_serving["calories"] == 400.0
        assert result.per_serving["protein"] == 20.0

    def test_servings_negative_falls_back_to_one(self, db):
        """servings 为负数时也应回退为 1。"""
        ing = make_ingredient(db, name="A", calories=400, protein=20, fat=10, carbs=50)
        recipe = make_recipe(db, "R-neg", [(ing, 100)], servings=-3)

        result = crud.calculate_recipe_nutrition(db, recipe.id)

        assert result is not None
        assert result.per_serving["calories"] == 400.0

    def test_empty_ingredient_list_returns_zeros(self, db):
        """配料表为空 → 总营养全为 0；不报错。"""
        recipe = make_recipe(db, "R-empty", [], servings=2)

        result = crud.calculate_recipe_nutrition(db, recipe.id)

        assert result is not None
        assert result.total_calories == 0
        assert result.total_protein == 0
        assert result.total_fat == 0
        assert result.total_carbs == 0
        assert result.per_serving["calories"] == 0
        assert result.per_serving["protein"] == 0

    def test_recipe_not_found_returns_none(self, db):
        assert crud.calculate_recipe_nutrition(db, 9999) is None

    def test_rounding_accumulation_total_vs_sum_of_per_serving(self, db):
        """
        多次累加和四舍五入误差测试。

        先对 total_* 求和、再四舍五入；per_serving 是除以 servings 后再四舍五入。
        若把 per_serving × servings 重新相加，理论应等于 total_*；但由于
        多次独立 round(.., 2) 的误差累积，两者可能存在最多 0.01*servings 量级偏差。
        """
        # 构造能产生 1/3 类无尽小数的食材数据
        ing = make_ingredient(
            db, name="oddA",
            calories=33.333, protein=11.111, fat=7.777, carbs=22.222,
            fiber=0, sodium=0, vitamin_a=0, vitamin_c=0, calcium=0, iron=0,
        )
        # 100g + 200g + 333g 多次累加
        recipe = make_recipe(
            db, "R-round",
            [(ing, 100), (ing, 200), (ing, 333)],
            servings=3,
        )

        result = crud.calculate_recipe_nutrition(db, recipe.id)
        assert result is not None
        # total_calories = 33.333 * (1 + 2 + 3.33) = 33.333 * 6.33 = 210.99789
        assert abs(result.total_calories - round(33.333 * 6.33, 2)) < 1e-6
        # per_serving 与 total/servings 应一致（同一来源），但与
        # round(per_serving)*servings 比较时可能因精度差 0.01 左右
        per = result.per_serving["calories"]
        # 检测累积偏差：reconstructed != total 的可能性
        reconstructed = round(per * 3, 2)
        # 不强制断言相等，只要保证差值很小即可（说明没有失控的误差累积）
        assert abs(reconstructed - result.total_calories) <= 0.05


class TestCalculateRecipeNutritionPerServing:
    def test_per_serving_division(self, db):
        ing = make_ingredient(
            db, name="X", calories=400, protein=40, fat=20, carbs=60
        )
        recipe = make_recipe(db, "R-share", [(ing, 200)], servings=4)
        # total = 800 cal, 80 protein → per_serving = 200 / 20
        result = crud.calculate_recipe_nutrition(db, recipe.id)
        assert result.per_serving["calories"] == 200.0
        assert result.per_serving["protein"] == 20.0
        assert result.per_serving["fat"] == 10.0
        assert result.per_serving["carbs"] == 30.0
