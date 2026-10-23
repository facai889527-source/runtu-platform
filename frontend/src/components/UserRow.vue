<script setup>
import { roleLabel } from '../utils/userDirectory.js'
defineProps({user:{type:Object,required:true},selfId:String})
defineEmits(['manage'])
</script>
<template>
<li class="managed-user user-directory-row">
<div class="directory-identity">
<span class="directory-avatar" aria-hidden="true">{{user.username.slice(0,1).toUpperCase()}}</span>
<div>
<h3>{{user.username}} <span v-if="user.id===selfId" class="directory-self">我</span>
</h3>
<span class="directory-date">{{new Date(user.created_at).toLocaleDateString('zh-CN')}} 加入</span>
</div>
</div>
<span class="directory-role" :class="{'is-owner':user.role==='owner'}">{{roleLabel(user.role)}}</span>
<span class="directory-status" :class="{'is-disabled':!user.active}">
<i aria-hidden="true" />{{user.active?'已启用':'已禁用'}}</span>
<button class="directory-manage" :aria-label="`管理 ${user.username}`" @click="$emit('manage',user)">管理 <span aria-hidden="true">›</span>
</button>
</li>
</template>
