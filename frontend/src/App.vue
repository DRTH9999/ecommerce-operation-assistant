<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, Store, Package, Upload, Settings, Sprout, Search, LogOut, ChevronRight, ArrowUpRight, Menu, X } from 'lucide-vue-next'
import { auth, api, isAdmin, labels, notifications, setSession, notify } from './api'
const route = useRoute(), router = useRouter()
const search = ref(''), mobileNav = ref(false)
const navigation = [
  { path: '/', name: '工作台', icon: LayoutDashboard }, { path: '/stores', name: '店铺管理', icon: Store },
  { path: '/products', name: '商品池', icon: Package }, { path: '/imports', name: '导入中心', icon: Upload },
]
async function logout() {
  try { await api('/auth/logout', 'POST') } catch (error) { notify((error as Error).message, true) }
  setSession('', null); await router.push('/login')
}
function searchProducts() { router.push({ path: '/products', query: { search: search.value } }); search.value = '' }
</script>
<template>
  <RouterView v-if="route.path === '/login'" />
  <div v-else class="app-shell">
    <div v-if="mobileNav" class="nav-shade" @click="mobileNav=false"></div>
    <aside class="sidebar" :class="{ 'mobile-open': mobileNav }">
      <RouterLink class="brand" to="/" @click="mobileNav=false"><span class="brand-mark"><Sprout :size="25" /></span><span>青禾<span class="brand-sub">电商运营助手</span></span></RouterLink>
      <div class="workspace-label">我的工作空间<span>WORKSPACE</span></div>
      <nav aria-label="主导航"><RouterLink v-for="item in navigation" :key="item.path" :to="item.path" class="nav-link" :class="{ active: item.path === '/' ? route.path === '/' : route.path.startsWith(item.path) }" @click="mobileNav=false"><component :is="item.icon" :size="19" /><span>{{ item.name }}</span><ChevronRight :size="14" class="nav-arrow" /></RouterLink></nav>
      <div class="sidebar-growth"><div class="growth-icon"><Sprout :size="26" /></div><strong>让每一步，都向生长</strong><p>从一件好商品开始，<br />积累每一次运营的经验。</p><RouterLink to="/products">开启单品运营 <ArrowUpRight :size="14" /></RouterLink></div>
      <div class="sidebar-bottom"><RouterLink v-if="isAdmin()" to="/settings" class="nav-link" :class="{ active: route.path === '/settings' }" @click="mobileNav=false"><Settings :size="19" />系统设置</RouterLink><span class="version">青禾运营工作台 <span>v1.0</span></span></div>
    </aside>
    <div class="main-shell">
      <header class="topbar"><div class="breadcrumbs"><button class="icon-button mobile-toggle" aria-label="展开导航" @click="mobileNav=!mobileNav"><Menu :size="20" /></button><span>工作空间</span><ChevronRight :size="14" /><strong>{{ route.meta.title }}</strong></div>
        <div class="topbar-right"><form class="global-search" @submit.prevent="searchProducts"><Search :size="16" /><input v-model="search" placeholder="搜索商品…" aria-label="搜索商品" /><kbd>↵</kbd></form><span class="top-divider"></span><div class="user-avatar">{{ auth.user?.display_name?.slice(0,1) }}</div><div class="user-info"><strong>{{ auth.user?.display_name }}</strong><small>{{ labels[auth.user?.role || ''] }}</small></div><button class="icon-button" title="退出登录" aria-label="退出登录" @click="logout"><LogOut :size="17" /></button></div>
      </header>
      <main class="page-content"><RouterView /></main>
      <footer class="app-footer"><span>青禾 · 专注每一件商品的生长</span><span>有据可循，有序向前。</span></footer>
    </div>
  </div>
  <div class="toast-stack" aria-live="polite"><div v-for="item in notifications" :key="item.id" class="toast" :class="{ error:item.error }"><span>{{ item.message }}</span><button aria-label="关闭提示" @click="notifications.splice(notifications.indexOf(item),1)"><X :size="16" /></button></div></div>
</template>
