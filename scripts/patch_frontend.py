"""Apply all frontend changes cleanly in one pass."""
path = r'D:\Agent\PrivateFinanaceExpert\web\index.html'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# ── Change 1: Search + autocomplete ──
old1 = """      const doResearch = useCallback(async () => {
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
      }, [query]);"""

new1 = """      const [error, setError] = useState('');
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
        else { setKlineData(null); setError('未找到 K 线数据。请输入6位代码，如 600519。'); }
        if (priceData) setStockInfo(priceData);
        setLoading(false);
      }, []);

      const selectStock = (code) => { setQuery(code); setSuggestions([]); doResearchCode(code); };

      const doResearch = useCallback(async () => {
        const code = query.trim(); if (!code) return;
        setSuggestions([]); doResearchCode(code);
      }, [query, doResearchCode]);"""

assert old1 in c, "old1 not found"
c = c.replace(old1, new1)

# ── Change 2: Search bar UI ──
old2 = '<input className="form-input" placeholder="输入代码 如 600519" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key===\'Enter\'&&doResearch()} style={{maxWidth:200}} />'
new2 = """<div style={{position:'relative',flex:1,minWidth:200,maxWidth:300}}>
              <input className="form-input" placeholder="输入代码或名称 如 600519 茅台" value={query}
                onChange={e=>{setQuery(e.target.value);searchStocks(e.target.value);}}
                onKeyDown={e=>e.key==='Enter'&&doResearch()}
                style={{width:'100%',boxSizing:'border-box'}}
                onBlur={()=>setTimeout(()=>setSuggestions([]),200)} />
              {suggestions.length > 0 && (
                <div style={{position:'absolute',top:'100%',left:0,right:0,zIndex:99,
                  background:'var(--elevated)',border:'1px solid var(--border)',borderRadius:'0 0 6px 6px',maxHeight:240,overflow:'auto'}}>
                  {suggestions.map(s => (
                    <div key={s.code} onMouseDown={()=>selectStock(s.code)}
                      style={{padding:'8px 14px',cursor:'pointer',fontSize:13,
                        borderBottom:'1px solid var(--border)',
                        color:'var(--text)',display:'flex',justifyContent:'space-between'}}>
                      <span>{s.name}</span>
                      <span style={{color:'var(--muted)',fontSize:12,fontFamily:'var(--font-mono)'}}>{s.code}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>"""
assert old2 in c, "old2 not found"
c = c.replace(old2, new2)

# Add error display after the search button
c = c.replace(
    '<button className="btn btn-primary" onClick={doResearch} disabled={loading}>{loading?\'搜索中...\':\'搜索\'}</button>',
    '<button className="btn btn-primary" onClick={doResearch} disabled={loading}>{loading?\'搜索中...\':\'搜索\'}</button>\n            {error && <span style={{fontSize:12,color:\'var(--warning)\'}}>{error}</span>}'
)

# ── Change 3: K-line linear x-axis ──
c = c.replace(
    'const labels = (data || []).map(d => d.date?.slice(5) || "");\n      const closes = (data || []).map(d => d.close);',
    'const indices = useMemo(() => (data || []).map((_, i) => i), [data]);\n      const dateLabels = useMemo(() => (data || []).map(d => d.date?.slice(5) || ""), [data]);\n      const closes = useMemo(() => (data || []).map(d => d.close), [data]);'
)

c = c.replace('.getPixelForValue(labels[i])', '.getPixelForValue(indices[i])')

# Linear x-axis scale
c = c.replace(
    "x: { grid: { color: 'rgba(99,130,255,0.04)' }, ticks: { color: '#8892A8', font: { size: 10 }, maxTicksLimit: 8 } },",
    "x: { type: 'linear', grid: { color: 'rgba(99,130,255,0.04)' }, ticks: { color: '#8892A8', font: { size: 10 }, maxTicksLimit: 8, callback: (v) => dateLabels[v] || '' } },"
)

# Fix dependency arrays
c = c.replace('[data, labels]', '[data, indices]')
c = c.replace('[maPeriods, maLines, maColors, labels]', '[maPeriods, maLines, maColors, indices]')
c = c.replace('[subIndicator, macdData, kdjData, data, labels]', '[subIndicator, macdData, kdjData, data, indices]')
c = c.replace('[data, labels, closes,', '[data, indices, closes,')

# ── Write back ──
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print(f'Done: {len(c)} chars')
