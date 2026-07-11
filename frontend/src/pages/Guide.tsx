import { Link } from "react-router-dom";
import { useGuideCase } from "../lib/api";
import { Chart } from "../components/Chart";


const MICRO_INDICATORS = [
  {
    icon: <span className="inline-block h-1 w-5 rounded bg-[#ff9f0a] align-middle" />,
    title: "50WMA: “Where’s the trend?”",
    body: "The stock’s long-term trend line. Price sitting 0 to 3% above a rising 50WMA is the retest zone where a healthy trend usually resumes higher.",
  },
  {
    icon: "🔄",
    title: "Retest",
    body: "Price pushes above the 50WMA, then pulls back to that line to check whether buyers still find value there.",
  },
  {
    icon: <span className="inline-block h-2 w-5 rounded bg-gradient-to-r from-red-500 to-green-500 align-middle" />,
    title: "EMA Cloud: “Is short-term momentum turning?”",
    body: "Three short-term trend lines that flip from a red cloud (downtrend) into a green cloud (uptrend), signaling short-term momentum just turned bullish.",
  },
  {
    icon: "📊",
    title: "Volume: “Is anyone actually behind this move?”",
    body: "How many shares traded. A breakout on 1.5x average volume or more means real money is behind the move, not just noise.",
  },
  {
    icon: "⚡",
    title: "RSI: “Is momentum overheated or fresh?”",
    body: "A 0-to-100 momentum gauge. The system watches for RSI freshly crossing above 50, a sign momentum just turned positive rather than already overheated.",
  },
  {
    icon: "💪",
    title: "Mansfield RS: “Is this stock beating the market?”",
    body: "Compares the stock to the S&P 500. Turning positive means the stock has started outperforming the broader market, not just rising with it.",
  },
];

const SETUPS = [
  {
    icon: <span className="font-black text-xl" style={{ color: "#8b5cf6" }}>↑</span>,
    title: "Holy Grail Setup",
    body: "The full confluence: price in the retest zone, green EMA cloud, positive Mansfield RS, and RSI above 50. The highest-probability entry. Price is ready to move higher in a few weeks to a month.",
  },
  {
    icon: <span style={{ color: "#e040fb" }}>■</span>,
    title: "HRR (High Risk/Reward)",
    body: "An early flip of EMA5 above EMA21 before the trend is fully confirmed. A higher-payoff but riskier entry.",
  },
  {
    icon: <span className="text-gold">●</span>,
    title: "Partial Setup",
    body: "Price is in the retest zone with a high score, but one or two criteria are still missing. Worth watching, but not yet a trade.",
  },
];

interface Case {
  ticker: string;
  start: string;
  end: string;
  title: string;
  body: React.ReactNode;
}

const CASES: Case[] = [
  {
    ticker: "ARM",
    start: "2025-08-01",
    end: "2026-06-01",
    title: "ARM Holdings: The Apex Setup",
    body: (
      <>
        <p>
          ARM spent the second half of 2025 building a long base, a stretch of time where buyers and sellers reached balance, with the price consistently accepted above its 50-week average (the long-term uptrend line). On March 30 and again on April 6, 2026, everything lined up at once: the stock closed at $149 while that 50-week average sat at $135.67, rising.
        </p>
        <ul className="mt-3 space-y-1.5 pl-5 marker:text-muted">
          <li className="list-disc"><strong>50WMA uptrend:</strong> Price was holding above the 50-week average, confirming the long-term trend was still up.</li>
          <li className="list-disc"><strong>Retest:</strong> Price had pushed above the 50WMA earlier, then came back down to that level to check whether buyers still saw value there, and they did.</li>
          <li className="list-disc"><strong>EMA cloud flip:</strong> The short-term moving averages flipped green, signaling the near-term trend had turned bullish too.</li>
          <li className="list-disc"><strong>Mansfield RS:</strong> ARM was growing faster than the S&P 500 over the past 52 weeks, a sign of relative strength.</li>
          <li className="list-disc"><strong>Breakout volume:</strong> More buyers stepped in at the same price level, confirming real demand behind the move.</li>
        </ul>
        <p className="mt-3">
          🔥 <strong>Result:</strong> ARM surged from $149 to $353 by late May 2026, a +135% move in under two months.
        </p>
      </>
    ),
  },
  {
    ticker: "AMD",
    start: "2025-01-01",
    end: "2026-06-19",
    title: "AMD: Winning Trades Repeated",
    body: (
      <>
        <p>
          AMD spent early 2025 building a solid base, buyers and sellers reaching balance, with price consistently accepted above its rising 50-week average (the long-term uptrend line). On June 23, 2025, it triggered a full setup at $143.81, resting right on its $126.60 50WMA.
        </p>
        <ul className="mt-3 space-y-1.5 pl-5 marker:text-muted">
          <li className="list-disc"><strong>50WMA uptrend:</strong> Price held above the 50-week average, confirming the long-term trend was still climbing.</li>
          <li className="list-disc"><strong>Retest:</strong> Price came back down to check the 50WMA level after being above it, and buyers stepped back in, confirming the level still held value.</li>
          <li className="list-disc"><strong>Mansfield RS:</strong> AMD’s relative strength score turned positive, meaning it had started growing faster than the S&P 500, momentum had clearly shifted in AMD’s favor.</li>
        </ul>
        <p className="mt-3">
          ✅ <strong>Result:</strong> Entering in that low-risk retest zone captured a massive run. AMD climbed to $537 by June 2026, a +273% return.
        </p>
      </>
    ),
  },
  {
    ticker: "ADBE",
    start: "2024-10-01",
    end: "2025-08-01",
    title: "Adobe: The Risks and The Traps",
    body: (
      <>
        <p>
          Adobe is a case study in why the 50-week average is treated as an absolute rule, no exceptions. On December 2, 2024, an HRR (High Risk/Reward) signal fired at $552.96: the fast-moving average (EMA5) flipped above the EMA21, an early, higher-payoff entry, but the trend wasn’t fully confirmed yet. Sure enough, the stock was actually underperforming the S&P 500 at the time (Mansfield RS was negative, -0.91), and price dropped -15.8% the very next week.
        </p>
        <p>
          🚫 Then from April to June 2025, bargain hunters bought a rally up to $417, but this wasn’t a real setup. Price stayed below its declining 50-week average the whole time, with relative strength still negative. Since price below the 50WMA means no setup exists, full stop, Adobe collapsed back down into the $340s.
        </p>
      </>
    ),
  },
];

function CaseChart({ c }: { c: Case }) {
  const { data, isLoading, isError } = useGuideCase(c.ticker, c.start, c.end);
  return (
    <div className="card overflow-hidden p-3">
      {isLoading && <div className="skeleton h-[360px]" />}
      {isError && (
        <div className="grid h-[360px] place-items-center text-sm text-muted">
          Chart unavailable for {c.ticker}.
        </div>
      )}
      {data && <Chart data={data} showCloud height={360} />}
    </div>
  );
}

export function Guide() {
  return (
    <div className="animate-fade-up space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight">
          How to Read <span className="text-gradient">the Charts</span>
        </h1>
        <p className="mt-1.5 max-w-3xl text-sm text-muted">
          The core indicators and momentum rules of the Holy Grail system, with three real case
          studies showing high-probability entries and value traps.
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="font-display text-xl font-bold tracking-tight">The Micro Indicators</h2>
          <Link to="/scanner?tab=Dashboard" onClick={() => window.scrollTo(0, 0)} className="text-sm font-semibold text-violet transition hover:opacity-80">
            Test in Dashboard →
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {MICRO_INDICATORS.map((i) => (
            <div key={i.title} className="card flex gap-3 p-4">
              <div className="mt-0.5 w-6 shrink-0 text-center text-lg">{i.icon}</div>
              <div>
                <div className="text-sm font-semibold">{i.title}</div>
                <div className="mt-0.5 text-[13px] leading-relaxed text-muted">{i.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-baseline gap-3">
          <h2 className="font-display text-xl font-bold tracking-tight">The 3 Setups</h2>
          <span className="text-sm text-muted">— The only setups you need to read the charts.</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {SETUPS.map((i) => (
            <div key={i.title} className="card flex gap-3 p-4">
              <div className="mt-0.5 w-6 shrink-0 text-center text-lg">{i.icon}</div>
              <div>
                <div className="text-sm font-semibold">{i.title}</div>
                <div className="mt-0.5 text-[13px] leading-relaxed text-muted">{i.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-6">
        {CASES.map((c, i) => (
          <section key={c.ticker} className="grid items-start gap-5 lg:grid-cols-5">
            <div className={`lg:col-span-2 ${i % 2 ? "lg:order-2" : ""}`}>
              <h2 className="text-lg font-bold">
                {i + 1}. {c.title}
              </h2>
              <div className="ai-prose mt-2 space-y-2 text-[13.5px] leading-relaxed text-muted">
                {c.body}
              </div>
            </div>
            <div className={`lg:col-span-3 ${i % 2 ? "lg:order-1" : ""}`}>
              <CaseChart c={c} />
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
