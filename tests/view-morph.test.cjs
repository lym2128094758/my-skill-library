const test=require('node:test');
const assert=require('node:assert/strict');
const {interpolate}=require('../web/view-morph.js');

test('morph matches node and relation identities across reordered views and preserves endpoints',()=>{
  const node=(id,x,y)=>({id,name:id,x,y,radius:3,color:'#718f7f',alpha:1,labelAlpha:0});
  const edge=(ax,bx)=>({id:'a:b',width:1,color:'#83998c',alpha:1,path:Array.from({length:17},(_,i)=>({x:ax+(bx-ax)*i/16,y:0,alpha:1}))});
  const plane={sphere:0,nodes:[node('a',10,20),node('b',100,40),node('plane-only',30,50)],edges:[edge(10,100)]};
  const sphere={sphere:1,nodes:[node('b',400,200),node('a',200,300),node('sphere-only',500,500)],edges:[edge(200,400)]};
  const mid=interpolate(plane,sphere,.5),a=mid.nodes.find(n=>n.id==='a');
  assert.deepEqual([a.x,a.y],[105,160]);
  assert.equal(new Set(mid.nodes.map(n=>n.id)).size,4);
  assert.equal(mid.nodes.find(n=>n.id==='plane-only').alpha,.5);
  assert.equal(mid.nodes.find(n=>n.id==='sphere-only').alpha,.5);
  assert.equal(mid.edges[0].path[0].x,a.x);
  assert.equal(mid.edges[0].path[16].x,mid.nodes.find(n=>n.id==='b').x);
  assert.equal(interpolate(plane,sphere,1).nodes.find(n=>n.id==='a').x,200);
  const restored=interpolate(sphere,plane,1).nodes.find(n=>n.id==='a');
  assert.deepEqual([restored.x,restored.y],[10,20]);
});

test('returning to 2D ends at the actual SVG label position, alignment, and font size',()=>{
  const node={id:'a',name:'Skill',x:100,y:120,radius:4,color:'#718f7f',alpha:1,labelAlpha:1};
  const sphere={sphere:1,nodes:[{...node,labelX:108,labelY:112,labelAlign:0,labelSize:11}],edges:[]};
  const plane={sphere:0,nodes:[{...node,labelX:100,labelY:144,labelAlign:.5,labelSize:13,labelFamily:'Segoe UI'}],edges:[]};
  const mid=interpolate(sphere,plane,.5).nodes[0];
  assert.deepEqual([mid.labelX,mid.labelY,mid.labelAlign,mid.labelSize],[104,128,.25,12]);
  const end=interpolate(sphere,plane,1).nodes[0];
  assert.deepEqual([end.x,end.y,end.labelX,end.labelY,end.labelAlign,end.labelSize],[100,120,100,144,.5,13]);
  assert.equal(end.labelFamily,'Segoe UI');
});

test('manual dragging controls the scene directly, can reverse, and settles from the release position',()=>{
  const {run}=require('../web/view-morph.js');
  const originals={document:global.document,requestAnimationFrame:global.requestAnimationFrame,cancelAnimationFrame:global.cancelAnimationFrame};
  const queued=new Map();let next=0,completed=false,removed=false;
  const ctx=new Proxy({}, {get:(_,key)=>key==='createRadialGradient'?()=>({addColorStop(){}}):()=>{}});
  global.document={createElement:()=>({className:'',style:{},setAttribute(){},getContext:()=>ctx,remove(){removed=true;}})};
  global.requestAnimationFrame=fn=>{queued.set(++next,fn);return next;};
  global.cancelAnimationFrame=id=>queued.delete(id);
  try{
    const node=x=>({id:'a',x,y:100,radius:3,color:'#718f7f',alpha:1,labelAlpha:0});
    const from={sphere:0,nodes:[node(0)],edges:[]},to={sphere:1,nodes:[node(200)],edges:[]};
    const view=run({clientWidth:800,clientHeight:600,append(){}},from,to,()=>{completed=true;},()=>{},true);
    assert.equal(queued.size,0);
    view.seek(.6);assert.equal(view.snapshot().nodes[0].x,120);
    view.seek(.25);assert.equal(view.snapshot().nodes[0].x,50);
    assert.equal(queued.size,0);assert.equal(completed,false);
    view.play();assert.equal(view.snapshot().nodes[0].x,50);
    const frame=[...queued.values()][0];queued.clear();frame(performance.now()+1000);
    assert.equal(view.snapshot().nodes[0].x,200);assert.equal(completed,true);assert.equal(removed,true);
  }finally{
    for(const [key,value] of Object.entries(originals))if(value===undefined)delete global[key];else global[key]=value;
  }
});
