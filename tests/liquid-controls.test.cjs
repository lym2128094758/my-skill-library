const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

function setup(){
  const events={},clicks=[];
  const classes=()=>({add(){},remove(){}});
  const buttons=['left','right'].map((id,index)=>({id,offsetLeft:4+56*index,offsetWidth:54,disabled:false,
    classList:{contains:()=>active===id},click(){active=id;clicks.push(id);}}));
  let active='left',capture=false;
  const lens={style:{},setAttribute(){},animate(){return {cancel(){}};}};
  const group={clientLeft:1,offsetWidth:120,classList:classes(),prepend(){},querySelectorAll:()=>buttons,
    addEventListener:(key,fn)=>{events[key]=fn;},setPointerCapture(){capture=true;},
    hasPointerCapture:()=>capture,releasePointerCapture(){capture=false;}};
  const context={document:{querySelectorAll:()=>[group],createElement:()=>lens},matchMedia:()=>({matches:false}),
    getComputedStyle:el=>({transform:el.style.transform||'none'}),
    DOMMatrixReadOnly:class {constructor(value){this.m41=Number(/translate3d\(([-.\d]+)px/.exec(value)?.[1]||0);}},
    MutationObserver:class {observe(){}},ResizeObserver:class {observe(){}},performance:{now:()=>100}};
  vm.runInNewContext(fs.readFileSync(require.resolve('../web/liquid-controls.js'),'utf8'),context);
  const emit=(type,x,extra={})=>events[type]({pointerId:1,button:0,clientX:x,target:{closest:()=>buttons[0]},preventDefault(){},...extra});
  return {emit,clicks,lens};
}

test('one held drag can cross thresholds repeatedly without triggering in the middle',()=>{
  const {emit,clicks}=setup();
  emit('pointerdown',20);
  emit('pointermove',50);assert.deepEqual(clicks,[]);
  emit('pointermove',62);assert.deepEqual(clicks,['right']);
  emit('pointermove',45);assert.deepEqual(clicks,['right']);
  emit('pointermove',34);assert.deepEqual(clicks,['right','left']);
  emit('pointermove',64);assert.deepEqual(clicks,['right','left','right']);
  emit('pointerup',64);assert.equal(clicks.length,3);
});

test('a fresh pointer gesture is not blocked by the previous drag click suppression',()=>{
  const {emit}=setup();let blocked=false;
  emit('pointerdown',20);emit('pointermove',62);emit('pointerup',62);
  emit('pointerdown',80);
  emit('click',80,{isTrusted:true,preventDefault(){blocked=true;},stopImmediatePropagation(){blocked=true;}});
  assert.equal(blocked,false);
});

test('extreme pulls allow a small overhang but never exceed the elastic limit',()=>{
  const {emit,lens,clicks}=setup();emit('pointerdown',20);
  for(let i=0;i<20;i++){
    emit('pointermove',i%2===0?10000:-10000);
    const match=/translate3d\(([-.\d]+)px,0,0\) scale\(([-.\d]+),([-.\d]+)\)/.exec(lens.style.transform);
    const x=Number(match[1]),sx=Number(match[2]),sy=Number(match[3]),extra=54*(sx-1)/2;
    assert.ok(x-extra>=-21-1e-8);assert.ok(x+54+extra<=139+1e-8);
    if(i%2===0)assert.ok(x+54+extra>119);
    else assert.ok(x-extra<-1);
    assert.ok(sx<=1.04);assert.ok(sy<=1.06);
  }
  assert.equal(clicks.length,20);emit('pointerup',20);
});
