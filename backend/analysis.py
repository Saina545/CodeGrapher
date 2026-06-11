import ast, re
from collections import defaultdict
from datetime import datetime, timezone

PYTHON_BUILTINS = {
    'print','len','range','type','isinstance','int','str','float','bool','list',
    'dict','set','tuple','enumerate','zip','map','filter','sorted','reversed',
    'min','max','sum','abs','round','open','input','repr','format','id','hash',
    'getattr','setattr','hasattr','delattr','callable','iter','next','super',
    'object','property','staticmethod','classmethod','vars','dir','hex','oct',
    'bin','chr','ord','pow','divmod','all','any','bytes','bytearray','complex',
    'frozenset','eval','exec','globals','locals','__import__',
    'append','extend','insert','remove','pop','clear','sort','reverse','copy',
    'count','index','get','keys','values','items','update','join','split','strip',
    'replace','find','upper','lower','encode','decode','write','read','close',
}
PYTHON_STDLIB_PREFIXES = {
    'os','sys','re','io','math','json','time','datetime','pathlib','collections',
    'itertools','functools','operator','string','copy','enum','abc','typing',
    'dataclasses','contextlib','warnings','logging','traceback','inspect','ast',
    'threading','subprocess','socket','http','urllib','email','html','xml','csv',
    'sqlite3','hashlib','hmac','secrets','base64','uuid','random','statistics',
    'decimal','heapq','bisect','queue','struct','pickle','zipfile','tarfile',
    'gzip','zlib','argparse','unittest','asyncio','concurrent',
}
JAVA_STDLIB = {
    'System','Math','Object','String','Integer','Double','Float','Long','Short',
    'Byte','Boolean','Character','StringBuilder','StringBuffer','Arrays',
    'Collections','Optional','println','print','printf','format','toString',
    'equals','hashCode','compareTo','length','size','get','put','add','remove',
    'contains','isEmpty','clear','next','hasNext','valueOf','parseInt',
    'parseDouble','trim','substring','charAt','indexOf','startsWith','endsWith',
    'replace','split','toUpperCase','toLowerCase',
}

DB_IO_PY   = re.compile(
    r'\b(execute|fetchall|fetchone|commit|rollback|cursor|connect|query|'
    r'select|insert|update|delete|read|write|requests?\.|urllib|httpx|'
    r'aiohttp|socket|send|recv)\b', re.I)
DB_IO_JAVA = re.compile(
    r'\b(executeQuery|executeUpdate|prepareStatement|getConnection|ResultSet|'
    r'Statement|HttpClient|URLConnection|Socket|FileInputStream|'
    r'FileOutputStream|BufferedReader|PrintWriter)\b')

def is_user_defined(call, all_names, lang):
    base = call.split('.')[0]
    last = call.split('.')[-1]
    if lang == 'python':
        if base in PYTHON_BUILTINS or last in PYTHON_BUILTINS: return False
        for p in PYTHON_STDLIB_PREFIXES:
            if base == p or call.startswith(p + '.'): return False
    else:
        if base in JAVA_STDLIB or last in JAVA_STDLIB: return False
    return last in all_names or call in all_names

class PythonAnalyzer(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.functions = {}
        self.classes   = {}
        self.imports   = []
        self.current_func  = None
        self.current_class = None
        self._lines = []

    def set_source(self, src):
        self._lines = src.splitlines()

    def visit_Import(self, node):
        for a in node.names: self.imports.append(a.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module: self.imports.append(node.module)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        prev = self.current_class
        self.current_class = node.name
        self.classes[node.name] = {
            'lineno': node.lineno,
            'end_lineno': getattr(node, 'end_lineno', node.lineno),
            'methods': [],
            'bases': [self._name(b) for b in node.bases],
        }
        self.generic_visit(node)
        self.current_class = prev

    def visit_FunctionDef(self, node): self._proc(node)
    visit_AsyncFunctionDef = visit_FunctionDef

    def _proc(self, node):
        key = f"{self.current_class}.{node.name}" if self.current_class else node.name
        start, end = node.lineno, getattr(node, 'end_lineno', node.lineno)
        complexity = 1 + sum(
            1 for n in ast.walk(node)
            if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                               ast.With, ast.Assert, ast.comprehension)))
        func_src = '\n'.join(self._lines[start-1:end]) if self._lines else ''
        self.functions[key] = {
            'name': node.name, 'lineno': start, 'end_lineno': end,
            'args': [a.arg for a in node.args.args],
            'calls': [], 'parent_func': self.current_func,
            'class_name': self.current_class, 'filename': self.filename,
            'is_async': isinstance(node, ast.AsyncFunctionDef),
            'decorators': [self._name(d) for d in node.decorator_list],
            'complexity': complexity,
            'loc': end - start + 1,
            'has_db_io': bool(DB_IO_PY.search(func_src)),
        }
        if self.current_class and key not in self.classes[self.current_class]['methods']:
            self.classes[self.current_class]['methods'].append(key)
        prev = self.current_func
        self.current_func = key
        self.generic_visit(node)
        self.current_func = prev

    def visit_Call(self, node):
        if self.current_func:
            n = self._call_name(node)
            if n: self.functions[self.current_func]['calls'].append(n)
        self.generic_visit(node)

    def _call_name(self, node):
        if isinstance(node.func, ast.Name): return node.func.id
        if isinstance(node.func, ast.Attribute):
            return f"{self._name(node.func.value)}.{node.func.attr}"
        return None

    def _name(self, node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._name(node.value)}.{node.attr}"
        if isinstance(node, ast.Constant): return str(node.value)
        return '?'

def analyze_python_file(filepath, filename):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()
    try: tree = ast.parse(source)
    except SyntaxError as e: return None, str(e)
    a = PythonAnalyzer(filename)
    a.set_source(source)
    a.visit(tree)
    return {
        'functions': a.functions, 'classes': a.classes,
        'imports': a.imports, 'source': source,
        'loc_total': len(source.splitlines()),
    }, None

def _walk_java(nodes):
    try:
        import javalang
        if nodes is None: return
        if isinstance(nodes, (list, tuple, set)):
            for item in nodes: yield from _walk_java(item)
        elif isinstance(nodes, javalang.tree.Node):
            yield None, nodes
            for attr in nodes.attrs:
                yield from _walk_java(getattr(nodes, attr, None))
    except Exception: return

def analyze_java_file(filepath, filename):
    try: import javalang
    except ImportError: return None, "javalang not installed"
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()
    try: tree = javalang.parse.parse(source)
    except Exception as e: return None, f"Parse error: {e}"

    functions, classes, imports = {}, {}, []
    lines = source.splitlines()
    for imp in tree.imports: imports.append(imp.path)

    for _, node in tree.filter(javalang.tree.ClassDeclaration):
        cls = node.name
        classes[cls] = {
            'lineno': node.position.line if node.position else 0,
            'end_lineno': 0, 'methods': [],
            'bases': [node.extends.name] if node.extends else [],
        }
        for _, m in node.filter(javalang.tree.MethodDeclaration):
            key = f"{cls}.{m.name}"
            calls = []
            if m.body:
                for _, inv in _walk_java(m.body):
                    if isinstance(inv, javalang.tree.MethodInvocation):
                        q = inv.qualifier or ''
                        calls.append(f"{q}.{inv.member}" if q else inv.member)
            complexity = 1
            if m.body:
                for _, bn in _walk_java(m.body):
                    if type(bn).__name__ in (
                        'IfStatement','ForStatement','WhileStatement',
                        'DoStatement','SwitchStatement','CatchClause',
                        'TernaryExpression'):
                        complexity += 1
            start = m.position.line if m.position else 0
            func_src = '\n'.join(lines[max(0,start-1):start+50]) if start else ''
            functions[key] = {
                'name': m.name, 'lineno': start, 'end_lineno': 0,
                'args': [p.name for p in (m.parameters or [])],
                'calls': calls, 'parent_func': None,
                'class_name': cls, 'filename': filename,
                'is_async': False, 'decorators': [],
                'return_type': str(m.return_type.name) if m.return_type else 'void',
                'modifiers': list(m.modifiers) if m.modifiers else [],
                'complexity': complexity, 'loc': 20,
                'has_db_io': bool(DB_IO_JAVA.search(func_src)),
            }
            classes[cls]['methods'].append(key)

    return {
        'functions': functions, 'classes': classes,
        'imports': imports, 'source': source,
        'loc_total': len(lines),
    }, None

def build_graph(all_files_data, language):
    nodes, edges = [], []
    all_user_names = set()
    for fdata in all_files_data.values():
        for fk, fd in fdata.get('functions', {}).items():
            all_user_names.add(fd['name'])
            all_user_names.add(fk)

    func_lookup = {}
    for fname, fdata in all_files_data.items():
        file_id = f"file::{fname}"
        nodes.append({'id': file_id, 'label': fname, 'type': 'file',
                       'level': 0, 'filename': fname,
                       'loc_total': fdata.get('loc_total', 0)})
        for cls_name, cls_data in fdata.get('classes', {}).items():
            cls_id = f"class::{fname}::{cls_name}"
            nodes.append({'id': cls_id, 'label': cls_name, 'type': 'class',
                           'level': 1, 'filename': fname,
                           'lineno': cls_data.get('lineno', 0),
                           'bases': cls_data.get('bases', [])})
            edges.append({'from': file_id, 'to': cls_id, 'type': 'contains'})

        for fk, fd in fdata.get('functions', {}).items():
            fid = f"func::{fname}::{fk}"
            func_lookup[fd['name']] = fid
            func_lookup[fk]         = fid
            nodes.append({
                'id': fid, 'label': fd['name'], 'type': 'function',
                'level': 2, 'filename': fname,
                'lineno': fd.get('lineno', 0),
                'end_lineno': fd.get('end_lineno', 0),
                'args': fd.get('args', []),
                'class_name': fd.get('class_name'),
                'is_async': fd.get('is_async', False),
                'decorators': fd.get('decorators', []),
                'modifiers': fd.get('modifiers', []),
                'complexity': fd.get('complexity', 1),
                'loc': fd.get('loc', 0),
                'has_db_io': fd.get('has_db_io', False),
                'func_key': fk,
            })
            parent = (f"class::{fname}::{fd['class_name']}"
                      if fd.get('class_name') else file_id)
            edges.append({'from': parent, 'to': fid, 'type': 'contains'})

    added = set()
    for fname, fdata in all_files_data.items():
        for fk, fd in fdata.get('functions', {}).items():
            from_id = f"func::{fname}::{fk}"
            for call in fd.get('calls', []):
                if not is_user_defined(call, all_user_names, language):
                    continue
                to_id = func_lookup.get(call) or func_lookup.get(call.split('.')[-1])
                if to_id and to_id != from_id:
                    ek = f"{from_id}|{to_id}"
                    if ek not in added:
                        added.add(ek)
                        edges.append({'from': from_id, 'to': to_id, 'type': 'calls'})

    return {'nodes': nodes, 'edges': edges}

def generate_risk_report(all_files_data, graph, language):
    nodes = graph['nodes']
    edges = graph['edges']
    func_nodes = {n['id']: n for n in nodes if n['type'] == 'function'}
    call_edges = [e for e in edges if e['type'] == 'calls']

    fan_in  = defaultdict(int)
    fan_out = defaultdict(int)
    for e in call_edges:
        fan_in[e['to']]   += 1
        fan_out[e['from']] += 1

    callee_set = {e['to'] for e in call_edges}
    SKIP = {'__init__','__new__','__main__','main','setup','teardown',
            '__str__','__repr__','__eq__','__hash__','__len__',
            '__enter__','__exit__','__call__'}

    dead = []
    for nid, n in func_nodes.items():
        nm = n['label']
        if nm in SKIP or nm.startswith('test_') or nm.startswith('Test'):
            continue
        if nid not in callee_set and fan_in[nid] == 0:
            dead.append({'id': nid, 'name': nm,
                          'filename': n.get('filename',''),
                          'lineno': n.get('lineno', 0),
                          'fan_out': fan_out[nid],
                          'complexity': n.get('complexity', 1)})

    complex_issues = []
    for nid, n in func_nodes.items():
        c = n.get('complexity', 1)
        if c >= 5:
            complex_issues.append({
                'id': nid, 'name': n['label'],
                'filename': n.get('filename',''),
                'lineno': n.get('lineno', 0),
                'complexity': c, 'loc': n.get('loc', 0),
                'severity': 'CRITICAL' if c >= 10 else 'WARNING',
            })
    complex_issues.sort(key=lambda x: -x['complexity'])

    high_fanin = []
    for nid, n in func_nodes.items():
        fi = fan_in[nid]
        if fi >= 3:
            rs = min(100, fi * 15 + n.get('complexity', 1) * 5)
            callers_list = [e['from'].split('::')[-1] for e in call_edges if e['to'] == nid][:10]
            high_fanin.append({
                'id': nid, 'name': n['label'],
                'filename': n.get('filename',''),
                'lineno': n.get('lineno', 0),
                'fan_in': fi, 'fan_out': fan_out[nid],
                'complexity': n.get('complexity', 1),
                'risk_score': rs, 'callers': callers_list,
            })
    high_fanin.sort(key=lambda x: -x['risk_score'])

    file_out = defaultdict(set)
    file_in  = defaultdict(set)
    for e in call_edges:
        fn = func_nodes.get(e['from'], {})
        tn = func_nodes.get(e['to'], {})
        ff, ft = fn.get('filename',''), tn.get('filename','')
        if ff and ft and ff != ft:
            file_out[ff].add(ft); file_in[ft].add(ff)

    coupling = []
    for fname, fdata in all_files_data.items():
        ef = len(file_out[fname]); af = len(file_in[fname])
        coupling.append({
            'filename': fname,
            'total_functions': len(fdata.get('functions', {})),
            'efferent_coupling': ef, 'afferent_coupling': af,
            'instability': round(ef / max(ef + af, 1), 3),
            'loc_total': fdata.get('loc_total', 0),
        })
    coupling.sort(key=lambda x: -x['efferent_coupling'])

    data_io = [
        {'id': nid, 'name': n['label'],
         'filename': n.get('filename',''),
         'lineno': n.get('lineno', 0),
         'complexity': n.get('complexity', 1),
         'fan_in': fan_in[nid], 'fan_out': fan_out[nid]}
        for nid, n in func_nodes.items() if n.get('has_db_io')
    ]

    god = [c for c in complex_issues
           if fan_out.get(c['id'], 0) >= 3 and c['complexity'] >= 5]

    tf = len(func_nodes)
    avg_c = sum(n.get('complexity',1) for n in func_nodes.values()) / max(tf, 1)
    health = max(0, min(100, round(
        100 - (len(dead)/max(tf,1))*30 - max(0, avg_c-3)*5 - len(god)*8 - sum(1 for c in coupling if c['efferent_coupling']>=3)*3
    )))

    return {
        'dead_functions': dead, 'complexity_issues': complex_issues,
        'high_fanin_functions': high_fanin, 'coupling_metrics': coupling,
        'data_entry_exit': data_io, 'god_functions': god,
        'summary': {
            'total_functions': tf, 'dead_functions_count': len(dead),
            'high_complexity_count': len(complex_issues), 'high_fanin_count': len(high_fanin),
            'data_points_count': len(data_io), 'health_score': health,
            'avg_complexity': round(avg_c, 2), 'total_files': len(all_files_data),
        }
    }

def generate_markdown_doc(all_files_data, graph, risk_report, summary, language):
    now    = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    health = risk_report['summary']['health_score']
    h_tag  = ('🟢 Healthy' if health >= 75 else '🟡 Moderate Risk' if health >= 50 else '🔴 High Risk')

    dead_ids    = {d['id'] for d in risk_report['dead_functions']}
    complex_ids = {c['id']: c['severity'] for c in risk_report['complexity_issues']}
    fanin_ids   = {f['id']: f['risk_score'] for f in risk_report['high_fanin_functions']}
    dbio_ids    = {d['id'] for d in risk_report['data_entry_exit']}

    nodes     = {n['id']: n for n in graph['nodes']}
    call_edges = [e for e in graph['edges'] if e['type'] == 'calls']
    fan_in    = defaultdict(int)
    fan_out   = defaultdict(int)
    callers   = defaultdict(list)
    callees   = defaultdict(list)
    for e in call_edges:
        fan_in[e['to']]   += 1
        fan_out[e['from']] += 1
        callers[e['to']].append(nodes.get(e['from'],{}).get('label','?'))
        callees[e['from']].append(nodes.get(e['to'],{}).get('label','?'))

    L = []
    L += [
        f"# {'🐍' if language=='python' else '☕'} CodeGrapher — Project Documentation",
        f"", f"> **Generated:** {now}  ", f"> **Language:** {language.title()}  ",
        f"> **Health Score:** {health}/100 {h_tag}  ",
        f"> **Files:** {summary['total_files']} | **Functions:** {summary['total_functions']} | **Classes:** {summary['total_classes']} | **Calls:** {summary['total_call_edges']}",
        f"", f"---", f"", f"## Table of Contents",
        f"1. [Project Overview](#1-project-overview)", f"2. [File Documentation](#2-file-documentation)",
        f"3. [Call Graph Reference](#3-call-graph-reference)", f"4. [Risk Report](#4-risk-report)",
        f"5. [Data Flow](#5-data-flow-analysis)", f"6. [Recommendations](#6-recommendations)",
        f"", f"---", f"", f"## 1. Project Overview", f"",
        f"| Metric | Value |", f"|--------|-------|",
        f"| Language | {language.title()} |", f"| Files | {summary['total_files']} |",
        f"| Functions | {summary['total_functions']} |", f"| Classes | {summary['total_classes']} |",
        f"| Call Edges | {summary['total_call_edges']} |", f"| Dead Functions | ⚠️ {risk_report['summary']['dead_functions_count']} |",
        f"| Avg Complexity | {risk_report['summary']['avg_complexity']} |", f"| Health Score | {health}/100 |",
        f"", f"---", f"", f"## 2. File Documentation", f"",
    ]
    cb = "``" + "`"
    for fname, fdata in all_files_data.items():
        fns = fdata.get('functions', {})
        cls = fdata.get('classes', {})
        imp = fdata.get('imports', [])
        L += [f"### 📄 `{fname}`", f"", f"- **LoC:** {fdata.get('loc_total',0)} | **Functions:** {len(fns)} | **Classes:** {len(cls)}"]
        if imp: L.append(f"- **Imports:** `{'`, `'.join(imp[:8])}{'...' if len(imp)>8 else ''}`")
        L.append("")

        for cls_name, cd in cls.items():
            bases = f" extends `{'`, `'.join(cd['bases'])}`" if cd.get('bases') else ""
            L += [f"#### Class `{cls_name}`{bases}", f"- Line: {cd.get('lineno',0)} | Methods: {len(cd.get('methods',[]))}", ""]

        for fk, fd in fns.items():
            fid = f"func::{fname}::{fk}"
            badges = []
            if fid in dead_ids:    badges.append("`⚫ DEAD`")
            sv = complex_ids.get(fid)
            if sv == 'CRITICAL':   badges.append("`🔴 HIGH COMPLEXITY`")
            elif sv == 'WARNING':  badges.append("`🟡 COMPLEX`")
            rs = fanin_ids.get(fid, 0)
            if rs >= 60:           badges.append(f"`⚡ CRITICAL DEP ({rs})`")
            elif rs >= 30:         badges.append(f"`⚠️ SHARED DEP ({rs})`")
            if fid in dbio_ids:    badges.append("`🗄️ DATA I/O`")
            if fd.get('is_async'): badges.append("`async`")

            args_s = ', '.join(fd.get('args',[]))
            sig    = (f"{' '.join(fd.get('modifiers',[]))} {fd.get('return_type','void')} {fd['name']}({args_s})"
                      if language == 'java' else f"{fd['name']}({args_s})")
            L += [
                f"##### `{sig.strip()}` {'  '.join(badges)}", f"", f"| | |", f"|-|-|",
                f"| Line | {fd.get('lineno',0)} |", f"| Complexity | {fd.get('complexity',1)} |",
                f"| LoC | {fd.get('loc',0)} |", f"| Fan-in | {fan_in[fid]} |", f"| Fan-out | {fan_out[fid]} |",
            ]
            if fd.get('class_name'): L.append(f"| Class | `{fd['class_name']}` |")
            L.append("")
            if callers[fid]: L.append(f"**Called by:** `{'`, `'.join(callers[fid][:6])}`\n")
            if callees[fid]: L.append(f"**Calls:** `{'`, `'.join(callees[fid][:6])}`\n")

    L += [f"---", f"", f"## 3. Call Graph Reference", f""]
    for fname, fdata in all_files_data.items():
        if not fdata.get('functions'): continue
        L += [f"### `{fname}`", "", cb]
        for fk, fd in fdata['functions'].items():
            fid = f"func::{fname}::{fk}"
            cl  = callees[fid]
            if cl:
                for c in cl[:5]: L.append(f"  {fd['name']:<28} ──▶  {c}")
            else:
                L.append(f"  {fd['name']:<28} (leaf — no outgoing calls)")
        L += [cb, ""]

    rr = risk_report; s = rr['summary']
    L += [f"---", f"", f"## 4. Risk Report", f"", f"### Health Score: {health}/100 {h_tag}", f"", f"### ⚫ Dead Functions ({len(rr['dead_functions'])})", f""]
    if rr['dead_functions']:
        L += ["| Function | File | Line | Complexity |", "|----------|------|------|------------|"]
        for d in rr['dead_functions']: L.append(f"| `{d['name']}` | `{d['filename']}` | {d['lineno']} | {d['complexity']} |")
        L.append("")
    else: L += ["> ✅ No dead functions.", ""]

    L += [f"### 🔴 Complexity Issues ({len(rr['complexity_issues'])})", ""]
    if rr['complexity_issues']:
        L += ["| Sev | Function | File | Complexity | LoC |", "|-----|----------|------|------------|-----|"]
        for c in rr['complexity_issues']: L.append(f"| {'🔴' if c['severity']=='CRITICAL' else '🟡'} | `{c['name']}` | `{c['filename']}` | {c['complexity']} | {c['loc']} |")
        L.append("")
    else: L += ["> ✅ No complexity issues.", ""]

    L += [f"### ⚡ Deletion Risk ({len(rr['high_fanin_functions'])})", ""]
    if rr['high_fanin_functions']:
        L += ["| Risk | Function | File | Callers |", "|------|----------|------|---------|"]
        for f in rr['high_fanin_functions']: L.append(f"| {f['risk_score']}/100 | `{f['name']}` | `{f['filename']}` | {f['fan_in']} |")
        L.append("")
    else: L += ["> ✅ No high-risk functions.", ""]

    L += [f"---", f"", f"## 5. Data Flow Analysis", f""]
    if rr['data_entry_exit']:
        L += ["| Function | File | Complexity |", "|----------|------|------------|"]
        for d in rr['data_entry_exit']: L.append(f"| `{d['name']}` | `{d['filename']}` | {d['complexity']} |")
        L.append("")
    else: L += ["> No data I/O patterns detected.", ""]

    L += [f"---", f"", f"## 6. Recommendations", f""]
    recs = []
    if s['dead_functions_count']: recs.append(f"🗑️ Remove **{s['dead_functions_count']} dead function(s)**.")
    if s['high_complexity_count']: recs.append(f"✂️ Refactor **{s['high_complexity_count']} complex function(s)**.")
    critical_deps = [f for f in rr['high_fanin_functions'] if f['risk_score']>=60]
    if critical_deps: recs.append(f"🛡️ Add tests for critical functions: {', '.join(f'`{f["name"]}`' for f in critical_deps[:3])}")
    if rr['data_entry_exit']: recs.append(f"🔒 Audit **{len(rr['data_entry_exit'])} data I/O point(s)**.")
    if rr['god_functions']: recs.append(f"👑 Split **{len(rr['god_functions'])} god function(s)**.")
    for r in recs: L.append(f"- {r}\n")
    if not recs: L.append("> ✅ Codebase looks healthy!")

    L += ["", f"---", f"", f"*Generated by CodeGrapher on {now}*", ""]
    return '\n'.join(L)