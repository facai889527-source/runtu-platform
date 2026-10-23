<script setup>
import { shallowRef,computed,useId,useTemplateRef,nextTick,onMounted,onUnmounted,watch } from 'vue'
const props=defineProps({modelValue:String,options:{type:Array,required:true},label:{type:String,required:true},disabled:Boolean})
const emit=defineEmits(['update:modelValue'])
const id=useId(),open=shallowRef(false),highlight=shallowRef(0),position=shallowRef({}),target=shallowRef(null),trigger=useTemplateRef('trigger'),popup=useTemplateRef('popup')
const selected=computed(()=>props.options.find(o=>o.value===props.modelValue)),activeId=computed(()=>open.value?`${id}-option-${highlight.value}`:undefined)
let letters='',timer
function place(){
 if(!open.value||!trigger.value)return
 const r=trigger.value.getBoundingClientRect(),width=Math.min(Math.max(r.width,180),innerWidth-16),below=innerHeight-r.bottom-12,above=r.top-12,up=below<150&&above>below,height=Math.min(248,Math.max(80,up?above:below))
 position.value={position:'fixed',left:`${Math.max(8,Math.min(r.left,innerWidth-width-8))}px`,width:`${width}px`,maxHeight:`${height}px`,...(up?{bottom:`${innerHeight-r.top+6}px`}:{top:`${r.bottom+6}px`})}
}
function show(){if(props.disabled||!props.options.length||trigger.value?.matches(':disabled'))return;open.value=true;highlight.value=Math.max(0,props.options.findIndex(o=>o.value===props.modelValue));place();reveal()}
function hide(){open.value=false;letters='';clearTimeout(timer)}
function reveal(){nextTick(()=>document.getElementById(`${id}-option-${highlight.value}`)?.scrollIntoView({block:'nearest'}))}
function choose(index){const option=props.options[index];if(option){emit('update:modelValue',option.value);hide();trigger.value?.focus()}}
function keyboard(e){
 if(props.disabled)return
 if(e.key==='Tab'){hide();return}
 if(e.key==='Escape'&&open.value){e.preventDefault();e.stopPropagation();hide();return}
 if(['ArrowDown','ArrowUp','Home','End','Enter',' '].includes(e.key)){
  e.preventDefault();e.stopPropagation()
  if(!open.value){show();return}
  if(e.key==='Enter'||e.key===' '){choose(highlight.value);return}
  highlight.value=e.key==='Home'?0:e.key==='End'?props.options.length-1:(highlight.value+(e.key==='ArrowUp'?-1:1)+props.options.length)%props.options.length;reveal()
 }else if(e.key.length===1&&!e.ctrlKey&&!e.metaKey){if(!open.value)show();letters+=e.key.toLowerCase();clearTimeout(timer);timer=setTimeout(()=>letters='',700);const i=props.options.findIndex(o=>o.label.toLowerCase().startsWith(letters));if(i>=0){highlight.value=i;reveal()}}
}
function outside(e){if(!trigger.value?.contains(e.target)&&!popup.value?.contains(e.target))hide()}
watch(()=>props.disabled,hide)
watch(()=>props.options,()=>{if(open.value){highlight.value=Math.max(0,props.options.findIndex(o=>o.value===props.modelValue));place()}})
onMounted(()=>{target.value=trigger.value.closest('dialog')||document.body;document.addEventListener('pointerdown',outside,true);window.addEventListener('resize',place);window.addEventListener('scroll',place,true)})
onUnmounted(()=>{clearTimeout(timer);document.removeEventListener('pointerdown',outside,true);window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true)})
</script>
<template>
<span class="account-select">
<button ref="trigger" type="button" class="account-select-trigger" role="combobox" aria-haspopup="listbox" :aria-label="label" :aria-expanded="open" :aria-controls="open?`${id}-listbox`:undefined" :aria-activedescendant="activeId" :disabled="disabled" @click="open?hide():show()" @keydown="keyboard"><span>{{selected?.label||'请选择'}}</span><svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m6 9 6 6 6-6" /></svg></button>
<Teleport v-if="target" :to="target"><div v-if="open" :id="`${id}-listbox`" ref="popup" class="account-select-popup" role="listbox" :aria-label="label" :style="position" @pointerdown.prevent><div v-for="(option,index) in options" :id="`${id}-option-${index}`" :key="option.value" role="option" :aria-selected="option.value===modelValue" class="account-select-option" :class="{'is-highlighted':highlight===index}" @pointermove="highlight=index" @click="choose(index)"><span>{{option.label}}<small v-if="option.description">{{option.description}}</small></span><span class="select-check" aria-hidden="true">{{option.value===modelValue?'✓':''}}</span></div></div></Teleport>
</span>
</template>
<style>
.account-select{display:block;min-width:0}.account-select-trigger{width:100%;justify-content:space-between;gap:20px;min-height:44px;background:#fff;border:1px solid #dce5e6;color:var(--ink);font-size:13px;box-shadow:0 1px 2px #183e3803}.account-select-trigger>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.account-select-trigger svg{flex-shrink:0;transition:transform 180ms}.account-select-trigger[aria-expanded=true]{border-color:#549b8f;box-shadow:0 0 0 3px #176e6610}.account-select-trigger[aria-expanded=true] svg{transform:rotate(180deg)}.account-select-popup{z-index:100;padding:6px;border:1px solid #dde7e5;border-radius:12px;background:white;box-shadow:0 10px 30px #1b3c3826;overflow:auto;overscroll-behavior:contain;animation:account-options-in 160ms ease-out;color:var(--ink)}.account-select-option{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:42px;padding:10px 12px;border-radius:7px;font-size:13px;cursor:pointer;line-height:1.6}.account-select-option.is-highlighted{background:#edf6f3}.account-select-option[aria-selected=true]{color:var(--accent);font-weight:600}.account-select-option small{display:block;font-weight:400;font-size:11px;color:var(--muted)}.select-check{width:16px;flex-shrink:0;color:var(--accent)}@keyframes account-options-in{from{opacity:0;transform:translateY(-3px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.account-select-popup{animation:none}.account-select-trigger svg{transition:none}}
</style>
