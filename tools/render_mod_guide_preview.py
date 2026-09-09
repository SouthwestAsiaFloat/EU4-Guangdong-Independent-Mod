"""Standalone, colour-aware reading preview; not a simulation of native EU4 UI."""
from pathlib import Path
import base64
import html
import io
import json
import re
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def rich(value):
 parts=re.split(r'(§[YBGR!])',value);out=[];opened=False
 for part in parts:
  if part.startswith('§') and len(part)==2:
   if opened:out.append('</span>');opened=False
   if part!='§!':out.append('<span class="c'+part[1]+'">');opened=True
  else:out.append(html.escape(part))
 if opened:out.append('</span>')
 return ''.join(out)


def render_html(data,status):
 assets={}
 for category,a in data['art'].items():
  with Image.open(ROOT/a['source_image']) as im:
   w,h=im.size;top=a['crop_top'];ch=round(w*132/512)
   im=im.crop((0,top,w,top+ch)).resize((512,132),Image.Resampling.LANCZOS).convert('RGB')
   buf=io.BytesIO();im.save(buf,format='PNG');assets[category]='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
 rows=[]
 for p in data['pages']:
  rows.append(dict(key=p['key'],title=p['title'],category=p['category'],body=rich(p['body']),links=p['links'],parent=p['parent'],status=status[p['status']][1],outside=status[p['status']][2]))
 payload=json.dumps(dict(pages=rows,assets=assets),ensure_ascii=False).replace('</','<\\/')
 template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>模组介绍 · 分行与配色预览</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#202821;color:#ece6d9;font-family:"PingFang SC","Microsoft YaHei",sans-serif}
header{padding:20px 28px;border-bottom:1px solid #576052}header h1{font-size:21px;margin:0 0 8px}header p{font-size:13px;color:#bac4b4;margin:0}.layout{display:grid;grid-template-columns:260px 1fr;max-width:1120px;margin:0 auto}aside{padding:22px 16px;height:calc(100vh - 94px);overflow:auto;border-right:1px solid #46503f}input,select{width:100%;padding:10px;margin:0 0 12px;background:#303d32;color:#fff;border:1px solid #65705b;border-radius:5px}.index button{display:block;width:100%;text-align:left;border:0;padding:9px 8px;border-radius:4px;background:none;color:#cad1c3;cursor:pointer}.index button:hover,.index button.active{background:#49583e;color:white}main{padding:24px 28px}.legend{font-size:13px;display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}.legend span{padding:4px 8px;border-radius:4px;background:#3c4833}article{max-width:620px;border:2px solid #9a7947;background:#dec396;color:#2c2216;box-shadow:0 10px 28px #0005}h2{margin:0;padding:16px;background:#283d3c;color:#f4ead5;text-align:center;font-size:21px;font-weight:500}.art{display:block;width:100%;aspect-ratio:512/132;object-fit:cover}.content{padding:17px 24px}.status{font-size:13px;color:#58452c;border-bottom:1px solid #a6885e;padding-bottom:12px;margin-bottom:14px}.body{white-space:pre-wrap;font-size:16px;line-height:1.65;letter-spacing:0}.cY{color:#846000;font-weight:650}.cB{color:#143bcc;font-weight:600}.cG{color:#146525;font-weight:600}.cR{color:#b32525;font-weight:600}.legend .cY{color:#ffbd00}.legend .cB{color:#80a8ff}.legend .cG{color:#80d38f}.legend .cR{color:#ff9a91}nav{padding:5px 24px 19px;display:grid;gap:7px}nav button{padding:9px 10px;background:#2e4140;color:#f6eddb;border:1px solid #907348;cursor:pointer;font-size:14px;border-radius:3px}nav button:hover{background:#435a55}.foot{max-width:620px;font-size:12px;color:#b7c1b1;line-height:1.7;margin-top:12px}@media(max-width:760px){.layout{grid-template-columns:1fr}aside{height:180px;border-right:0;border-bottom:1px solid #46503f}.index{display:flex;flex-wrap:wrap}.index button{width:auto}main{padding:14px}.content{padding:14px}nav{padding:0 14px 14px}}
</style>
<header><h1>模组介绍 · 分行与配色预览</h1><p>只读排版预览，非游戏截图。纸面颜色为预览调整，游戏内使用原生黄、蓝、绿、红。</p></header>
<div class="layout"><aside><input id="search" aria-label="查找页面" placeholder="查找标题或正文"><select id="scope" aria-label="适用提示"><option value="status">显示适用提示</option><option value="outside">显示不适用提示</option></select><div class="index" id="index"></div></aside>
<main><div class="legend"><span class="cY">机制 / 入口</span><span class="cB">门槛 / 期限</span><span class="cG">收益</span><span class="cR">代价 / 禁止</span></div><article><h2 id="title"></h2><img class="art" id="art" alt="分类插图"><div class="content"><div class="status" id="status"></div><div class="body" id="body"></div></div><nav id="nav"></nav></article><div class="foot" id="foot"></div></main></div>
<script>const data=PAYLOAD;const pages=new Map(data.pages.map(p=>[p.key,p]));let current='home';const $=id=>document.getElementById(id);
function go(key){const p=pages.get(key)||pages.get('home');current=p.key;$('title').textContent=p.title;$('body').innerHTML=p.body;$('status').textContent=p[$('scope').value];$('art').src=data.assets[p.category];$('nav').replaceChildren();let links=[...p.links];if(p.parent)links.push({label:'返回：'+pages.get(p.parent).title,target:p.parent});if(p.parent&&p.parent!=='home'&&links.length<5)links.push({label:'返回总目录',target:'home'});for(const link of links){let b=document.createElement('button');b.textContent=link.label;b.onclick=()=>go(link.target);$('nav').append(b)}let close=document.createElement('button');close.textContent='合卷，日后再读';close.onclick=()=>go('home');$('nav').append(close);$('foot').textContent=`${data.pages.length} 个说明页 · 当前为 ${p.key}。实际游戏的字号、窗口高度与适用判断以游戏内显示为准。`;history.replaceState(null,'','#'+p.key);index()}
function index(){const q=$('search').value.trim().toLowerCase();$('index').replaceChildren();for(const p of data.pages){if(q&&!p.title.toLowerCase().includes(q)&&!p.body.toLowerCase().includes(q))continue;const b=document.createElement('button');b.textContent=p.title;b.className=p.key===current?'active':'';b.onclick=()=>go(p.key);$('index').append(b)}}$('search').oninput=index;$('scope').onchange=()=>go(current);go(location.hash.slice(1)||'home');</script></html>'''
 return template.replace('PAYLOAD',payload).encode()
