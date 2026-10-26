<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Search, ArrowRight, Upload, Package, LayoutGrid, List } from 'lucide-vue-next'
import { api, canWrite, money, platformName, platforms, time, type Row } from '../api'
import { useEditor, newProduct } from '../forms'
import FormModal from '../components/FormModal.vue'
import ProductArt from '../components/ProductArt.vue'
import StatusBadge from '../components/StatusBadge.vue'
import EmptyState from '../components/EmptyState.vue'
const route=useRoute(), products=ref<Row[]>([]), stores=ref<Row[]>([]), search=ref(String(route.query.search||'')), platform=ref(''), storeId=ref(''), status=ref(''), error=ref(''), loading=ref(true), grid=ref(false)
async function load() {
  const query=new URLSearchParams({search:search.value})
  if(platform.value) query.set('platform',platform.value)
  if(storeId.value) query.set('store_id',storeId.value)
  if(status.value) query.set('status',status.value)
  try { [products.value,stores.value]=await Promise.all([api<Row[]>('/products?'+query),api<Row[]>('/stores')]); error.value='' }
  catch(err){error.value=(err as Error).message}finally{loading.value=false}
}
const editor=useEditor(load)
watch(()=>route.query.search,value=>{search.value=String(value||'');load()}); onMounted(load)
</script>
<template>
  <div class="page-heading"><div><span class="eyebrow">PRODUCT GARDEN</span><h1>商品池<span class="heading-dot">.</span></h1><p>每一件商品，都是值得认真经营的可能。</p></div><div class="heading-actions"><RouterLink to="/imports" class="button secondary"><Upload :size="16" />批量导入</RouterLink><button v-if="canWrite()" class="button primary" @click="newProduct(editor,stores)"><Plus :size="17" />录入商品</button></div></div>
  <section class="panel"><div class="list-toolbar"><form class="search-input" @submit.prevent="load"><Search :size="16" /><input v-model="search" aria-label="搜索商品名称" placeholder="搜索商品名称，回车查询" /></form><select v-model="platform" class="filter-select" aria-label="筛选平台" @change="load"><option value="">全部平台</option><option v-for="p in platforms" :key="p.value" :value="p.value">{{ p.label }}</option></select><select v-model="storeId" class="filter-select" aria-label="筛选店铺" @change="load"><option value="">全部店铺</option><option v-for="s in stores" :key="s.id" :value="s.id">{{ s.store_name }}</option></select><select v-model="status" class="filter-select" aria-label="筛选状态" @change="load"><option value="">全部状态</option><option value="draft">草稿</option><option value="active">在售</option><option value="inactive">已停用</option></select><div class="view-toggle"><button :class="{active:!grid}" aria-label="列表视图" @click="grid=false"><List :size="17" /></button><button :class="{active:grid}" aria-label="卡片视图" @click="grid=true"><LayoutGrid :size="17" /></button></div></div><div class="list-caption">共 <strong>{{ products.length }}</strong> 件商品<span>选择商品，开始一轮完整运营</span></div>
    <div v-if="error" class="error-panel">{{ error }}<button @click="load">重试</button></div><div v-if="loading" class="loading-panel">正在加载商品…</div>
    <div v-else-if="products.length && !grid" class="table-wrap"><table><thead><tr><th>商品信息</th><th>平台 / 店铺</th><th>售价</th><th>库存</th><th>状态</th><th>最近诊断 / 复盘</th><th></th></tr></thead><tbody><tr v-for="(p,i) in products" :key="p.id"><td><RouterLink :to="'/products/'+p.id" class="product-cell"><ProductArt :category="p.category" :image="p.images_json?.[0]" :name="p.name" :index="i" /><div><strong>{{ p.name }}</strong><small>{{ p.category || '待补充类目' }} · #{{ p.id }}</small></div></RouterLink></td><td><span class="platform-tag" :class="p.platform">{{ platformName(p.platform) }}</span><small class="block muted spaced">{{ p.store_name }}</small></td><td class="numeric">{{ money(p.price) }}</td><td :class="{'text-warning':p.low_stock_count}">{{ p.stock_qty }}<small v-if="p.low_stock_count" class="block">{{ p.low_stock_count }} 个预警</small></td><td><StatusBadge :value="p.status" /></td><td class="muted small">{{ time(p.last_diagnosis_at) }}<br />{{ time(p.last_review_at) }}</td><td><RouterLink :to="'/products/'+p.id" class="table-link">进入运营 <ArrowRight :size="14" /></RouterLink></td></tr></tbody></table></div>
    <div v-else-if="products.length && grid" class="product-grid"><RouterLink v-for="(p,i) in products" :key="p.id" :to="'/products/'+p.id" class="product-grid-card"><ProductArt :category="p.category" :image="p.images_json?.[0]" :name="p.name" :index="i" /><div><StatusBadge :value="p.status" /><h3>{{ p.name }}</h3><p>{{ p.store_name }}</p><strong>{{ money(p.price) }}</strong></div></RouterLink></div>
    <EmptyState v-else title="这里还没有找到商品" text="试着调整筛选条件，或录入你的第一件好商品。" />
  </section>
  <FormModal v-if="editor.form" v-bind="editor.form" :saving="editor.saving" :error="editor.error" @close="editor.close" @submit="editor.save" />
</template>
