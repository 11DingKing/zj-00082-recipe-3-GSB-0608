`import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch
import itertools

import models
import schemas
import crud
from database import Base

_seq = itertools.count(1)


def _uid(prefix="t"):
    return f"{prefix}_{next(_seq)}"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _mk_ing(db, **kw):
    d = dict(
        name=_uid("ing"),
        category=models.IngredientCategory.MEAT,
        calories=200.0, protein=20.0, fat=10.0, carbs=5.0,
        fiber=0.0, sodium=50.0, vitamin_a=0.0, vitamin_c=0.0,
        calcium=0.0, iron=0.0, allergens=[], unit_price=10.0,
    )
    d.update(kw)
    return crud.create_ingredient(db, schemas.IngredientCreate(**d))


def _mk_rec(db, ing_grams, **kw):
    d = dict(
        name=_uid("rec"),
        category=models.RecipeCategory.LUNCH,
        cook_time=30,
        difficulty=models.Difficulty.EASY,
        steps=[{"order": 1, "description": "Cook", "duration": 30}],
        tags=[],
        servings=1,
    )
    d.update(kw)
    ris = [
        schemas.RecipeIngredientCreate(ingredient_id=iid, amount=amt)
        for iid, amt in ing_grams
    ]
    return crud.create_recipe(db, schemas.RecipeCreate(recipe_ingredients=ris, **d))


def _mk_usr(db):
    return crud.create_user(db, schemas.UserCreate(
        username=_uid("u"), email=f"{_uid('e')}@x.com", password="pw123456"
    ))


# ═══════════════════════════════════════════════════════════════════════
#  calculate_recipe_nutrition
# ═══════════════════════════════════════════════════════════════════════

class TestCalculateRecipeNutrition:

    def test_basic_weighted_sum(self, db):
        ing = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       fiber=3, sodium=200, vitamin_a=10, vitamin_c=30,
                       calcium=50, iron=2)
        rec = _mk_rec(db, [(ing.id, 200)])
        n = crud.calculate_recipe_nutrition(db, rec.id)
        assert n.total_calories == 200.0
        assert n.total_protein == 20.0
        assert n.total_fat == 10.0
        assert n.total_carbs == 40.0
        assert n.total_fiber == 6.0
        assert n.total_sodium == 400.0
        assert n.total_vitamin_a == 20.0
        assert n.total_vitamin_c == 60.0
        assert n.total_calcium == 100.0
        assert n.total_iron == 4.0

    def test_multiple_ingredients_weighted_sum(self, db):
        a = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20)
        b = _mk_ing(db, calories=200, protein=20, fat=10, carbs=40)
        rec = _mk_rec(db, [(a.id, 100), (b.id, 50)])
        n = crud.calculate_recipe_nutrition(db, rec.id)
        assert n.total_calories == pytest.approx(100 * 1.0 + 200 * 0.5)
        assert n.total_protein == pytest.approx(10 * 1.0 + 20 * 0.5)
        assert n.total_fat == pytest.approx(5 * 1.0 + 10 * 0.5)
        assert n.total_carbs == pytest.approx(20 * 1.0 + 40 * 0.5)

    def test_servings_zero_defaults_to_one(self, db):
        ing = _mk_ing(db, calories=300, protein=30, fat=15, carbs=60)
        rec = _mk_rec(db, [(ing.id, 100)])
        rec.servings = 0
        db.commit()
        n = crud.calculate_recipe_nutrition(db, rec.id)
        assert n.total_calories == 300.0
        assert n.per_serving["calories"] == 300.0
        assert n.per_serving["calories"] == n.total_calories

    def test_servings_negative_defaults_to_one(self, db):
        ing = _mk_ing(db, calories=300, protein=30, fat=15, carbs=60)
        rec = _mk_rec(db, [(ing.id, 100)])
        rec.servings = -5
        db.commit()
        n = crud.calculate_recipe_nutrition(db, rec.id)
        assert n.per_serving["calories"] == n.total_calories
        assert n.per_serving["protein"] == n.total_protein

    def test_empty_ingredients_all_zeros(self, db):
        rec = _mk_rec(db, [])
        n = crud.calculate_recipe_nutrition(db, rec.id)
        assert n.total_calories == 0
        assert n.total_protein == 0
        assert n.total_fat == 0
        assert n.total_carbs == 0
        assert n.total_fiber == 0
        assert n.total_sodium == 0
        assert n.total_vitamin_a == 0
        assert n.total_vitamin_c == 0
        assert n.total_calcium == 0
        assert n.total_iron == 0
        assert n.per_serving["calories"] == 0
        assert n.per_serving["protein"] == 0

    def test_rounding_precision_no_accumulation(self, db):
        a = _mk_ing(db, calories=10.005, protein=10.005, fat=10.005, carbs=10.005)
        b = _mk_ing(db, calories=10.005, protein=10.005, fat=10.005, carbs=10.005)
        rec = _mk_rec(db, [(a.id, 100), (b.id, 100)])
        n = crud.calculate_recipe_nutrition(db, rec.id)
        expected_total_cal = round(10.005 + 10.005, 2)
        assert n.total_calories == expected_total_cal
        expected_total_protein = round(10.005 + 10.005, 2)
        assert n.total_protein == expected_total_protein

    def test_per_serving_with_multiple_servings(self, db):
        ing = _mk_ing(db, calories=400, protein=40, fat=20, carbs=80)
        rec = _mk_rec(db, [(ing.id, 100)], servings=4)
        n = crud.calculate_recipe_nutrition(db, rec.id)
        assert n.total_calories == 400.0
        assert n.per_serving["calories"] == 100.0
        assert n.per_serving["protein"] == 10.0
        assert n.per_serving["fat"] == 5.0
        assert n.per_serving["carbs"] == 20.0

    def test_recipe_not_found_returns_none(self, db):
        assert crud.calculate_recipe_nutrition(db, 99999) is None

    def test_fractional_amount_factor(self, db):
        ing = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20)
        rec = _mk_rec(db, [(ing.id, 33.33)])
        n = crud.calculate_recipe_nutrition(db, rec.id)
        factor = 33.33 / 100.0
        assert n.total_calories == pytest.approx(100 * factor, abs=0.01)
        assert n.total_protein == pytest.approx(10 * factor, abs=0.01)

    def test_per_serving_independent_of_total_rounding(self, db):
        ing = _mk_ing(db, calories=33.33, protein=33.33, fat=33.33, carbs=33.33)
        rec = _mk_rec(db, [(ing.id, 100)], servings=3)
        n = crud.calculate_recipe_nutrition(db, rec.id)
        raw_per_serving_cal = 33.33 / 3
        assert n.per_serving["calories"] == round(raw_per_serving_cal, 2)
        assert n.total_calories == 33.33


# ═══════════════════════════════════════════════════════════════════════
#  generate_meal_plan
# ═══════════════════════════════════════════════════════════════════════

class TestGenerateMealPlan:

    def _make_recipe_with_nutrition(self, db, cal, protein, **kw):
        ing = _mk_ing(db, calories=cal, protein=protein, fat=5, carbs=20)
        return _mk_rec(db, [(ing.id, 100)], **kw)

    def test_basic_generation(self, db):
        user = _mk_usr(db)
        for _ in range(3):
            self._make_recipe_with_nutrition(db, 500, 15)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is not None
        assert len(mp.items) == 4
        assert mp.target_calories == 2000
        assert mp.target_protein == 60
        meal_types = [item.meal_type for item in mp.items]
        assert meal_types == ["早餐", "午餐", "晚餐", "加餐"]

    def test_combination_limit_5000(self, db):
        user = _mk_usr(db)
        for _ in range(10):
            self._make_recipe_with_nutrition(db, 500, 15)
        counter = [0]
        orig_product = itertools.product

        def counting_product(*a, **kw):
            for item in orig_product(*a, **kw):
                counter[0] += 1
                yield item

        with patch("itertools.product", counting_product):
            mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
                goal=models.Goal.MAINTENANCE,
                target_calories=2000,
                target_protein=60,
                days=1,
            ))
        assert mp is not None
        assert counter[0] == 5001

    def test_combination_limit_not_triggered_few_recipes(self, db):
        user = _mk_usr(db)
        for _ in range(3):
            self._make_recipe_with_nutrition(db, 500, 15)
        counter = [0]
        orig_product = itertools.product

        def counting_product(*a, **kw):
            for item in orig_product(*a, **kw):
                counter[0] += 1
                yield item

        with patch("itertools.product", counting_product):
            mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
                goal=models.Goal.MAINTENANCE,
                target_calories=2000,
                target_protein=60,
                days=1,
            ))
        assert mp is not None
        assert counter[0] == 3 ** 4

    def test_no_feasible_plan_still_returns_best_infeasible(self, db):
        user = _mk_usr(db)
        self._make_recipe_with_nutrition(db, 100, 5)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is not None
        assert len(mp.items) == 4
        total_cal = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["calories"]
            for item in mp.items
        )
        total_protein = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["protein"]
            for item in mp.items
        )
        assert total_cal < 2000 * 0.9
        assert total_protein < 60

    def test_feasibility_calories_at_lower_boundary(self, db):
        user = _mk_usr(db)
        self._make_recipe_with_nutrition(db, 450, 20)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is not None
        total_cal = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["calories"]
            for item in mp.items
        )
        assert total_cal == pytest.approx(1800.0)
        assert total_cal >= 2000 * 0.9

    def test_feasibility_calories_just_below_lower_boundary(self, db):
        user = _mk_usr(db)
        self._make_recipe_with_nutrition(db, 449.99, 20)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is not None
        total_cal = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["calories"]
            for item in mp.items
        )
        assert total_cal < 2000 * 0.9

    def test_feasibility_calories_at_upper_boundary(self, db):
        user = _mk_usr(db)
        self._make_recipe_with_nutrition(db, 550, 20)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is not None
        total_cal = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["calories"]
            for item in mp.items
        )
        assert total_cal == pytest.approx(2200.0)
        assert total_cal <= 2000 * 1.1

    def test_feasibility_calories_just_above_upper_boundary(self, db):
        user = _mk_usr(db)
        self._make_recipe_with_nutrition(db, 550.01, 20)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is not None
        total_cal = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["calories"]
            for item in mp.items
        )
        assert total_cal > 2000 * 1.1

    def test_feasibility_protein_exactly_at_target(self, db):
        user = _mk_usr(db)
        self._make_recipe_with_nutrition(db, 500, 15)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is not None
        total_protein = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["protein"]
            for item in mp.items
        )
        assert total_protein == pytest.approx(60.0)
        assert total_protein >= 60

    def test_feasibility_protein_just_below_target(self, db):
        user = _mk_usr(db)
        self._make_recipe_with_nutrition(db, 500, 14.99)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is not None
        total_protein = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["protein"]
            for item in mp.items
        )
        assert total_protein < 60

    def test_empty_recipes_returns_none(self, db):
        user = _mk_usr(db)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is None

    def test_fallback_index_error_bug(self, db):
        """
        [BUG] 当所有食谱的营养计算都返回 None 时，recipe_list 为空，
        best_combination 保持 None，退化分支访问 recipe_list[0] 抛出 IndexError。
        正常流程下此分支不可达（recipe_list 非空时 product 必产出组合，
        best_score 初始 inf 保证首次必更新），但若因任何原因 recipe_list 为空，
        则退化分支会崩溃而非优雅降级。
        """
        user = _mk_usr(db)
        ing = _mk_ing(db)
        _mk_rec(db, [(ing.id, 100)])
        with patch.object(crud, "calculate_recipe_nutrition", return_value=None):
            with pytest.raises(IndexError):
                crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
                    goal=models.Goal.MAINTENANCE,
                    target_calories=2000,
                    target_protein=60,
                    days=1,
                ))

    def test_multi_day_generation(self, db):
        user = _mk_usr(db)
        self._make_recipe_with_nutrition(db, 500, 15)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=3,
        ))
        assert mp is not None
        assert len(mp.items) == 12

    def test_feasible_preferred_over_infeasible(self, db):
        user = _mk_usr(db)
        self._make_recipe_with_nutrition(db, 500, 15,
                                          category=models.RecipeCategory.BREAKFAST)
        self._make_recipe_with_nutrition(db, 100, 5,
                                          category=models.RecipeCategory.SNACK)
        mp = crud.generate_meal_plan(db, user.id, schemas.MealPlanGenerate(
            goal=models.Goal.MAINTENANCE,
            target_calories=2000,
            target_protein=60,
            days=1,
        ))
        assert mp is not None
        total_cal = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["calories"]
            for item in mp.items
        )
        total_protein = sum(
            crud.calculate_recipe_nutrition(db, item.recipe_id).per_serving["protein"]
            for item in mp.items
        )
        assert 2000 * 0.9 <= total_cal <= 2000 * 1.1
        assert total_protein >= 60


# ═══════════════════════════════════════════════════════════════════════
#  get_ingredient_substitutes
# ═══════════════════════════════════════════════════════════════════════

class TestGetIngredientSubstitutes:

    def test_basic_substitutes(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        cand = _mk_ing(db, calories=105, protein=11, fat=5.5, carbs=22,
                        category=models.IngredientCategory.MEAT)
        result = crud.get_ingredient_substitutes(db, src.id)
        assert len(result) >= 1
        assert result[0]["ingredient"].id == cand.id
        assert result[0]["similarity_score"] > 0

    def test_division_by_zero_calories_bug(self, db):
        """
        [BUG] 源配料 calories=0 时，计算 calories_diff 执行
        abs(candidate.calories - 0) / 0 → ZeroDivisionError。
        只要同分类下存在任何候选配料就会触发。
        """
        src = _mk_ing(db, calories=0, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.VEGETABLE)
        _mk_ing(db, calories=10, protein=10, fat=5, carbs=20,
                 category=models.IngredientCategory.VEGETABLE)
        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db, src.id)

    def test_division_by_zero_protein_bug(self, db):
        """
        [BUG] 源配料 protein=0 时，计算 protein_diff 执行
        abs(candidate.protein - 0) / 0 → ZeroDivisionError。
        """
        src = _mk_ing(db, calories=100, protein=0, fat=5, carbs=20,
                       category=models.IngredientCategory.VEGETABLE)
        _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                 category=models.IngredientCategory.VEGETABLE)
        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db, src.id)

    def test_division_by_zero_fat_bug(self, db):
        """
        [BUG] 源配料 fat=0 时，计算 fat_diff 执行
        abs(candidate.fat - 0) / 0 → ZeroDivisionError。
        """
        src = _mk_ing(db, calories=100, protein=10, fat=0, carbs=20,
                       category=models.IngredientCategory.VEGETABLE)
        _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                 category=models.IngredientCategory.VEGETABLE)
        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db, src.id)

    def test_similarity_threshold_exact_0_2_included(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        _mk_ing(db, calories=120, protein=10, fat=5, carbs=20,
                 category=models.IngredientCategory.MEAT)
        result = crud.get_ingredient_substitutes(db, src.id)
        assert len(result) == 1
        assert result[0]["similarity_score"] == pytest.approx(
            1 - (0.2 + 0 + 0) / 3
        )

    def test_similarity_threshold_above_0_2_excluded(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        _mk_ing(db, calories=121, protein=10, fat=5, carbs=20,
                 category=models.IngredientCategory.MEAT)
        result = crud.get_ingredient_substitutes(db, src.id)
        assert len(result) == 0

    def test_similarity_threshold_protein_exact_0_2(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        _mk_ing(db, calories=100, protein=12, fat=5, carbs=20,
                 category=models.IngredientCategory.MEAT)
        result = crud.get_ingredient_substitutes(db, src.id)
        assert len(result) == 1

    def test_similarity_threshold_fat_exact_0_2(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        _mk_ing(db, calories=100, protein=10, fat=6, carbs=20,
                 category=models.IngredientCategory.MEAT)
        result = crud.get_ingredient_substitutes(db, src.id)
        assert len(result) == 1

    def test_top_n_sorting_descending(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        c1 = _mk_ing(db, calories=105, protein=10.5, fat=5, carbs=20,
                      category=models.IngredientCategory.MEAT)
        c2 = _mk_ing(db, calories=110, protein=11, fat=5.5, carbs=20,
                      category=models.IngredientCategory.MEAT)
        c3 = _mk_ing(db, calories=102, protein=10.2, fat=5.1, carbs=20,
                      category=models.IngredientCategory.MEAT)
        result = crud.get_ingredient_substitutes(db, src.id, top_n=2)
        assert len(result) == 2
        assert result[0]["similarity_score"] >= result[1]["similarity_score"]
        assert result[0]["ingredient"].id == c3.id
        assert result[1]["ingredient"].id == c1.id

    def test_top_n_larger_than_candidates(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        _mk_ing(db, calories=105, protein=10, fat=5, carbs=20,
                 category=models.IngredientCategory.MEAT)
        result = crud.get_ingredient_substitutes(db, src.id, top_n=10)
        assert len(result) == 1

    def test_ingredient_not_found_returns_none(self, db):
        assert crud.get_ingredient_substitutes(db, 99999) is None

    def test_no_candidates_in_same_category(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.NUT)
        result = crud.get_ingredient_substitutes(db, src.id)
        assert result == []

    def test_excludes_self(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        result = crud.get_ingredient_substitutes(db, src.id)
        ids = [r["ingredient"].id for r in result]
        assert src.id not in ids

    def test_perfect_match_similarity_1(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                 category=models.IngredientCategory.MEAT)
        result = crud.get_ingredient_substitutes(db, src.id)
        assert len(result) == 1
        assert result[0]["similarity_score"] == pytest.approx(1.0)

    def test_cross_category_not_matched(self, db):
        src = _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                       category=models.IngredientCategory.MEAT)
        _mk_ing(db, calories=100, protein=10, fat=5, carbs=20,
                 category=models.IngredientCategory.VEGETABLE)
        result = crud.get_ingredient_substitutes(db, src.id)
        assert len(result) == 0
