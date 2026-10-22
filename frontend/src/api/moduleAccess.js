import { sessionFetch } from './session.js'
import { ApiError } from './client.js'
import { securityHeaders } from './auth.js'
function item(row) {
  if (!row || Object.keys(row).length !== 4 || typeof row.module_id !== 'string' || !/^[a-z][a-z0-9_]{0,63}$/.test(row.module_id)
    || typeof row.name !== 'string' || typeof row.enabled !== 'boolean' || typeof row.granted !== 'boolean') throw new Error('模块授权数据格式异常。')
  return row
}
async function result(response) {
  if (!response.ok) throw new ApiError(response.status, {
    401:'登录已失效，请重新登录。',403:'没有模块授权权限，或目标不可授权。',404:'目标不存在，请刷新。',
    409:'授权状态已变化，请刷新后确认。',422:'模块授权请求格式无效。',503:'模块授权存储暂不可用，请确认迁移后重试。',
  }[response.status] || '模块授权请求失败，请重试。')
  return response.json()
}
async function page(path,after,signal,own=false) {
  const query=new URLSearchParams({limit:'20'})
  if(after!=null) query.set('after_module',after)
  const value=await result(await sessionFetch(`${path}?${query}`,{signal,credentials:'same-origin',headers:{Accept:'application/json'}}))
  if(!Array.isArray(value.items)||value.items.length>20) throw new Error('模块授权列表格式异常。')
  value.items.forEach((row,index)=>{item(row);if((own&&(!row.enabled||!row.granted))||(after!=null&&row.module_id<=after)||(index&&row.module_id<=value.items[index-1].module_id))throw new Error('模块授权顺序异常。')})
  if(!(value.next_after_module===null||(value.items.length===20&&value.next_after_module===value.items.at(-1).module_id)))throw new Error('模块授权分页异常。')
  return {items:value.items,next_after_module:value.next_after_module}
}
export const readUserModules=(id,after,signal)=>page(`/api/admin/users/${encodeURIComponent(id)}/modules`,after,signal)
export const readMyModules=(after,signal)=>page('/api/me/modules',after,signal,true)
export async function saveUserModule(id,moduleId,value,signal) {
  const headers=await securityHeaders(signal)
  const saved=item(await result(await sessionFetch(`/api/admin/users/${encodeURIComponent(id)}/modules/${encodeURIComponent(moduleId)}`,{method:'PUT',credentials:'same-origin',headers,signal,body:JSON.stringify(value)})))
  if(saved.module_id!==moduleId||saved.granted!==value.granted)throw new Error('授权保存结果无法确认，请刷新。')
  return saved
}
