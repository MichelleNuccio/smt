(function(){
const api=window.sandbox,d=api.data;
const assert=(condition,message)=>{if(!condition)throw Error(message);};
const approx=(a,b)=>Math.abs(a-b)<1e-8*Math.max(1,Math.abs(a));
const defaults={plantings:0,rain:41,interception:15,young:2.8,older:.57};
const baseline=api.snapshots[0];
assert(d.trees.length===12715&&d.blocks.length===580,'Record counts');
assert(baseline.alive.reduce((a,b)=>a+b,0)===12094,'2015 alive count');
assert(d.trees.filter(t=>t.block<0).length===267,'Unmatched count');
assert(d.trees.filter(t=>t.status==='Alive'&&t.dbh===null).length===1,'Invalid DBH');
assert(d.trees.every((t,i)=>t.status!=='Alive'||t.dbh===null||approx(baseline.dbh[i],t.dbh*2.54)),'2015 observed DBH');
const pear=d.equations.PYCA.crown_diameter_from_dbh;
assert(approx(api.equation(pear,11*2.54),.41182+.28531*11*2.54),'Pear inches-to-cm formula');
const crown=api.crownFromDbh('PYCA',11*2.54);
const expectedWater=Math.PI*(crown/2)**2*41*.0254*.15*264.17;
const values=api.valuesFor(baseline,defaults);
assert(Array.from(values.trees).filter(Number.isFinite).length===12089,'Unknown estimates: '+JSON.stringify(d.trees.filter((t,i)=>baseline.alive[i]&&!Number.isFinite(values.trees[i])).map(t=>({id:t.id,species:t.species,dbh:t.dbh}))));
const matchedSum=Array.from(values.trees).reduce((s,v,i)=>s+(d.trees[i].block>=0&&Number.isFinite(v)?v:0),0);
assert(approx(matchedSum,values.blocks.reduce((s,v)=>s+v,0)),'Block totals equal matched tree sums');
const twice=api.valuesFor(baseline,{...defaults,rain:82});
assert(Array.from(values.trees).every((v,i)=>!Number.isFinite(v)||approx(twice.trees[i],2*v)),'Rainfall scales water only');
const repeated=api.simulate(defaults);
for(let y=0;y<31;y++)assert(Array.from(repeated[y].alive).every((v,i)=>v===api.snapshots[y].alive[i]),'Repeatable draws '+y);
const noDeaths=api.simulate({...defaults,young:0,older:0,plantings:100});
assert(noDeaths[0].alive.reduce((a,b)=>a+b,0)===12094,'No planting in 2015');
assert(noDeaths[1].alive.reduce((a,b)=>a+b,0)===12194,'Exactly 100 planted in 2016');
assert(noDeaths[7].alive.reduce((a,b)=>a+b,0)===12715,'All 621 sites exhausted by 2022');
assert(noDeaths[30].alive.reduce((a,b)=>a+b,0)===12715,'Sites cannot be replanted');
const plantIndex=d.trees.findIndex((t,i)=>t.status!=='Alive'&&noDeaths[1].alive[i]);
assert(approx(noDeaths[1].dbh[plantIndex],7.62),'New planting begins at 3 inches');
const plantedWithDeaths=api.simulate({...defaults,young:10,older:10,plantings:100});
assert(plantedWithDeaths[30].born.filter(v=>v>2015).length===621,'Deaths never reopen original sites');
assert(api.ageFromDbh('GLTR',1000)===api.ageFromDbh('GLTR',d.equations.GLTR.age_from_dbh.x_max),'Age uses x_max');
assert(api.crownFromDbh('GLTR',100)!==api.crownFromDbh('GLTR',d.equations.GLTR.age_from_dbh.x_max),'Crown uses actual DBH');
let invalid=0,negativeGrowth=0;
for(const snap of noDeaths)for(let i=0;i<d.trees.length;i++)if(snap.alive[i]&&d.trees[i].dbh!==null){
  const dbh=snap.dbh[i],code=d.trees[i].status==='Alive'?d.trees[i].equation:'GLTR';
  assert(Number.isFinite(dbh)&&dbh>0,'Finite simulated diameters');
  if(!Number.isFinite(api.crownFromDbh(code,dbh))||api.crownFromDbh(code,dbh)<0)invalid++;
}
const total=values.trees.reduce((s,v)=>s+(Number.isFinite(v)?v:0),0);
return JSON.stringify({checks:'passed',baselineGallons:total,baselineBlockGallons:matchedSum,
  pear11inGallons:expectedWater,invalidCrownsAcrossNoDeathRun:invalid,
  defaultAlive2045:api.snapshots[30].alive.reduce((a,b)=>a+b,0)},null,2);
})();
