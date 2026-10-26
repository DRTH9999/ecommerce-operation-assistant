"""将常见输入错误转成用户可读的中文，同时避免把敏感输入回显。"""
FIELDS = {
    'username': '用户名', 'password': '密码', 'display_name': '显示名称', 'role': '角色',
    'store_id': '店铺编号', 'product_id': '商品编号', 'store_name': '店铺名称', 'name': '名称',
    'platform': '平台', 'category': '类目', 'price': '售价', 'cost': '成本', 'status': '状态',
    'sku_code': 'SKU 编码', 'sku_name': '规格名称', 'stock_qty': '库存数量', 'locked_qty': '锁定数量',
    'warning_threshold': '预警阈值', 'change_qty': '库存变动量', 'reason_text': '调整原因',
    'period_start': '开始日期', 'period_end': '结束日期', 'impressions': '曝光量',
    'clicks': '点击量', 'conversions': '成交量', 'spend': '花费', 'revenue': '收入',
    'source_url': '公开链接', 'target_url': '目标链接', 'product_url': '商品链接',
    'daily_budget': '日预算', 'total_budget': '总预算', 'budget_amount': '实验预算', 'days': '天数',
    'score': '评分', 'version_no': '版本号', 'review_status': '审核状态',
    'job_timeout_seconds': '任务超时时间', 'job_max_attempts': '最大尝试次数',
    'creative_plan_id': '方案编号', 'generated_asset_id': '素材编号', 'promotion_link_id': '推广链接编号',
    'experiment_id': '实验编号', 'recommendation_id': '建议编号', 'rows': '导入行',
}


def validation_message(error):
    kind, context = error['type'], error.get('ctx', {})
    messages = {
        'missing': '此项为必填项', 'int_parsing': '请输入整数', 'int_type': '请输入整数',
        'float_parsing': '请输入有效数字', 'float_type': '请输入有效数字',
        'int_from_float': '数量必须为整数', 'finite_number': '请输入有限的有效数字',
        'string_type': '请输入文本', 'list_type': '应为列表', 'dict_type': '应为对象',
        'extra_forbidden': '不接受此字段，请使用模板或页面提供的字段',
        'literal_error': '请选择有效选项', 'date_from_datetime_parsing': '日期格式应为 YYYY-MM-DD',
        'date_parsing': '日期格式应为 YYYY-MM-DD', 'json_invalid': 'JSON 格式不正确',
    }
    if kind in {'greater_than_equal', 'greater_than', 'less_than_equal', 'less_than'}:
        key, relation = {'greater_than_equal': ('ge', '不得小于'), 'greater_than': ('gt', '必须大于'),
                         'less_than_equal': ('le', '不得大于'), 'less_than': ('lt', '必须小于')}[kind]
        message = relation + str(context.get(key, '限制值'))
    elif kind == 'string_too_short':
        message = f'至少填写 {context.get("min_length", 1)} 个字符'
    elif kind == 'string_too_long':
        message = f'最多填写 {context.get("max_length", "指定")} 个字符'
    elif kind == 'string_pattern_mismatch':
        message = '格式不正确，请使用允许的字母、数字或符号'
    elif kind in {'too_short', 'too_long'}:
        message = '列表长度不符合要求'
    elif kind == 'value_error':
        message = str(context.get('error', error.get('msg', '输入不符合要求'))).removeprefix('Value error, ')
    else:
        message = messages.get(kind, '字段格式不符合要求')
    field = next((str(part) for part in reversed(error.get('loc', [])) if part not in {'body', 'query', 'path'} and not isinstance(part, int)), '')
    label = FIELDS.get(field, field)
    return (label + '：' if label else '') + message
