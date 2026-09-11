#!/usr/bin/env python3
"""Incremental ChatGPT export + attachment semantic index."""
from __future__ import annotations

import argparse, hashlib, json, mimetypes, os, re, shutil, sqlite3, subprocess, tempfile
import urllib.error, urllib.request, zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from chatgpt_memory import APP_ROOT, DEFAULT_EXPORT, flatten_conversation, init_database, iso, now, processing_priority, text_part, transcript, user_text

DB_DEFAULT = APP_ROOT / "data" / "memory.sqlite3"
EMBED_MODEL = os.getenv("AGENTOS_EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
XDG = Path(os.getenv("XDG_DATA_HOME", str(Path.home()/".local/share"))).expanduser() / "agenticos"
CACHE = XDG / "chatgpt-imports"
ASSET_VIEW = XDG / "chatgpt-assets"
FILE_ID = re.compile(r"\bfile[-_]([A-Za-z0-9]{8,})\b", re.I)
MAX_TEXT = 2_000_000
CONTENT_HASH_VERSION = "analysis-v1"
CONTENT_HASH_VERSION = "analysis-v1"
EXT = {
    "image/jpeg":".jpg","image/png":".png","image/gif":".gif","image/webp":".webp","image/heif":".heif",
    "application/pdf":".pdf","application/json":".json","application/zip":".zip",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":".docx",
    "audio/x-wav":".wav","audio/wav":".wav","audio/x-m4a":".m4a","video/mp4":".mp4",
    "text/plain":".txt","text/csv":".csv","text/x-shellscript":".sh","text/x-script.python":".py","text/x-c":".c",
}


def connect(db: Path):
    con=sqlite3.connect(db,timeout=30); con.row_factory=sqlite3.Row; con.execute("PRAGMA foreign_keys=ON"); return con


def ensure_schema(db: Path):
    bootstrap=not db.exists()
    if not bootstrap:
        try:
            with sqlite3.connect(db) as c:
                bootstrap=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='conversations'").fetchone() is None
        except sqlite3.Error: bootstrap=True
    if bootstrap: init_database(db)
    with connect(db) as c:
        cols={r[1] for r in c.execute("PRAGMA table_info(conversations)")}
        if "content_sha256" not in cols: c.execute("ALTER TABLE conversations ADD COLUMN content_sha256 TEXT")
        if "content_hash_version" not in cols: c.execute("ALTER TABLE conversations ADD COLUMN content_hash_version TEXT")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS chat_chunks(
          id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id), chunk_index INTEGER NOT NULL,
          start_message INTEGER NOT NULL,end_message INTEGER NOT NULL,chunk_text TEXT NOT NULL,embedding_json TEXT,embedding_model TEXT,
          chunk_hash TEXT NOT NULL UNIQUE,updated_at TEXT NOT NULL,UNIQUE(conversation_id,chunk_index));
        CREATE INDEX IF NOT EXISTS idx_chat_chunks_conversation ON chat_chunks(conversation_id);
        CREATE TABLE IF NOT EXISTS assets(
          asset_id TEXT PRIMARY KEY,source_path TEXT NOT NULL,source_sha256 TEXT NOT NULL,recovered_path TEXT,detected_mime TEXT NOT NULL,
          recovered_ext TEXT NOT NULL,size_bytes INTEGER NOT NULL,extracted_text TEXT,extraction_status TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS asset_references(
          ref_hash TEXT PRIMARY KEY,asset_id TEXT NOT NULL REFERENCES assets(asset_id),conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
          node_id TEXT NOT NULL,message_id TEXT,original_name TEXT,context_text TEXT,metadata_json TEXT NOT NULL DEFAULT '{}');
        CREATE INDEX IF NOT EXISTS idx_asset_refs_asset ON asset_references(asset_id);
        CREATE INDEX IF NOT EXISTS idx_asset_refs_conversation ON asset_references(conversation_id);
        CREATE TABLE IF NOT EXISTS asset_chunks(
          id INTEGER PRIMARY KEY,asset_id TEXT NOT NULL REFERENCES assets(asset_id),chunk_index INTEGER NOT NULL,chunk_text TEXT NOT NULL,
          content_kind TEXT NOT NULL,embedding_json TEXT,embedding_model TEXT,chunk_hash TEXT NOT NULL UNIQUE,updated_at TEXT NOT NULL,
          UNIQUE(asset_id,chunk_index));
        CREATE TABLE IF NOT EXISTS archive_imports(
          import_id TEXT PRIMARY KEY,source_path TEXT NOT NULL,source_sha256 TEXT,prepared_path TEXT NOT NULL,imported_at TEXT NOT NULL,metrics_json TEXT NOT NULL);
        """)


def sha(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()


def digest_json(v: Any):
    raw=json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")); return hashlib.sha256(raw.encode()).hexdigest(),raw


def conversation_digest(conv: dict[str, Any]) -> str:
    """Hash only analysis-relevant conversation content, not volatile export metadata."""
    material = {
        "title": conv.get("title") or "Untitled",
        "messages": flatten_conversation(conv),
    }
    return digest_json(material)[0]


def conversation_digest(conv: dict[str, Any]) -> str:
    """Hash only analysis-relevant conversation content, not volatile export metadata."""
    material = {
        "title": conv.get("title") or "Untitled",
        "messages": flatten_conversation(conv),
    }
    return digest_json(material)[0]


def base_url(host: str):
    host=host.strip().rstrip("/"); return host if host.startswith(("http://","https://")) else "http://"+host


def post_json(url,payload):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read().decode())


def embed(text,model=EMBED_MODEL,host=OLLAMA_HOST):
    base=base_url(host); sample=text[:8000]
    try:
        data=post_json(base+"/api/embeddings",{"model":model,"prompt":sample})
        if data.get("embedding"): return data["embedding"]
    except urllib.error.HTTPError as e:
        if e.code not in {404,405}: raise
    data=post_json(base+"/api/embed",{"model":model,"input":sample}); values=data.get("embeddings") or []
    if values and isinstance(values[0],list): return values[0]
    raise RuntimeError(f"no embedding returned for {model}")


def prepare_source(source: Path,cache=CACHE):
    source=source.expanduser().resolve()
    if source.is_dir(): return source,"dir-"+hashlib.sha256(str(source).encode()).hexdigest()[:16],None
    if not source.is_file() or not zipfile.is_zipfile(source): raise ValueError(f"expected export directory or ZIP: {source}")
    zsha=sha(source); stem=re.sub(r"[^A-Za-z0-9._-]+","-",source.stem).strip("-._") or "chatgpt-export"; dest=cache/f"{stem}-{zsha[:12]}"
    if (dest/".agenticos-import-complete").exists(): return dest,zsha,zsha
    cache.mkdir(parents=True,exist_ok=True); tmp=Path(tempfile.mkdtemp(prefix=".chatgpt-",dir=cache))
    try:
        with zipfile.ZipFile(source) as z:
            root=tmp.resolve()
            for m in z.infolist():
                if m.is_dir() or ((m.external_attr>>16)&0o170000)==0o120000: continue
                target=(tmp/m.filename).resolve()
                try: target.relative_to(root)
                except ValueError: raise ValueError(f"unsafe ZIP member: {m.filename}")
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(m) as src,target.open("wb") as dst: shutil.copyfileobj(src,dst)
        (tmp/".agenticos-import-complete").write_text(zsha+"\n")
        if dest.exists(): shutil.rmtree(dest)
        tmp.rename(dest)
    except Exception:
        shutil.rmtree(tmp,ignore_errors=True); raise
    return dest,zsha,zsha


def conversation_files(source):
    return sorted(set(source.rglob("conversations-*.json"))|set(source.rglob("conversations.json")))


def invalidate(c,cid):
    for table,col in (("candidate_memories","conversation_id"),("deep_facts","source_conversation_id"),("deep_extractions","conversation_id"),
                      ("project_facts","source_conversation_id"),("project_extraction_chunks","source_conversation_id"),("analyses","conversation_id"),
                      ("asset_references","conversation_id")):
        c.execute(f"DELETE FROM {table} WHERE {col}=?",(cid,))


def ingest(db: Path,source: Path):
    ensure_schema(db); m={"added":0,"updated":0,"unchanged":0,"files":0}
    with connect(db) as c:
        for p in conversation_files(source):
            m["files"]+=1; fsha=sha(p); items=json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(items,list): raise ValueError(f"{p} is not a conversation list")
            for conv in items:
                if not isinstance(conv,dict): continue
                cid=conv.get("id") or conv.get("conversation_id")
                if not cid: continue

                raw=json.dumps(conv,ensure_ascii=False,sort_keys=True,separators=(",",":"))
                d=conversation_digest(conv)
                row=c.execute(
                    "SELECT raw_json,content_sha256,content_hash_version FROM conversations WHERE conversation_id=?",
                    (cid,)
                ).fetchone()

                title=conv.get("title") or "Untitled"
                created=iso(conv.get("create_time"))
                updated=iso(conv.get("update_time"))
                text=transcript(conv)
                prio=processing_priority(title,user_text(conv))

                if not row:
                    c.execute("""INSERT INTO conversations(
                        conversation_id,title,created_at,updated_at,source_file,source_sha256,
                        raw_json,transcript,priority,content_sha256,content_hash_version
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (cid,title,created,updated,str(p),fsha,raw,text,prio,d,CONTENT_HASH_VERSION))
                    m["added"]+=1
                    continue

                if row["content_hash_version"] == CONTENT_HASH_VERSION and row["content_sha256"]:
                    old = row["content_sha256"]
                else:
                    try:
                        old = conversation_digest(json.loads(row["raw_json"]))
                    except Exception:
                        old = None

                values=(title,created,updated,str(p),fsha,raw,text,prio,d,CONTENT_HASH_VERSION,cid)

                if old == d:
                    c.execute("""UPDATE conversations SET
                        title=?,created_at=?,updated_at=?,source_file=?,source_sha256=?,
                        raw_json=?,transcript=?,priority=?,content_sha256=?,content_hash_version=?
                        WHERE conversation_id=?""", values)
                    m["unchanged"]+=1
                else:
                    invalidate(c,cid)
                    c.execute("""UPDATE conversations SET
                        title=?,created_at=?,updated_at=?,source_file=?,source_sha256=?,
                        raw_json=?,transcript=?,priority=?,content_sha256=?,content_hash_version=?,
                        state='pending',attempts=0,last_error=NULL,claimed_at=NULL,processed_at=NULL
                        WHERE conversation_id=?""", values)
                    m["updated"]+=1
            c.commit()
        c.execute("INSERT INTO events(at,kind,detail) VALUES(?,?,?)",(now(),"archive-import",json.dumps(m,sort_keys=True)))
    return m


def split_message(text,max_chars=3200):
    text=text.strip()
    if len(text)<=max_chars: return [text] if text else []
    parts=[]; buf=""
    for block in re.split(r"\n\s*\n",text):
        if len(block)>max_chars:
            if buf: parts.append(buf); buf=""
            parts.extend(block[i:i+max_chars] for i in range(0,len(block),max_chars)); continue
        candidate=(buf+"\n\n"+block).strip() if buf else block
        if buf and len(candidate)>max_chars: parts.append(buf); buf=block
        else: buf=candidate
    if buf: parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def chat_chunks(conv,target=2600):
    units=[]
    for mi,msg in enumerate(flatten_conversation(conv)):
        for piece in split_message(msg["text"]): units.append((mi,f"[{msg['role']}] {piece}"))
    groups=[]; cur=[]; size=0
    for unit in units:
        n=len(unit[1])+2
        if cur and size+n>target: groups.append(cur); cur=[]; size=0
        cur.append(unit); size+=n
    if cur: groups.append(cur)
    out=[]
    for i,g in enumerate(groups):
        material=list(g)
        if i and sum(len(x[1])+2 for x in material)+len(groups[i-1][-1][1])+2<=4200: material.insert(0,groups[i-1][-1])
        out.append((i,min(x[0] for x in material),max(x[0] for x in material),"\n\n".join(x[1] for x in material)))
    return out


def index_chats(db,model=EMBED_MODEL,host=OLLAMA_HOST,do_embed=True):
    ensure_schema(db); m={"conversations":0,"chunks":0,"embedded":0,"reused":0}
    with connect(db) as c:
        rows=c.execute("SELECT conversation_id,raw_json FROM conversations ORDER BY created_at,conversation_id").fetchall()
        for row in rows:
            try: parts=chat_chunks(json.loads(row["raw_json"]))
            except json.JSONDecodeError: continue
            m["conversations"]+=1
            for idx,start,end,text in parts:
                h=hashlib.sha256(f"{row['conversation_id']}\0{start}\0{end}\0{text}".encode()).hexdigest()
                old=c.execute("SELECT chunk_hash,embedding_json,embedding_model FROM chat_chunks WHERE conversation_id=? AND chunk_index=?",(row["conversation_id"],idx)).fetchone(); emb=None
                if old and old["chunk_hash"]==h and old["embedding_json"] and old["embedding_model"]==model: emb=old["embedding_json"]; m["reused"]+=1
                elif do_embed: emb=json.dumps(embed(text,model,host)); m["embedded"]+=1
                c.execute("""INSERT INTO chat_chunks(conversation_id,chunk_index,start_message,end_message,chunk_text,embedding_json,embedding_model,chunk_hash,updated_at)
                             VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(conversation_id,chunk_index) DO UPDATE SET start_message=excluded.start_message,end_message=excluded.end_message,
                             chunk_text=excluded.chunk_text,embedding_json=excluded.embedding_json,embedding_model=excluded.embedding_model,chunk_hash=excluded.chunk_hash,updated_at=excluded.updated_at""",
                          (row["conversation_id"],idx,start,end,text,emb,model if emb else None,h,now())); m["chunks"]+=1
            c.execute("DELETE FROM chat_chunks WHERE conversation_id=? AND chunk_index>=?",(row["conversation_id"],len(parts))); c.commit()
    return m


def asset_id(path):
    match=FILE_ID.search(path.stem); return match.group(1).lower() if match else sha(path)[:32]


def mime(path):
    with path.open("rb") as f: head=f.read(64)
    if head.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if head.startswith((b"GIF87a",b"GIF89a")): return "image/gif"
    if head.startswith(b"%PDF"): return "application/pdf"
    if head.startswith(b"RIFF") and head[8:12]==b"WEBP": return "image/webp"
    if head.startswith(b"RIFF") and head[8:12]==b"WAVE": return "audio/x-wav"
    if len(head)>=12 and head[4:8]==b"ftyp": return "image/heif" if any(x in head[8:16].lower() for x in (b"heic",b"heif",b"mif1")) else "video/mp4"
    if head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(path) as z:
                if "word/document.xml" in z.namelist(): return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except Exception: pass
        return "application/zip"
    cmd=shutil.which("file")
    if cmd:
        try:
            p=subprocess.run([cmd,"--brief","--mime-type",str(path)],capture_output=True,text=True,timeout=10,check=False)
            if p.returncode==0 and p.stdout.strip(): return p.stdout.strip()
        except (OSError,subprocess.SubprocessError): pass
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def docx_text(path):
    with zipfile.ZipFile(path) as z: root=ElementTree.fromstring(z.read("word/document.xml"))
    ns="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"; out=[]
    for p in root.iter(ns+"p"):
        s="".join(n.text or "" for n in p.iter(ns+"t")).strip()
        if s: out.append(s)
    return "\n\n".join(out)[:MAX_TEXT]


def extract(path,m):
    try:
        if m.startswith("text/") or m in {"application/json","text/csv"}:
            with path.open("rb") as f: return f.read(MAX_TEXT).decode("utf-8",errors="replace"),"extracted"
        if m=="application/vnd.openxmlformats-officedocument.wordprocessingml.document": return docx_text(path),"extracted"
        if m=="application/pdf":
            cmd=shutil.which("pdftotext")
            if not cmd: return "","pdf-no-pdftotext"
            p=subprocess.run([cmd,"-layout",str(path),"-"],capture_output=True,text=True,timeout=60,check=False)
            return (p.stdout[:MAX_TEXT],"extracted") if p.returncode==0 else ("",f"pdf-extract-error:{p.returncode}")
        if m=="application/zip":
            with zipfile.ZipFile(path) as z: return "Archive contents:\n"+"\n".join(x.filename for x in z.infolist()[:500]),"extracted"
        if m.startswith(("image/","audio/","video/")): return "","metadata-only"
        return "","unsupported"
    except Exception as e: return "",f"error:{type(e).__name__}"


def discover_assets(source):
    return sorted(p for p in source.rglob("*") if p.is_file() and (p.suffix.lower()==".dat" or p.name.lower().startswith(("file_","file-"))))


def index_assets(db,source):
    ensure_schema(db); m={"assets":0,"new_or_changed":0,"unchanged":0}
    with connect(db) as c:
        for p in discover_assets(source):
            aid=asset_id(p); h=sha(p); mt=mime(p); ext=EXT.get(mt) or mimetypes.guess_extension(mt) or (p.suffix if p.suffix.lower()!=".dat" else ".bin")
            old=c.execute("SELECT source_sha256 FROM assets WHERE asset_id=?",(aid,)).fetchone()
            if old and old[0]==h:
                c.execute("UPDATE assets SET source_path=?,detected_mime=?,recovered_ext=?,size_bytes=?,updated_at=? WHERE asset_id=?",(str(p),mt,ext,p.stat().st_size,now(),aid)); m["unchanged"]+=1
            else:
                text,status=extract(p,mt)
                c.execute("""INSERT INTO assets(asset_id,source_path,source_sha256,recovered_path,detected_mime,recovered_ext,size_bytes,extracted_text,extraction_status,updated_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(asset_id) DO UPDATE SET source_path=excluded.source_path,source_sha256=excluded.source_sha256,
                             detected_mime=excluded.detected_mime,recovered_ext=excluded.recovered_ext,size_bytes=excluded.size_bytes,extracted_text=excluded.extracted_text,
                             extraction_status=excluded.extraction_status,updated_at=excluded.updated_at""",(aid,str(p),h,None,mt,ext,p.stat().st_size,text,status,now()))
                c.execute("DELETE FROM asset_chunks WHERE asset_id=?",(aid,)); m["new_or_changed"]+=1
            m["assets"]+=1
    return m


def message_text(msg):
    parts=(msg.get("content") or {}).get("parts") or []; return "\n".join(filter(None,(text_part(x) for x in parts))).strip()[:4000]


def walk(v,parent=None):
    if isinstance(v,str): yield v,parent
    elif isinstance(v,dict):
        for x in v.values(): yield from walk(x,v)
    elif isinstance(v,list):
        for x in v: yield from walk(x,parent)


def link_assets(db):
    ensure_schema(db); m={"references":0,"linked_assets":0}; linked=set()
    with connect(db) as c:
        known={r[0] for r in c.execute("SELECT asset_id FROM assets")}; c.execute("DELETE FROM asset_references")
        for row in c.execute("SELECT conversation_id,raw_json FROM conversations").fetchall():
            try: conv=json.loads(row["raw_json"])
            except json.JSONDecodeError: continue
            for node_id,node in (conv.get("mapping") or {}).items():
                msg=node.get("message") if isinstance(node,dict) else None
                if not isinstance(msg,dict): continue
                ctx=message_text(msg); msgid=str(msg.get("id") or node_id); seen=set()
                for s,parent in walk(msg):
                    for match in FILE_ID.finditer(s):
                        aid=match.group(1).lower()
                        if aid not in known: continue
                        meta={k:parent.get(k) for k in ("id","file_id","asset_pointer","name","filename","file_name","mime_type","size") if isinstance(parent,dict) and k in parent}
                        rawmeta=json.dumps(meta,ensure_ascii=False,sort_keys=True,default=str); key=(aid,rawmeta)
                        if key in seen: continue
                        seen.add(key); name=next((meta.get(k) for k in ("name","filename","file_name") if isinstance(meta.get(k),str)),None)
                        rh=hashlib.sha256(f"{aid}\0{row['conversation_id']}\0{node_id}\0{msgid}\0{name or ''}\0{rawmeta}".encode()).hexdigest()
                        c.execute("INSERT OR IGNORE INTO asset_references VALUES(?,?,?,?,?,?,?,?)",(rh,aid,row["conversation_id"],str(node_id),msgid,name,ctx,rawmeta)); m["references"]+=1; linked.add(aid)
        m["linked_assets"]=len(linked)
    return m


def materialize(db,view=ASSET_VIEW):
    view.mkdir(parents=True,exist_ok=True); m={"materialized":0,"errors":0}
    with connect(db) as c:
        for r in c.execute("SELECT asset_id,source_path,recovered_ext FROM assets").fetchall():
            src=Path(r["source_path"]); dst=view/f"file_{r['asset_id']}{r['recovered_ext']}"
            try:
                if dst.is_symlink() or dst.exists():
                    if not (dst.is_symlink() and dst.resolve()==src.resolve()): dst.unlink()
                if not dst.exists() and not dst.is_symlink(): dst.symlink_to(src.resolve())
                c.execute("UPDATE assets SET recovered_path=?,updated_at=? WHERE asset_id=?",(str(dst),now(),r["asset_id"])); m["materialized"]+=1
            except OSError: m["errors"]+=1
    return m


def chunks(text,size=2400,overlap=300):
    text=text.strip()
    if not text: return []
    if len(text)<=size: return [text]
    step=max(1,size-overlap); return [text[i:i+size].strip() for i in range(0,len(text),step) if text[i:i+size].strip()]


def asset_text(c,a):
    refs=c.execute("""SELECT r.original_name,r.context_text,c.title,c.created_at,c.conversation_id FROM asset_references r JOIN conversations c USING(conversation_id)
                      WHERE r.asset_id=? ORDER BY c.created_at""",(a["asset_id"],)).fetchall()
    lines=[f"Asset file_{a['asset_id']}{a['recovered_ext']}",f"MIME type: {a['detected_mime']}"]; kind="metadata"
    if a["extracted_text"]: lines += ["","Extracted content:",a["extracted_text"]]; kind="extracted_text"
    if refs:
        lines += ["","Conversation references:"]
        for r in refs[:20]:
            if r["original_name"]: lines.append("Original name: "+r["original_name"])
            lines.append(f"Conversation: {r['title']} ({r['created_at']}) id={r['conversation_id']}")
            if r["context_text"]: lines.append(r["context_text"])
        if kind=="metadata": kind="conversation_context"
    return "\n".join(lines)[:MAX_TEXT],kind


def index_asset_chunks(db,model=EMBED_MODEL,host=OLLAMA_HOST,do_embed=True):
    ensure_schema(db); m={"assets":0,"chunks":0,"embedded":0,"reused":0}
    with connect(db) as c:
        for a in c.execute("SELECT * FROM assets ORDER BY asset_id").fetchall():
            text,kind=asset_text(c,a); parts=chunks(text)
            for idx,part in enumerate(parts):
                h=hashlib.sha256(f"{a['asset_id']}\0{part}".encode()).hexdigest(); old=c.execute("SELECT chunk_hash,embedding_json,embedding_model FROM asset_chunks WHERE asset_id=? AND chunk_index=?",(a["asset_id"],idx)).fetchone(); emb=None
                if old and old["chunk_hash"]==h and old["embedding_json"] and old["embedding_model"]==model: emb=old["embedding_json"]; m["reused"]+=1
                elif do_embed and kind!="metadata": emb=json.dumps(embed(part,model,host)); m["embedded"]+=1
                c.execute("""INSERT INTO asset_chunks(asset_id,chunk_index,chunk_text,content_kind,embedding_json,embedding_model,chunk_hash,updated_at) VALUES(?,?,?,?,?,?,?,?)
                             ON CONFLICT(asset_id,chunk_index) DO UPDATE SET chunk_text=excluded.chunk_text,content_kind=excluded.content_kind,embedding_json=excluded.embedding_json,
                             embedding_model=excluded.embedding_model,chunk_hash=excluded.chunk_hash,updated_at=excluded.updated_at""",(a["asset_id"],idx,part,kind,emb,model if emb else None,h,now())); m["chunks"]+=1
            c.execute("DELETE FROM asset_chunks WHERE asset_id=? AND chunk_index>=?",(a["asset_id"],len(parts))); c.commit(); m["assets"]+=1
    return m


def import_archive(source,db=DB_DEFAULT,model=EMBED_MODEL,host=OLLAMA_HOST,do_embed=True,with_assets=True,with_links=True,cache=CACHE,view=ASSET_VIEW):
    prepared,import_id,zsha=prepare_source(Path(source),cache); ensure_schema(db)
    result={"import_id":import_id,"source":str(source),"prepared_source":str(prepared),"conversations":ingest(db,prepared)}
    result["conversation_embeddings"]=index_chats(db,model,host,do_embed)
    if with_assets:
        result["assets"]=index_assets(db,prepared); result["asset_references"]=link_assets(db)
        if with_links: result["asset_view"]=materialize(db,view)
        result["asset_embeddings"]=index_asset_chunks(db,model,host,do_embed)
    with connect(db) as c:
        c.execute("""INSERT INTO archive_imports VALUES(?,?,?,?,?,?) ON CONFLICT(import_id) DO UPDATE SET source_path=excluded.source_path,source_sha256=excluded.source_sha256,
                     prepared_path=excluded.prepared_path,imported_at=excluded.imported_at,metrics_json=excluded.metrics_json""",(import_id,str(source),zsha,str(prepared),now(),json.dumps(result,sort_keys=True)))
    return result


embed_text = embed
ingest_conversations = ingest
index_conversation_embeddings = index_chats
detect_mime = mime
extract_asset_text = extract
link_asset_references = link_assets
materialize_assets = materialize
index_asset_embeddings = index_asset_chunks


def status(db=DB_DEFAULT):
    ensure_schema(db)
    with connect(db) as c:
        return {"conversations":c.execute("SELECT count(*) FROM conversations").fetchone()[0],"chat_chunks":c.execute("SELECT count(*) FROM chat_chunks").fetchone()[0],
                "chat_embeddings":c.execute("SELECT count(*) FROM chat_chunks WHERE embedding_json IS NOT NULL").fetchone()[0],"assets":c.execute("SELECT count(*) FROM assets").fetchone()[0],
                "linked_assets":c.execute("SELECT count(DISTINCT asset_id) FROM asset_references").fetchone()[0],"asset_chunks":c.execute("SELECT count(*) FROM asset_chunks").fetchone()[0],
                "asset_embeddings":c.execute("SELECT count(*) FROM asset_chunks WHERE embedding_json IS NOT NULL").fetchone()[0],"imports":c.execute("SELECT count(*) FROM archive_imports").fetchone()[0]}


def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="command",required=True)
    p=sub.add_parser("import"); p.add_argument("source",nargs="?",type=Path,default=DEFAULT_EXPORT); p.add_argument("--db",type=Path,default=DB_DEFAULT); p.add_argument("--host",default=OLLAMA_HOST); p.add_argument("--embed-model",default=EMBED_MODEL); p.add_argument("--no-embeddings",action="store_true"); p.add_argument("--no-assets",action="store_true"); p.add_argument("--no-materialize-assets",action="store_true"); p.add_argument("--cache-root",type=Path,default=CACHE); p.add_argument("--asset-view",type=Path,default=ASSET_VIEW)
    s=sub.add_parser("status"); s.add_argument("--db",type=Path,default=DB_DEFAULT); args=ap.parse_args()
    if args.command=="status": print(json.dumps(status(args.db),indent=2,sort_keys=True)); return 0
    print(json.dumps(import_archive(args.source,args.db,args.embed_model,args.host,not args.no_embeddings,not args.no_assets,not args.no_materialize_assets,args.cache_root,args.asset_view),indent=2,sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())
