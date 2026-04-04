import { useState, useEffect } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// ─── Config ───────────────────────────────────────────────

const MODELS = [
  { value: "ensemble", label: "Ensemble (PPO + SAC)", desc: "Best of both worlds" },
  { value: "ppo", label: "PPO", desc: "Stable, on-policy" },
  { value: "sac", label: "SAC", desc: "Exploratory, off-policy" },
  { value: "ppo_lstm", label: "PPO + LSTM", desc: "PPO with temporal memory" },
  { value: "sac_lstm", label: "SAC + LSTM", desc: "SAC with temporal memory" },
];

const RISK_LEVELS = [
  { value: "low", label: "Conservative", desc: "5% max DD · Small positions", icon: "🛡" },
  { value: "medium", label: "Moderate", desc: "15% max DD · Balanced", icon: "⚖" },
  { value: "high", label: "Aggressive", desc: "25% max DD · Large positions", icon: "🎯" },
];

const ASSET_OPTIONS = [
  { value: "stocks", label: "Stocks", icon: "📈" },
  { value: "crypto", label: "Crypto", icon: "₿" },
  { value: "forex", label: "Forex", icon: "💱" },
  { value: "commodities", label: "Commodities", icon: "🛢" },
];

const EPISODE_PRESETS = [
  { value: 50, label: "50", desc: "Quick test" },
  { value: 100, label: "100", desc: "Fast" },
  { value: 250, label: "250", desc: "Standard" },
  { value: 500, label: "500", desc: "Recommended" },
  { value: 1000, label: "1K", desc: "Thorough" },
  { value: 2000, label: "2K", desc: "Deep train" },
];

const TIMESTEP_OPTIONS = [
  { value: 512, label: "512" },
  { value: 1024, label: "1,024" },
  { value: 2048, label: "2,048 (default)" },
  { value: 4096, label: "4,096" },
  { value: 8192, label: "8,192" },
];

const LR_PRESETS = [
  { value: 0.0001, label: "1e-4", desc: "Slow, stable" },
  { value: 0.0003, label: "3e-4", desc: "Balanced (default)" },
  { value: 0.001, label: "1e-3", desc: "Fast, volatile" },
];

const BATCH_OPTIONS = [32, 64, 128, 256];

// ─── Helpers ──────────────────────────────────────────────

function Section({
  title,
  subtitle,
  icon,
  children,
}: {
  title: string;
  subtitle?: string;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl bg-white/70 dark:bg-neutral-900/70 backdrop-blur-md border border-neutral-200/70 dark:border-neutral-800/50 shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-neutral-100/80 dark:border-neutral-800/50">
        <span className="text-base">{icon}</span>
        <div>
          <h3 className="text-[13px] font-semibold text-neutral-800 dark:text-neutral-100">
            {title}
          </h3>
          {subtitle && (
            <p className="text-[11px] text-neutral-400 mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-2">
      {children}
    </div>
  );
}

function NumberInput({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  prefix,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  prefix?: string;
  suffix?: string;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="relative flex items-center">
        {prefix && (
          <span className="absolute left-3 text-[12px] text-neutral-400 font-medium select-none">
            {prefix}
          </span>
        )}
        <input
          type="number"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className={`w-full rounded-xl bg-neutral-50 dark:bg-neutral-800/80 border border-neutral-200 dark:border-neutral-700/60 text-[13px] text-neutral-800 dark:text-neutral-200 font-medium py-2.5 outline-none focus:border-emerald-500 dark:focus:border-emerald-500 transition-colors ${prefix ? "pl-7 pr-3" : "px-3"} ${suffix ? "pr-10" : ""}`}
        />
        {suffix && (
          <span className="absolute right-3 text-[11px] text-neutral-400 font-medium select-none">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────

export default function SettingsPage() {
  const [profile, setProfile] = useState({
    risk_tolerance: "medium",
    asset_classes: ["stocks"],
    selected_model: "ensemble",
    capital_allocation: 1_000_000,
    max_drawdown: 0.15,
    stop_loss_pct: 0.05,
    take_profit_pct: 0.15,
    reward_weights: { w1: 0.35, w2: 0.25, w3: 0.2, w4: 0.2 },
    // Training config
    n_episodes: 500,
    n_steps: 2048,
    learning_rate: 0.0003,
    batch_size: 64,
    gamma: 0.99,
    gae_lambda: 0.95,
  });
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saveError, setSaveError] = useState("");

  // GPU / device state
  const [deviceInfo, setDeviceInfo] = useState<{
    available: boolean;
    device: string;
    name: string | null;
    vram_mb?: number;
    error: string | null;
  }>({ available: false, device: "cpu", name: null, error: null });
  const [deviceLoading, setDeviceLoading] = useState(false);
  const [deviceError, setDeviceError] = useState("");

  useEffect(() => {
    fetch(`${API}/profile`)
      .then((r) => r.json())
      .then((d) => {
        if (d.data) setProfile((prev) => ({ ...prev, ...d.data }));
      })
      .catch(() => {});
    // Fetch GPU / device info
    fetch(`${API}/device`)
      .then((r) => r.json())
      .then((d) => {
        if (d.data) setDeviceInfo(d.data);
      })
      .catch(() => {});
  }, []);

  const handleDeviceSwitch = async (target: "cpu" | "cuda") => {
    setDeviceLoading(true);
    setDeviceError("");
    try {
      const r = await fetch(`${API}/device`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device: target }),
      });
      const d = await r.json();
      if (r.ok) {
        setDeviceInfo(d.data);
      } else {
        setDeviceError(d.detail || "Failed to switch device");
      }
    } catch {
      setDeviceError("Backend offline");
    } finally {
      setDeviceLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setSaved(false);
    setSaveError("");
    try {
      const r = await fetch(`${API}/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      if (r.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } else {
        setSaveError("Save failed — check backend");
      }
    } catch {
      setSaveError("Backend offline");
    } finally {
      setLoading(false);
    }
  };

  const updateWeight = (key: string, value: number) => {
    setProfile((p) => ({
      ...p,
      reward_weights: { ...p.reward_weights, [key]: value },
    }));
  };

  const toggleAsset = (asset: string) => {
    setProfile((p) => ({
      ...p,
      asset_classes: p.asset_classes.includes(asset)
        ? p.asset_classes.filter((a) => a !== asset)
        : [...p.asset_classes, asset],
    }));
  };

  const weightSum =
    profile.reward_weights.w1 +
    profile.reward_weights.w2 +
    profile.reward_weights.w3 +
    profile.reward_weights.w4;

  const totalTimesteps = profile.n_episodes * profile.n_steps;
  const fmtNum = (n: number) =>
    n >= 1_000_000
      ? `${(n / 1_000_000).toFixed(1)}M`
      : n >= 1_000
        ? `${(n / 1_000).toFixed(0)}K`
        : String(n);

  return (
    <div className="h-full overflow-y-auto">
      {/* Gradient header */}
      <div className="sticky top-0 z-10 bg-neutral-50/80 dark:bg-neutral-950/80 backdrop-blur-md border-b border-neutral-200/60 dark:border-neutral-800/60 px-6 py-4">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-[15px] font-bold text-neutral-900 dark:text-neutral-100 tracking-tight">
              Settings
            </h1>
            <p className="text-[11px] text-neutral-400 mt-0.5">
              Agent configuration, risk parameters, and training setup
            </p>
          </div>
          <div className="flex items-center gap-2">
            {saveError && (
              <span className="text-[11px] text-red-500 font-medium">{saveError}</span>
            )}
            {saved && (
              <span className="text-[11px] text-emerald-500 font-semibold">
                ✓ Saved
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={loading}
              className={`rounded-xl px-4 py-2 text-[12px] font-bold tracking-wide transition-all disabled:opacity-50 ${
                saved
                  ? "bg-emerald-500 text-white"
                  : "bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 hover:opacity-80"
              }`}
            >
              {loading ? "Saving…" : saved ? "Saved ✓" : "Save changes"}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-6 pb-20 space-y-4">

        {/* ── Risk Tolerance ────────────────────────── */}
        <Section icon="🛡" title="Risk Tolerance" subtitle="Controls drawdown limits and position sizing">
          <div className="grid grid-cols-3 gap-2">
            {RISK_LEVELS.map((lvl) => {
              const active = profile.risk_tolerance === lvl.value;
              return (
                <button
                  key={lvl.value}
                  onClick={() =>
                    setProfile((p) => ({
                      ...p,
                      risk_tolerance: lvl.value,
                      max_drawdown:
                        lvl.value === "low" ? 0.05 : lvl.value === "medium" ? 0.15 : 0.25,
                    }))
                  }
                  className={`rounded-xl border p-3 text-left transition-all duration-150 ${
                    active
                      ? "border-emerald-500 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-500/10 dark:to-teal-500/10 shadow-sm"
                      : "border-neutral-200 dark:border-neutral-700/60 hover:border-neutral-300 dark:hover:border-neutral-600"
                  }`}
                >
                  <div className="text-base mb-1">{lvl.icon}</div>
                  <div
                    className={`text-[12px] font-semibold ${
                      active
                        ? "text-emerald-700 dark:text-emerald-400"
                        : "text-neutral-700 dark:text-neutral-300"
                    }`}
                  >
                    {lvl.label}
                  </div>
                  <div className="text-[10px] text-neutral-400 mt-0.5 leading-tight">
                    {lvl.desc}
                  </div>
                </button>
              );
            })}
          </div>
        </Section>

        {/* ── Asset Classes ─────────────────────────── */}
        <Section icon="📊" title="Asset Classes" subtitle="Enable the markets your agent will trade">
          <div className="flex flex-wrap gap-2">
            {ASSET_OPTIONS.map((asset) => {
              const active = profile.asset_classes.includes(asset.value);
              return (
                <button
                  key={asset.value}
                  onClick={() => toggleAsset(asset.value)}
                  className={`flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[12px] font-semibold border transition-all ${
                    active
                      ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 shadow-sm"
                      : "border-neutral-200 dark:border-neutral-700/60 text-neutral-500 hover:border-neutral-400 dark:hover:border-neutral-500"
                  }`}
                >
                  <span className="text-sm">{asset.icon}</span>
                  <span>{asset.label}</span>
                </button>
              );
            })}
          </div>
        </Section>

        {/* ── RL Model ──────────────────────────────── */}
        <Section icon="🤖" title="RL Model" subtitle="Choose the reinforcement learning algorithm">
          <div className="space-y-1.5">
            {MODELS.map((m) => {
              const active = profile.selected_model === m.value;
              return (
                <button
                  key={m.value}
                  onClick={() => setProfile((p) => ({ ...p, selected_model: m.value }))}
                  className={`w-full flex items-center justify-between rounded-xl border px-4 py-3 text-left transition-all ${
                    active
                      ? "border-emerald-500 bg-gradient-to-r from-emerald-50/80 to-transparent dark:from-emerald-500/10 dark:to-transparent shadow-sm"
                      : "border-neutral-200 dark:border-neutral-700/60 hover:border-neutral-300 dark:hover:border-neutral-600"
                  }`}
                >
                  <div>
                    <div
                      className={`text-[13px] font-semibold ${
                        active
                          ? "text-emerald-700 dark:text-emerald-400"
                          : "text-neutral-700 dark:text-neutral-300"
                      }`}
                    >
                      {m.label}
                    </div>
                    <div className="text-[11px] text-neutral-400 mt-0.5">{m.desc}</div>
                  </div>
                  {active && (
                    <div className="h-5 w-5 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
                      <span className="text-white text-[9px] font-black">✓</span>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </Section>

        {/* ── Compute Device (GPU / CPU) ─────────────── */}
        <Section icon="⚡" title="Compute Device" subtitle="Switch between CPU and GPU for training acceleration">
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              {(["cpu", "cuda"] as const).map((dev) => {
                const active = deviceInfo.device === dev;
                const isGpu = dev === "cuda";
                const disabled = isGpu && !deviceInfo.available;
                return (
                  <button
                    key={dev}
                    onClick={() => !disabled && !deviceLoading && handleDeviceSwitch(dev)}
                    disabled={disabled || deviceLoading}
                    className={`relative rounded-xl border p-4 text-left transition-all ${
                      disabled
                        ? "opacity-40 cursor-not-allowed border-neutral-200 dark:border-neutral-700/60"
                        : active
                          ? "border-emerald-500 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-500/10 dark:to-teal-500/10 shadow-sm"
                          : "border-neutral-200 dark:border-neutral-700/60 hover:border-neutral-300 dark:hover:border-neutral-600 cursor-pointer"
                    }`}
                  >
                    {active && (
                      <div className="absolute top-2.5 right-2.5 h-5 w-5 rounded-full bg-emerald-500 flex items-center justify-center">
                        <span className="text-white text-[9px] font-black">✓</span>
                      </div>
                    )}
                    <div className="text-lg mb-1">{isGpu ? "🖥" : "💻"}</div>
                    <div className={`text-[13px] font-semibold ${active ? "text-emerald-700 dark:text-emerald-400" : "text-neutral-700 dark:text-neutral-300"}`}>
                      {isGpu ? "GPU (CUDA)" : "CPU"}
                    </div>
                    <div className="text-[10px] text-neutral-400 mt-0.5 leading-tight">
                      {isGpu
                        ? deviceInfo.available
                          ? `${deviceInfo.name} · ${deviceInfo.vram_mb ?? "?"}MB VRAM`
                          : "No compatible GPU detected"
                        : "Default · Works everywhere"}
                    </div>
                  </button>
                );
              })}
            </div>

            {deviceLoading && (
              <div className="flex items-center gap-2 text-[11px] text-neutral-500">
                <span className="h-3 w-3 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                Switching device…
              </div>
            )}

            {deviceError && (
              <div className="rounded-xl border border-red-300 dark:border-red-500/30 bg-red-50 dark:bg-red-500/5 px-4 py-3">
                <div className="flex items-start gap-2">
                  <span className="text-red-500 text-sm shrink-0 mt-0.5">⚠</span>
                  <div>
                    <div className="text-[12px] font-semibold text-red-700 dark:text-red-400">GPU not available</div>
                    <div className="text-[11px] text-red-600/80 dark:text-red-400/70 mt-0.5">{deviceError}</div>
                  </div>
                </div>
              </div>
            )}

            {!deviceInfo.available && !deviceError && (
              <div className="rounded-xl border border-amber-300/40 dark:border-amber-500/20 bg-amber-50/50 dark:bg-amber-500/5 px-4 py-2.5">
                <div className="text-[11px] text-amber-700 dark:text-amber-400">
                  GPU acceleration requires an NVIDIA GPU with CUDA support and PyTorch installed with CUDA.
                </div>
              </div>
            )}
          </div>
        </Section>

        {/* ── Training Configuration ────────────────── */}
        <Section
          icon="🏋"
          title="Training Configuration"
          subtitle={`Total timesteps: ${fmtNum(totalTimesteps)} · Episodes × Steps/episode`}
        >
          {/* Episodes */}
          <div className="mb-5">
            <div className="flex items-center justify-between mb-2">
              <Label>Number of Episodes</Label>
              <div className="flex items-center gap-1.5">
                <span className="text-[13px] font-bold text-neutral-800 dark:text-neutral-200 tabular-nums">
                  {profile.n_episodes.toLocaleString()}
                </span>
                <span className="text-[10px] text-neutral-400">episodes</span>
              </div>
            </div>
            {/* Preset pills */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              {EPISODE_PRESETS.map((p) => {
                const active = profile.n_episodes === p.value;
                return (
                  <button
                    key={p.value}
                    onClick={() => setProfile((prev) => ({ ...prev, n_episodes: p.value }))}
                    className={`rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition-all ${
                      active
                        ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                        : "border-neutral-200 dark:border-neutral-700/60 text-neutral-500 hover:border-neutral-400"
                    }`}
                  >
                    <span>{p.label}</span>
                    <span className="ml-1 text-[9px] opacity-60">{p.desc}</span>
                  </button>
                );
              })}
            </div>
            {/* Slider */}
            <input
              type="range"
              min={50}
              max={2000}
              step={50}
              value={profile.n_episodes}
              onChange={(e) =>
                setProfile((p) => ({ ...p, n_episodes: Number(e.target.value) }))
              }
              className="w-full h-1.5 rounded-full appearance-none bg-neutral-200 dark:bg-neutral-700 accent-emerald-500 cursor-pointer"
            />
            <div className="flex justify-between text-[9px] text-neutral-400 tabular-nums mt-1">
              <span>50</span>
              <span>500</span>
              <span>1,000</span>
              <span>1,500</span>
              <span>2,000</span>
            </div>
            {/* Manual input */}
            <div className="mt-3">
              <NumberInput
                label="Custom value"
                value={profile.n_episodes}
                onChange={(v) => setProfile((p) => ({ ...p, n_episodes: Math.max(1, v) }))}
                min={1}
                max={10000}
                suffix="episodes"
              />
            </div>
          </div>

          {/* Steps per episode */}
          <div className="mb-5">
            <Label>Timesteps per Episode</Label>
            <div className="grid grid-cols-5 gap-1.5">
              {TIMESTEP_OPTIONS.map((opt) => {
                const active = profile.n_steps === opt.value;
                return (
                  <button
                    key={opt.value}
                    onClick={() => setProfile((p) => ({ ...p, n_steps: opt.value }))}
                    className={`rounded-xl border py-2.5 text-center transition-all ${
                      active
                        ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                        : "border-neutral-200 dark:border-neutral-700/60 text-neutral-500 hover:border-neutral-400"
                    }`}
                  >
                    <div className="text-[11px] font-bold">{opt.label}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Total timesteps summary */}
          <div className="rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200/60 dark:border-neutral-700/40 px-4 py-3 mb-5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-neutral-500">Total training timesteps</span>
              <span className="text-[15px] font-bold text-neutral-800 dark:text-neutral-200 tabular-nums">
                {fmtNum(totalTimesteps)}
              </span>
            </div>
            <div className="mt-2 h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-500"
                style={{
                  width: `${Math.min((totalTimesteps / (2000 * 8192)) * 100, 100).toFixed(1)}%`,
                }}
              />
            </div>
            <div className="flex justify-between text-[9px] text-neutral-400 tabular-nums mt-1">
              <span>Light</span>
              <span>Heavy ({fmtNum(2000 * 8192)})</span>
            </div>
          </div>

          {/* Learning rate */}
          <div className="mb-5">
            <Label>Learning Rate</Label>
            <div className="grid grid-cols-3 gap-2 mb-2">
              {LR_PRESETS.map((lr) => {
                const active = profile.learning_rate === lr.value;
                return (
                  <button
                    key={lr.value}
                    onClick={() =>
                      setProfile((p) => ({ ...p, learning_rate: lr.value }))
                    }
                    className={`rounded-xl border px-3 py-2.5 text-center transition-all ${
                      active
                        ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10"
                        : "border-neutral-200 dark:border-neutral-700/60 hover:border-neutral-400"
                    }`}
                  >
                    <div
                      className={`text-[12px] font-bold font-mono ${
                        active
                          ? "text-emerald-700 dark:text-emerald-400"
                          : "text-neutral-700 dark:text-neutral-300"
                      }`}
                    >
                      {lr.label}
                    </div>
                    <div className="text-[10px] text-neutral-400 mt-0.5">{lr.desc}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Batch size + Gamma row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Batch Size</Label>
              <div className="grid grid-cols-4 gap-1">
                {BATCH_OPTIONS.map((b) => {
                  const active = profile.batch_size === b;
                  return (
                    <button
                      key={b}
                      onClick={() => setProfile((p) => ({ ...p, batch_size: b }))}
                      className={`rounded-lg border py-2 text-[11px] font-bold transition-all ${
                        active
                          ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                          : "border-neutral-200 dark:border-neutral-700/60 text-neutral-500 hover:border-neutral-400"
                      }`}
                    >
                      {b}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <Label>Discount (γ)</Label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.9}
                  max={0.999}
                  step={0.001}
                  value={profile.gamma}
                  onChange={(e) =>
                    setProfile((p) => ({ ...p, gamma: Number(e.target.value) }))
                  }
                  className="flex-1 h-1.5 rounded-full appearance-none bg-neutral-200 dark:bg-neutral-700 accent-emerald-500 cursor-pointer"
                />
                <span className="text-[12px] font-mono font-bold text-neutral-700 dark:text-neutral-300 tabular-nums w-12 text-right">
                  {profile.gamma.toFixed(3)}
                </span>
              </div>
            </div>
          </div>
        </Section>

        {/* ── Capital & Risk ────────────────────────── */}
        <Section icon="💰" title="Capital & Risk Parameters" subtitle="Position sizing and loss limits">
          <div className="grid grid-cols-2 gap-4">
            <NumberInput
              label="Capital allocation"
              value={profile.capital_allocation}
              onChange={(v) => setProfile((p) => ({ ...p, capital_allocation: v }))}
              min={1000}
              prefix="$"
            />
            <NumberInput
              label="Max drawdown"
              value={Math.round(profile.max_drawdown * 100)}
              onChange={(v) => setProfile((p) => ({ ...p, max_drawdown: v / 100 }))}
              min={1}
              max={50}
              suffix="%"
            />
            <NumberInput
              label="Stop loss"
              value={Math.round(profile.stop_loss_pct * 100)}
              onChange={(v) => setProfile((p) => ({ ...p, stop_loss_pct: v / 100 }))}
              min={1}
              max={30}
              suffix="%"
            />
            <NumberInput
              label="Take profit"
              value={Math.round(profile.take_profit_pct * 100)}
              onChange={(v) => setProfile((p) => ({ ...p, take_profit_pct: v / 100 }))}
              min={1}
              max={100}
              suffix="%"
            />
          </div>
        </Section>

        {/* ── Reward Weights ────────────────────────── */}
        <Section
          icon="⚖"
          title="Reward Function Weights"
          subtitle="R = w1·R_ann − w2·σ_down + w3·D_ret + w4·T_ry"
        >
          {[
            { key: "w1", label: "Annualized return", note: "R_ann", color: "#22c55e" },
            { key: "w2", label: "Downside deviation", note: "σ_down", color: "#ef4444" },
            { key: "w3", label: "Differential return", note: "D_ret", color: "#3b82f6" },
            { key: "w4", label: "Treynor ratio", note: "T_ry", color: "#f59e0b" },
          ].map((w) => {
            const val = (profile.reward_weights as any)[w.key];
            return (
              <div key={w.key} className="mb-4">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ background: w.color }}
                    />
                    <span className="text-[12px] text-neutral-600 dark:text-neutral-300">
                      {w.label}
                    </span>
                    <span className="text-[10px] text-neutral-400 font-mono">({w.note})</span>
                  </div>
                  <span className="text-[12px] font-bold font-mono text-neutral-700 dark:text-neutral-200 tabular-nums">
                    {val.toFixed(2)}
                  </span>
                </div>
                <div className="relative">
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={val}
                    onChange={(e) => updateWeight(w.key, Number(e.target.value))}
                    className="w-full h-2 rounded-full appearance-none cursor-pointer"
                    style={{ accentColor: w.color }}
                  />
                  <div
                    className="absolute left-0 top-1/2 -translate-y-1/2 h-2 rounded-full pointer-events-none"
                    style={{
                      width: `${val * 100}%`,
                      background: w.color,
                      opacity: 0.25,
                    }}
                  />
                </div>
              </div>
            );
          })}
          <div
            className={`flex items-center justify-between rounded-xl border px-4 py-2.5 mt-2 ${
              Math.abs(weightSum - 1) > 0.01
                ? "border-amber-400/40 bg-amber-50/50 dark:bg-amber-500/5"
                : "border-emerald-400/40 bg-emerald-50/50 dark:bg-emerald-500/5"
            }`}
          >
            <span className="text-[11px] text-neutral-500">Weight sum</span>
            <div className="flex items-center gap-2">
              <span
                className={`text-[13px] font-bold font-mono tabular-nums ${
                  Math.abs(weightSum - 1) > 0.01
                    ? "text-amber-600 dark:text-amber-400"
                    : "text-emerald-600 dark:text-emerald-400"
                }`}
              >
                {weightSum.toFixed(2)}
              </span>
              {Math.abs(weightSum - 1) > 0.01 && (
                <span className="text-[10px] text-amber-500 font-medium">≠ 1.0</span>
              )}
            </div>
          </div>
        </Section>

      </div>
    </div>
  );
}
