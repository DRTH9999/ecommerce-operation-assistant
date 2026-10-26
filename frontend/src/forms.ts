import { reactive } from 'vue'
import { api, notify, platforms, type Row } from './api'
import type { Field } from './components/FormModal.vue'

type FormConfig = { title: string; fields: Field[]; initial: Row; endpoint: string; method: string; transform?: (data: Row) => Row }
export function useEditor(afterSave: () => unknown) {
  const editor = reactive({
    form: null as FormConfig | null, saving: false, error: '',
    open(title: string, fields: Field[], initial: Row, endpoint: string, method = 'POST', transform?: (data: Row) => Row) {
      editor.form = { title, fields, initial, endpoint, method, transform }; editor.error = ''
    },
    close() { if (!editor.saving) editor.form = null },
    async save(data: Row) {
      if (!editor.form || editor.saving) return
      editor.saving = true; editor.error = ''
      try {
        await api(editor.form.endpoint, editor.form.method, editor.form.transform ? editor.form.transform(data) : data)
        editor.form = null; notify('已保存'); await afterSave()
      } catch (error) { editor.error = (error as Error).message }
      finally { editor.saving = false }
    },
  })
  return editor
}

export function useAction(after?: () => unknown) {
  return reactive({
    busy: '',
    async run(key: string, task: () => Promise<unknown>, message = '操作已完成') {
      if (this.busy) return
      this.busy = key
      try { await task(); if (message) notify(message); await after?.() }
      catch (error) { notify((error as Error).message, true) }
      finally { this.busy = '' }
    },
  })
}

export const storeFields: Field[] = [
  { key: 'store_name', label: '店铺名称', required: true },
  { key: 'platform', label: '所属平台', type: 'select', options: platforms, required: true },
  { key: 'owner_name', label: '负责人' }, { key: 'external_store_id', label: '平台店铺编号' },
  { key: 'remark', label: '备注', type: 'textarea' },
]

export function productFields(stores: Row[], edit = false): Field[] {
  return [
    { key: 'name', label: '商品名称', required: true },
    { key: 'store_id', label: '所属店铺', type: 'select', required: true, options: stores.map(s => ({ value: s.id, label: s.store_name })) },
    { key: 'category', label: '商品类目', placeholder: '例如：家居 / 水具' },
    { key: 'status', label: '商品状态', type: 'select', options: [{ value: 'draft', label: '草稿' }, { value: 'active', label: '在售' }, { value: 'inactive', label: '已停用' }] },
    { key: 'price', label: '售价（元）', type: 'number', required: true, min: 0, step: 0.01 },
    { key: 'cost', label: '成本（元）', type: 'number', min: 0, step: 0.01 },
    { key: 'product_url', label: '商品公开链接', placeholder: 'https://' },
    { key: 'images_json', label: '商品图片地址（每行一个）', type: 'lines', hint: '可填写公开 HTTPS 图片地址，第一张作为商品预览图。' },
    { key: 'target_audience', label: '目标人群', type: 'textarea' },
    { key: 'selling_points', label: '核心卖点', type: 'textarea', hint: '填写可验证的规格、功能和使用体验。' },
  ]
}

export function newProduct(editor: ReturnType<typeof useEditor>, stores: Row[]) {
  if (!stores.length) { notify('请先由管理员创建店铺，再录入商品', true); return }
  editor.open('录入新商品', productFields(stores), { store_id: stores[0]?.id, status: 'draft', price: 0, cost: 0 }, '/products', 'POST',
    data => ({ ...data, store_id: Number(data.store_id), platform: stores.find(s => s.id === Number(data.store_id))?.platform }))
}

export const skuFields: Field[] = [
  { key: 'sku_code', label: 'SKU 编码', required: true }, { key: 'sku_name', label: '规格名称', required: true },
  { key: 'price', label: '售价（元）', type: 'number', min: 0, required: true, step: 0.01 },
  { key: 'cost', label: '成本（元）', type: 'number', min: 0, step: 0.01 },
  { key: 'stock_qty', label: '初始库存', type: 'number', min: 0, step: 1 },
  { key: 'warning_threshold', label: '预警阈值', type: 'number', min: 0, step: 1 },
  { key: 'location_text', label: '库位' },
]

export const competitorFields: Field[] = [
  { key: 'name', label: '竞品名称', required: true },
  { key: 'platform', label: '平台', type: 'select', options: platforms, required: true },
  { key: 'url', label: '公开链接' }, { key: 'price', label: '价格（元）', type: 'number', min: 0, step: 0.01 },
  { key: 'sales_hint', label: '公开销量提示', hint: '未知时请留空，不推断销量。' },
  { key: 'title', label: '页面标题' }, { key: 'main_image', label: '主图公开地址' },
  { key: 'selling_points', label: '卖点', type: 'textarea' }, { key: 'review_keywords', label: '评价关键词', type: 'textarea' },
]
