import { useState, useMemo, useEffect, useRef } from "react";

const DATA = {"pv":[1000000,999909.34,1000019.81,999994.73,1000007,1000032.05,1000235.93,1000259.28,1000178.01,1000082.02,1000070.81,1000158.46,1000166.26,1000148.92,1000082.39,999976.93,999957.02,1000024.45,999971.14,999989.02,1000093.66,1000177.3,1000110.42,999974.32,1000143.31,1000119.38,1000106.56,1000146.68,1000378.99,1000421.53,1000406.39,1000451.71,1000525.98,1000521.44,1000502.51,1000468.83,1000430.22,1000342.94,1000338.23,1000213.01,1000285.37,1000225.01,1000317.09,1000654.26,1000569.98,1000653.56,1000680.56,1000508.52,1000411.31,1000336.56,1000265.74,1000376.87,1000328.13,1000220.51,1000317.63,1000282.77,1000269.53,1000207.77,1000445.91,1000511.63,1000275.98,1000265.3,1000277.67,1000213.26,1000111.08,1000133.16,1000066.71,1000034.61,999943.25,1000112.56,1000149.31,1000104.84,1000125.02,1000276.98,1000177.98,999853.34,999933.41,999868.91,999913.28,999816.51,999974.32,999944.32,999821.81,999938.88,999955.79,999950.77,1000036.23,1000093.42,1000121.69,1000054.67,1000077.68,999989.4,999887.37,999918.53,999904.01,999831.03,999530.37,999443.61,999476.17,999491,999415.29,999396.93,999503.35,999675.32,999575.01,999320.59,999358.06,999354.68,999205.87,999109.4,999026.02,999077.56,999052.21,998932.74,998953.43,998896.12,998857,998884.68,998660.86,998534.7,998574.36,998532.84,998572.37,998506.69,998411.28,998565.75,998626.43,998627.28,998645.97,998745.57,998662.91,998729.62,998874.92,998887.68,998857.24,998897,998877.91,998915.96,998907.46,998866.46,998880.77,998809.81,998809.48,998777.18,998584.88,998298.5,998422.55,998390.41,998336.69,998393.51,998316.24,998377.48,998537.08,998526.87,998271.01,998177.99,998138.67,998138.43,998256.67,998353.52,998347.14,998232.9,998231.67,998219.95,998347.94,998335.83,998311.3,998187.51,998241.88,997915.39,997820.67,997829.39,997902.08,998034.73,998009.15,998163.59,998173,998130.27,998162.31,998176.8,998203.61,998154.47,998057.05,998006.67,997992.13,997865.16,997767.69,997763.94,997808.9,997825.18,997825.34,997835.71,997831.37,997853.64,997861.29,997844.01,997769.07,997747.9,997764.77,997825.65,997759.6,997760.34,997875.57,998026.36,998044.38,998090.11,998077.77,998060.14,997962.07,998013.49,998023.18,997938.81,997956.7,998010.57,997962.68,997936.92,997873.07,997920.54,998030.06,997957.43,998038.81,998090.46,997954.12,997942.91,997898.75,997768.03,997706.29,997816.54,997843.82,997840.35,997876.28,997844.74,997630.4,997599.24,997576.55,997647.43,997734.84,997719.29,997776.88,997784.89,997909.11,997864.83,997921.38,997814.13,997822.41,997943.2,998009.4,998004,998009.3,998038.83,997998.13,998098.89,997962.33,997958.11,997987.23,997858.74,997648.21,997654.68,997727.91,997670.76,997714.32,997665.11,997575.19,997569.05,997481.25,997358.9,997435.26,997510.31,997537.65,997587.5,997710.6,997755.22,997890.48,997687.25,997866.91,997869.05,997863.83,997715.23,997507.93,997069.34,997072.55,996884.19,996750.15,996319.7,996254.45,996266.75,996156.01,996114.93,996122.6,996098.25,996261.37,996226.09,996147.74,996130.51],"regimes":["High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","Sideways","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","High Volatility","Sideways"],"tm":{"total_return":"-3.59%","annualized_return":"-3.09%","sharpe_ratio":"-6.266","sortino_ratio":"-7.489","max_drawdown":"3.95%","win_rate":"43.00%","alpha":"-0.0711","beta":"-0.002","volatility":"1.13%","calmar_ratio":"-0.783","n_trades":1465,"profit_factor":"0.00","benchmark_return":"-9.63%"},"tr":[-474.4,-479.0,-447.2,-410.0,-523.5],"sent":[{"title":"Insider selling detected at AAPL, raises investor concerns","ticker":"AAPL","sentiment":"negative","confidence":0.75,"source":"Bloomberg"},{"title":"GOOGL CEO speaks at industry conference on future outlook","ticker":"GOOGL","sentiment":"neutral","confidence":0.8,"source":"Bloomberg"},{"title":"AAPL warns of slowing growth in key market segment","ticker":"AAPL","sentiment":"negative","confidence":0.84,"source":"Financial Times"},{"title":"Supply chain disruptions impact GOOGL production targets","ticker":"GOOGL","sentiment":"negative","confidence":0.75,"source":"Financial Times"},{"title":"AAPL to release quarterly results next week","ticker":"AAPL","sentiment":"neutral","confidence":0.83,"source":"WSJ"},{"title":"GOOGL reports record quarterly earnings, beating estimates","ticker":"GOOGL","sentiment":"positive","confidence":0.61,"source":"The Motley Fool"},{"title":"AAPL warns of slowing growth in key market segment","ticker":"AAPL","sentiment":"negative","confidence":0.84,"source":"Seeking Alpha"},{"title":"GOOGL launches innovative product line","ticker":"GOOGL","sentiment":"positive","confidence":0.84,"source":"The Motley Fool"},{"title":"Supply chain disruptions impact AAPL production targets","ticker":"AAPL","sentiment":"negative","confidence":0.86,"source":"MarketWatch"},{"title":"GOOGL misses earnings estimates, shares drop in after-hours","ticker":"GOOGL","sentiment":"negative","confidence":0.72,"source":"The Motley Fool"},{"title":"AAPL completes routine corporate restructuring","ticker":"AAPL","sentiment":"neutral","confidence":0.89,"source":"Seeking Alpha"},{"title":"GOOGL to release quarterly results next week","ticker":"GOOGL","sentiment":"neutral","confidence":0.66,"source":"CNBC"},{"title":"AAPL announces layoffs affecting 5% of workforce","ticker":"AAPL","sentiment":"negative","confidence":0.95,"source":"Seeking Alpha"},{"title":"GOOGL reports record quarterly earnings","ticker":"GOOGL","sentiment":"positive","confidence":0.64,"source":"Financial Times"},{"title":"AAPL files new patent applications in emerging technology","ticker":"AAPL","sentiment":"neutral","confidence":0.85,"source":"WSJ"}],"expl":[{"step":0,"text":"Agent HELD AAPL: MACD bearish, negative sentiment (75%), High Volatility regime, 93% agent consensus."},{"step":10,"text":"Agent HELD AAPL: RSI=63 overbought, MACD bullish, negative sentiment (84%), High Volatility regime."},{"step":20,"text":"Agent HELD AAPL: RSI=69 overbought, MACD bearish, neutral sentiment (83%), High Volatility regime."},{"step":30,"text":"Agent HELD AAPL: MACD bullish, negative sentiment (84%), Sideways regime, 94% consensus."},{"step":40,"text":"Agent HELD AAPL: MACD bearish, negative sentiment (86%), Sideways regime, 92% consensus."},{"step":50,"text":"Agent HELD AAPL: MACD bullish, neutral sentiment (89%), Sideways regime, 95% consensus."},{"step":60,"text":"Agent HELD AAPL: RSI=36 oversold, MACD bullish, negative sentiment (95%), Sideways regime."},{"step":70,"text":"Agent HELD AAPL: RSI=34 oversold, MACD bullish, neutral sentiment (85%), Sideways regime."},{"step":80,"text":"Agent HELD AAPL: RSI=77 overbought, MACD bearish, positive sentiment (87%), Sideways regime."},{"step":90,"text":"Agent HELD AAPL: MACD bearish, neutral sentiment (84%), Sideways regime, 93% consensus."}],"trades":[{"ticker":"AAPL","action":"SELL","shares":2.5,"price":778.89,"step":60},{"ticker":"GOOGL","action":"BUY","shares":2.9,"price":690.19,"step":60},{"ticker":"MSFT","action":"SELL","shares":1.1,"price":986.13,"step":60},{"ticker":"NFLX","action":"BUY","shares":7.5,"price":82.9,"step":60},{"ticker":"TSLA","action":"BUY","shares":3.6,"price":293.94,"step":60},{"ticker":"AAPL","action":"SELL","shares":1.6,"price":773.61,"step":61},{"ticker":"GOOGL","action":"BUY","shares":0.1,"price":670.03,"step":61},{"ticker":"MSFT","action":"BUY","shares":0.0,"price":995.73,"step":61},{"ticker":"NFLX","action":"SELL","shares":7.1,"price":83.51,"step":61},{"ticker":"TSLA","action":"SELL","shares":1.4,"price":285.16,"step":61}]};

const TICKERS = ["AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"];

function fmt(n) { return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 }); }
function pct(s) { return s; }

function MiniChart({ data, color, height = 48, width = 160 }) {
  const mn = Math.min(...data);
  const mx = Math.max(...data);
  const range = mx - mn || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - mn) / range) * (height - 4) - 2;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

function MetricCard({ label, value, sub, trend, color }) {
  return (
    <div style={{
      background: "var(--color-background-secondary)",
      borderRadius: "var(--border-radius-md)",
      padding: "14px 16px",
      minWidth: 0
    }}>
      <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 4, letterSpacing: "0.02em" }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 500, color: color || "var(--color-text-primary)", lineHeight: 1.2 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function RegimeBadge({ regime }) {
  const colors = {
    "High Volatility": { bg: "#EEEDFE", text: "#534AB7", dbg: "#3C3489", dt: "#CECBF6" },
    "Sideways": { bg: "#FAEEDA", text: "#854F0B", dbg: "#633806", dt: "#FAC775" },
    "Bull Market": { bg: "#EAF3DE", text: "#3B6D11", dbg: "#27500A", dt: "#C0DD97" },
    "Bear Market": { bg: "#FCEBEB", text: "#A32D2D", dbg: "#791F1F", dt: "#F7C1C1" },
  };
  const isDark = typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const c = colors[regime] || colors["Sideways"];
  return (
    <span style={{
      display: "inline-block",
      fontSize: 11,
      fontWeight: 500,
      padding: "3px 10px",
      borderRadius: "var(--border-radius-md)",
      background: isDark ? c.dbg : c.bg,
      color: isDark ? c.dt : c.text,
    }}>{regime}</span>
  );
}

function SentimentDot({ sentiment }) {
  const c = sentiment === "positive" ? "#22c55e" : sentiment === "negative" ? "#ef4444" : "#eab308";
  return <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: c, marginRight: 6, flexShrink: 0 }} />;
}

function PortfolioChart({ data }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    const loadChart = async () => {
      if (!window.Chart) {
        await new Promise((res) => {
          const s = document.createElement("script");
          s.src = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js";
          s.onload = res;
          document.head.appendChild(s);
        });
      }
      if (chartRef.current) chartRef.current.destroy();

      const regimeColors = data.map((_, i) => {
        const r = DATA.regimes[i] || "Sideways";
        return r === "High Volatility" ? "rgba(127,119,221,0.08)" : "rgba(234,179,8,0.04)";
      });

      const isDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
      const gridColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";
      const textColor = isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.45)";

      chartRef.current = new window.Chart(canvasRef.current, {
        type: "line",
        data: {
          labels: data.map((_, i) => i),
          datasets: [{
            label: "Portfolio",
            data: data,
            borderColor: "#534AB7",
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.3,
            fill: true,
            backgroundColor: (ctx) => {
              const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, 260);
              g.addColorStop(0, "rgba(83,74,183,0.12)");
              g.addColorStop(1, "rgba(83,74,183,0)");
              return g;
            },
          }, {
            label: "Benchmark",
            data: data.map((_, i) => 1000000 * (1 - 0.0963 * i / data.length)),
            borderColor: isDark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.15)",
            borderWidth: 1,
            borderDash: [4, 3],
            pointRadius: 0,
            tension: 0.3,
            fill: false,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: {
            callbacks: { label: (c) => "$" + Math.round(c.parsed.y).toLocaleString() }
          }},
          scales: {
            x: { display: true, grid: { display: false }, ticks: { display: true, maxTicksLimit: 6, color: textColor, font: { size: 11 } } },
            y: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 11 }, callback: (v) => "$" + (v / 1000).toFixed(0) + "k" },
              min: Math.min(...data) - 500,
              max: Math.max(...data) + 500
            }
          },
          interaction: { intersect: false, mode: "index" }
        }
      });
    };
    loadChart();
    return () => { if (chartRef.current) chartRef.current.destroy(); };
  }, [data]);

  return <canvas ref={canvasRef} />;
}

function TrainingChart() {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);
  useEffect(() => {
    if (!canvasRef.current || !window.Chart) return;
    if (chartRef.current) chartRef.current.destroy();
    const isDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
    chartRef.current = new window.Chart(canvasRef.current, {
      type: "bar",
      data: {
        labels: DATA.tr.map((_, i) => `Ep ${i + 1}`),
        datasets: [{ data: DATA.tr, backgroundColor: "#7F77DD", borderRadius: 4, barThickness: 28 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.45)", font: { size: 11 } } },
          y: { grid: { color: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" }, ticks: { color: isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.45)", font: { size: 11 } } }
        }
      }
    });
    return () => { if (chartRef.current) chartRef.current.destroy(); };
  }, []);
  return <canvas ref={canvasRef} />;
}

const TABS = ["overview", "trades", "sentiment", "explanations"];

export default function Dashboard() {
  const [tab, setTab] = useState("overview");
  const pv = DATA.pv;
  const currentValue = pv[pv.length - 1];
  const peakValue = Math.max(...pv);
  const currentRegime = DATA.regimes[DATA.regimes.length - 1] || "Sideways";
  const currentDD = ((peakValue - currentValue) / peakValue * 100).toFixed(2);
  const totalReturn = ((currentValue - 1000000) / 1000000 * 100).toFixed(2);

  return (
    <div style={{ fontFamily: "var(--font-sans)", maxWidth: 800, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 500, margin: 0, color: "var(--color-text-primary)" }}>RL trading agent</h2>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>PPO + SAC ensemble &middot; 5 assets &middot; LSTM backbone</p>
        </div>
        <RegimeBadge regime={currentRegime} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginBottom: 20 }}>
        <MetricCard label="Portfolio value" value={fmt(currentValue)} sub={`${totalReturn}% total`} color={totalReturn >= 0 ? "#22c55e" : "#ef4444"} />
        <MetricCard label="Max drawdown" value={DATA.tm.max_drawdown} sub="vs 9.63% bench" />
        <MetricCard label="Sharpe ratio" value={DATA.tm.sharpe_ratio} />
        <MetricCard label="Win rate" value={DATA.tm.win_rate} sub={`${DATA.tm.n_trades} trades`} />
      </div>

      <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "0.5px solid var(--color-border-tertiary)", paddingBottom: 4 }}>
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            background: tab === t ? "var(--color-background-secondary)" : "transparent",
            border: "none", borderRadius: "var(--border-radius-md)",
            padding: "6px 14px", fontSize: 13, fontWeight: tab === t ? 500 : 400,
            color: tab === t ? "var(--color-text-primary)" : "var(--color-text-secondary)",
            cursor: "pointer", textTransform: "capitalize"
          }}>{t}</button>
        ))}
      </div>

      {tab === "overview" && (
        <div>
          <div style={{ display: "flex", gap: 12, marginBottom: 16, fontSize: 12, color: "var(--color-text-secondary)" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 10, height: 3, borderRadius: 1, background: "#534AB7", display: "inline-block" }} />Portfolio
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 10, height: 0, borderTop: "1px dashed rgba(128,128,128,0.5)", display: "inline-block" }} />Benchmark (S&P 500)
            </span>
          </div>
          <div style={{ position: "relative", height: 280, marginBottom: 24 }}>
            <PortfolioChart data={pv} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10, marginBottom: 24 }}>
            <MetricCard label="Sortino ratio" value={DATA.tm.sortino_ratio} />
            <MetricCard label="Beta" value={DATA.tm.beta} sub="Market sensitivity" />
            <MetricCard label="Alpha" value={DATA.tm.alpha} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", marginBottom: 8 }}>Training rewards</div>
              <div style={{ position: "relative", height: 140 }}>
                <TrainingChart />
              </div>
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", marginBottom: 8 }}>Regime timeline</div>
              <div style={{ display: "flex", height: 24, borderRadius: 4, overflow: "hidden", marginBottom: 8 }}>
                {(() => {
                  const segments = [];
                  let curr = DATA.regimes[0], start = 0;
                  for (let i = 1; i <= DATA.regimes.length; i++) {
                    if (i === DATA.regimes.length || DATA.regimes[i] !== curr) {
                      const w = ((i - start) / DATA.regimes.length * 100).toFixed(1) + "%";
                      const bg = curr === "High Volatility" ? "#AFA9EC" : "#FAC775";
                      segments.push(<div key={start} style={{ width: w, background: bg, height: "100%" }} title={`${curr}: day ${start}-${i}`} />);
                      if (i < DATA.regimes.length) { curr = DATA.regimes[i]; start = i; }
                    }
                  }
                  return segments;
                })()}
              </div>
              <div style={{ display: "flex", gap: 12, fontSize: 11, color: "var(--color-text-secondary)" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: "#AFA9EC" }} />High volatility
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: "#FAC775" }} />Sideways
                </span>
              </div>

              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", marginBottom: 8 }}>Reward function</div>
                <div style={{ fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.7, fontFamily: "var(--font-mono)" }}>
                  R = 0.35·R<sub>ann</sub> − 0.25·σ<sub>down</sub> + 0.20·D<sub>ret</sub> + 0.20·T<sub>ry</sub>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === "trades" && (
        <div>
          <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>
            Recent trades from evaluation run ({DATA.tm.n_trades} total)
          </div>
          <div style={{ border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-lg)", overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--color-background-secondary)" }}>
                  {["Step", "Ticker", "Action", "Shares", "Price"].map(h => (
                    <th key={h} style={{ padding: "8px 12px", textAlign: "left", fontWeight: 500, color: "var(--color-text-secondary)", fontSize: 12 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {DATA.trades.map((t, i) => (
                  <tr key={i} style={{ borderTop: "0.5px solid var(--color-border-tertiary)" }}>
                    <td style={{ padding: "6px 12px", color: "var(--color-text-tertiary)" }}>{t.step}</td>
                    <td style={{ padding: "6px 12px", fontWeight: 500 }}>{t.ticker}</td>
                    <td style={{ padding: "6px 12px" }}>
                      <span style={{
                        fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: "var(--border-radius-md)",
                        background: t.action === "BUY" ? "var(--color-background-success)" : "var(--color-background-danger)",
                        color: t.action === "BUY" ? "var(--color-text-success)" : "var(--color-text-danger)"
                      }}>{t.action}</span>
                    </td>
                    <td style={{ padding: "6px 12px" }}>{t.shares.toFixed(1)}</td>
                    <td style={{ padding: "6px 12px" }}>${t.price.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "sentiment" && (
        <div>
          <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>
            LLM-analyzed news sentiment used for decision validation
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {DATA.sent.map((s, i) => (
              <div key={i} style={{
                background: "var(--color-background-primary)",
                border: "0.5px solid var(--color-border-tertiary)",
                borderRadius: "var(--border-radius-lg)",
                padding: "12px 16px"
              }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                  <SentimentDot sentiment={s.sentiment} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", lineHeight: 1.4 }}>{s.title}</div>
                    <div style={{ display: "flex", gap: 12, marginTop: 4, fontSize: 11, color: "var(--color-text-tertiary)" }}>
                      <span>{s.ticker}</span>
                      <span>{s.source}</span>
                      <span>{Math.round(s.confidence * 100)}% confidence</span>
                      <span style={{ textTransform: "capitalize" }}>{s.sentiment}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "explanations" && (
        <div>
          <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>
            Agent decision explanations combining RL policy, sentiment, and regime
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {DATA.expl.map((e, i) => (
              <div key={i} style={{
                background: "var(--color-background-primary)",
                border: "0.5px solid var(--color-border-tertiary)",
                borderRadius: "var(--border-radius-lg)",
                padding: "12px 16px",
                borderLeft: "3px solid #7F77DD"
              }}>
                <div style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginBottom: 4 }}>Step {e.step}</div>
                <div style={{ fontSize: 13, color: "var(--color-text-primary)", lineHeight: 1.6 }}>{e.text}</div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 24 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", marginBottom: 12 }}>System architecture</div>
            <div style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-lg)", padding: 16, fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)", lineHeight: 1.8, whiteSpace: "pre" }}>
{`┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Data        │───▶│  LSTM Feature │───▶│  PPO Agent   │──┐
│  Pipeline    │    │  Extractor    │    └──────────────┘  │
│  (yfinance)  │    └──────────────┘    ┌──────────────┐  ├──▶ Ensemble
└─────────────┘                         │  SAC Agent   │──┘    Action
       │         ┌──────────────┐       └──────────────┘       │
       └────────▶│  Regime      │──────────────────────────────┤
                 │  Detector    │                               │
                 └──────────────┘       ┌──────────────┐       │
                                        │  Sentiment   │───────┤
                 ┌──────────────┐       │  Validator   │       │
                 │  Risk Mgmt   │◀──────┴──────────────┘       │
                 │  (external)  │◀─────────────────────────────┘
                 └──────┬───────┘
                        │
                 ┌──────▼───────┐
                 │  Trading     │
                 │  Environment │
                 └──────────────┘`}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
