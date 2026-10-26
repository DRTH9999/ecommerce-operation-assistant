<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Plus, Pencil, Sparkles, ShieldCheck, Link2, Store, ArrowRight } from 'lucide-vue-next'
import { api, canWrite, isAdmin, money, platformName, time, type Row } from '../api'
import { useAction, useEditor, storeFields, newProduct } from '../forms'
import FormModal from '../components/FormModal.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ProductArt from '../components/ProductArt.vue'
import EmptyState from '../components/EmptyState.vue'
const route=useRoute(), store=ref<Row|null>(null), advice=ref<Row|null>(null), error=ref('')
async function load() { try { store.value=await api('/stores/'+route.params.id); error.value='' } catch(err){error.value=(err as Error).message} }
const editor=useEditor(load), action=useAction(load)
function addAccount() { editor.open('添加平台账号占位',[{key:'account_name',label:'账号名称',required:true},{key:'remark',label:'备注',type:'textarea'}],{},`/stores/${store.value!.id}/platform-accounts`,'POST',data=>({...data,platform:store.value!.platform})) }
async function authorize(account:Row) {
  await action.run('auth-'+account.id,async()=>{
    const state=await api(`/stores/${store.value!.id}/platform-accounts/${account.id}/authorization/start`,'POST')
    editor.open('保存授权占位元数据',[{key:'external_account_id',label:'平台账号编号',required:true},
      {key:'scopes',label:'授权范围（每行一个）',type:'lines'},{key:'expires_at',label:'过期时间（可留空）'}],{},
      `/stores/${store.value!.id}/platform-accounts/${account.id}/authorization/callback-placeholder`,'POST',data=>({...data,state:state.state}))
  },'授权占位已创建，当前未连接真实平台')
}
onMounted(load); watch(()=>route.params.id,load)
</script>
<template>
  <RouterLink to="/stores" class="back-link"><ArrowLeft :size="15" />返回店铺列表</RouterLink><div v-if="error" class="error-panel">{{ error }}<button @click="load">重试</button></div>
  <template v-if="store"><div class="page-heading"><div><span class="eyebrow">STORE WORKSPACE</span><h1>{{ store.store_name }}</h1><p><span class="platform-tag" :class="store.platform">{{ platformName(store.platform) }}</span> <span class="inline-detail">负责人 {{ store.owner_name || '未设置' }} · 更新于 {{ time(store.updated_at) }}</span></p></div><div class="heading-actions"><button v-if="isAdmin()" class="button secondary" @click="editor.open('编辑店铺',storeFields,store,'/stores/'+store.id,'PATCH')"><Pencil :size="15" />编辑店铺</button><button v-if="canWrite()" class="button primary" @click="newProduct(editor,[store])"><Plus :size="17" />录入商品</button></div></div>
  <div class="stats-grid"><article class="stat-card"><span class="muted">在管商品</span><strong>{{ store.products.length }}<small>件</small></strong></article><article class="stat-card"><span class="muted">SKU 总数</span><strong>{{ store.skus.length }}</strong></article><article class="stat-card"><span class="muted">库存总量</span><strong>{{ store.skus.reduce((sum:number,s:Row)=>sum+s.stock_qty,0) }}</strong></article><article class="stat-card"><span class="muted">低库存 SKU</span><strong class="text-warning">{{ store.skus.filter((s:Row)=>s.low_stock).length }}</strong></article></div>
  <div class="detail-columns"><section class="panel"><div class="panel-heading"><div><h2>店铺商品</h2><p>{{ store.remark || '专注每一件商品的经营' }}</p></div></div><div v-if="store.products.length" class="table-wrap"><table><thead><tr><th>商品</th><th>售价</th><th>库存</th><th>状态</th><th></th></tr></thead><tbody><tr v-for="(p,i) in store.products" :key="p.id"><td><RouterLink :to="'/products/'+p.id" class="product-cell"><ProductArt :category="p.category" :image="p.images_json?.[0]" :name="p.name" :index="Number(i)" /><div><strong>{{ p.name }}</strong><small>{{ p.category }}</small></div></RouterLink></td><td>{{ money(p.price) }}</td><td :class="{'text-warning':p.low_stock_count}">{{ p.stock_qty }}</td><td><StatusBadge :value="p.status" /></td><td><RouterLink :to="'/products/'+p.id" class="table-link">运营 <ArrowRight :size="13" /></RouterLink></td></tr></tbody></table></div><EmptyState v-else title="店铺里还没有商品" /></section>
  <section class="panel"><div class="panel-heading"><div><h2>平台账号</h2><p>仅管理安全元数据与授权占位</p></div><button v-if="isAdmin()" class="icon-button" aria-label="添加平台账号" @click="addAccount"><Plus :size="18" /></button></div><div class="panel-body"><div v-for="account in store.platform_accounts" :key="account.id" class="account-card"><ShieldCheck :size="23" /><div><strong>{{ account.account_name }}</strong><p><StatusBadge :value="account.auth_status" /></p><small v-if="account.auth_meta_json.external_account_id">平台编号：{{ account.auth_meta_json.external_account_id }}</small></div><button v-if="isAdmin()" class="text-button" :disabled="!!action.busy" @click="authorize(account)">授权占位</button></div><p v-if="!store.platform_accounts.length" class="muted">尚未添加平台账号。</p><div class="callout small">当前为平台接入占位，不代表已获得真实平台授权。</div></div></section></div>
  <section class="panel section-block"><div class="panel-heading"><div><h2>库存概览与建议</h2><p>按可用库存与预警阈值检查</p></div><button v-if="canWrite()" class="button secondary small-button" :disabled="!!action.busy" @click="action.run('advice',async()=>{advice=await api('/stores/'+store!.id+'/inventory-advice/generate','POST')},'库存建议已生成')"><Sparkles :size="14" />生成库存建议</button></div><div class="table-wrap"><table><thead><tr><th>商品 / 规格</th><th>可用库存</th><th>锁定</th><th>预警阈值</th><th>库位</th><th>建议</th></tr></thead><tbody><tr v-for="sku in store.skus" :key="sku.id"><td><RouterLink :to="'/products/'+sku.product_id" class="table-link">{{ sku.product_name }}</RouterLink><small class="block muted">{{ sku.sku_name }}</small></td><td :class="{'text-warning':sku.low_stock}">{{ sku.available_qty }}</td><td>{{ sku.locked_qty }}</td><td>{{ sku.warning_threshold }}</td><td>{{ sku.location_text || '—' }}</td><td class="muted">{{ advice?.items.find((a:Row)=>a.sku_id===sku.id)?.advice || (sku.low_stock?'低库存，请安排核对':'库存正常') }}</td></tr></tbody></table></div></section>
  <section class="panel section-block"><div class="panel-heading"><div><h2>最近库存流水</h2><p>每一次变化都有记录</p></div></div><div class="table-wrap"><table><thead><tr><th>时间</th><th>SKU</th><th>变动</th><th>调整前 → 调整后</th><th>原因</th></tr></thead><tbody><tr v-for="movement in store.inventory_movements.slice(0,12)" :key="movement.id"><td>{{ time(movement.created_at) }}</td><td>{{ store.skus.find((s:Row)=>s.id===movement.sku_id)?.sku_name }}</td><td :class="movement.change_qty>0?'text-success':'text-warning'">{{ movement.change_qty>0?'+':'' }}{{ movement.change_qty }}</td><td>{{ movement.before_qty }} → {{ movement.after_qty }}</td><td>{{ movement.reason_text }}</td></tr></tbody></table></div></section>
  </template><div v-else-if="!error" class="loading-panel">正在加载店铺…</div>
  <FormModal v-if="editor.form" v-bind="editor.form" :saving="editor.saving" :error="editor.error" @close="editor.close" @submit="editor.save" />
</template>
