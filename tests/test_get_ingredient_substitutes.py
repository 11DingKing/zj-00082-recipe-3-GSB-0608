"""get_ingredient_substitutes 单元测试。

覆盖：
- 候选食材的 protein/fat 为 0 时, 相似度计算的 ZeroDivisionError
- 0.2 阈值的边界判定
- top_n 截取与按 similarity_score 排序
"""
from __future__ import annotations

import pytest

import crud
import models

from .conftest import make_ingredient


CAT = models.IngredientCategory.MEAT


class TestGetIngredientSubstitutesZeroDivision:
    def test_target_protein_zero_raises_zero_division(self, db):
        """
        BUG: 当目标食材 protein=0 时, ``protein_diff = abs(...) / db_ingredient.protein``
        会触发 ZeroDivisionError.
        """
        target = make_ingredient(
            db, name="target", category=CAT,
            calories=100, protein=0, fat=10, carbs=10,
        )
        # 至少一个同类候选, 否则 candidates 为空就走不到除法
        make_ingredient(
            db, name="cand", category=CAT,
            calories=100, protein=0, fat=10, carbs=10,
        )
        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db, target.id)

    def test_target_fat_zero_raises_zero_division(self, db):
        """
        BUG: 目标食材 fat=0 时同样会 ZeroDivisionError.
        """
        target = make_ingredient(
            db, name="target", category=CAT,
            calories=100, protein=10, fat=0, carbs=10,
        )
        make_ingredient(
            db, name="cand", category=CAT,
            calories=100, protein=10, fat=0, carbs=10,
        )
        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db, target.id)

    def test_target_calories_zero_raises_zero_division(self, db):
        """
        BUG: 目标食材 calories=0 时同样 ZeroDivisionError.
        """
        target = make_ingredient(
            db, name="target", category=CAT,
            calories=0, protein=10, fat=10, carbs=10,
        )
        make_ingredient(
            db, name="cand", category=CAT,
            calories=0, protein=10, fat=10, carbs=10,
        )
        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db, target.id)


class TestGetIngredientSubstitutesThreshold:
    def test_threshold_inclusive_at_0_2(self, db):
        """
        diff 恰好 = 0.2 时应当被纳入(<=).
        target: cal=100, protein=10, fat=10
        cand_in: cal=120 (diff 0.2), protein=12 (0.2), fat=12 (0.2) → 全部 == 0.2 边界
        """
        target = make_ingredient(
            db, name="t", category=CAT,
            calories=100, protein=10, fat=10, carbs=10,
        )
        cand_in = make_ingredient(
            db, name="c_in", category=CAT,
            calories=120, protein=12, fat=12, carbs=10,
        )
        result = crud.get_ingredient_substitutes(db, target.id)
        assert result is not None
        assert len(result) == 1
        assert result[0]["ingredient"].id == cand_in.id
        # similarity = 1 - (0.2*3)/3 = 0.8
        assert abs(result[0]["similarity_score"] - 0.8) < 1e-9

    def test_threshold_just_above_0_2_excluded(self, db):
        """diff = 0.21 应被排除."""
        target = make_ingredient(
            db, name="t", category=CAT,
            calories=100, protein=10, fat=10, carbs=10,
        )
        # 任何一个维度 > 0.2 都应被排除: 这里 calories diff=0.21
        make_ingredient(
            db, name="c_out", category=CAT,
            calories=121, protein=10, fat=10, carbs=10,
        )
        result = crud.get_ingredient_substitutes(db, target.id)
        assert result == []

    def test_different_category_excluded(self, db):
        """不同 category 的食材一开始就不会进入候选列表."""
        target = make_ingredient(
            db, name="t", category=CAT,
            calories=100, protein=10, fat=10, carbs=10,
        )
        make_ingredient(
            db, name="other_cat", category=models.IngredientCategory.FRUIT,
            calories=100, protein=10, fat=10, carbs=10,
        )
        result = crud.get_ingredient_substitutes(db, target.id)
        assert result == []


class TestGetIngredientSubstitutesSorting:
    def test_sorted_by_similarity_descending_and_top_n(self, db):
        """
        - 多个候选时按 similarity 降序排列
        - top_n 截取生效
        """
        target = make_ingredient(
            db, name="t", category=CAT,
            calories=100, protein=10, fat=10, carbs=10,
        )
        # cand_high: 全部 diff = 0 → similarity = 1.0
        c_high = make_ingredient(
            db, name="c_high", category=CAT,
            calories=100, protein=10, fat=10, carbs=10,
        )
        # cand_mid: cal diff=0.1 → similarity = 1 - 0.1/3 ≈ 0.9667
        c_mid = make_ingredient(
            db, name="c_mid", category=CAT,
            calories=110, protein=10, fat=10, carbs=10,
        )
        # cand_low: 全部 0.2 → similarity 0.8
        c_low = make_ingredient(
            db, name="c_low", category=CAT,
            calories=120, protein=12, fat=12, carbs=10,
        )

        result = crud.get_ingredient_substitutes(db, target.id, top_n=10)
        assert [r["ingredient"].id for r in result] == [c_high.id, c_mid.id, c_low.id]
        # similarity 严格递减
        scores = [r["similarity_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

        # top_n=2 截取
        result_top2 = crud.get_ingredient_substitutes(db, target.id, top_n=2)
        assert len(result_top2) == 2
        assert [r["ingredient"].id for r in result_top2] == [c_high.id, c_mid.id]

    def test_top_n_zero_returns_empty(self, db):
        target = make_ingredient(
            db, name="t", category=CAT,
            calories=100, protein=10, fat=10, carbs=10,
        )
        make_ingredient(
            db, name="c", category=CAT,
            calories=100, protein=10, fat=10, carbs=10,
        )
        result = crud.get_ingredient_substitutes(db, target.id, top_n=0)
        assert result == []

    def test_target_not_found(self, db):
        assert crud.get_ingredient_substitutes(db, 9999) is None

    def test_self_excluded_from_candidates(self, db):
        """目标食材自己不应出现在结果中."""
        target = make_ingredient(
            db, name="t", category=CAT,
            calories=100, protein=10, fat=10, carbs=10,
        )
        result = crud.get_ingredient_substitutes(db, target.id)
        assert result == []  # 没有其他候选
