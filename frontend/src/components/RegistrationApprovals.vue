<script setup>
import { shallowRef,computed,watch,onUnmounted } from 'vue'
import { readApplications } from '../api/registration.js'
import { useResource } from '../composables/useResource.js'
import RegistrationReview from './RegistrationReview.vue'
import AccountSelect from './AccountSelect.vue'
const states=[{value:'pending',label:'待审核'},{value:'rejected',label:'已拒绝'}]
const props=defineProps({state:{type:String,default:'pending'}}),emit=defineEmits(['reviewed','update:state'])
const page=useResource(readApplications),after=shallowRef(null),previous=shallowRef([]),query=shallowRef(''),selected=shallowRef(null)
const rows=computed(()=>page.data.value?.items.filter(row=>row.username.toLowerCase().includes(query.value.trim().toLowerCase()))||[])
function load(){page.load(props.state,after.value)}
function first(){after.value=null;previous.value=[];query.value='';load()}
function next(){const cursor=page.data.value?.next_after_username;if(cursor!=null){previous.value=[...previous.value,after.value];after.value=cursor;query.value='';load()}}
function back(){const pages=[...previous.value];if(pages.length){after.value=pages.pop();previous.value=pages;query.value='';load()}}
function reviewed(state){selected.value=null;emit('reviewed',state);load()}
watch(()=>props.state,()=>{selected.value=null;first()},{immediate:true})
onUnmounted(page.cancel)
</script>
<template>
<section class="registration-directory" aria-label="注册申请目录">
<div class="review-toolbar"><label class="directory-search"><span class="sr-only">搜索本页申请人</span><span aria-hidden="true">⌕</span><input v-model="query" type="search" placeholder="搜索本页申请人…" /></label><AccountSelect :model-value="state" label="筛选申请状态" :options="states" @update:model-value="emit('update:state',$event)" /><button class="directory-refresh" :disabled="page.pending.value" @click="load">刷新申请</button></div>
<div class="directory-caption"><span>{{state==='pending'?'待审核申请尚不能登录，批准后才会进入用户账户。':'已拒绝申请不能登录，不计入用户账户。'}}</span><span v-if="page.data.value">本页 {{page.data.value.items.length}} 份</span></div>
<p v-if="page.pending.value" class="directory-state" role="status">正在加载注册申请…</p><div v-else-if="page.error.value" class="directory-state" role="alert"><p>{{page.error.value.message}}</p><button @click="load">重试申请查询</button></div>
<template v-else-if="page.data.value"><div v-if="!rows.length" class="directory-state"><span class="directory-empty-symbol" aria-hidden="true">✓</span><h3>{{query?'本页没有匹配的申请':state==='pending'?'暂无待审核申请':'暂无已拒绝申请'}}</h3><p>{{query?'搜索仅筛选本页，清除条件后重试。':state==='pending'?'新的注册申请会显示在这里。':'完成的拒绝决定会保留在此处。'}}</p><button v-if="query" @click="query=''">清除搜索</button></div>
<ul v-else class="application-items"><li v-for="item in rows" :key="item.id" class="application-row"><div class="directory-identity"><span class="directory-avatar" aria-hidden="true">{{item.username.slice(0,1).toUpperCase()}}</span><div><h3>{{item.username}}</h3><small>注册申请 · 尚未获准登录</small></div></div><span class="application-state" :class="item.state">{{state==='pending'?'待审核':'已拒绝'}}</span><button class="directory-manage" :aria-label="`查看申请 ${item.username}`" @click="selected=item.id">{{state==='pending'?'审核':'查看'}} <span aria-hidden="true">›</span></button></li></ul></template>
<footer class="directory-footer"><p>仅所有者可审核；申请与账户分开计数。</p><nav v-if="previous.length||page.data.value?.next_after_username!=null" class="user-pagination" aria-label="申请分页"><button :disabled="page.pending.value||!previous.length" @click="back">上一页申请</button><span>第 {{previous.length+1}} 页</span><button :disabled="page.pending.value||page.data.value?.next_after_username==null" @click="next">下一页申请</button></nav></footer>
<RegistrationReview v-if="selected" :key="selected" :application-id="selected" @close="selected=null" @reviewed="reviewed" />
</section>
</template>
<style>
.review-toolbar>.account-select{width:150px}.review-toolbar{display:flex;gap:12px;align-items:center;padding:20px 0 14px}.registration-directory .directory-caption{padding-inline:0}.application-row{display:grid;grid-template-columns:minmax(0,1fr) 110px 72px;align-items:center;gap:20px;padding:20px 14px;border-bottom:1px solid #e4e9ed}.application-row .directory-identity small{font-size:12px;color:var(--muted)}.application-state{display:inline-flex;align-items:center;gap:6px;font-size:11px;justify-self:start;padding:4px 9px;border-radius:20px;background:#f2f4f6;color:#657481}.application-state.pending{color:#95601c;background:#fbf2e2}.application-state.approved{background:#eaf5f1;color:var(--accent)}.directory-empty-symbol{display:grid;place-items:center;margin:0 auto 16px;width:46px;height:46px;border-radius:50%;background:#eaf3ef;color:var(--accent)}@media(max-width:760px){.application-row{grid-template-columns:minmax(0,1fr) auto;gap:12px;padding:18px 4px}.application-row .application-state{grid-row:2;padding-left:50px;background:transparent}.application-row .directory-manage{grid-row:1}.review-toolbar>.account-select{width:150px}.review-toolbar{padding-top:16px;display:grid;grid-template-columns:minmax(0,1fr) auto}.review-toolbar .directory-search{grid-column:1/-1}.review-toolbar>.account-select{width:auto}.registration-directory .directory-footer{padding-inline:0}}
</style>
