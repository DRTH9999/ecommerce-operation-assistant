<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Upload, Sparkles, Pencil, ArrowRight, BarChart3 } from 'lucide-vue-next'
import { api, canWrite, money, percent, labels, time, type Row } from '../api'
import { useAction, useEditor } from '../forms'
import type { Field } from './FormModal.vue'
import FormModal from './FormModal.vue'
import EmptyState from './EmptyState.vue'
const props=defineProps<{product:Row}>(),emit=defineEmits<{changed:[];tab:[value:string]}>()
const today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Shanghai'})
const from=ref(props.product.performance_records.length?props.product.performance_records[props.product.performance_records.length-1].period_start:today),to=ref(today)
const selected=ref(0),report=computed(()=>props.product.review_reports.find((r:Row)=>r.id===Number(selected.value)) || props.product.review_reports[0])
const records=computed(()=>props.product.performance_records.filter((r:Row)=>r.period_start>=from.value && r.period_end<=to.value))
const totals=computed(()=>{const result={impressions:0,clicks:0,conversions:0,spend:0,revenue:0};for(const r of records.value){for(const k of Object.keys(result) as (keyof typeof result)[]) result[k]+=r[k]}return result})
const action=useAction(()=>emit('changed')),editor=useEditor(()=>emit('changed'))
const base=()=>'/products/'+props.product.id
function addRecord() {
  const fields:Field[]=[{key:'period_start',label:'开始日期',type:'date',required:true},{key:'period_end',label:'结束日期',type:'date',required:true},
    {key:'impressions',label:'曝光量',type:'number',min:0,step:1,required:true},{key:'clicks',label:'点击量',type:'number',min:0,step:1,required:true},
    {key:'conversions',label:'成交量',type:'number',min:0,step:1,required:true},{key:'spend',label:'花费（元）',type:'number',min:0,step:0.01,required:true},
    {key:'revenue',label:'经营收入（元）',type:'number',min:0,step:0.01,required:true}]
  for(const [key,label,items,name] of [['creative_plan_id','关联创意方案',props.product.creative_plans,'title'],['generated_asset_id','关联素材',props.product.assets,'usage_scene'],['promotion_link_id','关联推广链接',props.product.links,'link_name'],['experiment_id','关联实验',props.product.experiments,'experiment_name']] as [string,string,Row[],string][]){fields.push({key,label,type:'select',options:[{value:0,label:'暂不关联'},...items.map((i:Row)=>({value:i.id,label:`#${i.id} · ${i[name]}`}))]})}
  fields.push({key:'notes',label:'数据备注',type:'textarea',hint:'使用一致的归因口径；不要重复录入同一组统计数据。'})
  editor.open('回填经营数据',fields,{period_start:today,period_end:today,impressions:0,clicks:0,conversions:0,spend:0,revenue:0,creative_plan_id:0,generated_asset_id:0,promotion_link_id:0,experiment_id:0},base()+'/performance-records','POST',data=>Object.fromEntries(Object.entries(data).filter(([k,v])=>!k.endsWith('_id') || Number(v)>0)))
}
function editReport() {const r=report.value;editor.open('编辑经营复盘报告',[{key:'summary_text',label:'周期摘要',type:'textarea',required:true},{key:'insights_json',label:'核心洞察（每行一个）',type:'lines',required:true},{key:'problem_judgment',label:'问题判断',type:'textarea',required:true},{key:'next_actions_json',label:'下一步动作（每行一个）',type:'lines',required:true}],r,base()+'/review-reports/'+r.id,'PATCH')}
</script>
<template>
  <div class="tab-intro"><div><h2>每一次复盘，都为下一轮生长</h2><p>回填真实经营数据，把观察转成可执行的下一步。</p></div><div v-if="canWrite()" class="inline-actions"><RouterLink :to="{path:'/imports',query:{kind:'performance-records',product_id:product.id}}" class="button secondary"><Upload :size="15" />导入数据</RouterLink><button class="button primary" @click="addRecord"><Plus :size="16" />录入经营数据</button></div></div>
  <div class="period-bar"><span>复盘周期</span><input v-model="from" type="date" aria-label="复盘开始日期" /><span>至</span><input v-model="to" type="date" aria-label="复盘结束日期" /><button v-if="canWrite()" class="button primary small-button" :disabled="!!action.busy || !from || !to || to<from" @click="action.run('report',()=>api(base()+'/review-reports/generate','POST',{period_start:from,period_end:to}),'复盘报告已生成')"><Sparkles :size="14" />{{ action.busy==='report'?'正在生成…':'生成复盘报告' }}</button></div>
  <div class="stats-grid review-stats"><article class="stat-card"><span class="muted">周期收入</span><strong>{{ money(totals.revenue) }}</strong></article><article class="stat-card"><span class="muted">周期花费</span><strong>{{ money(totals.spend) }}</strong></article><article class="stat-card"><span class="muted">点击率</span><strong>{{ percent(totals.impressions?totals.clicks/totals.impressions:0) }}</strong></article><article class="stat-card"><span class="muted">点击转化率</span><strong>{{ percent(totals.clicks?totals.conversions/totals.clicks:0) }}</strong></article></div>
  <section v-if="report" class="panel review-report"><div class="panel-heading"><div><h2>经营复盘报告</h2><p>{{ report.period_start }} — {{ report.period_end }} · {{ labels[report.source_type] }} · {{ time(report.created_at) }}</p></div><div class="inline-actions"><select v-model="selected" class="filter-select" aria-label="历史复盘报告"><option :value="0">最新复盘</option><option v-for="r in product.review_reports" :key="r.id" :value="r.id">#{{ r.id }} · {{ r.period_start }}</option></select><button v-if="canWrite()" class="button secondary small-button" @click="editReport"><Pencil :size="14" />编辑报告</button></div></div><div class="review-summary"><BarChart3 :size="25" /><p>{{ report.summary_text }}</p></div><div class="report-columns"><article><h3>核心洞察</h3><ul><li v-for="i in report.insights_json" :key="i">{{ i }}</li></ul></article><article><h3>问题判断</h3><p>{{ report.problem_judgment }}</p></article></div><div class="review-next"><span class="eyebrow">NEXT ROUND</span><h3>下一轮，我们这样做</h3><ol><li v-for="item in report.next_actions_json" :key="item">{{ item }}</li></ol><button class="button primary small-button" @click="emit('tab','diagnosis')">回到诊断，开启下一轮 <ArrowRight :size="14" /></button></div></section>
  <EmptyState v-else title="用数据完成这一轮经营" text="录入或导入经营数据后，选择周期生成第一份复盘报告。" />
  <section class="panel section-block"><div class="panel-heading"><div><h2>经营数据记录<span class="count-pill">{{ records.length }}</span></h2><p>仅汇总完整落在所选区间内的记录；ROI 口径为收入 / 花费，未扣除其他成本。</p></div></div><div v-if="records.length" class="table-wrap"><table><thead><tr><th>日期 / 周期</th><th>曝光 / 点击 / 成交</th><th>CTR / CVR</th><th>花费</th><th>收入</th><th>ROI</th><th>备注</th></tr></thead><tbody><tr v-for="record in records" :key="record.id"><td class="small">{{ record.period_start }}<span v-if="record.period_end!==record.period_start"> — {{ record.period_end }}</span></td><td>{{ record.impressions }} / {{ record.clicks }} / {{ record.conversions }}</td><td class="small">{{ percent(record.ctr) }} / {{ percent(record.conversion_rate) }}</td><td>{{ money(record.spend) }}</td><td>{{ money(record.revenue) }}</td><td>{{ record.roi.toFixed(2) }}</td><td class="muted small">{{ record.notes || '—' }}</td></tr></tbody></table></div><div v-else class="panel-body muted">所选周期暂无经营数据。</div></section>
  <FormModal v-if="editor.form" v-bind="editor.form" :saving="editor.saving" :error="editor.error" @close="editor.close" @submit="editor.save" />
</template>
