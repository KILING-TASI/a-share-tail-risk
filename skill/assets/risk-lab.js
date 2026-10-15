/* Pure deterministic calculators shared by the UI and regression tests. */
(function(root){
'use strict';
function num(x,min=0){if(typeof x!=='number'||!Number.isFinite(x)||x<min)throw Error('请填写有限且范围正确的数值');return x;}
function evaluate(d){
let mode=d.tool;
if(mode==='fragility'){
 let equity=num(d.equity),debt=num(d.debt),cash=num(d.cash),need=num(d.cashNeed),floor=num(d.equityFloor),haircut=num(d.haircutPct)/100,m=d.maintenanceRatio==null?null:num(d.maintenanceRatio,1),ss=d.shocksPct;
 if(haircut>1||ss.length<3||new Set(ss).size!==ss.length||ss.some((x,i)=>i&&x<=ss[i-1]))throw Error('冲击至少三个，须递增；折扣不能超过100%');
 let rows=ss.map(s=>{num(s);if(s>100)throw Error('冲击不能超过100%');let collateral=(equity+debt)*(1-s/100)*(1-haircut),call=m!==null&&debt?Math.max(0,m*debt-collateral):debt===0?0:null;return {shockPct:s,equityAfter:(equity+debt)*(1-s/100)-debt,priceLoss:(equity+debt)*s/100,collateralAfter:collateral,cashCall:call,cashHeadroom:call===null?null:cash-need-call,floorBreached:(equity+debt)*(1-s/100)-debt<floor};});
 return {tool:mode,rows,firstCashBreachPct:rows.find(r=>r.cashHeadroom!==null&&r.cashHeadroom<0)?.shockPct??null};
}
if(mode==='barbell'){
 let safe=num(d.safeAmount),h=num(d.safeHaircutPct)/100,blocked=num(d.blockedSafe),need=num(d.requiredReserve),risk=num(d.riskAmount),loss=num(d.maxLossPct)/100,budget=num(d.lossBudget),cost=num(d.cost),v=d.lossBoundVerified===true;
 if(h>1||loss>1||blocked>safe)throw Error('比例或不可用储备金额有误');let reserve=Math.max(0,safe*(1-h)-blocked),worst=risk*loss+cost;
 return {tool:mode,usableReserve:reserve,reserveHeadroom:reserve-need,declaredRiskLoss:worst,budgetHeadroom:v?budget-worst:null,lossBoundVerified:v,commonRiskReviewed:d.commonRiskReviewed===true};
}
if(mode==='protection'){
 let premium=num(d.premiumPerTerm),terms=num(d.terms,1);if(!Number.isInteger(terms))throw Error('期数须为整数');
 let cost=premium*terms+num(d.fees)+num(d.cashReserve)*num(d.opportunityRatePct)/100*num(d.months)/12,budget=num(d.budget),rows=d.scenarios.map(r=>{let net=num(r.grossPayout)-num(r.basisSlippage??0)-cost;return {label:r.label,netProtection:net,combinedPnL:net-num(r.underlyingLoss)};});return {tool:mode,totalCost:cost,budgetHeadroom:budget-cost,rows};
}
if(mode==='cashflow'){
 let months=d.months,cash=num(d.cash),income=num(d.monthlyIncome),loss=num(d.incomeLossPct)/100,expense=num(d.monthlyExpense),debt=num(d.monthlyDebt),delay=d.exitDelayMonths,proceeds=num(d.stressedSaleProceeds);
 if(!Number.isInteger(months)||months<1||months>120||!Number.isInteger(delay)||delay<0||delay>120||loss>1)throw Error('期限须为1至120月；到账月为0至120；收入冲击不超过100%');
 if(delay===0)cash+=proceeds;let rows=[];for(let m=1;m<=months;m++){cash+=income*(1-loss)-expense-debt;if(m===delay)cash+=proceeds;rows.push({month:m,endCash:cash});}return {tool:mode,rows,firstShortfallMonth:rows.find(r=>r.endCash<0)?.month??null};
}
throw Error('未知工具');
}
function run(d){let r=evaluate(d);function finite(x){if(typeof x==='number'&&!Number.isFinite(x))throw Error('金额溢出，请缩小输入');if(x&&typeof x==='object')Object.values(x).forEach(finite);}finite(r);return r;}
if(typeof module!=='undefined')module.exports={evaluate:run};else root.RiskLab={evaluate:run};
})(typeof window==='undefined'?{}:window);
