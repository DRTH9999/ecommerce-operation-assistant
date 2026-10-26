"""SQLAlchemy Core 数据模型；数据库约束与请求校验共同维护业务一致性。"""
from datetime import UTC, datetime

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, Column, Float, ForeignKey, Integer,
    MetaData, String, Table, Text, UniqueConstraint,
)

metadata = MetaData()


def utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec='milliseconds')


def table(name, *columns, updated=True):
    fields = [Column('id', Integer, primary_key=True), *columns,
              Column('created_at', String(40), nullable=False, default=utcnow)]
    if updated:
        fields.append(Column('updated_at', String(40), nullable=False, default=utcnow, onupdate=utcnow))
    return Table(name, metadata, *fields)


def text(name, default='', nullable=False):
    return Column(name, Text, default=default, nullable=nullable)


def num(name, default=0):
    return Column(name, Float, nullable=False, default=default)


def integer(name, default=0):
    return Column(name, Integer, nullable=False, default=default)


def ref(name, target, nullable=False):
    return Column(name, Integer, ForeignKey(target, ondelete='RESTRICT'), nullable=nullable, index=True)


def obj(name, default=dict):
    return Column(name, JSON, nullable=False, default=default)


users = table('users', Column('username', String(64), unique=True, nullable=False),
              text('display_name'), text('password_hash'), text('role', 'viewer'),
              text('status', 'active'), text('last_login_at', nullable=True), integer('token_version'),
              CheckConstraint("role IN ('admin','operator','viewer')"),
              CheckConstraint("status IN ('active','inactive')"))
stores = table('stores', text('store_name'), text('platform'), text('external_store_id'),
               text('owner_name'), text('remark'))
platform_accounts = table('platform_accounts', ref('store_id', 'stores.id'), text('platform'),
                         text('account_name'), text('auth_status', 'unconfigured'),
                         obj('auth_meta_json'), text('remark'))
products = table('products', ref('store_id', 'stores.id'), text('name'), text('platform'),
                 text('category'), num('price'), num('cost'), text('target_audience'),
                 text('selling_points'), text('product_url'), obj('images_json', list),
                 text('status', 'draft'), CheckConstraint('price >= 0 AND cost >= 0'),
                 CheckConstraint("status IN ('draft','active','inactive')"))
platform_product_mappings = table('platform_product_mappings', ref('product_id', 'products.id'),
    text('platform'), text('platform_product_id'), text('platform_sku_id'),
    text('mapping_status', 'mapped'), obj('raw_payload_json'), updated=False)
product_skus = table('product_skus', ref('product_id', 'products.id'),
    Column('sku_code', String(100), nullable=False), text('sku_name'), obj('spec_json'),
    num('price'), num('cost'), text('status', 'active'), text('platform_sku_id'),
    UniqueConstraint('product_id', 'sku_code'), CheckConstraint('price >= 0 AND cost >= 0'),
    CheckConstraint("status IN ('active','inactive')"))
inventory_items = table('inventory_items', ref('sku_id', 'product_skus.id'), integer('stock_qty'),
    integer('locked_qty'), integer('warning_threshold', 10), text('location_text'),
    UniqueConstraint('sku_id'), CheckConstraint('stock_qty >= 0 AND locked_qty >= 0 AND locked_qty <= stock_qty'),
    CheckConstraint('warning_threshold >= 0'))
inventory_movements = table('inventory_movements', ref('sku_id', 'product_skus.id'),
    text('movement_type'), integer('change_qty'), integer('before_qty'), integer('after_qty'),
    text('reason_text'), text('reference_type'), integer('reference_id'), updated=False)
competitors = table('competitors', ref('product_id', 'products.id'), text('name'), text('platform'),
    text('url'), num('price'), text('sales_hint'), text('title'), text('main_image'),
    text('selling_points'), text('review_keywords'), CheckConstraint('price >= 0'))
competitor_monitors = table('competitor_monitors', ref('competitor_id', 'competitors.id'),
    text('monitor_status', 'active'), integer('interval_minutes', 1440), text('next_run_at'),
    CheckConstraint('interval_minutes >= 60'), UniqueConstraint('competitor_id'), updated=False)
competitor_monitor_snapshots = table('competitor_monitor_snapshots', ref('monitor_id', 'competitor_monitors.id'),
    num('price'), text('sales_hint'), text('selling_points'), obj('raw_payload_json'), updated=False)
public_link_parse_tasks = table('public_link_parse_tasks', ref('product_id', 'products.id'),
    text('source_url'), text('task_status', 'pending'), integer('attempts'),
    obj('result_json'), text('error_message'))
product_diagnoses = table('product_diagnoses', ref('product_id', 'products.id'),
    text('source_type'), text('positioning'), text('price_band'), text('audience_insights'),
    text('pain_points'), text('selling_point_analysis'), text('risks'), text('recommendations'), text('raw_output'))
creative_plans = table('creative_plans', ref('product_id', 'products.id'), text('plan_type'),
    text('title'), obj('content_json'), text('rationale_text'), text('status', 'draft'),
    CheckConstraint("status IN ('draft','selected','archived')"),
    CheckConstraint("plan_type IN ('main_image','video_script')"))
generation_jobs = table('generation_jobs', ref('product_id', 'products.id'),
    ref('creative_plan_id', 'creative_plans.id'), text('job_kind'), text('job_status', 'pending'),
    integer('attempts'), integer('max_attempts', 3), text('locked_at', nullable=True),
    text('locked_by'), text('next_run_at'), obj('result_json'), text('error_message'),
    text('started_at', nullable=True), text('finished_at', nullable=True),
    CheckConstraint("job_status IN ('pending','running','succeeded','failed','cancelled','timeout')"))
generation_job_events = table('generation_job_events', ref('job_id', 'generation_jobs.id'),
    text('event_type'), text('event_message'), updated=False)
generated_assets = table('generated_assets', ref('product_id', 'products.id'),
    ref('creative_plan_id', 'creative_plans.id'), ref('job_id', 'generation_jobs.id', nullable=True),
    text('asset_type'), text('asset_url'), text('model_name'), integer('width', 1080),
    integer('height', 1080), num('duration_sec'), text('review_status', 'pending'),
    integer('version_no', 1), text('usage_scene'), num('score'), obj('tags_json', list), text('remark'),
    CheckConstraint("review_status IN ('pending','approved','rejected')"),
    CheckConstraint('score >= 0 AND score <= 5'), UniqueConstraint('job_id'), updated=False)
promotion_links = table('promotion_links', ref('product_id', 'products.id'), text('link_name'),
    text('target_url'), Column('tracking_code', String(64), unique=True, nullable=False),
    obj('utm_json'), text('status', 'active'), integer('click_count'), text('scene_text'), updated=False)
promotion_link_clicks = table('promotion_link_clicks', ref('promotion_link_id', 'promotion_links.id'),
    text('clicked_at'), text('client_ip'), text('user_agent'), updated=False)
ad_recommendations = table('ad_recommendations', ref('product_id', 'products.id'),
    text('source_type'), text('summary_text'), text('objective_text'), obj('audience_segments_json', list),
    obj('budget_plan_json'), obj('creative_tests_json', list), obj('bid_strategy_json'),
    obj('risk_controls_json', list), obj('next_steps_json', list), text('confirm_status', 'pending'),
    ref('confirmed_by', 'users.id', nullable=True), text('confirmed_at', nullable=True), text('confirm_remark'),
    CheckConstraint("confirm_status IN ('pending','confirmed','rejected')"), updated=False)
ad_experiments = table('ad_experiments', ref('product_id', 'products.id'),
    ref('recommendation_id', 'ad_recommendations.id'), ref('related_asset_id', 'generated_assets.id', nullable=True),
    ref('related_link_id', 'promotion_links.id', nullable=True), text('experiment_name'),
    text('target_text'), text('audience_text'), num('budget_amount'), text('success_metric_text'),
    text('hypothesis_text'), text('experiment_status', 'draft'),
    CheckConstraint('budget_amount >= 0'),
    CheckConstraint("experiment_status IN ('draft','confirmed','running','finished','cancelled')"))
performance_records = table('performance_records', ref('product_id', 'products.id'),
    ref('creative_plan_id', 'creative_plans.id', nullable=True), ref('generated_asset_id', 'generated_assets.id', nullable=True),
    ref('promotion_link_id', 'promotion_links.id', nullable=True), ref('experiment_id', 'ad_experiments.id', nullable=True),
    text('period_start'), text('period_end'), integer('impressions'), integer('clicks'), num('ctr'),
    integer('conversions'), num('conversion_rate'), num('spend'), num('revenue'), num('roi'), text('notes'),
    CheckConstraint('impressions >= clicks AND clicks >= conversions AND conversions >= 0'),
    CheckConstraint('spend >= 0 AND revenue >= 0'), updated=False)
review_reports = table('review_reports', ref('product_id', 'products.id'), text('source_type'),
    text('period_start'), text('period_end'), text('summary_text'), obj('insights_json', list),
    text('problem_judgment'), obj('next_actions_json', list), updated=False)
system_settings = table('system_settings', Column('key', String(64), unique=True, nullable=False), obj('value_json'))
