<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Store, Plus, ArrowUpRight, ArrowRight, Search, Package, AlertTriangle } from 'lucide-vue-next'
import { api, isAdmin, platformName, platforms, type Row } from '../api'
import { useEditor, storeFields } from '../forms'
import FormModal from '../components/FormModal.vue'
import EmptyState from '../components/EmptyState.vue'
const stores = ref<Row[]>([]), search = ref(''), platform = ref(''), loading = ref(true), error = ref('')
async function load() { try { stores.value = await api<Row[]>('/stores'); error.value = '' } catch (err) { error.value=(err as Error).message } finally { loading.value=false } }
const filtered = computed(() => stores.value.filter(s => (!platform.value || s.platform===platform.value) && s.store_name.includes(search.value)))
const editor = useEditor(load)
onMounted(load)
</script>
<template>
  <div class="page-heading"><div><span class="eyebrow">YOUR STORES</span><h1>店铺管理<span class="heading-dot">.</span></h1><p>管理每个经营阵地，让好商品各有所长。</p></div><button v-if="isAdmin()" class="button primary" @click="editor.open('创建店铺',storeFields,{platform:'taobao'},'/stores')"><Plus :size="17" />创建店铺</button></div>
  <div v-if="error" class="error-panel">{{ error }} <button @click="load">重试</button></div>
  <div class="compact-stats"><div><Store :size="21" /><span>全部店铺<strong>{{ stores.length }}</strong></span></div><div><Package :size="21" /><span>在管商品<strong>{{ stores.reduce((sum,s)=>sum+s.product_count,0) }}</strong></span></div><div><AlertTriangle :size="21" /><span>低库存 SKU<strong>{{ stores.reduce((sum,s)=>sum+s.low_stock_count,0) }}</strong></span></div></div>
  <div class="section-toolbar"><div class="search-input"><Search :size="16" /><input v-model="search" placeholder="搜索店铺名称" aria-label="搜索店铺" /></div><select v-model="platform" class="filter-select" aria-label="筛选平台"><option value="">全部平台</option><option v-for="p in platforms" :key="p.value" :value="p.value">{{ p.label }}</option></select></div>
  <div v-if="loading" class="loading-panel">正在加载店铺…</div><div v-else-if="filtered.length" class="store-grid"><RouterLink v-for="(store,i) in filtered" :key="store.id" :to="'/stores/'+store.id" class="store-card"><div class="store-card-top"><span class="store-avatar" :class="'store-color-'+i%3"><Store :size="23" /></span><span class="platform-tag" :class="store.platform">{{ platformName(store.platform) }}</span><ArrowUpRight :size="17" class="store-arrow" /></div><h3>{{ store.store_name }}</h3><p>负责人：{{ store.owner_name || '未设置' }}</p><p class="store-remark">{{ store.remark || '还没有店铺备注' }}</p><div class="store-card-bottom"><span><strong>{{ store.product_count }}</strong>在管商品</span><span :class="{'text-warning':store.low_stock_count}"><strong>{{ store.low_stock_count }}</strong>库存预警</span><span class="store-enter">进入店铺 <ArrowRight :size="13" /></span></div></RouterLink></div><EmptyState v-else title="没有找到店铺" text="创建一家新店铺，或调整搜索与筛选条件。" />
  <FormModal v-if="editor.form" v-bind="editor.form" :saving="editor.saving" :error="editor.error" @close="editor.close" @submit="editor.save" />
</template>
