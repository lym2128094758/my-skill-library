const test = require('node:test');
const assert = require('node:assert/strict');
const sphere = require('../web/sphere.js');

test('selected and local anchors stay centered through rotation, panel changes, and interrupted camera moves', () => {
  const handlers = new Map(), frames = new Map();
  let nextFrame = 0;
  const originals = {};
  const globals = {
    document: {hidden:false,addEventListener(){},removeEventListener(){}},
    matchMedia: () => ({matches:false,addEventListener(){},removeEventListener(){}}),
    ResizeObserver: class {observe(){} disconnect(){}},
    IntersectionObserver: class {observe(){} disconnect(){}},
    requestAnimationFrame: cb => {frames.set(++nextFrame, cb);return nextFrame;},
    cancelAnimationFrame: id => frames.delete(id),
  };
  for (const [key,value] of Object.entries(globals)) {originals[key]=global[key];global[key]=value;}
  const context = new Proxy({}, {get:(_,key) => key==='createRadialGradient' ? () => ({addColorStop(){}}) : key==='measureText' ? text => ({width:text.length*6}) : () => {}});
  const canvas = {style:{},getContext:()=>context,getBoundingClientRect:()=>({width:1000,height:800,left:0,top:0}),
    addEventListener:(key,fn)=>handlers.set(key,fn),removeEventListener(){}};
  let now=performance.now();
  const paint = () => {now+=750;const queued=[...frames.values()];frames.clear();queued.forEach(cb=>cb(now));};
  let view;
  try {
    let centerX=500;
    view=sphere.create(canvas,{center:()=>({x:centerX,y:400})});
    view.setData({nodes:[{id:'a',domain:'one'},{id:'b',domain:'two'},{id:'c',domain:'one'}],edges:[]});
    const before=view.position('a');
    view.local('a');paint();
    assert.equal(view.position('a').x,500);assert.equal(view.position('a').y,400);
    handlers.get('keydown')({target:canvas,key:'ArrowRight',preventDefault(){}});paint();
    assert.equal(view.position('a').x,500);assert.equal(view.position('a').y,400);
    view.local(null);paint();
    assert.ok(Math.abs(view.position('a').x-before.x)<1e-8);
    assert.ok(Math.abs(view.position('a').y-before.y)<1e-8);
    view.focus('b');paint();
    assert.equal(view.position('b').x,500);assert.equal(view.position('b').y,400);
    handlers.get('keydown')({target:canvas,key:'ArrowRight',preventDefault(){}});paint();
    assert.equal(view.position('b').x,500);assert.equal(view.position('b').y,400);
    centerX=350;paint();
    assert.equal(view.position('b').x,350);assert.equal(view.position('b').y,400);
    view.focus('c');
    handlers.get('wheel')({deltaY:80,preventDefault(){}});paint();
    assert.equal(view.position('c').x,350);assert.equal(view.position('c').y,400);
    view.select(null);paint();
    assert.notEqual(view.position('c').x,350);
  } finally {
    view?.destroy();
    for(const key of Object.keys(globals))if(originals[key]===undefined)delete global[key];else global[key]=originals[key];
  }
});
