import { createRouter, createWebHistory } from 'vue-router'
import { api, auth, setSession, type User } from './api'
import Dashboard from './views/Dashboard.vue'
import Login from './views/Login.vue'
import Stores from './views/Stores.vue'
import StoreDetail from './views/StoreDetail.vue'
import Products from './views/Products.vue'
import ProductDetail from './views/ProductDetail.vue'
import Imports from './views/Imports.vue'
import Settings from './views/Settings.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login, meta: { title: '登录' } },
    { path: '/', component: Dashboard, meta: { title: '工作台' } },
    { path: '/stores', component: Stores, meta: { title: '店铺管理' } },
    { path: '/stores/:id', component: StoreDetail, meta: { title: '店铺详情' } },
    { path: '/products', component: Products, meta: { title: '商品池' } },
    { path: '/products/:id', component: ProductDetail, meta: { title: '商品运营' } },
    { path: '/imports', component: Imports, meta: { title: '导入中心' } },
    { path: '/settings', component: Settings, meta: { title: '系统设置', admin: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async to => {
  if (auth.token && !auth.user) {
    try { auth.user = await api<User>('/auth/me') }
    catch { setSession('', null) }
  }
  if (to.path !== '/login' && !auth.user) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.path === '/login' && auth.user) return '/'
  if (to.meta.admin && auth.user?.role !== 'admin') return '/'
  document.title = `${to.meta.title || '工作台'} · 青禾运营助手`
})
export default router
