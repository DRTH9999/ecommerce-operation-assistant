from datetime import date
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal['admin', 'operator', 'viewer']
Platform = Literal['taobao', 'tmall', 'jd', 'douyin', 'pinduoduo', 'xiaohongshu', 'other']


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False, serialize_by_alias=True)


class Patch(Input):
    @model_validator(mode='before')
    @classmethod
    def no_explicit_null(cls, values):
        if isinstance(values, dict) and any(v is None for v in values.values()):
            raise ValueError('更新字段不能为 null，请省略不需要更新的字段')
        return values


def http_url(value: str) -> str:
    if not value:
        return ''
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('链接必须是有效的 http/https 地址，且不含账号密码')
    if len(value) > 2048:
        raise ValueError('链接长度不能超过 2048')
    return value


class Login(Input):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserCreate(Input):
    username: str = Field(min_length=3, max_length=64, pattern=r'^[a-zA-Z0-9_.-]+$')
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: Role = 'viewer'


class UserPatch(Patch):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: Role | None = None
    status: Literal['active', 'inactive'] | None = None


class StoreCreate(Input):
    store_name: str = Field(min_length=1, max_length=100)
    platform: Platform
    external_store_id: str = Field(default='', max_length=100)
    owner_name: str = Field(default='', max_length=100)
    remark: str = Field(default='', max_length=2000)


class StorePatch(Patch):
    store_name: str | None = Field(default=None, min_length=1, max_length=100)
    platform: Platform | None = None
    external_store_id: str | None = Field(default=None, max_length=100)
    owner_name: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=2000)


class AccountCreate(Input):
    platform: Platform
    account_name: str = Field(min_length=1, max_length=100)
    remark: str = Field(default='', max_length=1000)


class AuthorizationCallback(Input):
    state: str = Field(min_length=10, max_length=2000)
    external_account_id: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=list, max_length=30)
    expires_at: str = Field(default='', max_length=40)


class ProductCreate(Input):
    store_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    platform: Platform
    category: str = Field(default='', max_length=100)
    price: float = Field(ge=0, le=100000000)
    cost: float = Field(default=0, ge=0, le=100000000)
    target_audience: str = Field(default='', max_length=4000)
    selling_points: str = Field(default='', max_length=8000)
    product_url: str = ''
    images_json: list[str] = Field(default_factory=list, max_length=20)
    status: Literal['draft', 'active', 'inactive'] = 'draft'

    _url = field_validator('product_url')(http_url)

    @field_validator('images_json')
    @classmethod
    def image_urls(cls, urls):
        return [http_url(url) for url in urls]


class ProductPatch(Patch):
    store_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    platform: Platform | None = None
    category: str | None = Field(default=None, max_length=100)
    price: float | None = Field(default=None, ge=0, le=100000000)
    cost: float | None = Field(default=None, ge=0, le=100000000)
    target_audience: str | None = Field(default=None, max_length=4000)
    selling_points: str | None = Field(default=None, max_length=8000)
    product_url: str | None = None
    images_json: list[str] | None = Field(default=None, max_length=20)
    status: Literal['draft', 'active', 'inactive'] | None = None
    _url = field_validator('product_url')(http_url)

    @field_validator('images_json')
    @classmethod
    def image_urls(cls, urls):
        return [http_url(url) for url in urls]


class MappingCreate(Input):
    platform: Platform
    platform_product_id: str = Field(min_length=1, max_length=100)
    platform_sku_id: str = Field(default='', max_length=100)
    mapping_status: Literal['mapped', 'pending', 'inactive'] = 'mapped'


class SkuCreate(Input):
    sku_code: str = Field(min_length=1, max_length=100)
    sku_name: str = Field(min_length=1, max_length=200)
    spec_json: dict[str, str] = Field(default_factory=dict)
    price: float = Field(ge=0, le=100000000)
    cost: float = Field(default=0, ge=0, le=100000000)
    status: Literal['active', 'inactive'] = 'active'
    platform_sku_id: str = Field(default='', max_length=100)
    stock_qty: int = Field(default=0, ge=0, le=100000000)
    warning_threshold: int = Field(default=10, ge=0, le=100000000)
    location_text: str = Field(default='', max_length=100)


class SkuPatch(Patch):
    sku_name: str | None = Field(default=None, min_length=1, max_length=200)
    price: float | None = Field(default=None, ge=0, le=100000000)
    cost: float | None = Field(default=None, ge=0, le=100000000)
    spec_json: dict[str, str] | None = None
    status: Literal['active', 'inactive'] | None = None
    platform_sku_id: str | None = Field(default=None, max_length=100)


class InventoryAdjust(Input):
    change_qty: int = Field(ge=-100000000, le=100000000)
    reason_text: str = Field(min_length=1, max_length=500)
    warning_threshold: int | None = Field(default=None, ge=0, le=100000000)
    locked_qty: int | None = Field(default=None, ge=0, le=100000000)
    location_text: str | None = Field(default=None, max_length=100)


class CompetitorCreate(Input):
    name: str = Field(min_length=1, max_length=200)
    platform: Platform
    url: str = ''
    price: float = Field(default=0, ge=0, le=100000000)
    sales_hint: str = Field(default='', max_length=500)
    title: str = Field(default='', max_length=500)
    main_image: str = ''
    selling_points: str = Field(default='', max_length=4000)
    review_keywords: str = Field(default='', max_length=2000)
    _url = field_validator('url', 'main_image')(http_url)


class ParseCreate(Input):
    source_url: str = Field(min_length=8, max_length=2048)
    _url = field_validator('source_url')(http_url)


class MonitorCreate(Input):
    interval_minutes: int = Field(default=1440, ge=60, le=43200)
    monitor_status: Literal['active', 'paused'] = 'active'


class DiagnosisContent(Input):
    positioning: str = Field(min_length=1, max_length=8000)
    price_band: str = Field(min_length=1, max_length=8000)
    audience_insights: str = Field(min_length=1, max_length=8000)
    pain_points: str = Field(min_length=1, max_length=8000)
    selling_point_analysis: str = Field(min_length=1, max_length=8000)
    risks: str = Field(min_length=1, max_length=8000)
    recommendations: str = Field(min_length=1, max_length=8000)


class DiagnosisPatch(Patch):
    positioning: str | None = Field(default=None, min_length=1, max_length=8000)
    price_band: str | None = Field(default=None, min_length=1, max_length=8000)
    audience_insights: str | None = Field(default=None, min_length=1, max_length=8000)
    pain_points: str | None = Field(default=None, min_length=1, max_length=8000)
    selling_point_analysis: str | None = Field(default=None, min_length=1, max_length=8000)
    risks: str | None = Field(default=None, min_length=1, max_length=8000)
    recommendations: str | None = Field(default=None, min_length=1, max_length=8000)


class ImageContent(Input):
    layout: str = Field(min_length=1, max_length=4000)
    headline: str = Field(alias='copy', min_length=1, max_length=1000)
    selling_point: str = Field(min_length=1, max_length=4000)


class VideoContent(Input):
    hook: str = Field(min_length=1, max_length=1000)
    shots: list[str] = Field(min_length=1, max_length=20)
    voiceover: str = Field(min_length=1, max_length=6000)
    cta: str = Field(min_length=1, max_length=1000)


class PlanContent(Input):
    title: str = Field(min_length=1, max_length=200)
    content_json: ImageContent | VideoContent
    rationale_text: str = Field(min_length=1, max_length=4000)


class PlanBatch(Input):
    plans: list[PlanContent] = Field(min_length=3, max_length=6)


class PlanPatch(Patch):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content_json: dict | None = None
    rationale_text: str | None = Field(default=None, min_length=1, max_length=4000)
    status: Literal['draft', 'selected', 'archived'] | None = None


class AssetPatch(Patch):
    review_status: Literal['pending', 'approved', 'rejected'] | None = None
    version_no: int | None = Field(default=None, ge=1)
    usage_scene: str | None = Field(default=None, max_length=200)
    score: float | None = Field(default=None, ge=0, le=5)
    tags_json: list[str] | None = Field(default=None, max_length=20)
    remark: str | None = Field(default=None, max_length=2000)


class PlanAssetsPatch(AssetPatch):
    asset_id: int = Field(gt=0)


class PromotionCreate(Input):
    link_name: str = Field(min_length=1, max_length=100)
    target_url: str = Field(min_length=8)
    utm_json: dict[str, str] = Field(default_factory=dict)
    scene_text: str = Field(default='', max_length=500)
    _url = field_validator('target_url')(http_url)


class BudgetPlan(Input):
    daily_budget: float = Field(ge=0, le=100000000)
    days: int = Field(ge=1, le=365)
    total_budget: float = Field(ge=0, le=100000000)
    note: str = Field(default='', max_length=2000)


class BidStrategy(Input):
    strategy: str = Field(min_length=1, max_length=4000)
    note: str = Field(default='', max_length=2000)


class AdContent(Input):
    summary_text: str = Field(min_length=1, max_length=8000)
    objective_text: str = Field(min_length=1, max_length=4000)
    audience_segments_json: list[str] = Field(min_length=1, max_length=20)
    budget_plan_json: BudgetPlan
    creative_tests_json: list[str] = Field(min_length=1, max_length=20)
    bid_strategy_json: BidStrategy
    risk_controls_json: list[str] = Field(min_length=1, max_length=20)
    next_steps_json: list[str] = Field(min_length=1, max_length=20)


class AdPatch(Patch):
    summary_text: str | None = Field(default=None, min_length=1, max_length=8000)
    objective_text: str | None = Field(default=None, min_length=1, max_length=4000)
    audience_segments_json: list[str] | None = Field(default=None, min_length=1, max_length=20)
    budget_plan_json: BudgetPlan | None = None
    creative_tests_json: list[str] | None = Field(default=None, min_length=1, max_length=20)
    bid_strategy_json: BidStrategy | None = None
    risk_controls_json: list[str] | None = Field(default=None, min_length=1, max_length=20)
    next_steps_json: list[str] | None = Field(default=None, min_length=1, max_length=20)


class Confirmation(Input):
    confirm_status: Literal['confirmed', 'rejected']
    confirm_remark: str = Field(default='', max_length=1000)


class ExperimentCreate(Input):
    recommendation_id: int = Field(gt=0)
    related_asset_id: int | None = Field(default=None, gt=0)
    related_link_id: int | None = Field(default=None, gt=0)


class ExperimentPatch(Patch):
    experiment_name: str | None = Field(default=None, min_length=1, max_length=200)
    target_text: str | None = Field(default=None, max_length=2000)
    audience_text: str | None = Field(default=None, max_length=2000)
    budget_amount: float | None = Field(default=None, ge=0, le=100000000)
    success_metric_text: str | None = Field(default=None, max_length=2000)
    hypothesis_text: str | None = Field(default=None, max_length=4000)
    experiment_status: Literal['draft', 'confirmed', 'running', 'finished', 'cancelled'] | None = None


class Period(Input):
    period_start: date
    period_end: date

    @model_validator(mode='after')
    def period_order(self):
        if self.period_end < self.period_start:
            raise ValueError('结束日期不能早于开始日期')
        return self


class PerformanceCreate(Period):
    creative_plan_id: int | None = Field(default=None, gt=0)
    generated_asset_id: int | None = Field(default=None, gt=0)
    promotion_link_id: int | None = Field(default=None, gt=0)
    experiment_id: int | None = Field(default=None, gt=0)
    impressions: int = Field(ge=0, le=100000000000)
    clicks: int = Field(ge=0, le=100000000000)
    conversions: int = Field(ge=0, le=100000000000)
    spend: float = Field(ge=0, le=10000000000)
    revenue: float = Field(ge=0, le=10000000000)
    notes: str = Field(default='', max_length=4000)

    @model_validator(mode='after')
    def funnel(self):
        if not self.impressions >= self.clicks >= self.conversions:
            raise ValueError('数据须满足：曝光量 ≥ 点击量 ≥ 成交量')
        return self


class ReviewContent(Input):
    summary_text: str = Field(min_length=1, max_length=8000)
    insights_json: list[str] = Field(min_length=1, max_length=20)
    problem_judgment: str = Field(min_length=1, max_length=8000)
    next_actions_json: list[str] = Field(min_length=1, max_length=20)


class ReviewPatch(Patch):
    summary_text: str | None = Field(default=None, min_length=1, max_length=8000)
    insights_json: list[str] | None = Field(default=None, min_length=1, max_length=20)
    problem_judgment: str | None = Field(default=None, min_length=1, max_length=8000)
    next_actions_json: list[str] | None = Field(default=None, min_length=1, max_length=20)


class ImportRows(Input):
    rows: list[dict[str, Any]] = Field(max_length=5000)


class SettingsPatch(Patch):
    ai_mode: Literal['demo', 'compatible'] | None = None
    job_timeout_seconds: int | None = Field(default=None, ge=5, le=3600)
    job_max_attempts: int | None = Field(default=None, ge=1, le=10)
