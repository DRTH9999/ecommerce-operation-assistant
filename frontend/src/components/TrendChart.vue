<script setup lang="ts">
import { computed, ref } from 'vue'
import { money, time, type Row } from '../api'
const props = defineProps<{ data: Row[] }>()
const hover = ref<number | null>(null)
const max = computed(() => Math.max(...props.data.map(d => d.revenue), 100))
const points = computed(() => props.data.map((d, i) => `${50 + i * (650 / Math.max(1, props.data.length-1))},${185 - d.revenue / max.value * 145}`).join(' '))
const spendPoints = computed(() => props.data.map((d, i) => `${50 + i * (650 / Math.max(1, props.data.length-1))},${185 - d.spend / max.value * 145}`).join(' '))
</script>
<template>
  <div class="trend-chart">
    <div v-if="hover !== null && data[hover]" class="chart-tooltip">{{ data[hover]?.date }} · 收入 {{ money(data[hover]?.revenue) }} · 花费 {{ money(data[hover]?.spend) }}</div>
    <svg viewBox="0 0 730 220" role="img" aria-label="最近十四天日粒度收入与花费趋势">
      <defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#398f7c" stop-opacity=".15"/><stop offset="1" stop-color="#398f7c" stop-opacity="0"/></linearGradient></defs>
      <g v-for="i in 4" :key="i"><line x1="50" x2="710" :y1="40 + (i-1)*48.3" :y2="40 + (i-1)*48.3" stroke="#e9ede9" stroke-dasharray="3 4" /><text x="0" :y="44 + (i-1)*48.3" fill="#8b978f" font-size="10">{{ Math.round(max * (1-(i-1)/3)) }}</text></g>
      <polygon :points="'50,185 ' + points + ' 700,185'" fill="url(#chart-fill)" />
      <polyline :points="points" fill="none" stroke="#308872" stroke-width="2.8" stroke-linejoin="round" stroke-linecap="round" />
      <polyline :points="spendPoints" fill="none" stroke="#cba66d" stroke-width="2" stroke-dasharray="5 5" />
      <g v-for="(d,i) in data" :key="d.date"><rect :x="30+i*(650/Math.max(1,data.length-1))" y="10" width="40" height="190" fill="transparent" tabindex="0" :aria-label="`${d.date} 收入 ${money(d.revenue)} 花费 ${money(d.spend)}`" @mouseenter="hover=i" @mouseleave="hover=null" @focus="hover=i" @blur="hover=null"/><text v-if="i % 3 === 0 || i === data.length-1" :x="50+i*(650/Math.max(1,data.length-1))" y="212" text-anchor="middle" font-size="10" fill="#8b978f">{{ d.date.slice(5).replace('-','/') }}</text></g>
    </svg>
    <p class="chart-note">趋势展示单日记录；跨日汇总记录仅计入周期合计。</p>
  </div>
</template>
