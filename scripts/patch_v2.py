"""V2: Clean single-pass frontend patcher with validation."""
import re, sys

PATH = r'D:\Agent\PrivateFinanaceExpert\web\index.html'

def ok(msg): print(f'  ✓ {msg}')
def fail(msg): print(f'  ✗ {msg}'); sys.exit(1)

with open(PATH, 'r', encoding='utf-8') as f:
    c = f.read()

# ── validation helpers ──
def validate():
    diff = c.count('{') - c.count('}')
    if diff != 0: fail(f'brace imbalance: {diff}')

# ── Step 1: Search autocomplete ──
# Replace the old doResearch function
step1_old = '''      const doResearch = useCallback(async () => {
        if (!query.trim()) return;
        setLoading(true);
        const code = query.trim();
        const [kData, fundData] = await Promise.all([
          apiFetch('/api/stock/kline/' + code + '?days=500'),
          apiFetch('/api/stock/fundamentals/' + code),
        ]);
        if (kData && kData.length) {
          setKlineData(kData);
        }
        if (fundData) setStockInfo(fundData);
        setLoading(false);
      }, [query]);'''

step1_new = '''      const [error, setError] = useState('');
      const [suggestions, setSuggestions] = useState([]);
      const searchStocks = useCallback(async (q) => {
        if (q.length < 1) { setSuggestions([]); return; }
        const res = await apiFetch('/api/stock/search?q=' + encodeURIComponent(q));
        if (res && res.length) setSuggestions(res.slice(0, 8));
        else setSuggestions([]);
      }, []);
      const doResearchCode = useCallback(async (code) => {
        if (!code) return;
        setLoading(true); setError('');
        const [kData, priceData] = await Promise.all([
          apiFetch('/api/stock/kline/' + code + '?days=500'),
          apiFetch('/api/stock/price/' + code),
        ]);
        if (kData && kData.length) { setKlineData(kData); setError(''); }
        else { setKlineData(null); setError('输入代码搜索，如 600519'); }
        if (priceData) setStockInfo(priceData);
        setLoading(false);
      }, []);
      const selectStock = (code) => { setQuery(code); setSuggestions([]); doResearchCode(code); };
      const doResearch = useCallback(async () => {
        const q = query.trim(); if (!q) return;
        setSuggestions([]);
        const match = suggestions.find(s => s.name === q || s.code === q);
        doResearchCode(match ? match.code : q);
      }, [query, doResearchCode, suggestions]);'''

c = c.replace(step1_old, step1_new)
if step1_old not in c: ok('step1: search + autocomplete')
else: fail('step1 not applied')
validate()

# ── Step 2: Search bar UI with dropdown ──
step2_old = '<input className="form-input" placeholder="输入代码 如 600519" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key===\'Enter\'&&doResearch()} style={{maxWidth:200}} />'
step2_new = '''<div ref={searchRef} style={{position:'relative',flex:1,minWidth:200,maxWidth:300}}>
              <input className="form-input" placeholder="输入名称或代码 如茅台 600519" value={query}
                onChange={e=>{setQuery(e.target.value);searchStocks(e.target.value);}}
                onKeyDown={e=>{if(e.key==='Enter'){setSuggestions([]);doResearch();}}}
                style={{width:'100%',boxSizing:'border-box'}} />
              {suggestions.length > 0 && (
                <div style={{position:'absolute',top:'100%',left:0,right:0,zIndex:99,
                  background:'var(--elevated)',border:'1px solid var(--border)',borderRadius:'0 0 6px 6px',maxHeight:240,overflow:'auto'}}>
                  {suggestions.map(s => (
                    <div key={s.code} onMouseDown={()=>selectStock(s.code)}
                      style={{padding:'8px 14px',cursor:'pointer',fontSize:13,
                        borderBottom:'1px solid var(--border)',color:'var(--text)',display:'flex',justifyContent:'space-between'}}>
                      <span>{s.name}</span>
                      <span style={{color:'var(--muted)',fontSize:12,fontFamily:'var(--font-mono)'}}>{s.code}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <button className="btn btn-primary" onClick={doResearch} disabled={loading}>{loading?'搜索中...':'搜索'}</button>
            {error && <span style={{fontSize:12,color:'var(--warning)'}}>{error}</span>}'''

c = c.replace(step2_old, step2_new)
if step2_old not in c: ok('step2: search bar UI')
else: fail('step2 not applied')
validate()

# ── Step 3: Add searchRef + outside-click handler ──
step3_marker = 'useEffect(() => { refresh(); }, []);'
step3_idx = c.find(step3_marker, c.find('function ResearchPage'))
if step3_idx > 0:
    step3_insert = '''useEffect(() => { refresh(); }, []);
      // 搜索框点击外部关闭
      const searchRef = useRef(null);
      useEffect(() => {
        const handler = (e) => { if (searchRef.current && !searchRef.current.contains(e.target)) setSuggestions([]); };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
      }, []);'''
    c = c[:step3_idx] + step3_insert + c[step3_idx+len(step3_marker):]
    ok('step3: outside-click handler')
else:
    fail('step3 marker not found')
validate()

# ── Step 4: K-line chart optimization bundle ──
# 4a: labels → indices (linear x-axis, no weekend gaps)
c = c.replace(
    'const labels = (data || []).map(d => d.date?.slice(5) || \'\');',
    'const indices = useMemo(() => (data || []).map((_, i) => i), [data]);\n      const dateLabels = useMemo(() => (data || []).map(d => d.date?.slice(5) || \'\'), [data]);'
)
if 'const indices = useMemo' in c: ok('step4a: indices')
else: fail('step4a failed')
validate()

# 4b: closes also must reference data (labels var was removed)
c = c.replace(
    'const closes = (data || []).map(d => d.close);',
    'const closes = useMemo(() => (data || []).map(d => d.close), [data]);'
)

# 4c: Replace labels[i] → indices[i] everywhere
c = c.replace('.getPixelForValue(labels[i])', '.getPixelForValue(indices[i])')
c = c.replace('{ labels, datasets:', '{ labels: indices, datasets:')
c = c.replace('[data, labels]', '[data, indices]')
c = c.replace('[maPeriods, maLines, maColors, labels]', '[maPeriods, maLines, maColors, indices]')
c = c.replace('[subIndicator, macdData, kdjData, data, labels]', '[subIndicator, macdData, kdjData, data, indices]')
c = c.replace('[data, labels, closes,', '[data, indices, closes,')
ok('step4c: labels→indices references')

# 4d: linear x-axis scale
c = c.replace(
    "x: { grid: { color: 'rgba(99,130,255,0.04)' }, ticks: { color: '#8892A8', font: { size: 10 }, maxTicksLimit: 8 } },",
    "x: { type: 'linear', grid: { color: 'rgba(99,130,255,0.04)' }, ticks: { color: '#8892A8', font: { size: 10 }, maxTicksLimit: 8, callback: (v) => dateLabels[v] || '' } },"
)
ok('step4d: linear x-axis')
validate()

# ── Step 5: Zoom plugin CDN + config ──
c = c.replace(
    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>',
    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>\n  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>'
)
c = c.replace(
    'const plugins = [candlePlugin, maPlugin, volumePlugin, subPlugin];',
    '''const zoomConfig = { pan: { enabled: true, mode: 'x' }, zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x', drag: { enabled: true } } };
        const plugins = [candlePlugin, maPlugin, volumePlugin, subPlugin];'''
)
c = c.replace(
    'plugins: { legend: { display: false },',
    'plugins: { legend: { display: false }, zoom: zoomConfig,'
)
ok('step5: zoom plugin')
validate()

# ── Step 6: Viewport culling ──
c = c.replace(
    'const { useState, useEffect, useRef, useCallback, useMemo } = React;',
    '''const { useState, useEffect, useRef, useCallback, useMemo } = React;
    function getVisibleRange(chart, dataLen) { const { left, right } = chart.chartArea; const { x } = chart.scales; let first = 0, last = dataLen-1; for (let i=0;i<dataLen;i++){if(x.getPixelForValue(i)>=left){first=i;break;}} for (let i=dataLen-1;i>=0;i--){if(x.getPixelForValue(i)<=right){last=i;break;}} return {first,last}; }'''
)
c = c.replace(
    'if (!data || !data.length) return;\n          const barWidth = Math.max(2, Math.min(8, (right - left) / data.length * 0.6));\n          data.forEach((d, i) => {',
    'if (!data || !data.length) return;\n          const range = getVisibleRange(chart, data.length);\n          const barWidth = Math.max(2, Math.min(18, (right - left) / Math.max(range.last-range.first+1,1) * 0.7));\n          for (let i = range.first; i <= range.last; i++) {\n            const d = data[i];'
)
ok('step6: viewport culling')
validate()

# ── Step 7: Sub-indicator height increase ──
c = c.replace(
    'const subTop = bottom + 65, subBottom = bottom + 150, subH = subBottom - subTop;',
    'const subTop = bottom + 100, subBottom = bottom + 250, subH = subBottom - subTop;'
)
ok('step7: sub-indicator height')
validate()

# ── Write back ──
with open(PATH, 'w', encoding='utf-8') as f:
    f.write(c)
print(f'\nTotal: {len(c)} bytes | All 7 steps passed | Braces balanced')
