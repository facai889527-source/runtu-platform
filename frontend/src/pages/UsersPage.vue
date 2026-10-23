<script setup>
import { computed,shallowRef,watch,onUnmounted } from 'vue'
import { useResource } from '../composables/useResource.js'
import { readUsers } from '../api/users.js'
import { roleOptions,filterUserPage } from '../utils/userDirectory.js'
import UserCreate from '../components/UserCreate.vue'
import UserRow from '../components/UserRow.vue'
import UserManage from '../components/UserManage.vue'
import AccountSelect from '../components/AccountSelect.vue'
import RegistrationApprovals from '../components/RegistrationApprovals.vue'
const props=defineProps({access:Object,selfId:String})
const mode=shallowRef('accounts'),reviewState=shallowRef('pending')
const accountStates=[{value:'',label:'全部状态'},{value:'active',label:'已启用'},{value:'inactive',label:'已禁用'}],roles=[{value:'',label:'全部角色'},...roleOptions]
const allowed=computed(()=>Boolean(props.access?.data.value?.permissions.includes('users.manage')))
const users=useResource(readUsers),after=shallowRef(null),previous=shallowRef([]),creating=shallowRef(false),selected=shallowRef(null),query=shallowRef(''),role=shallowRef(''),state=shallowRef(''),toast=shallowRef('')
const filtered=computed(()=>filterUserPage(users.data.value?.items||[],query.value,role.value,state.value)),filtering=computed(()=>!!(query.value||role.value||state.value))
function centerTab(event){if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();mode.value=event.key==='Home'?'accounts':event.key==='End'?'reviews':mode.value==='accounts'?'reviews':'accounts';event.currentTarget.parentElement.querySelector('#users-'+mode.value+'-tab').focus()}}
let toastTimer
function notify(message){toast.value=message;clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.value='',6000)}
function load(){users.load(after.value)}
function resetFilters(){query.value='';role.value='';state.value=''}
function first(){after.value=null;previous.value=[];resetFilters();load()}
function next(){const cursor=users.data.value?.next_after_username;if(cursor!=null){previous.value=[...previous.value,after.value];after.value=cursor;resetFilters();load()}}
function back(){if(previous.value.length){const pages=[...previous.value];after.value=pages.pop();previous.value=pages;resetFilters();load()}}
function created(){creating.value=false;notify('用户已创建。请通过安全渠道交接初始密码。');if(mode.value==='accounts')first();else mode.value='accounts'}
function updated(){notify('账户变更已保存。');load()}
watch(()=>[allowed.value,props.selfId,mode.value],()=>{users.cancel();users.data.value=null;users.error.value=null;creating.value=false;selected.value=null;after.value=null;previous.value=[];resetFilters();if(allowed.value&&mode.value==='accounts')load()},{immediate:true})
onUnmounted(()=>{users.cancel();clearTimeout(toastTimer)})
</script>
<template>
<div class="users-page">
<p v-if="access?.pending.value && !access?.data.value" role="status">正在确认用户管理权限…</p>
<div v-else-if="access?.error.value" class="directory-state" role="status">用户管理权限暂无法确认。<button @click="access.load()">重试权限查询</button>
</div>
<p v-else-if="!allowed" class="directory-state" role="status">当前身份没有用户管理权限。</p>
<template v-else>
<header class="directory-intro">
<div>
<h2>账户与访问</h2>
<p>成员账户、工具权限与注册审核，统一管理。</p>
</div>
<button class="user-primary directory-create" @click="creating=true">
<span aria-hidden="true">＋</span> 新建用户</button>
</header>
<div class="account-center-tabs" role="tablist" aria-label="账户中心分类"><button id="users-accounts-tab" role="tab" :aria-selected="mode==='accounts'" :tabindex="mode==='accounts'?0:-1" aria-controls="users-accounts-panel" @click="mode='accounts'" @keydown="centerTab">用户账户</button><button id="users-reviews-tab" role="tab" :aria-selected="mode==='reviews'" :tabindex="mode==='reviews'?0:-1" aria-controls="users-reviews-panel" @click="mode='reviews'" @keydown="centerTab">注册审核</button></div>
<section v-if="mode==='reviews'" id="users-reviews-panel" role="tabpanel" aria-labelledby="users-reviews-tab" tabindex="0"><RegistrationApprovals v-model:state="reviewState" @reviewed="notify($event==='approved'?'申请已批准，普通用户账户已启用。':'申请已拒绝，申请人仍无法登录。')" /></section>
<section v-else id="users-accounts-panel" role="tabpanel" aria-labelledby="users-accounts-tab" tabindex="0" class="user-directory" aria-label="用户目录">
<div class="directory-toolbar">
<label class="directory-search">
<span class="sr-only">搜索本页用户名</span>
<span aria-hidden="true">⌕</span>
<input v-model="query" type="search" placeholder="搜索本页用户名…" />
</label>
<AccountSelect v-model="role" label="筛选本页角色" :options="roles" />
<AccountSelect v-model="state" label="筛选本页状态" :options="accountStates" />
<button class="directory-refresh" :disabled="users.pending.value" @click="load">刷新</button>
</div>
<div class="directory-caption">
<span>按用户名排序 · 每页最多 20 位</span>
<span v-if="users.data.value">本页 {{users.data.value.items.length}} 位<span v-if="filtering"> · 匹配 {{filtered.length}} 位</span>
</span>
</div>
<div class="directory-columns" aria-hidden="true">
<span>账户</span>
<span>角色</span>
<span>状态</span>
<span>操作</span>
</div>
<p v-if="users.pending.value" class="directory-state" role="status">正在加载用户目录…</p>
<div v-else-if="users.error.value" class="directory-state" role="alert">
<p>{{users.error.value.message}}</p>
<button @click="load">重试加载</button>
</div>
<template v-else-if="users.data.value">
<div v-if="!filtered.length" class="directory-state">
<h3>{{filtering?'本页没有匹配的账户':'此页暂无用户'}}</h3>
<p>{{filtering?'搜索和筛选仅作用于当前页，可清除条件或翻页查看。':'创建一个账户，邀请成员使用平台工具。'}}</p>
<button v-if="filtering" @click="resetFilters">清除筛选</button>
</div>
<ul v-else class="user-items">
<UserRow v-for="user in filtered" :key="user.id" :user="user" :self-id="selfId" @manage="selected=$event" />
</ul>
</template>
<footer class="directory-footer">
<p>角色或启停变更会撤销该账户已有会话。</p>
<nav v-if="previous.length||users.data.value?.next_after_username!=null" class="user-pagination" aria-label="用户分页">
<button :disabled="users.pending.value||!previous.length" @click="back">上一页</button>
<span>第 {{previous.length+1}} 页</span>
<button :disabled="users.pending.value||users.data.value?.next_after_username==null" @click="next">下一页</button>
</nav>
</footer>
</section>
<UserCreate v-if="creating" @close="creating=false" @created="created" />
<UserManage v-if="selected" :key="selected.id" :user="selected" :self-id="selfId" @close="selected=null" @updated="updated" />
</template>
<div v-if="toast" class="directory-toast" role="status">
<span aria-hidden="true">✓</span>{{toast}}<button aria-label="关闭提示" @click="toast=''">×</button>
</div>
</div>
</template>
<style>
.users-page{min-width:0}.directory-intro{display:flex;align-items:center;justify-content:space-between;gap:20px;margin:12px 0 24px}.directory-intro h2{font-size:22px;letter-spacing:-.03em}.directory-intro p{font-size:13px;color:var(--muted);margin:6px 0 0}.directory-create{flex-shrink:0}.directory-create>span{font-size:20px;line-height:1}.user-directory{background:transparent;border:0;border-radius:0;overflow:visible}.directory-toolbar{display:flex;align-items:center;gap:10px;padding:22px 0 14px}.directory-toolbar label{min-width:0}.directory-search{position:relative;flex:1}.directory-search>span[aria-hidden]{position:absolute;left:14px;top:8px;font-size:24px;color:var(--muted)}.directory-search input{width:100%;padding-left:42px;min-height:44px;background:#fff;border-color:#e2e8ed}.directory-toolbar>.account-select{width:140px}.directory-refresh{border:0;color:var(--muted)}.directory-caption{display:flex;justify-content:space-between;gap:16px;padding:0 0 18px;color:var(--muted);font-size:11px;line-height:1.8}.directory-columns,.user-directory-row{display:grid;grid-template-columns:minmax(0,1fr) 110px 110px 72px;align-items:center;gap:20px;padding:0 14px}.directory-columns{min-height:38px;background:transparent;border:0;border-bottom:1px solid #dbe3e7;font-size:11px;color:var(--muted)}.user-directory-row{min-height:86px;border-bottom:1px solid #e1e7eb;transition:background 160ms,box-shadow 160ms;border-radius:0}.user-directory-row:hover{background:#fff;box-shadow:0 3px 14px #233f3905}.directory-identity{display:flex;align-items:center;gap:12px;min-width:0}.directory-identity>div{min-width:0}.directory-identity h3{font-size:14px;font-weight:600;margin:0 0 5px;overflow-wrap:anywhere}.directory-avatar{display:grid;place-items:center;width:38px;height:38px;background:#eff5f3;border:1px solid #e1ede8;color:#39776b;font-size:14px;border-radius:50%;flex-shrink:0}.directory-date{font-size:11px;color:var(--muted)}.directory-self{font-size:10px;padding:2px 5px;background:#edf3f6;color:#60717c;margin-left:5px;border-radius:4px}.directory-role{font-size:12px;color:#5a6879}.directory-role.is-owner{color:var(--accent);font-weight:550}.directory-status{display:flex;align-items:center;gap:7px;font-size:12px;color:#477263}.directory-status i{width:6px;height:6px;border-radius:50%;background:#3e947e}.directory-status.is-disabled{color:var(--muted)}.directory-status.is-disabled i{background:#9ca8b2}.directory-manage{padding:8px 0;min-height:44px;border:0;background:transparent;color:var(--accent);font-size:12px;justify-content:flex-start;gap:12px}.directory-manage:hover{background:transparent;text-decoration:underline}.directory-footer{padding:20px 0;display:flex;gap:20px;align-items:center;justify-content:space-between}.directory-footer p{font-size:11px;color:var(--muted);margin:0}.user-pagination{display:flex;gap:10px;align-items:center}.user-pagination button{font-size:12px;min-height:36px;padding:7px 10px}.user-pagination>span{font-size:11px;color:var(--muted);white-space:nowrap}.directory-state{padding:40px 24px;text-align:center;color:var(--muted)}.directory-state p{font-size:13px}.directory-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:30;display:flex;align-items:center;gap:12px;width:max-content;max-width:calc(100% - 24px);background:#fff;border:1px solid #cce0d8;border-radius:10px;box-shadow:0 8px 28px #173b3e20;padding:10px 12px 10px 18px;font-size:13px}.directory-toast>span{color:var(--accent);font-weight:700}.directory-toast button{border:0;padding:0;width:36px;min-height:36px;color:var(--muted)}.account-center-tabs{display:flex;gap:28px;border-bottom:1px solid #dce4e8}.account-center-tabs button{padding:14px 0;border:0;border-bottom:2px solid transparent;border-radius:0;background:transparent;color:var(--muted);font-size:14px}.account-center-tabs button[aria-selected=true]{border-bottom-color:var(--accent);color:var(--accent);font-weight:600}.registration-review-link{font-size:13px;color:var(--muted);margin:0}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
@media(max-width:760px){.directory-intro{align-items:flex-start;gap:12px}.directory-intro h2{font-size:20px}.directory-intro p{max-width:160px;font-size:12px}.directory-create{padding:10px 12px;font-size:12px}.directory-toolbar{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) 44px;gap:8px;padding:18px 0 14px}.directory-search{grid-column:1/-1}.directory-toolbar>.account-select{width:auto}.directory-toolbar .account-select-trigger{font-size:12px;padding:10px}.directory-refresh{padding:0;font-size:12px}.directory-caption{padding:0 0 14px;gap:12px;font-size:10px;flex-wrap:wrap}.directory-columns{display:none}.user-directory-row{grid-template-columns:minmax(0,1fr) auto;gap:10px;padding:18px 4px;min-height:110px}.directory-identity{grid-column:1;grid-row:1}.directory-manage{grid-column:2;grid-row:1;padding-left:8px}.directory-role{grid-column:1;grid-row:2;padding-left:50px;font-size:11px}.directory-status{grid-column:2;grid-row:2;font-size:11px}.directory-footer{padding:18px 0;flex-direction:column;align-items:flex-start;gap:14px}.user-pagination{width:100%;justify-content:space-between}.directory-avatar{width:36px;height:36px}.directory-identity h3{font-size:13px}}@media(prefers-reduced-motion:reduce){.user-directory-row{transition:none}}
</style>
