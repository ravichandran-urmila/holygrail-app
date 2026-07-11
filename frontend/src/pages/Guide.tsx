import { useGuideCase } from "../lib/api";
import { Chart } from "../components/Chart";

const INDICATORS = [
  {
    icon: <span className="inline-block h-1 w-5 rounded bg-[#ff9f0a] align-middle" />,
    title: "50-Week MA",
    body: "The spine of the system — separates bullish from bearish regimes. Below the 50WMA, there is no setup. Period.",
  },
  {
    icon: <span className="font-black text-xl" style={{ color: "#8b5cf6" }}>↑</span>,
    title: "Holy Grail Setup",
    body: "The apex signal: price in the 50WMA retest zone, green EMA cloud, positive Mansfield RS and RSI > 50. Highest-probability entry.",
  },
  {
    icon: <span style={{ color: "#e040fb" }}>■</span>,
    title: "HRR (High Risk / Reward)",
    body: "Fast EMA5 crosses above EMA21 (red → green flip). An early, higher-payoff entry — but the trend isn't fully confirmed yet.",
  },
  {
    icon: <span className="text-gold">●</span>,
    title: "Partial Setup",
    body: "In the retest zone with a high score but missing one or two criteria. Almost perfect — patience for full confirmation is best.",
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
    title: "ARM Holdings — The Apex Setup",
    body: (
      <>
        <p>
          ARM built a prolonged base above the 50WMA through late 2025. On Mar 30 & Apr 6, 2026 it
          triggered a <strong>Full Holy Grail Setup</strong> at a $149 close (rising 50WMA at
          $135.67).
        </p>
        <p>
          Price sat in the retest zone, the EMA cloud flipped green, Mansfield RS was strongly
          positive, and RSI was above 50 — a textbook confluence.
        </p>
        <p>
          🔥 The result: ARM surged from $149 to $353 by late May 2026 — <strong>+135%</strong> in
          under two months.
        </p>
      </>
    ),
  },
  {
    ticker: "AMD",
    start: "2025-01-01",
    end: "2026-06-19",
    title: "AMD — Winning Trades Repeated",
    body: (
      <>
        <p>
          AMD established a solid support base above its rising 50WMA in early 2025. On Jun 23, 2025
          it triggered a Full Setup (score 0.75) at $143.81, resting on a $126.60 50WMA.
        </p>
        <p>
          Mansfield RS turned positive (0.4469), confirming momentum vs. the S&amp;P 500 had shifted
          in AMD's favor.
        </p>
        <p>
          ✅ Entering in the low-risk retest zone captured a run to <strong>+273%</strong> ($537 by
          Jun 2026).
        </p>
      </>
    ),
  },
  {
    ticker: "ADBE",
    start: "2024-10-01",
    end: "2025-08-01",
    title: "Adobe — The Risks & The Traps",
    body: (
      <>
        <p>
          Adobe illustrates HRR risk and the absolute rule of the 50WMA. A HRR signal fired at
          $552.96 (Dec 2, 2024) as the cloud flipped green — but relative strength was weak
          (Mansfield RS -0.91). It dropped <strong>-15.8%</strong> the very next week.
        </p>
        <p>
          🚫 From Apr–Jun 2025, value hunters bought a rally to $417 — but price stayed strictly
          below the declining 50WMA with negative RS.
        </p>
        <p>Because candles below the 50WMA mean no setup, ADBE collapsed back to the $340s.</p>
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

      <div className="grid gap-3 sm:grid-cols-2">
        {INDICATORS.map((i) => (
          <div key={i.title} className="card flex gap-3 p-4">
            <div className="mt-0.5 w-6 shrink-0 text-center text-lg">{i.icon}</div>
            <div>
              <div className="text-sm font-semibold">{i.title}</div>
              <div className="mt-0.5 text-[13px] leading-relaxed text-muted">{i.body}</div>
            </div>
          </div>
        ))}
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
