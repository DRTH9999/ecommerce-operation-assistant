-- 由 SQLAlchemy 模型生成；账户和演示数据请运行初始化脚本。

PRAGMA foreign_keys=ON;


CREATE TABLE stores (
	id INTEGER NOT NULL,
	store_name TEXT NOT NULL,
	platform TEXT NOT NULL,
	external_store_id TEXT NOT NULL,
	owner_name TEXT NOT NULL,
	remark TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE system_settings (
	id INTEGER NOT NULL,
	"key" VARCHAR(64) NOT NULL,
	value_json JSON NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE ("key")
)

;


CREATE TABLE users (
	id INTEGER NOT NULL,
	username VARCHAR(64) NOT NULL,
	display_name TEXT NOT NULL,
	password_hash TEXT NOT NULL,
	role TEXT NOT NULL,
	status TEXT NOT NULL,
	last_login_at TEXT,
	token_version INTEGER NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (role IN ('admin','operator','viewer')),
	CHECK (status IN ('active','inactive')),
	UNIQUE (username)
)

;


CREATE TABLE platform_accounts (
	id INTEGER NOT NULL,
	store_id INTEGER NOT NULL,
	platform TEXT NOT NULL,
	account_name TEXT NOT NULL,
	auth_status TEXT NOT NULL,
	auth_meta_json JSON NOT NULL,
	remark TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(store_id) REFERENCES stores (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_platform_accounts_store_id ON platform_accounts (store_id);


CREATE TABLE products (
	id INTEGER NOT NULL,
	store_id INTEGER NOT NULL,
	name TEXT NOT NULL,
	platform TEXT NOT NULL,
	category TEXT NOT NULL,
	price FLOAT NOT NULL,
	cost FLOAT NOT NULL,
	target_audience TEXT NOT NULL,
	selling_points TEXT NOT NULL,
	product_url TEXT NOT NULL,
	images_json JSON NOT NULL,
	status TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (price >= 0 AND cost >= 0),
	CHECK (status IN ('draft','active','inactive')),
	FOREIGN KEY(store_id) REFERENCES stores (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_products_store_id ON products (store_id);


CREATE TABLE ad_recommendations (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	source_type TEXT NOT NULL,
	summary_text TEXT NOT NULL,
	objective_text TEXT NOT NULL,
	audience_segments_json JSON NOT NULL,
	budget_plan_json JSON NOT NULL,
	creative_tests_json JSON NOT NULL,
	bid_strategy_json JSON NOT NULL,
	risk_controls_json JSON NOT NULL,
	next_steps_json JSON NOT NULL,
	confirm_status TEXT NOT NULL,
	confirmed_by INTEGER,
	confirmed_at TEXT,
	confirm_remark TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (confirm_status IN ('pending','confirmed','rejected')),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
	FOREIGN KEY(confirmed_by) REFERENCES users (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_ad_recommendations_product_id ON ad_recommendations (product_id);

CREATE INDEX ix_ad_recommendations_confirmed_by ON ad_recommendations (confirmed_by);


CREATE TABLE competitors (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	name TEXT NOT NULL,
	platform TEXT NOT NULL,
	url TEXT NOT NULL,
	price FLOAT NOT NULL,
	sales_hint TEXT NOT NULL,
	title TEXT NOT NULL,
	main_image TEXT NOT NULL,
	selling_points TEXT NOT NULL,
	review_keywords TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (price >= 0),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_competitors_product_id ON competitors (product_id);


CREATE TABLE creative_plans (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	plan_type TEXT NOT NULL,
	title TEXT NOT NULL,
	content_json JSON NOT NULL,
	rationale_text TEXT NOT NULL,
	status TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (status IN ('draft','selected','archived')),
	CHECK (plan_type IN ('main_image','video_script')),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_creative_plans_product_id ON creative_plans (product_id);


CREATE TABLE platform_product_mappings (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	platform TEXT NOT NULL,
	platform_product_id TEXT NOT NULL,
	platform_sku_id TEXT NOT NULL,
	mapping_status TEXT NOT NULL,
	raw_payload_json JSON NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_platform_product_mappings_product_id ON platform_product_mappings (product_id);


CREATE TABLE product_diagnoses (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	source_type TEXT NOT NULL,
	positioning TEXT NOT NULL,
	price_band TEXT NOT NULL,
	audience_insights TEXT NOT NULL,
	pain_points TEXT NOT NULL,
	selling_point_analysis TEXT NOT NULL,
	risks TEXT NOT NULL,
	recommendations TEXT NOT NULL,
	raw_output TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_product_diagnoses_product_id ON product_diagnoses (product_id);


CREATE TABLE product_skus (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	sku_code VARCHAR(100) NOT NULL,
	sku_name TEXT NOT NULL,
	spec_json JSON NOT NULL,
	price FLOAT NOT NULL,
	cost FLOAT NOT NULL,
	status TEXT NOT NULL,
	platform_sku_id TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (product_id, sku_code),
	CHECK (price >= 0 AND cost >= 0),
	CHECK (status IN ('active','inactive')),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_product_skus_product_id ON product_skus (product_id);


CREATE TABLE promotion_links (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	link_name TEXT NOT NULL,
	target_url TEXT NOT NULL,
	tracking_code VARCHAR(64) NOT NULL,
	utm_json JSON NOT NULL,
	status TEXT NOT NULL,
	click_count INTEGER NOT NULL,
	scene_text TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
	UNIQUE (tracking_code)
)

;

CREATE INDEX ix_promotion_links_product_id ON promotion_links (product_id);


CREATE TABLE public_link_parse_tasks (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	source_url TEXT NOT NULL,
	task_status TEXT NOT NULL,
	attempts INTEGER NOT NULL,
	result_json JSON NOT NULL,
	error_message TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_public_link_parse_tasks_product_id ON public_link_parse_tasks (product_id);


CREATE TABLE review_reports (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	source_type TEXT NOT NULL,
	period_start TEXT NOT NULL,
	period_end TEXT NOT NULL,
	summary_text TEXT NOT NULL,
	insights_json JSON NOT NULL,
	problem_judgment TEXT NOT NULL,
	next_actions_json JSON NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_review_reports_product_id ON review_reports (product_id);


CREATE TABLE competitor_monitors (
	id INTEGER NOT NULL,
	competitor_id INTEGER NOT NULL,
	monitor_status TEXT NOT NULL,
	interval_minutes INTEGER NOT NULL,
	next_run_at TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (interval_minutes >= 60),
	UNIQUE (competitor_id),
	FOREIGN KEY(competitor_id) REFERENCES competitors (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_competitor_monitors_competitor_id ON competitor_monitors (competitor_id);


CREATE TABLE generation_jobs (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	creative_plan_id INTEGER NOT NULL,
	job_kind TEXT NOT NULL,
	job_status TEXT NOT NULL,
	attempts INTEGER NOT NULL,
	max_attempts INTEGER NOT NULL,
	locked_at TEXT,
	locked_by TEXT NOT NULL,
	next_run_at TEXT NOT NULL,
	result_json JSON NOT NULL,
	error_message TEXT NOT NULL,
	started_at TEXT,
	finished_at TEXT,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (job_status IN ('pending','running','succeeded','failed','cancelled','timeout')),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
	FOREIGN KEY(creative_plan_id) REFERENCES creative_plans (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_generation_jobs_creative_plan_id ON generation_jobs (creative_plan_id);

CREATE INDEX ix_generation_jobs_product_id ON generation_jobs (product_id);


CREATE TABLE inventory_items (
	id INTEGER NOT NULL,
	sku_id INTEGER NOT NULL,
	stock_qty INTEGER NOT NULL,
	locked_qty INTEGER NOT NULL,
	warning_threshold INTEGER NOT NULL,
	location_text TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (sku_id),
	CHECK (stock_qty >= 0 AND locked_qty >= 0 AND locked_qty <= stock_qty),
	CHECK (warning_threshold >= 0),
	FOREIGN KEY(sku_id) REFERENCES product_skus (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_inventory_items_sku_id ON inventory_items (sku_id);


CREATE TABLE inventory_movements (
	id INTEGER NOT NULL,
	sku_id INTEGER NOT NULL,
	movement_type TEXT NOT NULL,
	change_qty INTEGER NOT NULL,
	before_qty INTEGER NOT NULL,
	after_qty INTEGER NOT NULL,
	reason_text TEXT NOT NULL,
	reference_type TEXT NOT NULL,
	reference_id INTEGER NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(sku_id) REFERENCES product_skus (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_inventory_movements_sku_id ON inventory_movements (sku_id);


CREATE TABLE promotion_link_clicks (
	id INTEGER NOT NULL,
	promotion_link_id INTEGER NOT NULL,
	clicked_at TEXT NOT NULL,
	client_ip TEXT NOT NULL,
	user_agent TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(promotion_link_id) REFERENCES promotion_links (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_promotion_link_clicks_promotion_link_id ON promotion_link_clicks (promotion_link_id);


CREATE TABLE competitor_monitor_snapshots (
	id INTEGER NOT NULL,
	monitor_id INTEGER NOT NULL,
	price FLOAT NOT NULL,
	sales_hint TEXT NOT NULL,
	selling_points TEXT NOT NULL,
	raw_payload_json JSON NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(monitor_id) REFERENCES competitor_monitors (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_competitor_monitor_snapshots_monitor_id ON competitor_monitor_snapshots (monitor_id);


CREATE TABLE generated_assets (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	creative_plan_id INTEGER NOT NULL,
	job_id INTEGER,
	asset_type TEXT NOT NULL,
	asset_url TEXT NOT NULL,
	model_name TEXT NOT NULL,
	width INTEGER NOT NULL,
	height INTEGER NOT NULL,
	duration_sec FLOAT NOT NULL,
	review_status TEXT NOT NULL,
	version_no INTEGER NOT NULL,
	usage_scene TEXT NOT NULL,
	score FLOAT NOT NULL,
	tags_json JSON NOT NULL,
	remark TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (review_status IN ('pending','approved','rejected')),
	CHECK (score >= 0 AND score <= 5),
	UNIQUE (job_id),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
	FOREIGN KEY(creative_plan_id) REFERENCES creative_plans (id) ON DELETE RESTRICT,
	FOREIGN KEY(job_id) REFERENCES generation_jobs (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_generated_assets_creative_plan_id ON generated_assets (creative_plan_id);

CREATE INDEX ix_generated_assets_product_id ON generated_assets (product_id);

CREATE INDEX ix_generated_assets_job_id ON generated_assets (job_id);


CREATE TABLE generation_job_events (
	id INTEGER NOT NULL,
	job_id INTEGER NOT NULL,
	event_type TEXT NOT NULL,
	event_message TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(job_id) REFERENCES generation_jobs (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_generation_job_events_job_id ON generation_job_events (job_id);


CREATE TABLE ad_experiments (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	recommendation_id INTEGER NOT NULL,
	related_asset_id INTEGER,
	related_link_id INTEGER,
	experiment_name TEXT NOT NULL,
	target_text TEXT NOT NULL,
	audience_text TEXT NOT NULL,
	budget_amount FLOAT NOT NULL,
	success_metric_text TEXT NOT NULL,
	hypothesis_text TEXT NOT NULL,
	experiment_status TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (budget_amount >= 0),
	CHECK (experiment_status IN ('draft','confirmed','running','finished','cancelled')),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
	FOREIGN KEY(recommendation_id) REFERENCES ad_recommendations (id) ON DELETE RESTRICT,
	FOREIGN KEY(related_asset_id) REFERENCES generated_assets (id) ON DELETE RESTRICT,
	FOREIGN KEY(related_link_id) REFERENCES promotion_links (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_ad_experiments_recommendation_id ON ad_experiments (recommendation_id);

CREATE INDEX ix_ad_experiments_related_link_id ON ad_experiments (related_link_id);

CREATE INDEX ix_ad_experiments_related_asset_id ON ad_experiments (related_asset_id);

CREATE INDEX ix_ad_experiments_product_id ON ad_experiments (product_id);


CREATE TABLE performance_records (
	id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	creative_plan_id INTEGER,
	generated_asset_id INTEGER,
	promotion_link_id INTEGER,
	experiment_id INTEGER,
	period_start TEXT NOT NULL,
	period_end TEXT NOT NULL,
	impressions INTEGER NOT NULL,
	clicks INTEGER NOT NULL,
	ctr FLOAT NOT NULL,
	conversions INTEGER NOT NULL,
	conversion_rate FLOAT NOT NULL,
	spend FLOAT NOT NULL,
	revenue FLOAT NOT NULL,
	roi FLOAT NOT NULL,
	notes TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	CHECK (impressions >= clicks AND clicks >= conversions AND conversions >= 0),
	CHECK (spend >= 0 AND revenue >= 0),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
	FOREIGN KEY(creative_plan_id) REFERENCES creative_plans (id) ON DELETE RESTRICT,
	FOREIGN KEY(generated_asset_id) REFERENCES generated_assets (id) ON DELETE RESTRICT,
	FOREIGN KEY(promotion_link_id) REFERENCES promotion_links (id) ON DELETE RESTRICT,
	FOREIGN KEY(experiment_id) REFERENCES ad_experiments (id) ON DELETE RESTRICT
)

;

CREATE INDEX ix_performance_records_generated_asset_id ON performance_records (generated_asset_id);

CREATE INDEX ix_performance_records_promotion_link_id ON performance_records (promotion_link_id);

CREATE INDEX ix_performance_records_product_id ON performance_records (product_id);

CREATE INDEX ix_performance_records_creative_plan_id ON performance_records (creative_plan_id);

CREATE INDEX ix_performance_records_experiment_id ON performance_records (experiment_id);
