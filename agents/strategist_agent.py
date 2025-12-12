# agents/strategist_agent.py

from __future__ import annotations

import json
import logging
from typing import Dict, Optional

from openai import OpenAI

from app.config import settings
from models.keyword_models import KeywordPlan
from models.analysis_models import KeywordStructureAnalysis
from models.strategy_models import StrategySummary, KeywordStrategyItem

logger = logging.getLogger(__name__)

# KeywordPlanner と合わせる場合は同じモデル名を使う
DEFAULT_MODEL = "gpt-4.1-mini"


def _safe_model_name() -> str:
    """
    settings に model 名があればそれを使う。
    なければデフォルトを返す。
    """
    model = getattr(settings, "openai_model", None)
    return model or DEFAULT_MODEL


def _to_compact_analysis_dict(
    analysis: Dict[str, KeywordStructureAnalysis]
) -> Dict:
    """
    LLM に渡すために、構造分析結果をコンパクトな dict に変換する。
    （pages の生データをすべて投げるとトークンが重くなるので、
      代表値だけに絞る余地があるが、まずは素直に dump する）
    """
    compact: Dict[str, Dict] = {}
    for kw, a in analysis.items():
        try:
            compact[kw] = a.model_dump()
        except Exception:
            # Pydantic でない場合に備えて fallback
            compact[kw] = {
                "keyword": getattr(a, "keyword", kw),
                "pages": [
                    getattr(p, "__dict__", {}) for p in getattr(a, "pages", [])
                ],
            }
    return compact


def build_strategy(
    seed_keyword: str,
    keyword_plan: Optional[KeywordPlan],
    analysis: Dict[str, KeywordStructureAnalysis],
    site_profile: Optional[str] = None,
) -> StrategySummary:
    """
    KeywordPlan + 構造分析結果を元に LLM で戦略サマリを生成する。

    - OPENAI_API_KEY がない場合は、簡易なダミー戦略を返す
    - LLM からの JSON パースに失敗した場合も、最低限の StrategySummary を返す
    """
    # まずはダミー / フォールバック用のベースを作っておく
    base_overview = (
        f"seed_keyword='{seed_keyword}' を起点とした簡易戦略サマリです。"
        "OPENAI_API_KEY 未設定または LLM 呼び出しエラー時のフォールバックとして生成されています。"
    )

    # キーワードプランが無い場合のフォールバック
    if not keyword_plan:
        logger.warning("[strategist] keyword_plan が None のためフォールバック戦略を返します")
        return StrategySummary(
            seed_keyword=seed_keyword,
            overview=base_overview,
            global_recommendations=[
                "まずはキーワードプランナーで seed_keyword 周辺の重要キーワードを設計してください。",
                "設計済みのキーワードを元に SERP 構造を解析し、その後に詳細な戦略を策定します。",
            ],
            keyword_strategies=[],
        )

    # OPENAI_API_KEY が無い場合のフォールバック
    if not settings.openai_api_key:
        logger.warning("[strategist] OPENAI_API_KEY が未設定のため LLM を使わずにフォールバック戦略を返します")
        items = []
        for kw_item in keyword_plan.top_keywords(limit=10):
            items.append(
                KeywordStrategyItem(
                    keyword=kw_item.keyword,
                    intent=getattr(kw_item, "intent", None),
                    priority=getattr(kw_item, "priority", None),
                    recommended_content_type="カテゴリ or 記事ページ（フォールバック）",
                    recommended_actions=[
                        "このキーワード用のランディングページ有無を確認する",
                        "タイトル・見出しにキーワードを自然に含める",
                    ],
                    notes="LLM 不使用のフォールバック結果です。",
                )
            )

        return StrategySummary(
            seed_keyword=seed_keyword,
            overview=base_overview,
            global_recommendations=[
                "主要キーワードごとに専用のランディングページを用意することを検討してください。",
                "各ページでタイトル/H1/本文にキーワードを自然な形で含めつつ、ユーザーニーズを満たす内容にします。",
            ],
            keyword_strategies=items,
        )

    # ===== ここから LLM 呼び出し =====
    client = OpenAI(api_key=settings.openai_api_key)
    model = _safe_model_name()

    # Pydantic モデル → JSON 文字列
    try:
        plan_json = keyword_plan.model_dump()
    except Exception:
        plan_json = getattr(keyword_plan, "__dict__", {})

    analysis_json = _to_compact_analysis_dict(analysis)

    # site_profile は任意
    site_profile_text = site_profile or "（サイトプロフィール情報は未設定）"

    # LLM へのプロンプト
    system_prompt = (
        "あなたはB2B製造業向けのSEO/AIOコンサルタントです。"
        "与えられたキーワードプランとSERP構造分析結果を読み取り、"
        "どのキーワードをどのようなコンテンツで狙うべきか、"
        "優先順位や対策方針を日本語で整理したJSONを返してください。"
    )

    user_prompt = f"""
[サイトのプロフィール]
{site_profile_text}

[seed_keyword]
{seed_keyword}

[キーワードプラン(JSON)]
{json.dumps(plan_json, ensure_ascii=False)}

[構造分析結果(JSON)]
{json.dumps(analysis_json, ensure_ascii=False)}

出力フォーマットは必ず次の JSON 形式で返してください（余計な文章は一切書かない）:

{{
  "overview": "全体方針の概要（日本語の文章）",
  "global_recommendations": [
    "サイト全体に共通する推奨アクション1",
    "サイト全体に共通する推奨アクション2"
  ],
  "keyword_strategies": [
    {{
      "keyword": "キーワード",
      "intent": "KNOW / BUY / COMPARE など",
      "priority": 1,
      "recommended_content_type": "カテゴリページ / 製品一覧 / 製品詳細 / コラム / FAQ など",
      "recommended_actions": [
        "このキーワードに対する具体アクション1",
        "このキーワードに対する具体アクション2"
      ],
      "notes": "補足メモ"
    }}
  ]
}}
    """.strip()

    try:
        logger.info("[strategist] LLM call start seed_keyword=%s model=%s", seed_keyword, model)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        content = resp.choices[0].message.content or ""
        logger.info("[strategist] LLM response length=%s", len(content))

        data = json.loads(content)

        # JSON を StrategySummary にマッピング
        overview = data.get("overview", "")
        global_recs = data.get("global_recommendations") or []

        kw_items = []
        for item in data.get("keyword_strategies", []):
            kw_items.append(
                KeywordStrategyItem(
                    keyword=item.get("keyword", ""),
                    intent=item.get("intent"),
                    priority=item.get("priority"),
                    recommended_content_type=item.get("recommended_content_type"),
                    recommended_actions=item.get("recommended_actions") or [],
                    notes=item.get("notes"),
                )
            )

        return StrategySummary(
            seed_keyword=seed_keyword,
            overview=overview,
            global_recommendations=global_recs,
            keyword_strategies=kw_items,
        )

    except Exception as e:
        logger.warning("[strategist] LLM 呼び出しまたは JSON パースに失敗しました: %s", e)

        # 失敗時はフォールバック
        items = []
        for kw_item in keyword_plan.top_keywords(limit=10):
            items.append(
                KeywordStrategyItem(
                    keyword=kw_item.keyword,
                    intent=getattr(kw_item, "intent", None),
                    priority=getattr(kw_item, "priority", None),
                    recommended_content_type="カテゴリ or 記事ページ（LLM失敗フォールバック）",
                    recommended_actions=[
                        "専用ページの有無を確認する",
                        "タイトル/H1/本文でのキーワード出現を最適化する",
                    ],
                    notes="LLM 呼び出しエラー時のフォールバック結果です。",
                )
            )

        return StrategySummary(
            seed_keyword=seed_keyword,
            overview=base_overview + "（LLM 呼び出しエラー）",
            global_recommendations=[
                "主要キーワードごとに専用ページやコンテンツの整備状況を棚卸してください。",
                "SERP上位ページの構造を参考にしつつ、自社ならではの付加価値情報を追加します。",
            ],
            keyword_strategies=items,
        )
