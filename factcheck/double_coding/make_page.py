"""Build coding_page.html: the blind double-coding sheet as a one-text-at-a-time page that opens in a browser.

Usage (from the repository root): python factcheck/double_coding/make_page.py
Reads coding_sheet.xlsx (ids and texts only; no first-pass label, no classifier output, no trial id) and writes
coding_page.html next to it. The page keeps the answers in the browser and exports coding_answers.csv
(id, label, confidence, note), which double_coding_eval.py accepts in place of the filled sheet.
"""

import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = [
    ("No funding", "Кончились деньги: funding, financing, budget, bankruptcy, lack of resources"),
    ("Safety / benefit-risk", "Безопасность: adverse events, toxicity, clinical hold, benefit/risk"),
    ("Efficacy / futility", "Не работает: futility, lack of efficacy, endpoint not met, interim analysis"),
    ("COVID-19", "Пандемия: COVID-19, pandemic"),
    ("Enrolment", "Не набрали пациентов: enrolment, recruitment, accrual, feasibility"),
    ("M&A / licensing", "Сделка: acquired, merger, licensed, rights returned, change of sponsor"),
    ("Business / strategic", "Бизнес-решение: business, strategic, portfolio, commercial, development discontinued"),
    ("Sponsor decision, unspecified", "«Спонсор решил» без причины: sponsor decision, administrative reasons"),
    ("Other", "Всё остальное: поставки, производство, исследователь, дизайн, неясный текст"),
]
PAGE = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><title>Слепая перекодировка причин остановки</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font:16px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#1b1b1b;background:#fafafa}
h1{font-size:20px;margin:0 0 4px} .sub{color:#555;font-size:14px;margin-bottom:16px}
#bar{height:8px;background:#e3e3e3;border-radius:4px;overflow:hidden;margin:8px 0 4px} #fill{height:100%;background:#2f6f4f;width:0}
#text{background:#fff;border:1px solid #d6d6d6;border-radius:8px;padding:18px;font-size:18px;min-height:90px;margin:14px 0}
.opt{display:flex;gap:10px;align-items:baseline;width:100%;text-align:left;background:#fff;border:1px solid #cfcfcf;border-radius:8px;
padding:9px 12px;margin:6px 0;font:inherit;cursor:pointer} .opt:hover{border-color:#2f6f4f} .opt.on{background:#e4f1ea;border-color:#2f6f4f}
.key{font-weight:600;color:#2f6f4f;min-width:1.2em} .name{font-weight:600;min-width:15em} .hint{color:#555;font-size:14px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:12px 0} input[type=text]{flex:1;min-width:220px;padding:8px;font:inherit;
border:1px solid #cfcfcf;border-radius:6px} button.nav{padding:9px 16px;font:inherit;border-radius:6px;border:1px solid #999;background:#fff;cursor:pointer}
button.main{background:#2f6f4f;color:#fff;border-color:#2f6f4f} .rules{font-size:14px;color:#333;background:#fff8e1;border:1px solid #ecd9a0;
border-radius:8px;padding:10px 14px;margin:14px 0} #warn{color:#a33;font-size:14px}
</style></head><body>
<h1>Слепая перекодировка причин остановки испытаний</h1>
<div class="sub">200 коротких текстов. Выберите одну категорию для каждого. Ответы сохраняются в этом браузере автоматически.</div>
<div class="rules"><b>Правила.</b> 1) Кодируйте то, что написано, а не то, что подозреваете. 2) Если прямо названа нехватка денег,
это всегда No funding. Иначе научная или организационная причина важнее деловой. 3) Отрицание не считается: «not due to safety» не Safety.</div>
<div id="count"></div><div id="bar"><div id="fill"></div></div>
<div id="text"></div><div id="opts"></div>
<div class="row"><label><input type="checkbox" id="low"> не уверен</label><input type="text" id="note" placeholder="заметка (необязательно)"></div>
<div class="row"><button class="nav" id="prev">← Назад</button><button class="nav" id="next">Дальше →</button>
<button class="nav" id="todo">К первому без ответа</button><button class="nav main" id="save">Скачать ответы (CSV)</button></div>
<div id="warn"></div>
<script>
const ITEMS = __ITEMS__, LABELS = __LABELS__, KEY = "double_coding_answers_v1";
let ans = {}; try { ans = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { ans = {}; }
let i = 0; const $ = id => document.getElementById(id);
function store(){ try { localStorage.setItem(KEY, JSON.stringify(ans)); $("warn").textContent = ""; }
  catch (e) { $("warn").textContent = "Браузер не сохраняет ответы: не закрывайте вкладку и скачайте CSV в конце."; } }
function done(){ return ITEMS.filter(x => ans[x.id] && ans[x.id].label).length; }
function show(){ const it = ITEMS[i], a = ans[it.id] || {};
  $("count").textContent = "Текст " + (i + 1) + " из " + ITEMS.length + " · готово " + done();
  $("fill").style.width = (100 * done() / ITEMS.length) + "%"; $("text").textContent = it.text;
  $("low").checked = a.confidence === "low"; $("note").value = a.note || "";
  $("opts").innerHTML = ""; LABELS.forEach((l, k) => { const b = document.createElement("button");
    b.className = "opt" + (a.label === l[0] ? " on" : "");
    b.innerHTML = '<span class="key">' + (k + 1) + '</span><span class="name"></span><span class="hint"></span>';
    b.children[1].textContent = l[0]; b.children[2].textContent = l[1]; b.onclick = () => pick(l[0]); $("opts").appendChild(b); }); }
function keep(){ const it = ITEMS[i], a = ans[it.id] || {}; a.confidence = $("low").checked ? "low" : "high"; a.note = $("note").value;
  if (a.label || a.note) ans[it.id] = a; store(); }
function pick(label){ const it = ITEMS[i]; ans[it.id] = Object.assign(ans[it.id] || {}, {label: label}); keep();
  if (i < ITEMS.length - 1) i++; show(); }
function go(d){ keep(); i = Math.max(0, Math.min(ITEMS.length - 1, i + d)); show(); }
$("prev").onclick = () => go(-1); $("next").onclick = () => go(1);
$("todo").onclick = () => { keep(); const k = ITEMS.findIndex(x => !(ans[x.id] && ans[x.id].label)); if (k >= 0) i = k; show(); };
$("low").onchange = keep; $("note").onchange = keep;
document.addEventListener("keydown", e => { if (e.target === $("note")) return;
  if (e.key >= "1" && e.key <= "9") pick(LABELS[+e.key - 1][0]); else if (e.key === "ArrowLeft") go(-1); else if (e.key === "ArrowRight") go(1); });
function q(s){ return '"' + String(s == null ? "" : s).replace(/"/g, '""') + '"'; }
$("save").onclick = () => { keep(); const rows = ["id,label,confidence,note"].concat(ITEMS.map(x => { const a = ans[x.id] || {};
    return [x.id, q(a.label), q(a.label ? (a.confidence || "high") : ""), q(a.note)].join(","); }));
  const blob = new Blob(["\\ufeff" + rows.join("\\n") + "\\n"], {type: "text/csv"}), u = URL.createObjectURL(blob), l = document.createElement("a");
  l.href = u; l.download = "coding_answers.csv"; document.body.appendChild(l); l.click(); l.remove(); URL.revokeObjectURL(u);
  $("warn").textContent = done() < ITEMS.length ? "Скачано, но без ответа ещё " + (ITEMS.length - done()) + " текстов." : ""; };
const first = ITEMS.findIndex(x => !(ans[x.id] && ans[x.id].label)); i = first >= 0 ? first : 0; show();
</script></body></html>
"""


def main():
    s = pd.read_excel(os.path.join(HERE, "coding_sheet.xlsx"), sheet_name="Coding")
    items = [{"id": int(i), "text": str(t)} for i, t in zip(s["id"], s.iloc[:, 1])]
    page = PAGE.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")).replace(
        "__LABELS__", json.dumps(LABELS, ensure_ascii=False)
    )
    with open(os.path.join(HERE, "coding_page.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"{len(items)} texts -> coding_page.html")


if __name__ == "__main__":
    main()
