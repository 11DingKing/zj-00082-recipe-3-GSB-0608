import pytest
from models import IngredientCategory
import schemas
import crud


class TestGetIngredientSubstitutes:
    
    def test_ingredient_not_found_returns_none(self, db):
        """测试不存在的配料返回 None"""
        result = crud.get_ingredient_substitutes(db, 99999)
        assert result is None
    
    def test_no_candidates_same_category(self, db, create_test_ingredient):
        """测试同分类下没有其他配料时返回空列表"""
        ing = create_test_ingredient(
            "唯一蔬菜",
            IngredientCategory.VEGETABLE,
            calories=50,
            protein=2,
            fat=0.5,
            carbs=10,
            unit_price=5.0
        )
        result = crud.get_ingredient_substitutes(db, ing.id)
        assert result == []
    
    def test_perfect_match_returns_highest_similarity(self, db, create_test_ingredient):
        """测试完全相同的配料相似度最高（应该等于 1）"""
        base = create_test_ingredient(
            "base", IngredientCategory.MEAT,
            calories=100, protein=20, fat=10, carbs=0, unit_price=10
        )
        identical = create_test_ingredient(
            "identical", IngredientCategory.MEAT,
            calories=100, protein=20, fat=10, carbs=0, unit_price=10
        )
        
        result = crud.get_ingredient_substitutes(db, base.id)
        
        assert len(result) >= 1
        assert result[0]["ingredient"].id == identical.id
        assert result[0]["similarity_score"] == 1.0
    
    def test_zero_protein_causes_division_by_zero(self, db, create_test_ingredient):
        """BUG 测试：原始配料蛋白质为 0 时会触发除零错误
        
        这是一个真实存在的 bug：
        protein_diff = abs(candidate.protein - db_ingredient.protein) / db_ingredient.protein
        当 db_ingredient.protein == 0 时直接 ZeroDivisionError
        """
        zero_protein_ing = create_test_ingredient(
            "零蛋白配料", IngredientCategory.GRAIN,
            calories=100, protein=0, fat=5, carbs=20, unit_price=5
        )
        candidate = create_test_ingredient(
            "候选配料", IngredientCategory.GRAIN,
            calories=110, protein=1, fat=5, carbs=22, unit_price=6
        )
        
        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db, zero_protein_ing.id)
    
    def test_zero_fat_causes_division_by_zero(self, db, create_test_ingredient):
        """BUG 测试：原始配料脂肪为 0 时会触发除零错误
        
        这是一个真实存在的 bug：
        fat_diff = abs(candidate.fat - db_ingredient.fat) / db_ingredient.fat
        当 db_ingredient.fat == 0 时直接 ZeroDivisionError
        """
        zero_fat_ing = create_test_ingredient(
            "零脂肪配料", IngredientCategory.VEGETABLE,
            calories=50, protein=2, fat=0, carbs=12, unit_price=3
        )
        candidate = create_test_ingredient(
            "候选配料", IngredientCategory.VEGETABLE,
            calories=55, protein=2, fat=0.5, carbs=13, unit_price=4
        )
        
        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db, zero_fat_ing.id)
    
    def test_zero_calories_causes_division_by_zero(self, db, create_test_ingredient):
        """BUG 测试：原始配料热量为 0 时会触发除零错误
        
        这是一个真实存在的 bug：
        calories_diff = abs(candidate.calories - db_ingredient.calories) / db_ingredient.calories
        当 db_ingredient.calories == 0 时直接 ZeroDivisionError
        """
        zero_cal_ing = create_test_ingredient(
            "零热量配料", IngredientCategory.SEASONING,
            calories=0, protein=0, fat=0, carbs=0, unit_price=1
        )
        candidate = create_test_ingredient(
            "候选配料", IngredientCategory.SEASONING,
            calories=5, protein=0, fat=0, carbs=1, unit_price=2
        )
        
        with pytest.raises(ZeroDivisionError):
            crud.get_ingredient_substitutes(db, zero_cal_ing.id)
    
    def test_threshold_exactly_02_is_included(self, db, create_test_ingredient):
        """测试阈值边界：差值正好 20% 应该被包含（<= 0.2）"""
        base = create_test_ingredient(
            "base", IngredientCategory.MEAT,
            calories=100, protein=20, fat=10, carbs=0, unit_price=10
        )
        
        exact_20_pct = create_test_ingredient(
            "exact_20_pct", IngredientCategory.MEAT,
            calories=120,
            protein=24,
            fat=12,
            carbs=0,
            unit_price=10
        )
        
        result = crud.get_ingredient_substitutes(db, base.id)
        ids = [r["ingredient"].id for r in result]
        assert exact_20_pct.id in ids
    
    def test_threshold_above_02_is_excluded(self, db, create_test_ingredient):
        """测试阈值边界：差值超过 20% 应该被排除"""
        base = create_test_ingredient(
            "base", IngredientCategory.MEAT,
            calories=100, protein=20, fat=10, carbs=0, unit_price=10
        )
        
        just_above = create_test_ingredient(
            "just_above", IngredientCategory.MEAT,
            calories=121,
            protein=20,
            fat=10,
            carbs=0,
            unit_price=10
        )
        
        result = crud.get_ingredient_substitutes(db, base.id)
        ids = [r["ingredient"].id for r in result]
        assert just_above.id not in ids
    
    def test_sorted_by_similarity_descending(self, db, create_test_ingredient):
        """测试结果按相似度从高到低排序"""
        base = create_test_ingredient(
            "base", IngredientCategory.MEAT,
            calories=100, protein=20, fat=10, carbs=0, unit_price=10
        )
        
        closest = create_test_ingredient(
            "closest", IngredientCategory.MEAT,
            calories=105, protein=21, fat=10.5, carbs=0, unit_price=10
        )
        middle = create_test_ingredient(
            "middle", IngredientCategory.MEAT,
            calories=110, protein=22, fat=11, carbs=0, unit_price=10
        )
        farthest = create_test_ingredient(
            "farthest", IngredientCategory.MEAT,
            calories=115, protein=23, fat=11.5, carbs=0, unit_price=10
        )
        
        result = crud.get_ingredient_substitutes(db, base.id)
        
        assert len(result) == 3
        assert result[0]["ingredient"].name == "closest"
        assert result[1]["ingredient"].name == "middle"
        assert result[2]["ingredient"].name == "farthest"
        
        assert result[0]["similarity_score"] > result[1]["similarity_score"]
        assert result[1]["similarity_score"] > result[2]["similarity_score"]
    
    def test_top_n_limits_results(self, db, create_test_ingredient):
        """测试 top_n 参数限制返回数量"""
        base = create_test_ingredient(
            "base", IngredientCategory.MEAT,
            calories=100, protein=20, fat=10, carbs=0, unit_price=10
        )
        
        for i in range(10):
            create_test_ingredient(
                f"candidate_{i}", IngredientCategory.MEAT,
                calories=100 + i,
                protein=20,
                fat=10,
                carbs=0,
                unit_price=10
            )
        
        result_default = crud.get_ingredient_substitutes(db, base.id)
        assert len(result_default) == 5
        
        result_3 = crud.get_ingredient_substitutes(db, base.id, top_n=3)
        assert len(result_3) == 3
        
        result_100 = crud.get_ingredient_substitutes(db, base.id, top_n=100)
        assert len(result_100) == 10
    
    def test_different_category_not_considered(self, db, create_test_ingredient):
        """测试不同分类的配料不会被考虑为替代品"""
        base = create_test_ingredient(
            "base", IngredientCategory.MEAT,
            calories=100, protein=20, fat=10, carbs=0, unit_price=10
        )
        
        veg_same_nutrition = create_test_ingredient(
            "veg_same", IngredientCategory.VEGETABLE,
            calories=100, protein=20, fat=10, carbs=0, unit_price=5
        )
        
        result = crud.get_ingredient_substitutes(db, base.id)
        ids = [r["ingredient"].id for r in result]
        assert veg_same_nutrition.id not in ids
    
    def test_all_three_nutrients_must_pass_threshold(self, db, create_test_ingredient):
        """测试三个营养指标必须全部通过阈值才会被选中"""
        base = create_test_ingredient(
            "base", IngredientCategory.MEAT,
            calories=100, protein=20, fat=10, carbs=0, unit_price=10
        )
        
        cal_ok_protein_bad = create_test_ingredient(
            "cal_ok_protein_bad", IngredientCategory.MEAT,
            calories=105, protein=50, fat=10.5, carbs=0, unit_price=10
        )
        
        protein_ok_fat_bad = create_test_ingredient(
            "protein_ok_fat_bad", IngredientCategory.MEAT,
            calories=105, protein=21, fat=50, carbs=0, unit_price=10
        )
        
        result = crud.get_ingredient_substitutes(db, base.id)
        ids = [r["ingredient"].id for r in result]
        
        assert cal_ok_protein_bad.id not in ids
        assert protein_ok_fat_bad.id not in ids
