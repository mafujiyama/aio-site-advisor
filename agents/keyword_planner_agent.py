# agents/keyword_planner_agent.py

from __future__ import annotations

import json
import logging
from typing import List, Optional

from openai import OpenAI

from app.config import settings
from models.keyword_models import KeywordPlan, KeywordItem

# ============================================================
# ロガー設定
# ============================================================

logger = logging.getLogger(__name__)

# 開発中は必ずコンソールに出したいので、ハンドラを直付け
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)

# デフォルトレベルを INFO に
logger.setLevel(logging.INFO)

# ============================================================
# 軽量化パラメータ
# ============================================================

# 1シードあたりに取得する最大キーワード数
MAX_ITEMS_DEFAULT = 12  # 必要なら 8 や 10 にすればさらに軽くなる
# reason の最大文字数
MAX_REASON_LEN = 30


# ============================================================
# フォールバックプラン
# ============================================================

def _fallback_plan(seed_keyword: str) -> KeywordPlan:
    """
    APIキーやLLMがなくても必ず動く、固定ロジックのキーワードプラン。
    KeywordPlannerエージェントのフォールバックとして扱う。
    """
    logger.info("[keyword_planner] use FALLBACK plan (no LLM) seed_keyword=%s", seed_keyword)

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


# ============================================================
# 正規化ユーティリティ
# ============================================================

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
    v = str(value).upper()
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


# ============================================================
# LLM プラン（軽量版）
# ============================================================

def _llm_plan(
    seed_keyword: str,
    site_profile: Optional[dict] = None,
    max_items: int = MAX_ITEMS_DEFAULT,
) -> KeywordPlan:
    """
    LLM を使ってキーワードプランを生成する（軽量版）。

    - 返却件数を max_items に制限
    - reason は短く（MAX_REASON_LEN）に切り詰める
    - max_tokens でレスポンス長を制御
    """
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY が設定されていません")

    model_name = getattr(settings, "openai_model", None) or "gpt-4.1-mini"

    logger.info(
        "[keyword_planner] LLM plan start seed_keyword=%s model=%s max_items=%d",
        seed_keyword,
        model_name,
        max_items,
    )

    client = OpenAI(api_key=settings.openai_api_key)

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
- reason は「短いフレーズ」で記載（{MAX_REASON_LEN}文字以内を目安）
- ロングテールキーワードも含める
- items は 最大 {max_items} 件まで（それ以上は返さないこと）
""".strip()

    response = client.chat.completions.create(
        model=model_name,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=800,
    )

    usage = getattr(response, "usage", None)
    logger.info(
        "[keyword_planner] LLM response received seed_keyword=%s total_tokens=%s",
        seed_keyword,
        getattr(usage, "total_tokens", None) if usage else None,
    )

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("LLM からコンテンツが返却されませんでした")

    try:
        data = json.loads(content)
    except Exception as e:  # noqa: BLE001
        logger.error(
            "[keyword_planner] JSON parse error seed_keyword=%s error=%s content=%r",
            seed_keyword,
            e,
            content[:2000],
        )
        raise RuntimeError("LLM からの JSON パースに失敗しました") from e

    raw_items = data.get("items", []) or []
    if not isinstance(raw_items, list):
        raise RuntimeError("LLM からの JSON の形式が不正です（items が配列でない）")

    raw_items = raw_items[:max_items]

    items: List[KeywordItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue

        keyword = raw.get("keyword")
        if not keyword:
            continue

        intent_raw = raw.get("intent")
        category = raw.get("category")
        priority_raw = raw.get("priority")
        reason = raw.get("reason")

        if isinstance(reason, str) and len(reason) > MAX_REASON_LEN:
            reason = reason[:MAX_REASON_LEN]

        items.append(
            KeywordItem(
                keyword=keyword,
                intent=_normalize_intent(intent_raw),
                category=category,
                priority=_clamp_priority(priority_raw),
                reason=reason,
            )
        )

    if not items:
        raise RuntimeError("LLM から有効な items が取得できませんでした")

    logger.info(
        "[keyword_planner] LLM plan success seed_keyword=%s item_count=%d",
        seed_keyword,
        len(items),
    )

    return KeywordPlan(seed_keyword=seed_keyword, items=items)


# ============================================================
# 公開関数
# ============================================================

def plan_keywords(seed_keyword: str, site_profile: Optional[dict] = None) -> KeywordPlan:
    """
    KeywordPlanner のメイン関数。

    優先順位:
    1. OPENAI_API_KEY が設定されていれば LLM ベースのプランを試す
    2. 例外が発生した場合や APIキー未設定時は、固定ロジックのフォールバックを返す
    """
    has_key = bool(settings.openai_api_key)
    logger.info(
        "[keyword_planner] plan_keywords called seed_keyword=%s has_openai_key=%s",
        seed_keyword,
        has_key,
    )

    # 1) APIキーが無い → 即フォールバック
    if not has_key:
        logger.info("[keyword_planner] mode=FALLBACK (no OPENAI_API_KEY)")
        return _fallback_plan(seed_keyword)

    # 2) APIキーがある → LLM を試す
    try:
        logger.info("[keyword_planner] mode=LLM (using OpenAI)")
        return _llm_plan(seed_keyword, site_profile=site_profile)
    except Exception as e:  # noqa: BLE001
        logger.warning("[keyword_planner] LLM error, fallback used: %s", e)
        return _fallback_plan(seed_keyword)
