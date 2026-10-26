<script setup lang="ts">
import { computed } from 'vue'
import { Sparkles, Pencil, ImagePlus, Clapperboard, ArrowRight, Check } from 'lucide-vue-next'
import { api, canWrite, type Row } from '../api'
import { useAction, useEditor } from '../forms'
import type { Field } from './FormModal.vue'
import FormModal from './FormModal.vue'
import StatusBadge from './StatusBadge.vue'
import EmptyState from './EmptyState.vue'
const props=defineProps<{product:Row;kind:'main_image'|'video_script'}>(),emit=defineEmits<{changed:[];tab:[value:string]}>()
const isVideo=computed(()=>props.kind==='video_script'),plans=computed(()=>props.product.creative_plans.filter((p:Row)=>p.plan_type===props.kind))
const action=useAction(()=>emit('changed')),editor=useEditor(()=>emit('changed'))
const base=()=>'/products/'+props.product.id
function edit(plan:Row) {
  const fields:Field[]=[{key:'title',label:'方案标题',required:true},{key:'rationale_text',label:'方案理由',type:'textarea',required:true}]
  const names=isVideo.value?{hook:'开头钩子',shots:'镜头分镜（每行一个）',voiceover:'口播文案',cta:'转化引导'}:{layout:'画面结构',copy:'核心文案',selling_point:'突出卖点'}
  fields.push(...Object.entries(names).map(([key,label]):Field=>({key:'content_'+key,label,type:key==='shots'?'lines':'textarea',required:true})))
  const initial={title:plan.title,rationale_text:plan.rationale_text,...Object.fromEntries(Object.entries(plan.content_json).map(([key,value])=>['content_'+key,value]))}
  editor.open('编辑'+(isVideo.value?'视频脚本':'主图方案'),fields,initial,base()+'/creative-plans/'+plan.id,'PATCH',data=>({title:data.title,rationale_text:data.rationale_text,content_json:Object.fromEntries(Object.keys(names).map(key=>[key,data['content_'+key]]))}))
}
function generateMedia(plan:Row) { action.run('media-'+plan.id,()=>api(base()+'/creative-plans/'+plan.id+'/'+(isVideo.value?'videos':'images')+'/generate','POST'),'素材任务已入队，可到任务页查看进度') }
function status(plan:Row,value:string) { action.run('status-'+plan.id,()=>api(base()+'/creative-plans/'+plan.id,'PATCH',{status:value}),'方案状态已更新') }
</script>
<template>
  <div class="tab-intro"><div><h2>{{ isVideo?'让商品故事，有一个好开头':'把商品优势，变成一眼看见的理由' }}</h2><p>{{ isVideo?'每次生成至少三条视频脚本，选中后提交异步视频任务。':'每次生成至少三个主图方向，核实文案后再提交素材任务。' }}</p></div><button v-if="canWrite()" class="button primary" :disabled="!!action.busy" @click="action.run('plans',()=>api(base()+'/creative-plans/'+(isVideo?'video-scripts':'main-images')+'/generate','POST'),'创意方案已生成')"><Sparkles :size="16" />{{ action.busy==='plans'?'正在生成…':isVideo?'生成视频脚本':'生成主图方案' }}</button></div>
  <div class="callout"><Sparkles :size="17" /><span>演示模式输出{{ isVideo?'动态分镜示意视频':'商品占位排版图' }}；用于验证流程。发布前请替换真实商品素材并人工审核。</span></div>
  <div v-if="plans.length" class="creative-grid"><article v-for="(plan,i) in plans" :key="plan.id" class="panel creative-card" :class="{ selected:plan.status==='selected' }"><div class="creative-cover" :class="isVideo?'video-cover':'image-cover'"><component :is="isVideo?Clapperboard:ImagePlus" :size="36" stroke-width="1.3" /><span>{{ isVideo?'STORY':'DIRECTION' }} {{ String(Number(i)+1).padStart(2,'0') }}</span><StatusBadge :value="plan.status" /></div><div class="creative-body"><h3>{{ plan.title }}</h3><template v-if="isVideo"><div class="creative-field"><span>开头钩子</span><p>{{ plan.content_json.hook }}</p></div><div class="creative-field"><span>镜头分镜</span><ol><li v-for="shot in plan.content_json.shots" :key="shot">{{ shot }}</li></ol></div><div class="creative-field"><span>口播文案</span><p>{{ plan.content_json.voiceover }}</p></div><div class="creative-field"><span>转化引导</span><p>{{ plan.content_json.cta }}</p></div></template><template v-else><div class="creative-field"><span>画面结构</span><p>{{ plan.content_json.layout }}</p></div><div class="creative-field"><span>核心文案</span><p class="creative-copy">{{ plan.content_json.copy }}</p></div><div class="creative-field"><span>突出卖点</span><p>{{ plan.content_json.selling_point }}</p></div></template><div class="creative-rationale"><strong>方案理由</strong><p>{{ plan.rationale_text }}</p></div></div><div v-if="canWrite()" class="creative-actions"><div class="inline-actions"><button class="text-button" @click="edit(plan)"><Pencil :size="13" />编辑</button><select :value="plan.status" aria-label="方案状态" class="status-select" :disabled="!!action.busy" @change="status(plan,($event.target as HTMLSelectElement).value)"><option value="draft">草稿</option><option value="selected">选中</option><option value="archived">归档</option></select></div><button class="button primary small-button" :disabled="!!action.busy || plan.status==='archived'" @click="generateMedia(plan)">{{ action.busy==='media-'+plan.id?'提交中…':isVideo?'生成视频':'生成图片' }}</button></div></article></div>
  <EmptyState v-else :title="isVideo?'第一条商品故事，从这里开始':'准备好商品的第一组主图方向'" text="请先生成商品诊断，再生成和编辑创意方案。" />
  <div v-if="plans.length" class="next-step"><button class="text-button" @click="emit('tab','tasks')">前往任务页查看进度 <ArrowRight :size="15" /></button></div>
  <FormModal v-if="editor.form" v-bind="editor.form" :saving="editor.saving" :error="editor.error" @close="editor.close" @submit="editor.save" />
</template>
