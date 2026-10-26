<script setup lang="ts">
withDefaults(defineProps<{ category?: string; index?: number; image?: string; name?: string }>(), { category: '', index: 0, image: '', name: '商品图片' })
</script>
<template>
  <div class="product-art" :class="'art-' + (index % 4)" aria-hidden="true">
    <img v-if="image" :src="image" :alt="name" loading="lazy" referrerpolicy="no-referrer" />
    <svg v-else-if="category.includes('收纳')" viewBox="0 0 120 120"><path d="M18 48 62 30 104 48 60 68Z" fill="#c7a582"/><path d="M18 48 60 68 60 100 18 80Z" fill="#b18b68"/><path d="M60 68 104 48 104 80 60 100Z" fill="#997556"/><path d="M36 40 80 60M60 32 60 66" stroke="#e4cdb4" stroke-width="3"/></svg>
    <svg v-else-if="category.includes('箱包')" viewBox="0 0 120 120"><path d="M28 42 92 42 101 103 19 103Z" fill="#e1cfb1"/><path d="M43 45V31a17 17 0 0 1 34 0v14" fill="none" stroke="#b09a75" stroke-width="6"/><path d="M47 62H74V87H47Z" fill="#c5b08e"/><path d="M20 103H101" stroke="#b6a080" stroke-width="3"/></svg>
    <svg v-else-if="category.includes('浴巾')" viewBox="0 0 120 120"><rect x="23" y="37" width="75" height="23" rx="10" fill="#e4d4c5"/><rect x="18" y="58" width="80" height="24" rx="10" fill="#c3b3a6"/><rect x="25" y="80" width="73" height="22" rx="10" fill="#ddcdbd"/><path d="M35 47H86M31 70H85M37 91H85" stroke="#f1e6da" stroke-width="2" stroke-dasharray="2 3"/></svg>
    <svg v-else-if="category.includes('香氛')" viewBox="0 0 120 120"><path d="M50 48 42 13M59 46 64 9M68 47 82 16" stroke="#9b7a50" stroke-width="3"/><rect x="38" y="43" width="44" height="15" rx="4" fill="#493e31"/><rect x="32" y="56" width="56" height="49" rx="13" fill="#b28859"/><rect x="39" y="70" width="42" height="23" rx="1" fill="#ede6d4"/><text x="60" y="85" text-anchor="middle" font-size="7" fill="#6e5b40">QINGHE</text></svg>
    <svg v-else-if="category.includes('咖啡')" viewBox="0 0 120 120"><path d="M33 50Q57 36 78 50L87 95Q56 111 26 95Z" fill="#52605a"/><path d="M32 61 10 42 19 39 44 65" fill="#52605a"/><path d="M79 58Q114 52 97 87L84 90" fill="none" stroke="#45544d" stroke-width="7"/><ellipse cx="56" cy="49" rx="23" ry="6" fill="#3a4942"/><path d="M55 40V33" stroke="#3a4942" stroke-width="6"/></svg>
    <svg v-else viewBox="0 0 120 120"><ellipse cx="61" cy="105" rx="29" ry="5" fill="#5c7665" opacity=".13"/><rect x="39" y="26" width="44" height="77" rx="14" fill="#4b8673"/><rect x="43" y="17" width="36" height="16" rx="5" fill="#2c5145"/><rect x="46" y="38" width="4" height="48" rx="2" fill="#b2cdb7" opacity=".4"/><text x="61" y="68" text-anchor="middle" font-size="6" fill="#e4ecd9" letter-spacing="1">QINGHE</text></svg>
  </div>
</template>
