const test = require("node:test");
const assert = require("node:assert/strict");
const model = require("../web/graph-model.js");
const nodes = [
  {id:"a",name:"alpha-skill",group:"personal",source:"personal",path:"/skills/alpha",description:"research writing"},
  {id:"b",name:"beta-skill",group:"plugin",source:"plugin",path:"/skills/beta",description:"research"},
  {id:"c",name:"gamma-skill",group:"plugin",source:"plugin",path:"/skills/gamma",description:"image"},
  {id:"d",name:"isolated",group:"personal",source:"personal",path:"/skills/isolated",description:""},
];
const edges = [{source:"a",target:"b",kind:"mention",forward:true},{source:"b",target:"c",kind:"mention"},
  {source:"a",target:"b",kind:"manual"},{source:"a",target:"c",kind:"topic"}];
const options = {query:"",hiddenGroups:new Set(),kinds:new Set(["mention","manual"]),showOrphans:true,mode:"global",depth:1,selectedId:"a"};
test("all sources unchecked produces an empty graph",()=>{
  assert.equal(model.filterGraph(nodes,edges,{...options,hiddenGroups:new Set(["personal","plugin"])}).nodes.length,0);
});
test("a filtered local anchor never falls back to global results",()=>{
  assert.equal(model.filterGraph(nodes,edges,{...options,mode:"local",query:"beta"}).nodes.length,0);
});
test("local depth traverses selected relation types and counts unique pairs",()=>{
  const one = model.filterGraph(nodes,edges,{...options,mode:"local"});
  assert.deepEqual(one.nodes.map(n=>n.id),["a","b"]);
  assert.equal(one.edges.length,1); assert.equal(one.degree.get("a"),1);
  assert.equal(one.edges[0].forward,true); assert.equal(one.edges[0].kind,"manual");
  assert.deepEqual(model.filterGraph(nodes,edges,{...options,mode:"local",depth:2}).nodes.map(n=>n.id),["a","b","c"]);
});
test("reversed duplicate direction survives merging",()=>{
  const merged=model.mergeEdges([{source:"b",target:"a",kind:"mention",forward:true}],new Set(["a","b"]),new Set(["mention"]));
  assert.equal(merged[0].backward,true);assert.equal(merged[0].forward,false);
});
test("orphans and suggestions are independently controllable",()=>{
  const result=model.filterGraph(nodes,edges,{...options,showOrphans:false});
  assert.equal(result.nodes.length,3);assert.equal(result.edges.length,2);
});
test("search supports quoted fields, exclusions and whitespace",()=>{
  assert.equal(model.matches(nodes[0],'source:"personal" research -image'),true);
  assert.equal(model.matches(nodes[0],"name:alpha -writing"),false);
  assert.equal(model.matches(nodes[1],"path:beta"),true);
});
test("label fade is continuous, bounded and monotonic",()=>{
  let prior=0;for(let scale=0;scale<6;scale+=.01){const opacity=model.labelOpacity(scale,1.1);assert.ok(opacity>=prior&&opacity>=0&&opacity<=1);prior=opacity;}
});
