<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Sprout, ArrowRight, LoaderCircle, Check } from 'lucide-vue-next'
import { api, setSession } from '../api'
const username = ref('admin'), password = ref(''), error = ref(''), busy = ref(false), demoEnabled = ref(false)
const router = useRouter(), route = useRoute()
onMounted(async () => { try { demoEnabled.value = (await api('/api/health')).demo_enabled } catch { error.value = '无法连接后端，请先启动项目服务' } })
async function login() {
  busy.value = true; error.value = ''
  try {
    const result = await api('/auth/login', 'POST', { username: username.value, password: password.value })
    setSession(result.access_token, result.user)
    const target = String(route.query.redirect || '/')
    await router.push(target.startsWith('/') && !target.startsWith('//') ? target : '/')
  } catch (err) { error.value = (err as Error).message }
  finally { busy.value = false }
}
</script>
<template>
  <div class="login-page"><div class="login-story"><a class="brand" href="/"><span class="brand-mark"><Sprout :size="27" /></span><span>青禾<span class="brand-sub">电商运营助手</span></span></a><div class="login-message"><span class="eyebrow">GOOD PRODUCTS. BETTER GROWTH.</span><h1>每一件好商品，<br />都值得好好经营。</h1><p>从商品洞察，到创意与复盘。<br />让繁杂的运营，变成清晰的下一步。</p><div class="login-checks"><span><Check :size="16" /> 一条完整的单品运营链路</span><span><Check :size="16" /> 每次决策，都有数据与记录</span><span><Check :size="16" /> 为小团队准备的日常工作台</span></div></div><svg class="login-plant" viewBox="0 0 300 330" aria-hidden="true"><path d="M146 313Q173 211 145 97" fill="none" stroke="#75997b" stroke-width="4"/><path d="M151 213Q33 211 40 115Q156 116 151 213Z" fill="#b2c6a8"/><path d="M157 163Q254 173 262 60Q158 62 157 163Z" fill="#90b096"/><path d="M147 105Q69 85 100 12Q173 39 147 105Z" fill="#ced7b7"/><path d="M155 260Q242 275 270 188Q178 175 155 260Z" fill="#c5d1ad"/></svg><span class="login-copyright">QINGHE WORKSPACE © 2026</span></div>
    <div class="login-form-wrap"><form class="login-form" @submit.prevent="login"><span class="eyebrow">WELCOME BACK</span><h2>欢迎回到青禾</h2><p>登录工作台，继续经营你的好商品。</p><label class="field"><span>用户名</span><input v-model="username" autocomplete="username" required placeholder="请输入用户名" /></label><label class="field"><span>密码</span><input v-model="password" type="password" autocomplete="current-password" required placeholder="请输入密码" /></label><p v-if="error" class="form-error" role="alert">{{ error }}</p><button class="button primary login-button" :disabled="busy"><LoaderCircle v-if="busy" :size="18" class="spin" />{{ busy ? '正在登录…' : '进入工作台' }}<ArrowRight :size="18" /></button><div v-if="demoEnabled" class="demo-credentials"><strong>本地演示环境</strong><p>初始管理员：admin / Admin@123456</p><small>若已配置或修改管理员密码，请使用实际密码。</small></div><p class="login-footnote">有据可循，有序向前。</p></form></div>
  </div>
</template>
