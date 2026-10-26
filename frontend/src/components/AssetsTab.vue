<script setup lang="ts">
import { computed, ref } from 'vue'
import { RefreshCw, Pencil, Star, Image, Video, ArrowUpRight } from 'lucide-vue-next'
import { api, canWrite, time, type Row } from '../api'
import { useAction, useEditor } from '../forms'
import FormModal from './FormModal.vue'
import StatusBadge from './StatusBadge.vue'
import EmptyState from './EmptyState.vue'
const props=defineProps<{product:Row}>(),emit=defineEmits<{changed:[]}>(),filter=ref('')
const assets=computed(()=>props.product.assets.filter((a:Row)=>!filter.value || a.review_status===filter.value))
const editor=useEditor(()=>emit('changed')),action=useAction(()=>emit('changed'))
function edit(asset:Row) {
  editor.open('审核与管理素材',[{key:'review_status',label:'审核状态',type:'select',required:true,options:[{value:'pending',label:'待审核'},{value:'approved',label:'审核通过'},{value:'rejected',label:'驳回'}]},
    {key:'score',label:'评分（0–5）',type:'number',min:0,max:5,step:0.5},{key:'version_no',label:'版本号',type:'number',min:1,step:1},
    {key:'usage_scene',label:'使用场景'},{key:'tags_json',label:'标签（每行一个）',type:'lines'},
    {key:'remark',label:'审核备注',type:'textarea'}],asset,'/products/'+props.product.id+'/assets/'+asset.id,'PATCH')
}
</script>
<template>
  <div class="tab-intro"><div><h2>让每份素材，都有清楚的去向</h2><p>生成完成后自动入库；审核通过后，才能用于投放实验。</p></div><button v-if="canWrite()" class="button secondary" :disabled="!!action.busy" @click="action.run('sync',()=>api('/products/'+product.id+'/assets/sync','POST'),'素材列表已同步')"><RefreshCw :size="15" />同步素材</button></div>
  <div class="section-toolbar"><div class="segmented"><button :class="{active:filter===''}" @click="filter=''">全部 {{ product.assets.length }}</button><button :class="{active:filter==='pending'}" @click="filter='pending'">待审核</button><button :class="{active:filter==='approved'}" @click="filter='approved'">已通过</button><button :class="{active:filter==='rejected'}" @click="filter='rejected'">已驳回</button></div></div>
  <div v-if="assets.length" class="asset-grid"><article v-for="asset in assets" :key="asset.id" class="panel asset-card"><div class="asset-preview"><video v-if="asset.asset_type==='video'" :src="asset.asset_url" controls preload="metadata" :aria-label="'生成视频 '+asset.id"></video><img v-else :src="asset.asset_url" :alt="product.name+' 创意排版示意 '+asset.id" loading="lazy" /><span class="asset-version">V{{ asset.version_no }}</span></div><div class="asset-info"><div class="row-between"><span class="asset-type"><component :is="asset.asset_type==='image'?Image:Video" :size="14" />{{ asset.usage_scene || (asset.asset_type==='image'?'图片':'视频') }}</span><StatusBadge :value="asset.review_status" :label="asset.review_status==='pending'?'待审核':undefined" /></div><h3>{{ product.creative_plans.find((p:Row)=>p.id===asset.creative_plan_id)?.title }}</h3><div class="asset-rating"><Star :size="13" />{{ asset.score.toFixed(1) }}<span>{{ asset.model_name }} · {{ time(asset.created_at) }}</span></div><div class="tag-list"><span v-for="tag in asset.tags_json" :key="tag">{{ tag }}</span></div><p class="asset-remark">{{ asset.remark || '暂无审核备注' }}</p></div><div class="asset-actions"><a :href="asset.asset_url" target="_blank" rel="noopener noreferrer" class="text-button">查看原文件 <ArrowUpRight :size="14" /></a><button v-if="canWrite()" class="button secondary small-button" @click="edit(asset)"><Pencil :size="13" />审核 / 编辑</button></div></article></div>
  <EmptyState v-else title="还没有符合条件的素材" text="在主图或视频页提交生成任务，完成后素材会自动出现在这里。" />
  <FormModal v-if="editor.form" v-bind="editor.form" :saving="editor.saving" :error="editor.error" @close="editor.close" @submit="editor.save" />
</template>
