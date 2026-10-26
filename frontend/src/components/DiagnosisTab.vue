<script setup lang="ts">
import { computed, ref } from 'vue'
import { Sparkles, Pencil, ArrowRight, ClipboardCheck } from 'lucide-vue-next'
import { api, canWrite, labels, time, type Row } from '../api'
import { useAction, useEditor } from '../forms'
import type { Field } from './FormModal.vue'
import FormModal from './FormModal.vue'
import EmptyState from './EmptyState.vue'
const props=defineProps<{product:Row}>(),emit=defineEmits<{changed:[];tab:[value:string]}>()
const selected=ref(0)
const diagnosis=computed(()=>props.product.diagnoses.find((d:Row)=>d.id===Number(selected.value)) || props.product.diagnoses[0])
const names:Record<string,string>={positioning:'商品定位',price_band:'价格带分析',audience_insights:'目标人群洞察',pain_points:'用户痛点',selling_point_analysis:'卖点分析',risks:'风险与边界',recommendations:'下一步优化建议'}
const fields:Field[]=Object.entries(names).map(([key,label])=>({key,label,type:'textarea',required:true}))
const action=useAction(()=>emit('changed')),editor=useEditor(()=>emit('changed'))
</script>
<template>
  <div class="tab-intro"><div><h2>先看清商品，再做经营决策</h2><p>结合商品档案、竞品和上一轮复盘，形成可编辑的结构化诊断。</p></div><button v-if="canWrite()" class="button primary" :disabled="!!action.busy" @click="action.run('generate',()=>api('/products/'+product.id+'/diagnoses/generate','POST'),'商品诊断已生成')"><Sparkles :size="16" />{{ action.busy?'正在生成…':product.diagnoses.length?'生成新一轮诊断':'生成商品诊断' }}</button></div>
  <section v-if="diagnosis" class="panel"><div class="panel-heading"><div><h2>商品诊断报告</h2><p>{{ labels[diagnosis.source_type] || diagnosis.source_type }} · {{ time(diagnosis.created_at) }}</p></div><div class="inline-actions"><select v-model="selected" class="filter-select" aria-label="诊断历史"><option :value="0">最新诊断</option><option v-for="d in product.diagnoses" :key="d.id" :value="d.id">#{{ d.id }} · {{ time(d.created_at) }}</option></select><button v-if="canWrite()" class="button secondary small-button" @click="editor.open('编辑商品诊断',fields,diagnosis,'/products/'+product.id+'/diagnoses/'+diagnosis.id,'PATCH')"><Pencil :size="14" />编辑诊断</button></div></div><div class="diagnosis-grid"><article v-for="(label,key,i) in names" :key="key" :class="{'diagnosis-wide':key==='recommendations'}"><span class="diagnosis-number">0{{ Number(i)+1 }}</span><div><h3>{{ label }}</h3><p class="pre-wrap">{{ diagnosis[key] }}</p></div></article></div><div class="panel-bottom"><span class="muted small">建议与假设需结合实际商品信息核实。</span><button class="text-button" @click="emit('tab','images')">下一步：主图方案 <ArrowRight :size="15" /></button></div></section>
  <EmptyState v-else title="从一次清晰的诊断开始" text="补充商品卖点与竞品信息后，生成你的第一份商品诊断。" />
  <FormModal v-if="editor.form" v-bind="editor.form" :saving="editor.saving" :error="editor.error" @close="editor.close" @submit="editor.save" />
</template>
