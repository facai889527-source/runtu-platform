export const roleLabel = role => ({owner:'所有者',admin:'管理员',viewer:'普通用户'})[role] || '未知角色'
export function filterUserPage(items, query, role, state) {
 const term=query.trim().toLowerCase()
 return items.filter(user=>user.username.toLowerCase().includes(term)&&(!role||user.role===role)&&(!state||user.active===(state==='active')))
}
