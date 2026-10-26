<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { X, LoaderCircle } from 'lucide-vue-next'
import type { Row } from '../api'
export type Field = {
  key: string; label: string; type?: 'text' | 'number' | 'textarea' | 'select' | 'date' | 'password' | 'json' | 'lines';
  required?: boolean; min?: number; max?: number; step?: number; placeholder?: string;
  options?: { value: string | number; label: string }[]; hint?: string;
}
const props = defineProps<{ title: string; fields: Field[]; initial?: Row; saving?: boolean; error?: string; submitLabel?: string }>()
const emit = defineEmits<{ close: []; submit: [data: Row] }>()
const values = ref<Row>({})
const localError = ref('')
const modal = ref<HTMLElement>()
const previousFocus = document.activeElement as HTMLElement | null
watch(() => props.initial, () => {
  values.value = Object.fromEntries(props.fields.map(field => {
    const value = props.initial?.[field.key] ?? (field.type === 'number' ? 0 : '')
    return [field.key, field.type === 'json' && typeof value !== 'string' ? JSON.stringify(value, null, 2)
      : field.type === 'lines' && Array.isArray(value) ? value.join('\n') : value]
  }))
}, { immediate: true })

function submit() {
  const data: Row = {}
  localError.value = ''
  try {
    for (const field of props.fields) {
      const value = values.value[field.key]
      if (field.type === 'json') data[field.key] = JSON.parse(value || '{}')
      else if (field.type === 'lines') data[field.key] = String(value).split('\n').map(line => line.trim()).filter(Boolean)
      else if (field.type === 'number') data[field.key] = Number(value)
      else data[field.key] = value
    }
    emit('submit', data)
  } catch { localError.value = 'JSON 格式不正确，请检查括号、引号和逗号' }
}
function keyboard(event: KeyboardEvent) {
  if (event.key === 'Escape' && !props.saving) emit('close')
  if (event.key === 'Tab' && modal.value) {
    const elements = [...modal.value.querySelectorAll<HTMLElement>('button:not(:disabled), input, select, textarea')]
    const first = elements[0], last = elements[elements.length - 1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }
}
onMounted(() => { document.addEventListener('keydown', keyboard); modal.value?.querySelector<HTMLElement>('input,textarea,select')?.focus() })
onBeforeUnmount(() => { document.removeEventListener('keydown', keyboard); previousFocus?.focus() })
</script>
<template>
  <Teleport to="body">
    <div class="modal-backdrop" @click.self="!saving && emit('close')">
      <section ref="modal" class="modal" role="dialog" aria-modal="true" aria-labelledby="form-title">
        <div class="modal-header"><div><span class="eyebrow">QINGHE WORKSPACE</span><h2 id="form-title">{{ title }}</h2></div><button class="icon-button" aria-label="关闭" :disabled="saving" @click="emit('close')"><X :size="20" /></button></div>
        <form @submit.prevent="submit">
          <div class="form-fields">
            <label v-for="field in fields" :key="field.key" class="field" :class="{ wide: ['textarea','json','lines'].includes(field.type || '') }">
              <span>{{ field.label }}<b v-if="field.required"> *</b></span>
              <select v-if="field.type === 'select'" v-model="values[field.key]" :required="field.required"><option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option></select>
              <textarea v-else-if="['textarea','json','lines'].includes(field.type || '')" v-model="values[field.key]" :required="field.required" :placeholder="field.placeholder" :rows="field.type === 'json' ? 5 : 3" :class="{ mono: field.type === 'json' }"></textarea>
              <input v-else v-model="values[field.key]" :type="field.type || 'text'" :min="field.min" :max="field.max" :step="field.step ?? (field.type === 'number' ? 'any' : undefined)" :required="field.required" :placeholder="field.placeholder" />
              <small v-if="field.hint">{{ field.hint }}</small>
            </label>
          </div>
          <p v-if="localError || error" class="form-error" role="alert">{{ localError || error }}</p>
          <div class="modal-footer"><button type="button" class="button secondary" :disabled="saving" @click="emit('close')">取消</button><button class="button primary" :disabled="saving"><LoaderCircle v-if="saving" :size="16" class="spin" />{{ saving ? '正在保存…' : (submitLabel || '保存') }}</button></div>
        </form>
      </section>
    </div>
  </Teleport>
</template>
