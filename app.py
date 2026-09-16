"""本地 Web 服务：首页登录 -> 控制台（设置提醒时间 / 手动抓取同步 / 探测）。"""
import json
from datetime import datetime, date
from flask import Flask, request, redirect, url_for, render_template_string, jsonify

from config import load_config, save_config, DATA_DIR
from auth import save_credentials, has_credentials, get_credentials
from pipeline import run_pipeline, load_last_sync, WEEKDAY_CN
from notes import (load_notes, set_subject_note, set_session_note,
                   note_for_event, session_key, subjects_in_schedule)

app = Flask(__name__)


def _esc_html(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _esc_attr(s):
    return (s or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


LAYOUT = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>课表同步 · Delta Student</title>
<style>
:root{--bg:#f5f7fa;--card:#fff;--line:#e5e9f0;--ink:#1f2430;--mut:#7a8290;--pri:#2f6df6;--ok:#1f9d55;--warn:#d9822b;--err:#d64545}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;background:var(--bg);color:var(--ink)}
.wrap{max-width:760px;margin:0 auto;padding:28px 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:18px;box-shadow:0 1px 3px rgba(20,30,50,.04)}
h1{font-size:20px;margin:0 0 4px}
h2{font-size:15px;margin:0 0 14px;color:var(--mut);font-weight:600}
label{display:block;font-size:13px;color:var(--mut);margin:12px 0 6px}
input,select{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:9px;font-size:14px;background:#fff}
input:focus,select:focus{outline:none;border-color:var(--pri)}
.row{display:flex;gap:12px}.row>div{flex:1}
.btn{display:inline-block;border:none;border-radius:9px;padding:11px 16px;font-size:14px;cursor:pointer;background:var(--pri);color:#fff;margin-top:14px}
.btn.ghost{background:#eef2f8;color:var(--ink)}
.btn.warn{background:var(--warn);color:#fff}
.msg{padding:12px 14px;border-radius:9px;font-size:13px;margin-top:14px;white-space:pre-wrap}
.msg.ok{background:#eaf7ef;color:var(--ok)}.msg.err{background:#fdeaea;color:var(--err)}
.msg.info{background:#eef4ff;color:var(--pri)}
.muted{color:var(--mut);font-size:12px;line-height:1.6}
code{background:#f0f2f6;padding:1px 6px;border-radius:5px;font-size:12px}
a{color:var(--pri)}
details.card{padding:0}
details.card>summary{list-style:none;cursor:pointer;padding:16px 22px;font-size:15px;font-weight:600;color:var(--ink);display:flex;align-items:center;gap:8px}
details.card>summary::-webkit-details-marker{display:none}
details.card>summary::before{content:"▸";color:var(--mut);font-size:12px}
details.card[open]>summary::before{content:"▾"}
details.card>.body{padding:0 22px 22px}
details.exec>summary{background:var(--pri);color:#fff;justify-content:center;border-radius:14px}
details.exec>summary::before{content:""}
details.exec[open]>summary{border-radius:14px 14px 0 0}
details.exec>.body{padding-top:16px}
details.more>summary{list-style:none;cursor:pointer;font-size:13px;color:var(--pri);font-weight:600;padding:12px 0;display:flex;align-items:center;gap:6px}
details.more>summary::-webkit-details-marker{display:none}
details.more>summary::before{content:"▸";font-size:11px}
details.more[open]>summary::before{content:"▾"}
.topbar{display:flex;gap:18px;align-items:stretch;margin-bottom:18px}
.topbar .account{flex:1;margin-bottom:0}
.sync-col{display:flex;flex-direction:column;gap:8px;justify-content:center}
.sync-btn{font-size:16px;padding:14px 24px;white-space:nowrap}
.sync-more{position:relative}
.sync-tri{width:34px;height:34px;border:1px solid var(--line);background:#eef2f8;border-radius:9px;cursor:pointer;font-size:14px;color:var(--ink)}
.sync-menu{position:absolute;right:0;top:100%;margin-top:6px;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 6px 20px rgba(20,30,50,.12);z-index:20;min-width:160px;overflow:hidden}
.menuitem{display:block;width:100%;text-align:left;background:none;border:none;padding:11px 14px;cursor:pointer;font-size:14px;color:var(--ink)}
.menuitem:hover{background:#f3f6fb}
.menuitem.warn{color:var(--err)}
.dial{width:100%;max-width:240px;display:block;margin:4px auto 2px;touch-action:none;cursor:ns-resize}
.dial-track{fill:none;stroke:#e9edf4;stroke-width:30}
.dial-tick{stroke:#c3cad6;stroke-width:2;stroke-linecap:round}
.dial-box{fill:rgba(255,255,255,.85);stroke:var(--pri);stroke-width:2.5}
.dial-label{font-size:13px;fill:#7a8290}
.btn:disabled{opacity:.62;cursor:progress}
#toastBox{position:fixed;right:18px;bottom:18px;z-index:60;display:flex;flex-direction:column;gap:10px;max-width:min(92vw,420px)}
.actions{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:16px}
.actions>*+*{margin-left:auto}
.fab{border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:10px;padding:10px 15px;font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 2px 8px rgba(20,30,50,.07)}
.fab:hover{background:#f5f8fd;border-color:var(--pri);color:var(--pri)}
.fab:disabled{opacity:.6;cursor:progress}
form.m0{margin:0}
.note-btn{border:1px solid var(--line);background:#fff;color:var(--mut);border-radius:8px;padding:4px 9px;font-size:12px;cursor:pointer;white-space:nowrap}
.note-btn:hover{border-color:var(--pri);color:var(--pri)}
.sched .note{font-size:12px;margin-top:3px;line-height:1.45;border-radius:7px;padding:4px 8px;white-space:pre-wrap;word-break:break-word}
.sched .note.sess{background:#fff4e6;color:#9a5b16;border-left:3px solid var(--warn)}
.sched .note.subj{background:#eef4ff;color:#2f5fc0;border-left:3px solid var(--pri)}
.subj-panel .row{display:flex;gap:10px;align-items:center;padding:9px 2px;border-top:1px solid var(--line)}
.subj-panel .row .name{font-weight:600;min-width:84px}
.subj-panel .row input{flex:1}
.subj-panel .row .del{border:none;background:none;color:var(--err);cursor:pointer;font-size:13px;padding:0 4px}
.modal{position:fixed;inset:0;background:rgba(20,30,50,.32);display:none;align-items:center;justify-content:center;z-index:80}
.modal-box{background:#fff;width:min(92vw,460px);border-radius:16px;padding:22px;box-shadow:0 18px 50px rgba(20,30,50,.25)}
.modal-box h3{margin:0 0 4px;font-size:17px}
.modal-box textarea{width:100%;border:1px solid var(--line);border-radius:9px;padding:10px;font-size:14px;font-family:inherit;resize:vertical}
.toast{background:#fff;border:1px solid var(--line);border-left:4px solid var(--pri);border-radius:11px;padding:13px 15px;box-shadow:0 10px 30px rgba(20,30,50,.16);font-size:13px;line-height:1.65;white-space:pre-wrap;word-break:break-all;animation:tin .22s ease-out}
.toast.ok{border-left-color:var(--ok)}
.toast.err{border-left-color:var(--err)}
.toast.info{border-left-color:var(--pri)}
@keyframes tin{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.sched .day{font-size:14px;font-weight:700;color:var(--ink);margin:14px 0 6px;display:flex;gap:8px;align-items:baseline}
.sched .day .d{color:var(--mut);font-weight:500;font-size:12px}
.sched .row{display:flex;gap:12px;align-items:center;padding:10px 2px;border-top:1px solid var(--line)}
.sched .t{font-variant-numeric:tabular-nums;font-weight:700;color:var(--pri);min-width:108px;font-size:14px}
.sched .subj{font-size:14px;font-weight:600;flex:1;line-height:1.35}
.sched .loc{font-size:12px;color:var(--mut);margin-top:2px}
.sched .empty{color:var(--mut);font-size:13px;padding:10px 2px}
.set-row{display:flex;gap:12px;flex-wrap:wrap}
.set-row>div{flex:1;min-width:180px}
select[name=sync_target]{margin-top:0}
</style></head><body><div class="wrap">{body}</div><div id="toastBox"></div>
<div id="noteModal" class="modal">
  <div class="modal-box">
    <h3 id="noteModalTitle">备注</h3>
    <p class="muted" id="noteModalSub"></p>
    <label>这节课专属备注（只作用于选中的这一节）</label>
    <textarea id="noteSessionInput" rows="3"></textarea>
    <p class="muted" id="noteSubjectInfo"></p>
    <div class="actions">
      <button class="btn" id="noteSave" type="button">保存</button>
      <button class="fab" id="noteDelete" type="button">删除</button>
      <button class="fab" id="noteClose" type="button">关闭</button>
    </div>
  </div>
</div>
<script>
(function(){
  var svg=document.getElementById('reminderDial');
  if(svg){
    var NS='http://www.w3.org/2000/svg';
    var input=document.getElementById('reminderInput');
    var ring=document.getElementById('dialRing');
    var CX=70,CY=80,R=75,N=11,STEP=360/N;
    var PX_PER_STEP=170,DETENT=0.92,EASE=0.32,WHEEL_UNIT=34;
    var kRaw=0,kTarget=null,dragging=false,lastY=0,wheelAcc=0;
    function norm(k){return ((k%N)+N)%N;}
    function smooth(f){return f*f*(3-2*f);}
    function dispOf(k){var i=Math.floor(k),f=k-i;return i+(f+DETENT*(smooth(f)-f));}
    function render(){
      var kd=dispOf(kRaw);
      var kSel=Math.round(kd);
      while(ring.firstChild)ring.removeChild(ring.firstChild);
      for(var k=kSel-2;k<=kSel+2;k++){
        var d=k-kd,e=d*STEP;
        if(e<-64||e>64)continue;
        var rad=e*Math.PI/180,ca=Math.cos(rad),sa=Math.sin(rad);
        var sel=(k===kSel);
        if(!sel){
          var tl=document.createElementNS(NS,'line');
          tl.setAttribute('x1',(CX+89*ca).toFixed(1));tl.setAttribute('y1',(CY-89*sa).toFixed(1));
          tl.setAttribute('x2',(CX+95*ca).toFixed(1));tl.setAttribute('y2',(CY-95*sa).toFixed(1));
          tl.setAttribute('class','dial-tick');
          tl.setAttribute('opacity',Math.max(0,(0.5-Math.abs(d)*0.12)).toFixed(2));
          ring.appendChild(tl);
        }
        var t=document.createElementNS(NS,'text');
        t.setAttribute('x',(CX+R*ca).toFixed(1));
        t.setAttribute('y',(CY-R*sa).toFixed(1));
        t.setAttribute('text-anchor','middle');
        t.setAttribute('dominant-baseline','central');
        t.setAttribute('font-size',sel?'23':'15');
        t.setAttribute('font-weight',sel?'700':'500');
        t.setAttribute('fill',sel?'#2f6df6':'#8b93a1');
        if(!sel)t.setAttribute('opacity',Math.max(0.15,(0.85-Math.abs(d)*0.28)).toFixed(2));
        t.textContent=norm(k);
        ring.appendChild(t);
      }
      input.value=norm(kSel);
    }
    (function loop(){requestAnimationFrame(loop);
      if(kTarget!==null&&!dragging){
        kRaw+=(kTarget-kRaw)*EASE;
        if(Math.abs(kTarget-kRaw)<0.002){kRaw=kTarget;kTarget=null;}
        render();
      }})();
    function endDrag(){if(!dragging)return;dragging=false;kTarget=Math.round(dispOf(kRaw));}
    svg.addEventListener('mousedown',function(e){dragging=true;kTarget=null;lastY=e.clientY;e.preventDefault();});
    svg.addEventListener('touchstart',function(e){dragging=true;kTarget=null;lastY=e.touches[0].clientY;e.preventDefault();},{passive:false});
    window.addEventListener('mousemove',function(e){if(dragging){kRaw+=(e.clientY-lastY)/PX_PER_STEP;lastY=e.clientY;render();}});
    window.addEventListener('touchmove',function(e){if(dragging){kRaw+=(e.touches[0].clientY-lastY)/PX_PER_STEP;lastY=e.touches[0].clientY;render();e.preventDefault();}},{passive:false});
    window.addEventListener('mouseup',endDrag);
    window.addEventListener('touchend',endDrag);
    svg.addEventListener('wheel',function(e){e.preventDefault();
      wheelAcc+=e.deltaY;
      var steps=Math.trunc(wheelAcc/WHEEL_UNIT);
      if(steps!==0){
        wheelAcc-=steps*WHEEL_UNIT;
        kTarget=(kTarget!==null?kTarget:Math.round(dispOf(kRaw)))+steps;
      }else if(Math.abs(wheelAcc)>0.5){wheelAcc*=0.9;}
    },{passive:false});
    var v0=parseInt(input.value||'5',10);
    if(isNaN(v0))v0=5;
    v0=Math.max(0,Math.min(10,v0));
    kRaw=v0;render();
  }
  var tri=document.getElementById('syncTri');
  var menu=document.getElementById('syncMenu');
  if(tri){tri.addEventListener('click',function(e){e.stopPropagation();menu.style.display=menu.style.display==='none'?'block':'none';});
    document.addEventListener('click',function(){menu.style.display='none';});}
  // ---------- 弹窗提示 + 原地执行（不跳转页面） ----------
  var box=document.getElementById('toastBox');
  function removeNode(n){ if(n&&n.parentNode){n.parentNode.removeChild(n);} }
  function toast(cls,text,ms){
    if(!box)return null;
    var d=document.createElement('div');
    d.className='toast '+cls; d.textContent=text||'完成';
    box.appendChild(d);
    setTimeout(function(){ d.style.transition='opacity .3s'; d.style.opacity='0';
      setTimeout(function(){removeNode(d);},320); }, ms||(cls==='err'?9000:5000));
    return d;
  }
  function refreshLastSync(){
    fetch('/api/last_sync',{headers:{'Accept':'application/json'}})
      .then(function(r){return r.json();})
      .then(function(j){
        var el=document.getElementById('lastSync');
        if(!el)return;
        el.innerHTML = (j && j.time)
          ? '上次更新时间：<b>'+j.time+'</b> · 写入 '+(j.pushed||0)+' 节课'
          : '上次更新时间：<b>—</b>（点右侧“同步”试一次）';
      }).catch(function(){});
  }
  var forms=document.querySelectorAll('form[data-ajax]');
  for(var fi=0;fi<forms.length;fi++){
    (function(f){
      f.addEventListener('submit',function(e){
        e.preventDefault();
        var btn=f.querySelector('button[type=submit]');
        var old=btn?btn.textContent:'';
        if(btn){btn.disabled=true;btn.textContent='执行中…';}
        var wait=toast('info','正在执行，通常需要 20–40 秒，请稍候…',600000);
        fetch(f.getAttribute('action'),{method:'POST',body:new FormData(f),headers:{'Accept':'application/json'}})
          .then(function(r){return r.json();})
          .then(function(j){
            removeNode(wait);
            toast(j.cls||'info', j.text||'完成');
            refreshLastSync();
          })
          .catch(function(err){
            removeNode(wait);
            toast('err','请求失败：'+err);
          })
          .then(function(){ if(btn){btn.disabled=false;btn.textContent=old;} });
      });
    })(forms[fi]);
  }

  // ---------- 备注：科目统一备注 + 指定某节课备注 ----------
  var noteModal = document.getElementById('noteModal');
  if (noteModal) {
    var curKey = '', curSubj = '';
    var sessInput = document.getElementById('noteSessionInput');
    document.addEventListener('click', function(e){
      var b = e.target.closest ? e.target.closest('.note-btn') : null;
      if (!b) return;
      curKey = b.getAttribute('data-key'); curSubj = b.getAttribute('data-subject');
      var t = b.closest('.row').querySelector('.t').textContent;
      document.getElementById('noteModalTitle').textContent = '给「' + curSubj + '」这节课加备注';
      document.getElementById('noteModalSub').textContent = '时间：' + t;
      sessInput.value = (window.__sessionNotes && window.__sessionNotes[curKey]) || '';
      var sn = (window.__subjectNotes && window.__subjectNotes[curSubj]) || '';
      document.getElementById('noteSubjectInfo').textContent = sn
        ? ('整门「' + curSubj + '」统一备注：' + sn)
        : '（该科目暂无统一备注；这里写的只作用于这一节课）';
      noteModal.style.display = 'flex';
    });
    function closeNote(){ noteModal.style.display = 'none'; }
    document.getElementById('noteClose').onclick = closeNote;
    noteModal.addEventListener('click', function(e){ if (e.target === noteModal) closeNote(); });
    document.getElementById('noteSave').onclick = function(){
      var fd = new URLSearchParams(); fd.set('key', curKey); fd.set('text', sessInput.value);
      var w = toast('info', '保存中…', 60000);
      fetch('/api/notes/session', {method:'POST', body:fd, headers:{'Accept':'application/json'}})
        .then(function(r){ return r.json(); })
        .then(function(j){ removeNode(w); if (window.__sessionNotes) window.__sessionNotes[curKey] = sessInput.value.trim(); noteModal.style.display='none'; refreshPreview(); toast(j.cls||'ok', j.text||'已保存'); })
        .catch(function(err){ removeNode(w); toast('err', '保存失败：' + err); });
    };
    document.getElementById('noteDelete').onclick = function(){
      var fd = new URLSearchParams(); fd.set('key', curKey); fd.set('text', '');
      fetch('/api/notes/session', {method:'POST', body:fd, headers:{'Accept':'application/json'}})
        .then(function(r){ return r.json(); })
        .then(function(j){ if (window.__sessionNotes) delete window.__sessionNotes[curKey]; noteModal.style.display='none'; refreshPreview(); toast(j.cls||'ok', j.text||'已删除'); })
        .catch(function(){});
    };
    // 科目备注面板：失焦自动保存
    Array.prototype.forEach.call(document.querySelectorAll('.subj-panel input[data-subject]'), function(inp){
      inp.addEventListener('blur', function(){
        var subj = inp.getAttribute('data-subject');
        var fd = new URLSearchParams(); fd.set('subject', subj); fd.set('text', inp.value);
        fetch('/api/notes/subject', {method:'POST', body:fd, headers:{'Accept':'application/json'}})
          .then(function(r){ return r.json(); })
          .then(function(j){ if (window.__subjectNotes){ if (inp.value.trim()) window.__subjectNotes[subj] = inp.value.trim(); else delete window.__subjectNotes[subj]; } refreshPreview(); toast(j.cls||'ok', j.text||'已保存'); })
          .catch(function(err){ toast('err', '保存失败：' + err); });
      });
    });
    // 科目备注「清空」按钮
    document.addEventListener('click', function(e){
      var del = e.target.closest ? e.target.closest('[data-del-subject]') : null;
      if (!del) return;
      var subj = del.getAttribute('data-del-subject');
      var fd = new URLSearchParams(); fd.set('subject', subj); fd.set('text', '');
      fetch('/api/notes/subject', {method:'POST', body:fd, headers:{'Accept':'application/json'}})
        .then(function(r){ return r.json(); })
        .then(function(j){ if (window.__subjectNotes) delete window.__subjectNotes[subj]; var inp = document.querySelector('.subj-panel input[data-subject="' + subj.replace(/"/g,'\\"') + '"]'); if (inp) inp.value = ''; refreshPreview(); toast(j.cls||'ok', j.text||'已清空'); })
        .catch(function(){});
    });
  }
  function refreshPreview(){
    fetch('/api/schedule_preview', {headers:{'Accept':'application/json'}})
      .then(function(r){ return r.text(); })
      .then(function(h){ var el = document.getElementById('schedCard'); if (el) el.outerHTML = h; })
      .catch(function(){});
  }
})();
</script>
</body></html>"""


def render(body):
    return render_template_string(LAYOUT.replace("{body}", body))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        if u and p:
            save_credentials(u, p)
            return redirect(url_for("dashboard"))
        return render(render_login("请输入账号和密码。"))
    if has_credentials():
        return redirect(url_for("dashboard"))
    return render(render_login())


def render_login(err=""):
    err_html = f'<div class="msg err">{err}</div>' if err else ""
    return f"""
    <div class="card">
      <h1>课表同步到 Apple Watch</h1>
      <h2>第一步：登录 schoolis.cn 学生端</h2>
      <form method="post" action="/">
        <label>账号</label><input name="username" autocomplete="username" required>
        <label>密码</label><input name="password" type="password" autocomplete="current-password" required>
        <button class="btn" type="submit">保存并继续</button>
      </form>
      {err_html}
      <p class="muted">账号密码仅保存在本机，不会上传到任何第三方。</p>
    </div>"""


@app.route("/dashboard")
def dashboard():
    if not has_credentials():
        return redirect(url_for("index"))
    cfg = load_config()
    u, _ = get_credentials()
    return render(render_dashboard(cfg, u))


def render_dashboard(cfg, user):
    last = load_last_sync()
    if last:
        last_detail = (f"上次更新时间：<b>{last.get('time','')}</b> · 写入 {last.get('pushed',0)} 节课")
    else:
        last_detail = "上次更新时间：<b>—</b>（尚未同步，点右侧“同步”试一次）"
    return render_dashboard_body(cfg, user, last_detail)


def render_schedule_preview():
    """本周课表简明预览：按天分组、24 小时制（不写上午/下午）、科目+地点优先。
    每行带「📝 备注」按钮，并显示已有备注（本节课专属 / 整门科目统一）。"""
    p = DATA_DIR / "schedule.json"
    if not p.exists():
        return ('<div class="card" id="schedCard"><h1>本周课表</h1>'
                '<p class="sched empty">还没有课表。点右上角「同步」抓取一次，这里就会显示。</p></div>')
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return ""
    events = data.get("classes") or data.get("events") or []
    if not events:
        return ('<div class="card" id="schedCard"><h1>本周课表</h1>'
                '<p class="sched empty">本周课表为空（可能已全部过期）。</p></div>')

    try:
        ws = data.get("week_start", "")
        week_start = datetime.strptime(ws, "%Y-%m-%d").date() if ws else None
    except Exception:
        week_start = None

    def wkname(d):
        if week_start:
            try:
                off = (d - week_start).days
                if 0 <= off < len(WEEKDAY_CN):
                    return WEEKDAY_CN[off]
            except Exception:
                pass
        return WEEKDAY_CN[d.weekday()]

    groups = {}
    for ev in events:
        try:
            d = date(ev["year"], ev["month"], ev["day"])
        except Exception:
            continue
        groups.setdefault(d, []).append(ev)
    rows = [
        '<div class="card" id="schedCard"><h1>本周课表</h1>',
        '<p class="muted">24 小时制 · 按天分组 · 科目 + 地点优先。点「📝 备注」可给这节课或整门科目加备注。</p>',
        '<div class="sched">',
    ]
    for d in sorted(groups):
        evs = sorted(groups[d], key=lambda e: (e.get("start_h", 0), e.get("start_m", 0)))
        rows.append(f'<div class="day">{wkname(d)}<span class="d">{d.month:02d}-{d.day:02d}</span></div>')
        for e in evs:
            sh, sm = e.get("start_h", 0), e.get("start_m", 0)
            eh, em = e.get("end_h", 0), e.get("end_m", 0)
            t = f"{sh:02d}:{sm:02d}–{eh:02d}:{em:02d}"
            title = e.get("title") or e.get("subject") or "（未命名）"
            loc = e.get("location", "")
            loc_html = f'<div class="loc">📍 {loc}</div>' if loc else ""
            s_note, sess_note = note_for_event(e)
            note_html = ""
            if sess_note:
                note_html += f'<div class="note sess">📌 {_esc_html(sess_note)}</div>'
            elif s_note:
                note_html += f'<div class="note subj">📝 {_esc_html(s_note)}</div>'
            key = session_key(e)
            rows.append(
                f'<div class="row"><div class="t">{t}</div>'
                f'<div class="subj">{_esc_html(title)}{loc_html}{note_html}</div>'
                f'<button class="note-btn" type="button" data-key="{_esc_attr(key)}" '
                f'data-subject="{_esc_attr(e.get("subject", ""))}">📝 备注</button></div>')
    rows.append('</div></div>')
    return "".join(rows)


def render_subject_notes_panel():
    """科目统一备注面板：列出本周出现的科目，每个可填一条对该科目所有课生效的备注。"""
    notes = load_notes()
    subs = subjects_in_schedule()
    if not subs:
        return ""
    rows = []
    for s in subs:
        cur = notes["subject_notes"].get(s, "")
        rows.append(
            f'<div class="row"><span class="name">{_esc_html(s)}</span>'
            f'<input data-subject="{_esc_attr(s)}" value="{_esc_attr(cur)}" '
            f'placeholder="整门「{_esc_attr(s)}」的统一备注（对所有该科目课生效）">'
            f'<button class="del" type="button" data-del-subject="{_esc_attr(s)}">清空</button></div>')
    return ('<div class="card"><h1>科目备注（对所有该科目课生效）</h1>'
            '<p class="muted">输入后点别处即自动保存；例如「数学：记得带计算器」。这条备注会出现在该科目每一节课下方，并随同步写进日历/提醒。</p>'
            '<div class="subj-panel">' + "".join(rows) + '</div></div>')


def render_dashboard_body(cfg, user, last_detail):
    return f"""
    <div class="topbar">
      <div class="card account">
        <h1>账号与状态</h1>
        <h2>已登录账号：<code>{user or '（未配置）'}</code></h2>
        <p class="muted" id="lastSync">{last_detail}</p>
      </div>
      <div class="sync-col">
        <form method="post" action="/run" data-ajax="1">
          <button class="btn sync-btn" type="submit">同步</button>
        </form>
        <div class="sync-more">
          <button type="button" class="sync-tri" id="syncTri" title="更多操作">▾</button>
          <div class="sync-menu" id="syncMenu" style="display:none">
            <form method="post" action="/push" data-ajax="1"><button class="menuitem" type="submit">仅补推课表</button></form>
            <form method="post" action="/probe" data-ajax="1"><button class="menuitem" type="submit">仅探测页面</button></form>
            <form method="post" action="/clear" data-ajax="1"><button class="menuitem warn" type="submit">清空专用日历</button></form>
          </div>
        </div>
      </div>
    </div>
    <div class="card">
      <h1>提醒与日历设置</h1>
      <form method="post" action="/settings" data-ajax="1" id="settingsForm">
        <div class="row">
          <div>
            <svg id="reminderDial" viewBox="0 0 212 160" class="dial">
              <defs>
                <clipPath id="dialWin">
                  <path d="M70,80 L157.7,-99.8 A200,200 0 0 1 157.7,259.8 Z"/>
                </clipPath>
              </defs>
              <g clip-path="url(#dialWin)">
                <circle class="dial-track" cx="70" cy="80" r="75"/>
                <rect class="dial-box" x="121" y="60" width="48" height="40" rx="10"/>
                <g id="dialRing"></g>
              </g>
              <text class="dial-label" x="112" y="80" text-anchor="end" dominant-baseline="central">上课前提醒</text>
              <text x="145" y="18" text-anchor="middle" font-size="10" fill="#c2c8d4">▲</text>
              <text x="145" y="154" text-anchor="middle" font-size="10" fill="#c2c8d4">▼</text>
              <text x="176" y="80" text-anchor="start" dominant-baseline="central" font-size="12" fill="#7a8290">分钟</text>
            </svg>
            <input type="hidden" name="reminder_lead_minutes" id="reminderInput" value="{cfg.get('reminder_lead_minutes',5)}">
          </div>
          <div class="set-row">
            <div>
              <label>专用日历名称</label>
              <input name="calendar_name" value="{cfg.get('calendar_name','课表')}">
            </div>
            <div>
              <label>提醒事项列表名</label>
              <input name="reminders_list" value="{cfg.get('reminders_list','课表')}">
            </div>
          </div>
        </div>
        <label>同步到（提醒功能靠“提醒事项”才能真正弹通知）</label>
        <select name="sync_target">
          <option value="both" {'selected' if cfg.get('sync_target','both')=='both' else ''}>日历 + 提醒事项（都写）</option>
          <option value="reminders" {'selected' if cfg.get('sync_target','both')=='reminders' else ''}>仅提醒事项</option>
          <option value="calendar" {'selected' if cfg.get('sync_target','both')=='calendar' else ''}>仅日历</option>
        </select>
        <label>周起始策略</label>
        <select name="week_start_mode">
          <option value="next_monday" {'selected' if cfg.get('week_start_mode')=='next_monday' else ''}>下周一</option>
          <option value="explicit" {'selected' if cfg.get('week_start_mode')=='explicit' else ''}>指定日期</option>
        </select>
        <details class="more">
          <summary>更多（高级设置）</summary>
          <div class="body">
            <label>指定起始日期(YYYY-MM-DD，仅“指定日期”模式需要)</label>
            <input name="week_start_date" value="{cfg.get('week_start_date','')}" placeholder="例如 2026-09-14">
            <label>无头浏览器（调试时关掉可看界面）</label>
            <select name="headless">
              <option value="true" {'selected' if cfg.get('headless',True) else ''}>是</option>
              <option value="false" {'selected' if not cfg.get('headless',True) else ''}>否（调试）</option>
            </select>
          </div>
        </details>
      </form>
      <div class="actions">
        <button class="btn" type="submit" form="settingsForm" style="margin-top:0">保存设置</button>
        <form method="post" action="/purge" data-ajax="1" class="m0">
          <button class="fab" type="submit">🧹 清理过期课表</button>
        </form>
      </div>
    </div>""" + _notes_json_script() + render_subject_notes_panel() + render_schedule_preview()


def _notes_json_script():
    """把当前备注（科目/单节）以 JSON 注入页面，供前端弹窗直接读取。"""
    notes = load_notes()
    return ("<script>window.__subjectNotes=" + json.dumps(notes["subject_notes"], ensure_ascii=False)
            + ";window.__sessionNotes=" + json.dumps(notes["session_notes"], ensure_ascii=False)
            + ";</script>")


@app.route("/ping")
def ping():
    """给 Mac App 启动器用的探活接口：返回固定串，避免误判成别的程序（如隔空播放接收器）。"""
    return "sendelta-scheduler-ok"


@app.route("/api/last_sync")
def api_last_sync():
    return jsonify(load_last_sync() or {})


@app.route("/api/notes")
def api_notes():
    notes = load_notes()
    return jsonify({
        "subject_notes": notes["subject_notes"],
        "session_notes": notes["session_notes"],
        "subjects": subjects_in_schedule(),
    })


@app.route("/api/notes/subject", methods=["POST"])
def api_notes_subject():
    subject = request.form.get("subject", "").strip()
    text = request.form.get("text", "")
    set_subject_note(subject, text)
    return jsonify({"cls": "ok", "text": f"已保存「{subject}」的科目备注。", "pushed": 0})


@app.route("/api/notes/session", methods=["POST"])
def api_notes_session():
    key = request.form.get("key", "")
    text = request.form.get("text", "")
    set_session_note(key, text)
    return jsonify({"cls": "ok", "text": "已保存这节课的备注。", "pushed": 0})


@app.route("/api/schedule_preview")
def api_schedule_preview():
    return render_schedule_preview()


@app.route("/settings", methods=["POST"])
def settings():
    cfg = load_config()
    cfg["reminder_lead_minutes"] = max(0, min(10, int(request.form.get("reminder_lead_minutes", 5))))
    cfg["calendar_name"] = request.form.get("calendar_name", "课表")
    cfg["reminders_list"] = request.form.get("reminders_list", "课表")
    cfg["sync_target"] = request.form.get("sync_target", "both")
    cfg["week_start_mode"] = request.form.get("week_start_mode", "next_monday")
    cfg["week_start_date"] = request.form.get("week_start_date", "")
    cfg["headless"] = request.form.get("headless", "true") == "true"
    save_config(cfg)
    if wants_json():
        return jsonify({"cls": "ok", "text": f"设置已保存。同步到：{cfg['sync_target']}；上课前提醒 {cfg['reminder_lead_minutes']} 分钟。",
                        "pushed": 0})
    return redirect(url_for("dashboard"))


@app.route("/run", methods=["POST"])
def run():
    res = run_pipeline(probe=False)
    return respond(res)


@app.route("/push", methods=["POST"])
def push():
    from pipeline import push_existing_schedule
    res = push_existing_schedule()
    return respond(res)


@app.route("/probe", methods=["POST"])
def probe():
    res = run_pipeline(probe=True)
    return respond(res)


@app.route("/clear", methods=["POST"])
def clear():
    from calendar_sync import clear_calendar
    from reminders_sync import clear_reminders
    cfg = load_config()
    target = (cfg.get("sync_target", "both") or "both").lower()
    parts = []
    if target in ("calendar", "both"):
        try:
            clear_calendar(cfg["calendar_name"])
            parts.append(f"已清空「{cfg['calendar_name']}」日历")
        except Exception as e:
            parts.append(f"日历清空失败：{e}")
    if target in ("reminders", "both"):
        try:
            clear_reminders(cfg["reminders_list"])
            parts.append(f"已清空「{cfg['reminders_list']}」提醒列表")
        except Exception as e:
            parts.append(f"提醒清空失败：{e}")
    return respond({"status": "ok", "msg": "；".join(parts) + "。", "pushed": 0})


@app.route("/purge", methods=["POST"])
def purge():
    """删除已经上完（结束时间早于现在）的过期课程——同时清理日历和提醒事项。"""
    from calendar_sync import purge_past_events
    from reminders_sync import purge_past_reminders
    cfg = load_config()
    target = (cfg.get("sync_target", "both") or "both").lower()
    msgs = []
    if target in ("calendar", "both"):
        name = cfg.get("calendar_name", "课表")
        try:
            removed, remain = purge_past_events(name)
            if removed < 0:
                msgs.append(f"还没有名为「{name}」的日历，无需清理")
            elif removed == 0:
                msgs.append(f"「{name}」日历没有过期课程（还剩 {remain} 节）")
            else:
                msgs.append(f"日历已删 {removed} 节过期课，「{name}」还剩 {remain} 节")
        except Exception as e:
            msgs.append(f"日历清理失败：{e}")
    if target in ("reminders", "both"):
        name = cfg.get("reminders_list", "课表")
        try:
            removed, remain = purge_past_reminders(name)
            if removed < 0:
                msgs.append(f"还没有名为「{name}」的提醒列表，无需清理")
            elif removed == 0:
                msgs.append(f"「{name}」提醒没有过期项（还剩 {remain} 条）")
            else:
                msgs.append(f"提醒已删 {removed} 条过期项，「{name}」还剩 {remain} 条")
        except Exception as e:
            msgs.append(f"提醒清理失败：{e}")
    return respond({"status": "ok", "msg": "；".join(msgs), "pushed": 0})


def wants_json():
    return (request.headers.get("Accept", "").startswith("application/json")
            or request.form.get("ajax") == "1")


def payload_of(res):
    """把 pipeline 的返回值整理成 (样式, 文案)。"""
    status = res.get("status")
    if res.get("error"):
        cls = "err"
    else:
        cls = "ok" if status in ("ok", "probe_saved") else (
            "err" if status in ("error", "no_credentials", "needs_selector") else "info")
    lines = [res.get("msg", "")]
    for k in ("week_start", "pushed", "skipped", "schedule_json", "html", "png", "tables_file"):
        if res.get(k):
            lines.append(f"{k}: {res[k]}")
    return cls, "\n".join(str(x) for x in lines if x).strip()


def respond(res):
    """AJAX 请求返回 JSON（页面不跳转）；否则退回原来的整页渲染。"""
    if wants_json():
        cls, text = payload_of(res)
        return jsonify({"cls": cls, "text": text or "已完成", "pushed": res.get("pushed", 0)})
    return render(render_dashboard(load_config(), get_credentials()[0]) + render_result(res))


def render_result(res):
    """旧版整页结果卡片（非 AJAX 时兜底）。"""
    cls, text = payload_of(res)
    safe = (text or "").replace("</div>", "&lt;/div&gt;")
    return f'<div class="card"><div class="msg {cls}">\n{safe}\n</div></div>'


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
