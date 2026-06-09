"""generate_meal_plan 单元测试。

覆盖：
- 5000 组合数上限是否真的生效
- "找不到可行方案时退化为只用第一个食谱"分支
- "热量 ±10%、蛋白质 >= 下限"可行性判断的临界点
"""
from __future__ import annotations

import itertools as _itertools

import crud
import models
import schemas

from .conftest import make_ingredient, make_recipe, make_user


def _basic_recipe(db, name, calories, protein):
    """构造一个 1 食材 / 100g / 1 份的食谱，per_serving 即等于食材每 100g 营养。"""
    ing = make_ingredient(
        db,
        name=f"ing_{name}",
        calories=calories,
        protein=protein,
        fat=0,
        carbs=0,
        fiber=0,
        sodium=0,
        vitamin_a=0,
        vitamin_c=0,
        calcium=0,
        iron=0,
    )
    return make_recipe(db, name, [(ing, 100)], servings=1)


class TestGenerateMealPlanCombinationCap:
    def test_no_recipes_returns_none(self, db):
        user = make_user(db)
        gen = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=1000.0,
            target_protein=50.0,
            days=1,
        )
        assert crud.generate_meal_plan(db, user.id, gen) is None

    def test_combination_cap_at_5000(self, monkeypatch, db):
        """9 个食谱 → 9^4 = 6561 个组合，但实际只能枚举 5001 次（>5000 时 break）。"""
        original_product = _itertools.product
        iter_count = {"value": 0}

        def counting_product(*args, **kwargs):
            cnt = 0
            for x in original_product(*args, **kwargs):
                cnt += 1
                iter_count["value"] = max(iter_count["value"], cnt)
                yield x

        monkeypatch.setattr(_itertools, "product", counting_product)

        # 9 个食谱
        for i in range(9):
            _basic_recipe(db, f"r{i}", calories=200 + i, protein=10 + i)

        user = make_user(db)
        gen = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=900.0,
            target_protein=40.0,
            days=1,
        )
        result = crud.generate_meal_plan(db, user.id, gen)
        assert result is not None
        # 至多产出 5001 个组合（第 5001 次循环触发 break）
        assert iter_count["value"] <= 5001
        # 若 cap 没生效则会枚举完 6561 个
        assert iter_count["value"] < 6561


class TestGenerateMealPlanFeasibilityBoundary:
    def test_calories_lower_bound_is_inclusive(self, db):
        """
        sum_cal 恰好等于 target * 0.9 时应判定为 feasible（<= 边界包含等号）。

        构造：
          X 食谱 per_serving = 225 cal / 25 protein → 4×X = 900 cal / 100 protein
          Y 食谱 per_serving = 100 cal / 5 protein  → 4×Y = 400 cal / 20 protein（不可行）
          target_calories = 1000（min=900，max=1100）
          target_protein = 80
        预期：选中 4×X（带 -1000 feasible 奖励，分数最低）。
        """
        rx = _basic_recipe(db, "X", calories=225, protein=25)
        _basic_recipe(db, "Y", calories=100, protein=5)
        user = make_user(db)
        gen = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=1000.0,
            target_protein=80.0,
            days=1,
        )
        result = crud.generate_meal_plan(db, user.id, gen)
        assert result is not None
        assert len(result.items) == 4
        for item in result.items:
            assert item.recipe_id == rx.id

    def test_calories_upper_bound_is_inclusive(self, db):
        """sum_cal = target * 1.1 时应判定为 feasible。"""
        # X: per_serving = 275 cal / 25 protein → 4×X = 1100 cal（恰好上限）
        rx = _basic_recipe(db, "X", calories=275, protein=25)
        # Y: per_serving = 1000 cal → 4×Y = 4000，远超上限不可行
        _basic_recipe(db, "Y", calories=1000, protein=10)
        user = make_user(db)
        gen = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=1000.0,
            target_protein=80.0,
            days=1,
        )
        result = crud.generate_meal_plan(db, user.id, gen)
        assert result is not None
        for item in result.items:
            assert item.recipe_id == rx.id

    def test_protein_lower_bound_is_inclusive(self, db):
        """sum_protein 恰好等于 target_protein 时应判定为 feasible（>= 边界包含等号）。"""
        # X: 4×X = 1000 cal / 80 protein 恰好等于 target_protein
        rx = _basic_recipe(db, "X", calories=250, protein=20)
        # Y: 蛋白偏低，4×Y = 1000 cal / 40 protein
        _basic_recipe(db, "Y", calories=250, protein=10)
        user = make_user(db)
        gen = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=1000.0,
            target_protein=80.0,
            days=1,
        )
        result = crud.generate_meal_plan(db, user.id, gen)
        assert result is not None
        # X 满足蛋白下限 → 应被选中
        for item in result.items:
            assert item.recipe_id == rx.id

    def test_calories_just_below_lower_bound_not_feasible(self, db):
        """sum_cal = target*0.9 - ε 时不可行；不可行项无 -1000 奖励，比可行的差。"""
        # X: per_serving = 224 cal/25 protein → 4×X = 896 cal （比 900 少 4，infeasible）
        _basic_recipe(db, "X", calories=224, protein=25)
        # Y: per_serving = 250 cal/25 protein → 4×Y = 1000 cal / 100 protein → feasible
        ry = _basic_recipe(db, "Y", calories=250, protein=25)
        user = make_user(db)
        gen = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=1000.0,
            target_protein=80.0,
            days=1,
        )
        result = crud.generate_meal_plan(db, user.id, gen)
        assert result is not None
        # 应选 Y（feasible，得到 -1000 奖励）
        for item in result.items:
            assert item.recipe_id == ry.id


class TestGenerateMealPlanFallbackBranch:
    def test_no_feasible_combo_does_not_actually_hit_first_recipe_fallback(self, db):
        """
        BUG: 函数中 ``if best_combination is None`` 分支被设计为
        "找不到可行方案时退化为只用第一个食谱"。

        但实际实现里, ``best_score`` 初始是 ``+inf``, ``score`` 永远是有限数,
        因此只要 ``recipe_list`` 非空, ``best_combination`` 必然被赋值, 即
        永远不会进入这个 fallback 分支 —— 该分支是死代码。

        而当 ``recipe_list`` 为空时, fallback 分支里的 ``recipe_list[0]``
        会立刻 IndexError —— 实际上 fallback 也无法成立。

        本测试构造一个"无可行方案"的场景, 证明返回的依然是 best-effort 的最佳组合,
        而不是注释意图中的 "全部用第一个食谱"。
        """
        # 全部食谱都无法配出 4×per_serving 落在 ±10% 的目标里, 蛋白也都不足
        r0 = _basic_recipe(db, "r0", calories=10, protein=1)
        _basic_recipe(db, "r1", calories=12, protein=1)
        user = make_user(db)
        gen = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=10000.0,   # 4×combo 至多 ~48 cal, 远低于 9000 下限
            target_protein=1000.0,
            days=1,
        )
        result = crud.generate_meal_plan(db, user.id, gen)
        assert result is not None
        assert len(result.items) == 4
        # 函数最终选了 score 最小的组合 (即 r1, r1, r1, r1, calories=48 最接近),
        # 而不是 fallback 期望的 "全部 r0"(即 first recipe)
        recipe_ids = {item.recipe_id for item in result.items}
        # 该断言演示: 实际实现并不会退化为只用第一个食谱(r0)
        # 如果 fallback 真的生效, 应该全是 r0; 实际全是 r1
        assert r0.id not in recipe_ids


class TestGenerateMealPlanMultiDay:
    def test_days_produces_correct_item_count(self, db):
        rx = _basic_recipe(db, "X", calories=250, protein=25)
        user = make_user(db)
        gen = schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=1000.0,
            target_protein=80.0,
            days=3,
        )
        result = crud.generate_meal_plan(db, user.id, gen)
        assert result is not None
        # 3 天 × 4 餐 = 12 个 item
        assert len(result.items) == 12
        for item in result.items:
            assert item.recipe_id == rx.id
