import { spawn } from 'node:child_process'
import { writeFile, mkdir } from 'node:fs/promises'
import assert from 'node:assert/strict'
import path from 'node:path'
const output = path.resolve('.git/codex-coordination/ui11')
await mkdir(output, { recursive: true })
let occupied = false
try { occupied = (await fetch('http://127.0.0.1:9229/json')).ok } catch { /* Port is free. */ }
assert.equal(occupied, false, '9229 is already occupied; refusing to attach to another browser')
const child = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new','--remote-debugging-port=9229',`--user-data-dir=${output}/chrome-profile`,'--no-first-run','--no-default-browser-check','about:blank'], {windowsHide:true,stdio:'ignore'})
let socket
try {
  let pages
  for (let i=0;i<60;i++) { try { pages=await (await fetch('http://127.0.0.1:9229/json')).json();break } catch { await new Promise(r=>setTimeout(r,250)) } }
  assert.ok(pages?.length,'Chrome CDP available')
  socket = new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl)
  await new Promise(r=>socket.addEventListener('open',r,{once:true}))
  let loads=0; let seq=0; const waiting=new Map(), errors=[]; let mode='real'
  socket.addEventListener('message', async(event)=>{
    const msg=JSON.parse(event.data)
    if(msg.id){const promise=waiting.get(msg.id);waiting.delete(msg.id);msg.error?promise.reject(new Error(JSON.stringify(msg.error))):promise.resolve(msg.result)}
    if(msg.method==='Page.loadEventFired') loads++
    if(msg.method==='Runtime.exceptionThrown') errors.push(msg.params.exceptionDetails)
    if(msg.method==='Fetch.requestPaused') {
      const {requestId,request}=msg.params
      const pathname=new URL(request.url).pathname
      if(mode==='real') { await send('Fetch.continueRequest',{requestId}); return }
      if(mode==='offline') { await send('Fetch.failRequest',{requestId,errorReason:'ConnectionFailed'}); return }
      let code=200, body
      if(pathname==='/api/health') {
        code=mode==='degraded'?503:200
        body={status:code===503?'degraded':'ok',platform:'Runtu browser fixture',database:code===503?'unavailable':'ready'}
      } else if(pathname==='/api/modules') body=mode==='empty'?[]:[{id:'disabled_test',name:'禁用测试模块',version:'1.0',description:'浏览器测试夹具',category:'tools',status:'disabled',capabilities:['inspect']}]
      else { code=mode==='404'?404:mode==='503'?503:200; body={id:'disabled_test',name:'禁用测试模块',version:'1.0',description:'浏览器测试夹具',category:'tools',status:'disabled',capabilities:['inspect'],public_config:{show_in_navigation:false,refresh_interval_seconds:30}} }
      if(mode==='long') {
        if(Array.isArray(body)) { body[0].name='非常长的模块名称'.repeat(8);body[0].capabilities=['very_long_capability_'.repeat(12)] }
        else if(pathname.startsWith('/api/modules/')) { body.name='非常长的模块名称'.repeat(8);body.capabilities=['very_long_capability_'.repeat(12)] }
      }
      if(mode==='loading') await new Promise(r=>setTimeout(r,600))
      await send('Fetch.fulfillRequest',{requestId,responseCode:code,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify(body)).toString('base64')})
    }
  })
  function send(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;waiting.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}))})}
  async function loadDocument(method, params={}) {
    const before=loads; await send(method, params)
    for(let i=0;i<100;i++) { if(loads>before)return; await new Promise(r=>setTimeout(r,100)) }
    throw new Error('Document load timed out')
  }
  async function evaluate(expression){const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value}
  async function until(expression){for(let i=0;i<100;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100))}throw new Error('Timed out: '+expression)}
  async function click(text){await evaluate(`(()=>{const el=[...document.querySelectorAll('button, a[href]')].find(e=>(e.textContent.trim()===${JSON.stringify(text)}||e.getAttribute('aria-label')===${JSON.stringify(text)})&&e.getClientRects().length);if(!el)throw new Error('Missing button');el.click()})()`)}
  async function screenshot(name){const result=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});await writeFile(path.join(output,name+'.png'),Buffer.from(result.data,'base64'))}
  await send('Runtime.enable');await send('Page.enable')
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false})
  await loadDocument('Page.navigate',{url:'http://127.0.0.1:5173'})
  await until(`document.body.innerText.includes('未配置数据库') && document.body.innerText.includes('演示模块')`)
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true)
  await screenshot('desktop-dashboard')
  await click('折叠侧栏'); await until("document.querySelector('.shell').classList.contains('collapsed')")
  await click('展开侧栏')
  await click('模块管理');await screenshot('desktop-modules');await click('演示模块')
  await until(`document.body.innerText.includes('公开配置') && document.body.innerText.includes('导航展示偏好')`)
  await screenshot('desktop-detail')
  await click('返回模块目录')
  await evaluate(`(()=>{const el=document.querySelector('input');el.value='no_such_module';el.dispatchEvent(new Event('input',{bubbles:true}))})()`)
  await until(`document.body.innerText.includes('没有匹配的模块')`)
  await click('清除筛选')
  await evaluate(`(()=>{const el=document.querySelector('select');el.value='disabled';el.dispatchEvent(new Event('change',{bubbles:true}))})()`)
  await until(`document.body.innerText.includes('找到 0 个模块')`)
  await click('重置筛选');await click('设置')
  await until(`document.body.innerText.includes('管理配置尚未开放')`)
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true})
  await new Promise(r=>setTimeout(r,300)); await click('打开导航')
  await until(`document.querySelector('[role=dialog]') && document.querySelector('.workspace').inert`)
  assert.equal(await evaluate(`document.querySelector('[aria-label="打开导航"]').getAttribute('aria-expanded')`),'true')
  await screenshot('mobile-navigation')
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27})
  await until(`!document.querySelector('.workspace').inert`)
  await new Promise(r=>setTimeout(r,300)); await click('打开导航');await click('仪表盘')
  await until(`document.body.innerText.includes('平台健康')`)
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true)
  await screenshot('mobile-dashboard')
  await new Promise(r=>setTimeout(r,300)); await click('打开导航');await click('模块管理')
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true)
  await screenshot('mobile-modules')
  // Test actual document navigation and dev history fallback at both widths.
  for (const [width, height] of [[1440, 900], [390, 844], [360, 800]]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<761})
    for (const [pathname, text] of [['/','平台健康'],['/modules','模块目录'],['/modules/demo','公开配置'],['/settings','管理配置尚未开放'],['/unknown-route','404 · 找不到这个页面']]) {
      await loadDocument('Page.navigate',{url:'http://127.0.0.1:5173'+pathname})
      await until(`location.pathname===${JSON.stringify(pathname)} && document.body.innerText.includes(${JSON.stringify(text)})`)
      assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true)
      if(pathname==='/' && width===360) { await until(`document.body.innerText.includes('演示模块')`); await screenshot('mobile-360-dashboard') }
      await loadDocument('Page.reload')
      await until(`location.pathname===${JSON.stringify(pathname)} && document.body.innerText.includes(${JSON.stringify(text)})`)
      assert.equal(await evaluate(`document.title.startsWith(document.querySelector('h1').textContent)`),true)
    }
    // Detail link is copyable and restores correctly through browser history.
    await loadDocument('Page.navigate',{url:'http://127.0.0.1:5173/modules'})
    await until(`document.querySelector('a[href="/modules/demo"]')`)
    await evaluate(`(()=>{const input=document.querySelector('input');input.value='演示';input.dispatchEvent(new Event('input',{bubbles:true}))})()`)
    await click('演示模块')
    await until(`location.pathname==='/modules/demo' && document.body.innerText.includes('公开配置')`)
    await evaluate('history.back()')
    await until(`location.pathname==='/modules' && document.querySelector('input')?.value==='演示'`)
    assert.equal(await evaluate(`document.activeElement.id`),'main-content')
    await evaluate('history.forward()')
    await until(`location.pathname==='/modules/demo' && document.body.innerText.includes('公开配置')`)
    assert.equal(await evaluate(`document.querySelector('nav [aria-current="page"]').getAttribute('href')`),'/modules')
    assert.equal(await evaluate(`document.activeElement.id`),'main-content')
    await screenshot(width===1440?'desktop-direct-detail':width===390?'mobile-direct-detail':'mobile-360-detail')
  }
  // Distinguish module API 404 from route 404, including malformed encoding.
  await loadDocument('Page.navigate',{url:'http://127.0.0.1:5173/modules/missing'})
  await until(`document.body.innerText.includes('读取失败（404）')`)
  assert.equal(await evaluate(`document.body.innerText.includes('404 · 找不到这个页面')`),false)
  await loadDocument('Page.navigate',{url:'http://127.0.0.1:5173/modules/%25'})
  await until(`document.body.innerText.includes('404 · 找不到这个页面')`)
  await click('返回仪表盘')
  await until(`location.pathname==='/' && document.body.innerText.includes('平台健康')`)
  await click('打开导航')
  await until(`document.querySelector('[role=dialog]') && document.querySelector('.workspace').inert`)
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9,modifiers:8})
  await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9})
  assert.equal(await evaluate(`document.activeElement.getAttribute('href')`),'/settings')
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9})
  await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9})
  assert.equal(await evaluate(`document.activeElement.textContent.trim()`),'关闭导航')
  // Popstate while the drawer is open must close it and focus the new page.
  await evaluate('history.back()')
  await until(`location.pathname==='/modules/%25' && !document.querySelector('.workspace').inert`)
  assert.equal(await evaluate(`document.activeElement.id`),'main-content')
  await click('打开导航');await click('模块管理')
  await until(`location.pathname==='/modules' && document.body.innerText.includes('模块目录')`)
  assert.equal(await evaluate(`document.activeElement.id`),'main-content')
  console.log('PASS routes: desktop/mobile direct access+reload, copyable links, back/forward, filters retained, titles, menu, focus, trap, route/API404 distinction')
  await send('Fetch.enable',{patterns:[{urlPattern:'*/api/*',requestStage:'Request'}]})
  mode='empty'; await click('刷新数据')
  await until(`document.body.innerText.includes('暂无已注册模块')`)
  mode='disabled'; await click('刷新数据')
  await until(`document.body.innerText.includes('禁用测试模块')`)
  await click('禁用测试模块')
  await until(`document.body.innerText.includes('业务路由不可用') && document.body.innerText.includes('30 秒')`)
  await screenshot('fixture-disabled-detail')
  for(const code of ['404','503']) {
    await click('返回模块目录'); mode=code; await click('禁用测试模块')
    await until(`document.body.innerText.includes('读取失败（${code}）')`)
    mode='disabled';await click('重新读取')
    await until(`document.body.innerText.includes('公开配置')`)
  }
  await click('返回模块目录'); mode='offline'; await click('刷新数据')
  await until(`document.body.innerText.includes('网络连接失败')`)
  mode='loading';await click('重新读取')
  await until(`document.body.innerText.includes('正在读取最新数据')`)
  await until(`document.body.innerText.includes('禁用测试模块')`)
  mode='degraded';await click('打开导航');await click('仪表盘');await click('刷新数据')
  await until(`document.body.innerText.includes('数据库不可用') && document.body.innerText.includes('服务降级')`)
  await screenshot('fixture-degraded-dashboard')
  console.log('PASS browser fixtures (intercepted only): empty/disabled/ready/degraded503/detail404/detail503/offline/loading/retry')
  mode='long'; await click('打开导航');await click('模块管理');await click('刷新数据')
  await until(`document.body.innerText.includes('非常长的模块名称')`)
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true)
  await evaluate(`document.querySelector('.module-link').click()`)
  await until(`document.querySelector('.identity-title')?.textContent.includes('非常长的模块名称')`)
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true)
  await screenshot('fixture-long-mobile-detail')
  await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]})
  assert.equal(await evaluate(`getComputedStyle(document.querySelector('button')).transitionDuration`),'0s')
  console.log('PASS visual: 1440x900 / 390x844 / 360x800, long-name/capability fixtures, reduced motion')
  assert.deepEqual(errors,[])
  console.log('PASS real API: desktop dashboard/detail, search/filters, settings, mobile drawer/Escape, 390px no overflow, no runtime exceptions')
  await send('Browser.close')
} finally {socket?.close();child.kill()}
