<script setup lang="ts">
import { labels } from '../api'
defineProps<{ value: string; label?: string }>()
</script>
<template><span class="badge" :class="'status-' + value"><i></i>{{ label || labels[value] || value }}</span></template>
