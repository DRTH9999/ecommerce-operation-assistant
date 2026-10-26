<script setup lang="ts">
import { computed } from 'vue'
import { RefreshCw, X, Check, Clock3, ArrowRight, Image, Video } from 'lucide-vue-next'
import { api, canWrite, isAdmin, labels, time, type Row } from '../api'
import { useAction } from '../forms'
import StatusBadge from './StatusBadge.vue'
import EmptyState from './EmptyState.vue'
const props=defineProps<{product:Row}>(),emit=defineEmits<{changed:[];tab:[value:string]}>()
const action=useAction(()=>emit('changed'))
const active=computed(()=>props.product.jobs.filter((j:Row)=>['pending','running'].includes(j.job_status)).length)
</script>
<template>
  <div class="tab-intro"><div><h2>创意正在成为素材</h2><p>当前 {{ active }} 个任务处理中，有活动任务时自动刷新。</p></div><div class="inline-actions"><button v-if="isAdmin()" class="button secondary" :disabled="!!action.busy" @click="action.run('sweep',()=>api('/workspace/generation-jobs/sweep-timeouts','POST'),'超时扫描已完成')"><Clock3 :size="15" />扫描超时</button><button class="button secondary" @click="emit('changed')"><RefreshCw :size="15" />刷新任务</button></div></div>
  <div v-if="product.jobs.length" class="task-list"><article v-for="job in product.jobs" :key="job.id" class="panel task-card"><div class="task-top"><span class="task-kind"><component :is="job.job_kind==='image'?Image:Video" :size="21" /></span><div class="grow"><h3>{{ job.job_kind==='image'?'图片生成':'视频生成' }} #{{ job.id }}</h3><p>{{ product.creative_plans.find((p:Row)=>p.id===job.creative_plan_id)?.title || '关联方案' }}</p></div><StatusBadge :value="job.job_status" /><div v-if="canWrite()" class="inline-actions"><button v-if="['failed','timeout'].includes(job.job_status)" class="button secondary small-button" :disabled="!!action.busy || job.attempts>=job.max_attempts" @click="action.run('retry-'+job.id,()=>api('/products/'+product.id+'/generation-jobs/'+job.id+'/retry','POST'),'任务已重新入队')"><RefreshCw :size="13" />重试</button><button v-if="['pending','running'].includes(job.job_status)" class="button secondary small-button" :disabled="!!action.busy" @click="action.run('cancel-'+job.id,()=>api('/products/'+product.id+'/generation-jobs/'+job.id+'/cancel','POST'),'任务已取消')"><X :size="13" />取消</button></div></div><div class="task-meta"><span>开始 {{ time(job.started_at) }}</span><span>结束 {{ time(job.finished_at) }}</span><span>已尝试 {{ job.attempts }} / {{ job.max_attempts }} 次</span></div><div v-if="job.error_message" class="task-error">{{ job.error_message }}</div><div class="event-timeline"><div v-for="event in job.events" :key="event.id" class="event-item"><span class="event-dot" :class="event.event_type"></span><div><strong>{{ labels[event.event_type] || event.event_type }}</strong><span>{{ event.event_message }}</span><small>{{ time(event.created_at) }}</small></div></div></div><div v-if="job.job_status==='succeeded'" class="task-bottom"><span class="muted small">输出已自动写入素材库，等待审核。</span><button class="text-button" @click="emit('tab','assets')">查看素材 <ArrowRight :size="14" /></button></div></article></div>
  <EmptyState v-else title="这里会记录每次生成的进度" text="在主图或视频标签页提交生成任务后，即可查看状态、事件、重试和取消操作。" />
</template>
