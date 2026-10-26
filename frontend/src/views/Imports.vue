<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FileSpreadsheet, Download, UploadCloud, CircleCheck, AlertCircle, ArrowRight, Package, Layers, BarChart3, Link2 } from 'lucide-vue-next'
import { api, upload, downloadTemplate, canWrite, type Row } from '../api'
import { useAction } from '../forms'
const route=useRoute(),router=useRouter()
const kinds=[{key:'products',name:'商品导入',icon:Package,description:'批量创建商品档案，指定所属店铺与平台。'},
  {key:'sku-inventory',name:'SKU 与库存',icon:Layers,description:'批量建立 SKU 和初始库存，同时生成库存流水。'},
  {key:'performance-records',name:'经营数据',icon:BarChart3,description:'回填曝光、点击、成交、花费与收入，用于复盘。'},
  {key:'platform-mappings',name:'平台字段映射',icon:Link2,description:'将不同平台商品编号关联到同一商品档案。'}]
const kind=ref(kinds.some(k=>k.key===route.query.kind)?String(route.query.kind):'products'),result=ref<Row|null>(null),filename=ref(''),committed=ref(false),fileInput=ref<HTMLInputElement>()
const selected=computed(()=>kinds.find(k=>k.key===kind.value)!),action=useAction()
const columns=computed(()=>result.value?.rows.length?Object.keys(result.value.rows[0].data):[])
function changeKind(value:string) {kind.value=value;router.replace({query:{kind:value}});result.value=null;filename.value='';committed.value=false;if(fileInput.value)fileInput.value.value=''}
async function chooseFile(event:Event) {
  const file=(event.target as HTMLInputElement).files?.[0]
  if(!file)return
  result.value=null;committed.value=false;filename.value=file.name
  await action.run('preview',async()=>{result.value=await upload('/workspace/imports/'+kind.value+'/preview-file',file)},'文件预览完成，请检查数据与错误行')
}
async function commit() {if(!result.value)return;await action.run('commit',async()=>{result.value=await api('/workspace/imports/'+kind.value,'POST',{rows:result.value!.rows.map((r:Row)=>r.data)});committed.value=true},'导入处理完成，成功与失败结果已分别统计')}
watch(()=>route.query.kind,value=>{if(value && value!==kind.value && kinds.some(k=>k.key===value))changeKind(String(value))})
</script>
<template>
  <div class="page-heading"><div><span class="eyebrow">IMPORT CENTER</span><h1>导入中心<span class="heading-dot">.</span></h1><p>把已有资料带进来，让数据准备更轻松。</p></div><span class="import-format"><FileSpreadsheet :size="17" />UTF-8 CSV · 最大 5 MB / 5000 行</span></div>
  <div class="import-types"><button v-for="item in kinds" :key="item.key" :class="{active:kind===item.key}" :disabled="!!action.busy" @click="changeKind(item.key)"><component :is="item.icon" :size="23" /><strong>{{ item.name }}</strong><p>{{ item.description }}</p></button></div>
  <section class="panel"><div class="panel-heading"><div><h2>{{ selected.name }}</h2><p>下载模板 → 填写数据 → 预览检查 → 确认导入</p></div><button class="button secondary small-button" @click="downloadTemplate(kind)"><Download :size="15" />下载模板</button></div><div class="import-guide"><div><span>01</span><strong>准备数据</strong><p>按模板字段填写。店铺、商品编号可在对应详情页查看。</p></div><div><span>02</span><strong>预览与校验</strong><p>先检查必填字段、日期、数量与关联关系，不写入正式数据。</p></div><div><span>03</span><strong>确认导入</strong><p>有效行分别入库，错误行保留具体原因，允许部分成功。</p></div></div>
  <div v-if="route.query.product_id" class="callout import-product-note">当前商品编号为 <strong>{{ route.query.product_id }}</strong>，请在 CSV 的 product_id 列中填写这个编号。</div>
  <div v-if="canWrite()" class="upload-zone" :class="{busy:!!action.busy}"><UploadCloud :size="36" stroke-width="1.4" /><h3>{{ action.busy==='preview'?'正在校验文件…':filename || '选择要导入的 CSV 文件' }}</h3><p>请使用下载的模板填写；金额不含货币符号，日期格式为 YYYY-MM-DD。</p><label class="button secondary"><input ref="fileInput" type="file" accept=".csv,text/csv" :disabled="!!action.busy" class="visually-hidden" aria-label="选择 CSV 文件" @change="chooseFile" />{{ filename?'重新选择文件':'选择 CSV 文件' }}</label></div><p v-else class="panel-body muted">查看人员可以下载模板；导入数据需要管理员或运营人员权限。</p>
  </section>
  <section v-if="result" class="panel section-block"><div class="panel-heading"><div><h2>{{ committed?'导入结果':'导入预览' }}<span class="count-pill">{{ result.total }} 行</span></h2><p>{{ committed?'本次导入已处理完成；错误行修正后可重新上传。':'请核对预览。确认后仅导入有效行，错误行不会写入。' }}</p></div><button v-if="canWrite() && !committed" class="button primary" :disabled="!!action.busy || !result.success_count" @click="commit"><CircleCheck :size="16" />{{ action.busy==='commit'?'正在导入…':'确认导入 '+result.success_count+' 行' }}</button></div><div class="import-result-summary"><span class="text-success"><CircleCheck :size="18" />{{ committed?'成功':'可导入' }} {{ result.success_count }} 行</span><span :class="result.error_count?'text-warning':'muted'"><AlertCircle :size="18" />错误 {{ result.error_count }} 行</span><RouterLink v-if="committed" :to="kind==='performance-records' && route.query.product_id?'/products/'+route.query.product_id+'?tab=review':'/products'" class="table-link">查看商品 <ArrowRight :size="14" /></RouterLink></div><div class="table-wrap"><table><thead><tr><th>CSV 行号</th><th>校验结果</th><th v-for="column in columns" :key="column">{{ column }}</th></tr></thead><tbody><tr v-for="row in result.rows.slice(0,100)" :key="row.row" :class="{'invalid-row':!row.valid}"><td>{{ row.row }}</td><td><span v-if="row.valid" class="text-success">{{ committed?'已导入':'有效' }}</span><span v-else class="import-row-error">{{ row.reason }}</span></td><td v-for="column in columns" :key="column" class="small">{{ row.data[column] }}</td></tr></tbody></table></div><p v-if="result.rows.length>100" class="panel-body muted small">页面展示前 100 行，确认导入会处理全部 {{ result.total }} 行。</p><div v-if="result.errors.length" class="panel-body border-top"><h3>错误行与原因</h3><ul class="error-list"><li v-for="error in result.errors" :key="error.row"><strong>第 {{ error.row }} 行</strong>{{ error.reason }}</li></ul></div></section>
</template>
