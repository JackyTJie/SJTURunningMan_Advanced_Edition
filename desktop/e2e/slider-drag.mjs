import assert from 'node:assert/strict';
import { chromium } from '@playwright/test';
const browser = await chromium.launch();
try {
  const page = await browser.newPage({viewport:{width:1200,height:840}});
  await page.addInitScript({path:'e2e/mock-init.js'});
  await page.goto(process.env.E2E_BASE_URL || 'http://localhost:4173/',{waitUntil:'networkidle'});
  await page.locator('md-dialog[open] md-checkbox').click();
  await page.locator('md-dialog[open] md-filled-button').click();
  await page.waitForTimeout(600);
  const host=page.locator('m-slider');
  const read=()=>host.evaluate(el=>{
    const root=el.shadowRoot;
    const handle=root.querySelector('[role=slider]');
    const container=root.querySelector('.mtrl-slider__container');
    const box=handle.getBoundingClientRect(), track=container.getBoundingClientRect();
    return { x:box.x+box.width/2,y:box.y+box.height/2,left:track.left,width:track.width,value:Number(handle.getAttribute('aria-valuenow')),segments:[...root.querySelectorAll('[part=segment]')].map(n=>getComputedStyle(n).transitionDuration) };
  });
  const initial=await read();
  const samples=[];
  // Clicking away from the handle starts a drag and must update the visual on its first frame.
  for(const fraction of [(initial.value - 1.2) / 3.8, 0.25, 0.7]){
    const x=initial.left+initial.width*fraction;
    await page.mouse.move(x,initial.y);
    await page.mouse.down();
    await page.evaluate(()=>new Promise(requestAnimationFrame));
    samples.push(await read());
    for(const dx of [1,2,8,20]){
      await page.mouse.move(x+dx,initial.y);
      await page.evaluate(()=>new Promise(requestAnimationFrame));
      samples.push(await read());
    }
    await page.mouse.up();
  }

  for(const sample of samples){
    assert.ok(sample.segments.every(duration => duration === '0s'), 'track segments must follow without a settling transition');
    const expected=sample.left+(sample.value-1.2)/3.8*sample.width;
    assert.ok(Math.abs(sample.x-expected)<1,`handle trails its current value by ${Math.abs(sample.x-expected).toFixed(1)}px`);
  }
  console.log('Slider drag checks passed');
} finally {await browser.close();}
