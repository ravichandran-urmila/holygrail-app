import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

function WelcomeModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in">
      <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-line bg-base p-6 shadow-2xl animate-in zoom-in-95">
        <div className="mb-4 flex items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-violet to-cyan text-xl shadow-glow-violet">
            🏆
          </span>
          <h2 className="font-display text-xl font-bold tracking-tight">Welcome to HolyGrail</h2>
        </div>
        
        <p className="mb-6 text-[14px] leading-relaxed text-muted">
          We built HolyGrail to give busy parents and early-life investors an accelerated path to mastering Technical Analysis. 
          By identifying specific visual setups where the odds are heavily stacked in your favor, you can ride explosive individual stock momentum before the rest of the world catches on.
        </p>
        
        <button
          onClick={onClose}
          className="w-full rounded-xl bg-ink py-2.5 text-sm font-semibold text-base transition hover:opacity-90 active:scale-[0.98]"
        >
          Enter HolyGrail
        </button>
      </div>
    </div>
  );
}

export function About() {
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    const hasSeenWelcome = localStorage.getItem("holygrail_has_seen_welcome");
    if (!hasSeenWelcome) {
      setShowModal(true);
    }
  }, []);

  const handleCloseModal = () => {
    localStorage.setItem("holygrail_has_seen_welcome", "true");
    setShowModal(false);
  };

  return (
    <>
      {showModal && <WelcomeModal onClose={handleCloseModal} />}
      
      <div className="animate-fade-up mx-auto max-w-3xl space-y-8">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">
            Welcome to <span className="text-gradient">HolyGrail</span>
          </h1>
        </div>

        <div className="prose prose-invert max-w-none text-muted space-y-6 text-[15px] leading-relaxed">
          <p>
            Over the last few decades, the global money supply has expanded at a staggering long-term average of nearly 7% annually, while the S&P 500 has compounded at roughly 10%. Meanwhile, real ordinary income has practically flatlined, growing at less than 1% per year.
          </p>
          <p>
            This massive economic divergence leaves working families stranded when major expenses land on their doorstep. While standard financial advice says to "just buy an index fund," a traditional S&P 500 strategy alone no longer cuts it. Official inflation metrics claim prices only rise a few percent a year, but the real-world expenses parents actually care about—housing, healthcare, and education—historically compound at rates much closer to the expansion of the money supply. When your cost of living grows at 7% a year, a standard index portfolio barely keeps your head above water after taxes and fees.
          </p>
          <p>
            We built HolyGrail to shatter this cycle by giving busy parents and early-life investors an accelerated path to mastering Technical Analysis.
          </p>
          <p>
            Think of it like weather forecasting for the stock market. Because human emotion and behavior repeat themselves, charts leave distinct visual footprints. Technical analysis is simply probability-based pattern recognition—identifying specific visual setups where the odds of a massive price move are heavily stacked in your favor.
          </p>
          <p>
            Because the charts always lead the narrative, HolyGrail provides the custom, high-conviction indicators you need to allocate a small-risk portfolio and ride explosive individual stock momentum—like Bitcoin, Nvidia, or Micron—before the rest of the world catches on.
          </p>
        </div>

        <div className="pt-4">
          <Link
            to="/scanner"
            className="inline-flex items-center justify-center rounded-xl bg-ink px-6 py-3 text-sm font-semibold text-base transition hover:opacity-90 active:scale-[0.98]"
          >
            Go to Scanner →
          </Link>
        </div>
      </div>
    </>
  );
}
