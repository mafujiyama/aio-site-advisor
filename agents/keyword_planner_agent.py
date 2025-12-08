# agents/keyword_planner_agent.py

from typing import Optional

from models.keyword_models import KeywordPlan, KeywordItem


def _fallback_plan(seed_keyword: str) -> KeywordPlan:
    """
    APIキーやLLMがなくても必ず動く、固定ロジックのキーワードプラン。
    当面はこれを「KeywordPlannerエージェント」として扱う。
    """
    items = [
        KeywordItem(
            keyword=seed_keyword,
            intent="KNOW",
            category="基礎・概要",
            priority=5,
            reason="軸キーワードのため最優先",
        ),
        KeywordItem(
            keyword=f"{seed_keyword} とは",
            intent="KNOW",
            category="基礎・概要",
            priority=5,
            reason="定義・概要コンテンツが必要",
        ),
        KeywordItem(
            keyword=f"{seed_keyword} 種類",
            intent="KNOW",
            category="基礎・概要",
            priority=4,
            reason="製品ラインナップやバリエーションの解説用",
        ),
        KeywordItem(
            keyword=f"{seed_keyword} 比較",
            intent="COMPARE",
            category="比較・選定",
            priority=4,
            reason="他方式・他社との比較コンテンツ向け",
        ),
        KeywordItem(
            keyword=f"{seed_keyword} 事例",
            intent="KNOW",
            category="導入事例",
            priority=4,
            reason="E-E-A-T強化・用途イメージ訴求に有効",
        ),
        KeywordItem(
            keyword=f"{seed_keyword} 設計",
            intent="KNOW",
            category="設計・ノウハウ",
            priority=3,
            reason="設計者向けの技術情報・設計Tips向け",
        ),
        KeywordItem(
            keyword=f"{seed_keyword} 強度 計算",
            intent="KNOW",
            category="設計・ノウハウ",
            priority=3,
            reason="技術系ニーズ（計算・条件検討）向け",
        ),
        KeywordItem(
            keyword=f"{seed_keyword} 価格",
            intent="BUY",
            category="購入・見積",
            priority=3,
            reason="価格・コスト比較ニーズに対応",
        ),
        KeywordItem(
            keyword=f"{seed_keyword} 見積",
            intent="BUY",
            category="購入・見積",
            priority=3,
            reason="BtoB調達担当向けの見積・リード獲得用",
        ),
        KeywordItem(
            keyword=f"{seed_keyword} メーカー",
            intent="NAVIGATIONAL",
            category="ナビゲーション",
            priority=2,
            reason="メーカー名・ブランド名でのナビゲーションニーズ向け",
        ),
    ]
    return KeywordPlan(seed_keyword=seed_keyword, items=items)


def plan_keywords(seed_keyword: str, site_profile: Optional[dict] = None) -> KeywordPlan:
    """
    現時点では LLM を使わず、
    どの環境でも必ず動作するフォールバックロジックのみを使用する。
    """
    # site_profile は将来の拡張用。今は使わない。
    return _fallback_plan(seed_keyword)
