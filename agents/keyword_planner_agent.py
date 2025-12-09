# agents/keyword_planner_agent.py

from __future__ import annotations

import json
from typing import List, Optional

from openai import OpenAI

from app.config import settings
from models.keyword_models import KeywordPlan, KeywordItem


def _fallback_plan(seed_keyword: str) -> KeywordPlan:
    """
    APIキーやLLMがなくても必ず動く、固定ロジックのキーワードプラン。
    当面はこれを「KeywordPlannerエージェント」のフォールバックとして扱う。
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


def _clamp_priority(value: Optional[int]) -> int:
    """priority を 1〜5 の範囲に丸める（None の場合は 3）。"""
    if value is None:
        return 3
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 3
    return max(1, min(5, v))


def _normalize_intent(value: Optional[str]) -> str:
    """LLM から返ってきた intent を既定の4分類に正規化する。"""
    if not value:
        return "KNOW"
    v = value.upper()
    if v in ("KNOW", "COMPARE", "BUY", "NAVIGATIONAL"):
        return v
    # ざっくりマッピング（日本語や英語のバリエーションが来た場合用）
    if "NAV" in v:
        return "NAVIGATIONAL"
    if "COMP" in v:
        return "COMPARE"
    if "BUY" in v or "PURCHASE" in v or "CV" in v:
        return "BUY"
    return "KNOW"


def _llm_plan(seed_keyword: str, site_profile: Optional[dict] = None) -> KeywordPlan:
    """LLM を使ってキーワードプランを生成する。失敗した場合は例外を投げる。"""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY が設定されていません")

    client = OpenAI(api_key=settings.openai_api_key)
    model_name = settings.openai_model

    # site_profile は将来拡張用（サイトの特徴・ターゲットなど）
    site_profile_text = json.dumps(site_profile, ensure_ascii=False) if site_profile else "null"

    system_prompt = """
あなたはBtoB製造業向けのSEOキーワードプランナーです。
指定された seed_keyword を軸に、関連する検索キーワード候補を JSON 形式で返してください。

必ず次のスキーマに従ってください:

{
  "items": [
    {
      "keyword": "string",
      "intent": "KNOW | COMPARE | BUY | NAVIGATIONAL | null",
      "category": "string | null",
      "priority": 1-5 | null,
      "reason": "string | null"
    }
  ]
}
""".strip()

    user_prompt = f"""
seed_keyword: {seed_keyword}

site_profile (JSON): {site_profile_text}

要件:
- intent は KNOW / COMPARE / BUY / NAVIGATIONAL のいずれか（不明なら null）
- priority は 1〜5（重要度が高いほど数値を大きく）
- category は「基礎・概要」「比較・選定」「導入事例」「設計・ノウハウ」「購入・見積」など任意
- reason には、なぜこのキーワードが有効かを一言で記載（省略可）
- ロングテールキーワードも含める
- items は20〜30件程度を目安とする
""".strip()

    response = client.chat.completions.create(
        model=model_name,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("LLM からコンテンツが返却されませんでした")

    data = json.loads(content)
    raw_items = data.get("items", [])

    items: List[KeywordItem] = []
    for raw in raw_items:
        keyword = raw.get("keyword")
        if not keyword:
            continue

        intent_raw = raw.get("intent")
        category = raw.get("category")
        priority_raw = raw.get("priority")
        reason = raw.get("reason")

        items.append(
            KeywordItem(
                keyword=keyword,
                intent=_normalize_intent(intent_raw),
                category=category,
                priority=_clamp_priority(priority_raw),
                reason=reason,
            )
        )

    # 念のため、一件も取れなかった場合はフォールバック
    if not items:
        raise RuntimeError("LLM から有効な items が取得できませんでした")

    return KeywordPlan(seed_keyword=seed_keyword, items=items)


def plan_keywords(seed_keyword: str, site_profile: Optional[dict] = None) -> KeywordPlan:
    """
    キーワードプランを生成するエントリポイント。

    優先順位:
    1. OPENAI_API_KEY が設定されていれば LLM ベースのプランを試す
    2. 例外が発生した場合や APIキー未設定時は、固定ロジックのフォールバックを返す
    """
    try:
        return _llm_plan(seed_keyword, site_profile=site_profile)
    except Exception:
        # ログ出力などは必要に応じてここに追加
        return _fallback_plan(seed_keyword)
