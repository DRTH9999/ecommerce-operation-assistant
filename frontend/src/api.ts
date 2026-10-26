import { reactive } from 'vue'

export type Row = Record<string, any>
export type User = { id: number; username: string; display_name: string; role: 'admin' | 'operator' | 'viewer'; status: string }
export const auth = reactive({ user: null as User | null, token: localStorage.getItem('commerce_token') || '' })
export const notifications = reactive<{ id: number; message: string; error: boolean }[]>([])

export function notify(message: string, error = false) {
  const id = Date.now() + Math.random()
  notifications.push({ id, message, error })
  setTimeout(() => { const i = notifications.findIndex(item => item.id === id); if (i >= 0) notifications.splice(i, 1) }, error ? 7000 : 4000)
}

export function setSession(token: string, user: User | null) {
  auth.token = token
  auth.user = user
  if (token) localStorage.setItem('commerce_token', token)
  else localStorage.removeItem('commerce_token')
}

async function request(path: string, init: RequestInit = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 95000)
  try {
    const headers = new Headers(init.headers)
    if (auth.token) headers.set('Authorization', 'Bearer ' + auth.token)
    if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
    const response = await fetch(path.startsWith('/api/') ? path : '/api/v1' + path, { ...init, headers, signal: controller.signal })
    if (response.status === 401 && !path.endsWith('/auth/login')) {
      setSession('', null)
      if (!location.pathname.startsWith('/login')) location.assign('/login')
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      const detail = Array.isArray(body.detail)
        ? body.detail.map((e: Row) => e.msg).join('；')
        : body.detail
      throw new Error(detail || `请求失败（${response.status}）`)
    }
    return response
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('请求超时，请检查服务状态后重试')
    throw error
  } finally { clearTimeout(timer) }
}

export async function api<T = Row>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await request(path, { method, ...(body === undefined ? {} : { body: JSON.stringify(body) }) })
  return response.json()
}

export async function upload(path: string, file: File): Promise<Row> {
  const form = new FormData()
  form.append('file', file)
  return (await request(path, { method: 'POST', body: form })).json()
}

export async function downloadTemplate(kind: string) {
  try {
    const blob = await (await request('/workspace/templates/' + kind)).blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = kind + '.csv'
    anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) { notify(String((error as Error).message), true) }
}

export const canWrite = () => auth.user?.role === 'admin' || auth.user?.role === 'operator'
export const isAdmin = () => auth.user?.role === 'admin'
export const money = (value: number = 0) => new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 2 }).format(value)
export const number = (value: number = 0) => new Intl.NumberFormat('zh-CN').format(value)
export const percent = (value: number = 0) => (value * 100).toFixed(2) + '%'
export const time = (value?: string) => value ? new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Shanghai' }) : '—'
export const platforms = [
  { value: 'taobao', label: '淘宝' }, { value: 'tmall', label: '天猫' }, { value: 'jd', label: '京东' },
  { value: 'douyin', label: '抖音' }, { value: 'pinduoduo', label: '拼多多' }, { value: 'xiaohongshu', label: '小红书' }, { value: 'other', label: '其他平台' },
]
export const platformName = (value: string) => platforms.find(p => p.value === value)?.label || value
export const labels: Record<string, string> = {
  draft: '草稿', active: '在售', inactive: '已停用', selected: '已选中', archived: '已归档',
  pending: '待处理', running: '运行中', succeeded: '已完成', failed: '失败', cancelled: '已取消', timeout: '已超时',
  confirmed: '已确认', rejected: '已驳回', finished: '已完成', approved: '审核通过',
  admin: '管理员', operator: '运营人员', viewer: '查看人员', queued: '已入队', retry: '重试',
  demo_rules: '演示规则生成', compatible_model: '模型生成', unconfigured: '未配置', placeholder_saved: '占位已保存',
}
