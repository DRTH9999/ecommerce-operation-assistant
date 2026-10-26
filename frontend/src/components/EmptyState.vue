<script setup lang="ts">
import { Sprout } from 'lucide-vue-next'
defineProps<{ title?: string; text?: string }>()
</script>
<template><div class="empty-state"><span class="empty-icon"><Sprout :size="30" /></span><h3>{{ title || '这里还没有内容' }}</h3><p>{{ text || '从第一个商品开始，让每一步运营都有迹可循。' }}</p><slot /></div></template>
