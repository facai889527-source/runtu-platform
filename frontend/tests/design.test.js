import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
const css = readFileSync(new URL('../src/style.css', import.meta.url), 'utf8')
const tokens = Object.fromEntries([...css.matchAll(/--([a-z-]+):\s*(#[\da-f]{3,6})\b/gi)].map((match) => [match[1], match[2]]))
function luminance(hex) {
  const digits = hex.slice(1).length === 3 ? [...hex.slice(1)].map((v) => v + v).join('') : hex.slice(1)
  const channels = [0,2,4].map((offset) => parseInt(digits.slice(offset,offset+2),16)/255)
    .map((value) => value <= .04045 ? value/12.92 : ((value+.055)/1.055)**2.4)
  return channels[0]*.2126 + channels[1]*.7152 + channels[2]*.0722
}
function contrast(first, second) {
  const values=[luminance(first),luminance(second)].sort((a,b)=>b-a)
  return (values[0]+.05)/(values[1]+.05)
}
test('core text and semantic state token pairs meet 4.5:1 contrast', () => {
  for (const [foreground,background] of [['ink','canvas'],['ink','surface'],['muted','canvas'],['muted','surface'],['accent','surface'],['warning','warning-soft'],['danger','danger-soft'],['nav-muted','sidebar']]) {
    const ratio=contrast(tokens[foreground],tokens[background])
    assert.ok(ratio>=4.5, `${foreground}/${background}: ${ratio.toFixed(2)}`)
    console.log(`${foreground}/${background}: ${ratio.toFixed(2)}:1`)
  }
})

test('authentication text, field boundaries and primary actions meet contrast targets', () => {
  for (const [foreground,background] of [['#56676d','#ffffff'],['#526873','#eef5f3'],['#ffffff','#176d58'],['#ffffff','#125844'],['#c5dfdc','#274b46'],['#9d3434','#fff3f1'],['#223b35','#fffffc']]) assert.ok(contrast(foreground,background)>=4.5,foreground+'/'+background)
  assert.ok(contrast('#7b929d','#fcfcf9')>=3,'input boundary')
})
