import { sessionStore } from "../app/sessionStore.js";
import { reportService } from "../services/reportService.js";
import { el, ReportTabs, ReportFilters, ReportState, Pagination, readHashQuery, responseState, statusLabel, dateText } from "../components/ReportComponents.js";

const ROUTES = { overview:"#/reports", pilots:"#/reports/pilots", actions:"#/reports/actions", kpis:"#/reports/kpis", incidents:"#/reports/incidents" };
const hasPermission = (permission) => (sessionStore.getCurrentUser()?.permissions ?? []).includes(permission);
const panel = (title) => { const section = el("section", "dashboard-panel report-panel"); section.append(el("h2", "dashboard-panel__title", title)); return section; };
const metric = (label, value, tone = "") => { const card = el("article", `dashboard-kpi ${tone ? `dashboard-kpi--${tone}` : ""}`); card.append(el("span", "dashboard-kpi__label", label), el("strong", "dashboard-kpi__value", String(value ?? "—"))); return card; };

const ReportShell = ({ title, description, active }) => {
  const page = el("div", "page reports-page");
  const heading = el("header", "page-heading reports-heading");
  heading.append(el("p", "page-heading__eyebrow", "تصمیم‌گیری مبتنی بر داده"), el("h1", "page-heading__title", title), el("p", "page-heading__description", description));
  const content = el("div", "reports-content");
  page.append(heading, ReportTabs(active), content);
  return { page, content };
};

const guard = (content, permission) => {
  if (hasPermission(permission)) return true;
  content.append(ReportState({ kind:"no-access", message:"مجوز مشاهده این بخش از گزارش‌ها برای شما تعریف نشده است." }));
  return false;
};

const loadInto = async ({ content, loader, render }) => {
  const controller = new AbortController();
  content.replaceChildren(ReportState({ kind:"loading" }));
  const retry = () => loadInto({ content, loader, render });
  try {
    const payload = await loader(controller.signal);
    const state = responseState(payload, retry);
    if (payload?.state === "NO_ACCESS" || payload?.state === "NO_DATA") { content.replaceChildren(state); return; }
    content.replaceChildren(); if (state) content.append(state); render(payload, content);
  } catch (error) {
    if (error?.name === "AbortError") return;
    content.replaceChildren(ReportState({ kind: error?.status === 403 ? "no-access" : "error", message:error?.message ?? "خطا در دریافت گزارش.", traceId:error?.traceId, retry:error?.status === 403 ? null : retry }));
  }
};

const summaryLabels = {
  total_pilots:"کل پرونده‌ها", active_pilots:"فعال", waiting_documents:"در انتظار مدارک", ready_for_operation:"آماده عملیات",
  in_operation:"در عملیات", ready_for_customer:"آماده مشتری", under_evaluation:"در ارزیابی", proposal_sent:"پیشنهاد ارسال‌شده",
  contracted:"قراردادشده", overdue_pilots:"پرونده معوق", at_risk_pilots:"نزدیک SLA", critical_open_incidents:"رخداد بحرانی باز",
  actions_due_today:"اقدام امروز", actions_without_owner:"اقدام بدون مسئول", actions_without_due_date:"اقدام بدون موعد",
};

export const ReportsOverviewPage = () => {
  const { page, content } = ReportShell({ title:"گزارش‌های مدیریتی پایلوت", description:"نمای یکپارچه وضعیت، ریسک و تصمیم‌های موردنیاز پرونده‌های قابل دسترس شما.", active:ROUTES.overview });
  if (!guard(content, "reports.read")) return page;
  content.append(ReportFilters({ route:ROUTES.overview }));
  const result = el("div", "reports-result"); content.append(result);
  const load = () => loadInto({ content:result, loader:async (signal) => {
    const filters = readHashQuery();
    const settled = await Promise.allSettled([reportService.getOverview(filters, signal), reportService.getPipeline(filters, signal), reportService.getGates({ ...filters, page_size:5 }, signal), reportService.getActions({ ...filters, due:"today", page_size:5 }, signal)]);
    const ok = settled.filter((item) => item.status === "fulfilled");
    if (!ok.length) throw settled[0].reason;
    return { state:ok.length < settled.length ? "PARTIAL_DATA" : ok[0].value.state, datasets:settled.map((item) => item.status === "fulfilled" ? item.value : null) };
  }, render:(payload, target) => {
    const [overview, pipeline, gates, actions] = payload.datasets;
    if (overview) { const cards = el("section", "dashboard-kpis"); Object.entries(summaryLabels).forEach(([key,label]) => cards.append(metric(label, overview.summary?.[key], key.includes("overdue") || key.includes("critical") ? "danger" : key.includes("risk") ? "warning" : ""))); target.append(cards); }
    const grid = el("div", "reports-grid");
    if (pipeline) { const section=panel("قیف وضعیت پرونده‌ها"); const list=el("ol","report-pipeline"); (pipeline.items??[]).forEach((item)=>{ const row=el("li","report-pipeline__item"); row.append(el("span","",item.label),el("strong","",String(item.count))); list.append(row); }); section.append(list); grid.append(section); }
    if (gates) { const section=panel("وضعیت Gateها"); const list=el("div","report-gates"); Object.entries(gates.summary??{}).forEach(([code,data])=>{ const card=el("article","report-gate"); card.append(el("strong","",`${code} — ${data.label}`),el("span","",`تأیید: ${data.approved}`),el("span","",`در انتظار: ${data.pending}`),el("span","",`نیازمند اصلاح: ${data.needs_revision}`)); list.append(card); }); section.append(list); grid.append(section); }
    if (actions) { const section=panel("اقدامات سررسید امروز"); section.append(actionList(actions.items??[])); grid.append(section); }
    target.append(grid);
  }});
  load(); return page;
};

const table = (headers, rows) => {
  const wrap=el("div","report-table-wrap"); const tableEl=el("table","report-table"); const head=el("thead"); const tr=el("tr"); headers.forEach(([_,label])=>tr.append(el("th","",label))); head.append(tr); const body=el("tbody");
  rows.forEach((row)=>{ const line=el("tr"); headers.forEach(([key,label,format])=>{ const cell=el("td"); cell.dataset.label=label; const value=format ? format(row[key],row) : statusLabel(row[key]); if(value instanceof Node) cell.append(value); else cell.textContent=value; line.append(cell); }); body.append(line); }); tableEl.append(head,body); wrap.append(tableEl); return wrap;
};

const actionLink = (_, row) => { const link=el("a","report-link","مشاهده اقدام"); link.href = row.entity_type === "incident" ? `#/incidents/${row.entity_id}` : row.entity_type === "stage" ? `#/pilots/${row.pilot_id}/stages/${row.stage_number}` : `#/pilots/${row.pilot_id}`; return link; };
const actionList = (items) => { if(!items.length) return el("p","report-empty-inline","اقدامی برای این فیلتر وجود ندارد."); const list=el("ul","report-action-list"); items.forEach((item)=>{ const row=el("li",`report-action report-priority--${item.priority}`); const link=el("a","report-link",item.title); link.href=actionLink(null,item).href; row.append(link,el("span","",`${item.project_name} · ${statusLabel(item.priority)}`),el("small","",dateText(item.due_at))); list.append(row); }); return list; };

const createListPage = ({ mode,title,description,extraFilters=[],service,headers,permission="reports.read" }) => () => {
  const route=ROUTES[mode]; const { page,content }=ReportShell({ title,description,active:route }); if(!guard(content,permission)) return page;
  content.append(ReportFilters({ route,extra:extraFilters })); const result=el("div","reports-result"); content.append(result);
  loadInto({ content:result,loader:(signal)=>service({ ...readHashQuery(),page:Number(readHashQuery().page||1),page_size:20 },signal),render:(payload,target)=>{ target.append(table(headers,payload.items??[]),Pagination({ pagination:payload.pagination,route,filters:readHashQuery() })); }});
  return page;
};

export const PilotProgressReportPage = createListPage({ mode:"pilots",title:"پیشرفت پرونده‌ها",description:"پیشرفت ۱۹ مرحله، Gate، SLA و اقدام بعدی هر پایلوت.",service:reportService.getPilots,extraFilters:[["مرتب‌سازی","sort",[["","آخرین تغییر"],["code","کد"],["stage","مرحله"],["progress","پیشرفت"]]]],headers:[
  ["pilot_code","پرونده",(v,r)=>{const a=el("a","report-link",`${v} — ${r.project_name}`);a.href=`#/reports/pilots/${r.pilot_id}`;return a;}],
  ["owner_name","مالک"],["current_stage_number","مرحله",(v,r)=>`${v} — ${r.current_stage_title??""}`],["progress_percent","پیشرفت",(v)=>`${v}%`],["current_gate","Gate"],["sla_status","SLA"],["next_action","اقدام بعدی"],["due_at","موعد",dateText],["critical_incidents","بحرانی"],["last_activity_at","آخرین تغییر",dateText],
] });

export const ActionsReportPage = createListPage({ mode:"actions",title:"اقدامات موردنیاز",description:"اقدامات باز با مسئول، موعد و اولویت واقعی بک‌اند.",service:reportService.getActions,extraFilters:[["موعد","due",[["","همه"],["today","امروز"],["overdue","معوق"],["upcoming","آینده"],["without_due_date","بدون موعد"]]],["اولویت","priority",[["","همه"],["critical","بحرانی"],["high","زیاد"],["medium","متوسط"],["low","کم"]]],["نوع","entity_type",[["","همه"],["stage","مرحله"],["incident","رخداد"],["mission","مأموریت"],["proposal","پیشنهاد تجاری"]]]],headers:[
  ["title","اقدام"],["project_name","پروژه"],["entity_type","نوع"],["assignee_name","مسئول"],["priority","اولویت"],["due_at","موعد",dateText],["overdue_days","روز تأخیر"],["action","لینک",actionLink],
] });

export const IncidentReportPage = createListPage({ mode:"incidents",title:"گزارش رخدادها",description:"رخدادهای مهم، بحرانی و معوق در محدوده دسترسی شما.",service:reportService.getIncidents,headers:[
  ["incident_code","کد",(v)=>{const a=el("a","report-link",v);a.href="#/incidents";return a;}],["project_name","پروژه"],["severity","شدت"],["type","نوع"],["stage_number","مرحله"],["description_short","شرح"],["owner","مسئول"],["due_at","موعد",dateText],["overdue_days","تأخیر"],["status","وضعیت"],
] });

export const KpiReportPage = () => {
  const route=ROUTES.kpis; const { page,content }=ReportShell({ title:"KPI و SLA",description:"شاخص‌های محاسبه‌شده در بک‌اند با هدف و حجم نمونه.",active:route });
  const canKpi=hasPermission("reports.kpi"), canSla=hasPermission("reports.sla"); if(!canKpi&&!canSla){content.append(ReportState({kind:"no-access",message:"مجوز KPI یا SLA برای شما تعریف نشده است."}));return page;}
  content.append(ReportFilters({ route })); const result=el("div","reports-result");content.append(result);
  loadInto({content:result,loader:async(signal)=>{const f=readHashQuery();const requests=[];if(canKpi)requests.push(reportService.getKpis(f,signal));if(canSla)requests.push(reportService.getSla({...f,page_size:20},signal));return {state:"SUCCESS",data:await Promise.all(requests)};},render:(payload,target)=>{let index=0;if(canKpi){const data=payload.data[index++];const section=panel("شاخص‌های کلیدی");const cards=el("div","report-kpis");(data.items??[]).forEach((item)=>{const card=el("article",`report-kpi report-kpi--${item.status}`);card.append(el("span","",item.label),el("strong","",item.value==null?"داده ناکافی":`${item.value}${item.unit==="percent"?"٪":""}`),el("small","",`هدف: ${item.target??"—"} · نمونه: ${item.sample_size??0}`));cards.append(card);});section.append(cards);target.append(section);}if(canSla){const data=payload.data[index];const section=panel("پایش SLA");const cards=el("div","dashboard-kpis");Object.entries(data.summary??{}).forEach(([key,value])=>cards.append(metric(statusLabel({total_monitored:"کل پایش",on_track:"در مسیر",at_risk:"نزدیک مهلت",overdue:"معوق",data_gaps:"داده ناقص"}[key]??key),value,key==="overdue"?"danger":"")));section.append(cards);target.append(section);}}});return page;
};

const definitionList = (object) => { const list=el("dl","report-definition"); Object.entries(object??{}).forEach(([key,value])=>{ const row=el("div",""); row.append(el("dt","",statusLabel(key.replaceAll("_"," "))),el("dd","",typeof value==="object"?JSON.stringify(value):statusLabel(value)));list.append(row);});return list; };

export const PilotOnePageReportPage = ({ pilotId }) => {
  const {page,content}=ReportShell({title:"گزارش تک‌صفحه‌ای پایلوت",description:"خلاصه تصمیم‌محور و قابل چاپ پرونده.",active:ROUTES.pilots}); if(!guard(content,"reports.read"))return page;
  const tools=el("div","report-print-actions");const back=el("a","button button--ghost","بازگشت به گزارش پرونده‌ها");back.href=ROUTES.pilots;const print=el("button","button button--primary","چاپ / ذخیره PDF");print.type="button";print.addEventListener("click",()=>window.print());tools.append(back,print);content.append(tools);const result=el("div","reports-result report-one-page");content.append(result);
  loadInto({content:result,loader:async(signal)=>{const [one,evidence]=await Promise.all([reportService.getOnePage(pilotId,signal),reportService.getExternalEvidence(pilotId,signal)]);return {state:one.state,one,evidence};},render:(payload,target)=>{const s=payload.one.summary??{};const header=el("header","report-document-header");header.append(el("h2","",`${s.header?.pilot_code??""} — ${s.header?.project_name??""}`),el("p","",`مالک: ${s.header?.owner_name??"ثبت نشده"} · مدیر پایلوت: ${s.header?.pilot_manager??"ثبت نشده"}`));target.append(header);[["نتیجه کلی",s.overall_result],["فرایند",s.process],["عملیات",s.operations],["تجربه مشتری",s.customer_experience],["تجاری",s.commercial],["اقدام بعدی",s.next_action]].forEach(([title,data])=>{const section=panel(title);section.append(definitionList(data));target.append(section);});const issues=panel("مسائل باز");issues.append(actionList((s.open_issues??[]).map((i)=>({title:i.label,project_name:i.code,priority:i.severity,due_at:i.due_at,pilot_id:pilotId,entity_type:"incident",entity_id:i.code}))));target.append(issues);const evidence=panel("شواهد خارجی");const list=el("ul","report-evidence");(payload.evidence.items??[]).forEach((item)=>{const row=el("li","");row.append(el("span","",item.evidence_label),el("strong","",item.checked?"تأیید شده":"تأیید نشده"),el("small","",item.short_result??"بدون توضیح"));list.append(row);});evidence.append(list);target.append(evidence);}});return page;
};
