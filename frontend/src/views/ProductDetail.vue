<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Pencil, Package, ScanSearch, Image, Clapperboard, LoaderCircle, FolderHeart, Link2, Megaphone, BarChart3, RefreshCw } from 'lucide-vue-next'
import { api, canWrite, money, platformName, type Row } from '../api'
import { useEditor, productFields } from '../forms'
import FormModal from '../components/FormModal.vue'
import ProductArt from '../components/ProductArt.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ProductBaseTab from '../components/ProductBaseTab.vue'
import DiagnosisTab from '../components/DiagnosisTab.vue'
import CreativeTab from '../components/CreativeTab.vue'
import TasksTab from '../components/TasksTab.vue'
import AssetsTab from '../components/AssetsTab.vue'
import LinksTab from '../components/LinksTab.vue'
import AdsTab from '../components/AdsTab.vue'
import ReviewTab from '../components/ReviewTab.vue'
const route=useRoute(),router=useRouter(),product=ref<Row|null>(null),error=ref(''),refreshing=ref(false)
const tabs=[{key:'base',name:'商品&竞品',icon:Package,component:ProductBaseTab},{key:'diagnosis',name:'诊断',icon:ScanSearch,component:DiagnosisTab},
  {key:'images',name:'主图',icon:Image,component:CreativeTab},{key:'videos',name:'视频',icon:Clapperboard,component:CreativeTab},
  {key:'tasks',name:'任务',icon:LoaderCircle,component:TasksTab},{key:'assets',name:'素材库',icon:FolderHeart,component:AssetsTab},
  {key:'links',name:'链接',icon:Link2,component:LinksTab},{key:'ads',name:'投放',icon:Megaphone,component:AdsTab},{key:'review',name:'复盘',icon:BarChart3,component:ReviewTab}]
const active=computed(()=>tabs.find(t=>t.key===route.query.tab)||tabs[0]!)
function changeTab(tab:string) {router.replace({query:{...route.query,tab}})}
async function load() {const id=String(route.params.id);try{const result=await api('/products/'+id);if(id===String(route.params.id)){product.value=result;error.value=''}}catch(err){error.value=(err as Error).message}finally{refreshing.value=false}}
const editor=useEditor(load)
async function edit() {try{const stores=await api<Row[]>('/stores');editor.open('编辑商品档案',productFields(stores,true),product.value!,'/products/'+product.value!.id,'PATCH',data=>({...data,store_id:Number(data.store_id),platform:stores.find(s=>s.id===Number(data.store_id))?.platform}))}catch(err){error.value=(err as Error).message}}
let timer:ReturnType<typeof setInterval>
onMounted(()=>{load();timer=setInterval(()=>{if(!document.hidden && product.value?.jobs.some((j:Row)=>['pending','running'].includes(j.job_status)) && !editor.saving)load()},2500)})
onBeforeUnmount(()=>clearInterval(timer));watch(()=>route.params.id,()=>{product.value=null;load()})
</script>
<template>
  <RouterLink to="/products" class="back-link"><ArrowLeft :size="15" />返回商品池</RouterLink><div v-if="error" class="error-panel">{{ error }}<button @click="load">重试</button></div>
  <template v-if="product"><div class="product-detail-header"><ProductArt :category="product.category" :image="product.images_json?.[0]" :name="product.name" /><div class="product-detail-title"><div class="inline-actions"><span class="platform-tag" :class="product.platform">{{ platformName(product.platform) }}</span><span class="muted small">{{ product.store_name }} / 商品 #{{ product.id }}</span></div><h1>{{ product.name }}</h1><div class="inline-actions"><strong class="detail-price">{{ money(product.price) }}</strong><StatusBadge :value="product.status" /><span class="muted small">{{ product.category }}</span></div></div><div class="heading-actions"><button class="button secondary" :disabled="refreshing" @click="refreshing=true;load()"><RefreshCw :size="15" :class="{spin:refreshing}" />刷新</button><button v-if="canWrite()" class="button primary" @click="edit"><Pencil :size="15" />编辑商品</button></div></div>
  <div class="workflow-strip"><span :class="{done:product.diagnoses.length}">01 商品诊断</span><i>→</i><span :class="{done:product.creative_plans.length}">02 创意与素材</span><i>→</i><span :class="{done:product.ad_recommendations.some((r:Row)=>r.confirm_status==='confirmed')}">03 确认与实验</span><i>→</i><span :class="{done:product.review_reports.length}">04 数据与复盘</span></div>
  <nav class="product-tabs" aria-label="商品运营标签页"><button v-for="tab in tabs" :key="tab.key" :class="{active:active.key===tab.key}" @click="changeTab(tab.key)"><component :is="tab.icon" :size="16" />{{ tab.name }}<span v-if="tab.key==='tasks' && product.jobs.some((j:Row)=>['pending','running'].includes(j.job_status))" class="live-dot"></span><span v-if="tab.key==='assets' && product.assets.filter((a:Row)=>a.review_status==='pending').length" class="tab-count">{{ product.assets.filter((a:Row)=>a.review_status==='pending').length }}</span></button></nav>
  <component :is="active.component" :key="product.id+'-'+active.key" :product="product" :kind="active.key==='videos'?'video_script':'main_image'" @changed="load" @tab="changeTab" />
  </template><div v-else-if="!error" class="loading-panel">正在加载商品运营空间…</div>
  <FormModal v-if="editor.form" v-bind="editor.form" :saving="editor.saving" :error="editor.error" @close="editor.close" @submit="editor.save" />
</template>
