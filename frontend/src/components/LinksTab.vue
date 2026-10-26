<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Sparkles, Copy, ArrowUpRight, Link2, MousePointer2 } from 'lucide-vue-next'
import { api, canWrite, notify, time, type Row } from '../api'
import { useAction, useEditor } from '../forms'
import FormModal from './FormModal.vue'
import EmptyState from './EmptyState.vue'
const props=defineProps<{product:Row}>(),emit=defineEmits<{changed:[]}>(),suggestions=ref<Row[]>([])
const editor=useEditor(()=>emit('changed')),action=useAction(()=>emit('changed'))
function create(suggestion?:Row) {
  editor.open('创建推广追踪链接',[{key:'link_name',label:'链接名称',required:true},{key:'target_url',label:'目标商品链接',required:true},
    {key:'scene_text',label:'使用场景'},{key:'utm_source',label:'来源 utm_source'},
    {key:'utm_medium',label:'媒介 utm_medium'},{key:'utm_campaign',label:'活动 utm_campaign'}],
    {link_name:suggestion?.link_name || props.product.name+' · 推广入口',target_url:suggestion?.target_url || props.product.product_url,
      scene_text:suggestion?.scene_text || '',...suggestion?.utm_json},'/products/'+props.product.id+'/promotion-links','POST',
    data=>({link_name:data.link_name,target_url:data.target_url,scene_text:data.scene_text,
      utm_json:Object.fromEntries(['utm_source','utm_medium','utm_campaign'].filter(k=>data[k]).map(k=>[k,data[k]]))}))
}
async function copy(code:string) { try { await navigator.clipboard.writeText(location.origin+'/api/v1/r/'+code);notify('追踪链接已复制') } catch { notify('复制失败，请从链接地址栏复制',true) } }
</script>
<template>
  <div class="tab-intro"><div><h2>每个入口，都有迹可循</h2><p>为不同素材和场景建立推广入口，记录经过本系统跳转的点击。</p></div><div class="inline-actions"><button v-if="canWrite()" class="button secondary" :disabled="!!action.busy" @click="action.run('suggest',async()=>{suggestions=(await api('/products/'+product.id+'/promotion-links/generate','POST')).suggestions},'链接建议已生成')"><Sparkles :size="15" />生成链接建议</button><button v-if="canWrite()" class="button primary" @click="create()"><Plus :size="16" />创建链接</button></div></div>
  <div v-if="suggestions.length" class="suggestion-grid"><article v-for="s in suggestions" :key="s.link_name" class="suggestion-card"><Link2 :size="21" /><h3>{{ s.scene_text }}</h3><p>{{ s.link_name }}</p><button class="text-button" @click="create(s)">采用建议 <Plus :size="13" /></button></article></div>
  <section v-if="product.links.length" class="panel"><div class="table-wrap"><table><thead><tr><th>链接名称 / 场景</th><th>追踪参数</th><th>点击次数</th><th>创建时间</th><th>操作</th></tr></thead><tbody><tr v-for="link in product.links" :key="link.id"><td><strong>{{ link.link_name }}</strong><small class="block muted">{{ link.scene_text }}</small><a :href="link.target_url" target="_blank" rel="noopener noreferrer" class="small table-link break-all">{{ link.target_url }}</a></td><td><div v-for="(value,key) in link.utm_json" :key="key" class="tracking-param"><span>{{ key }}</span>{{ value }}</div><code class="tracking-code">{{ link.tracking_code }}</code></td><td class="numeric">{{ link.click_count }}</td><td class="muted small">{{ time(link.created_at) }}</td><td><div class="inline-actions"><button class="text-button" @click="copy(link.tracking_code)"><Copy :size="14" />复制</button><a :href="'/api/v1/r/'+link.tracking_code" target="_blank" rel="noopener noreferrer" class="text-button">访问 <ArrowUpRight :size="14" /></a></div></td></tr></tbody></table></div></section><EmptyState v-else title="给每个推广入口起个名字" text="创建带追踪参数的链接，区分素材、媒介和运营场景。" />
  <FormModal v-if="editor.form" v-bind="editor.form" :saving="editor.saving" :error="editor.error" @close="editor.close" @submit="editor.save" />
</template>
