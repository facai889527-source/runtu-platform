import test from 'node:test'
import assert from 'node:assert/strict'
import { roleLabel,filterUserPage } from '../src/utils/userDirectory.js'
test('roles have exact public labels while identifiers stay unchanged',()=>{
 assert.deepEqual(['owner','admin','viewer'].map(roleLabel),['所有者','管理员','普通用户'])
})
test('directory filters intersect only the supplied page, with no fabricated totals',()=>{
 const rows=[{username:'alice',role:'owner',active:true},{username:'bob',role:'admin',active:false},{username:'carol',role:'viewer',active:true}]
 assert.deepEqual(filterUserPage(rows,'  ALI ','',''),[rows[0]])
 assert.deepEqual(filterUserPage(rows,'','admin','inactive'),[rows[1]])
 assert.deepEqual(filterUserPage(rows,'','viewer','active'),[rows[2]])
 assert.deepEqual(filterUserPage(rows,'alice','viewer',''),[])
 assert.deepEqual(filterUserPage([],'','',''),[])
 assert.equal(rows.length,3)
})
