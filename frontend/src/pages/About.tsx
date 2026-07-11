import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import aboutPerspective from "../assets/about-perspective.png";
import aboutGap from "../assets/about-gap.jpg";

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
          Frustrated hearing that your neighbor or your friend made multiple folds of profit in a single stock, but you didn't know when to catch the momentum? HolyGrail will teach you to fish for them yourself.
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
            We built HolyGrail to give busy parents and early-stage investors a faster path to mastering technical analysis. By learning to spot a few high-probability chart setups, you can catch powerful stock momentum before the crowd does.
          </p>
          <p>
            Over the last few decades, global broad money has grown at about 7% annually, the S&P 500 has compounded at roughly 10% nominally, and real household income has barely moved. That gap leaves working families squeezed when major expenses show up, because the things parents care about most — housing, healthcare, and education — often rise faster than wages.
          </p>
          <p>
            You may turn $100 into about $259 in the S&P 500 over 10 years, but if money supply expands at 7% annually, that’s only about $132 of real purchasing power. The gain is real — but much smaller than the headline suggests.
          </p>

          <figure className="my-8 overflow-hidden rounded-2xl border border-line bg-base/50 p-2 shadow-2xl">
            <img 
              src={aboutPerspective} 
              alt="10 Years. Two Perspectives. Nominal Growth vs Real Purchasing Power" 
              className="w-full rounded-xl"
            />
          </figure>

          <p>
            That is why a simple “buy an index fund” approach no longer feels enough on its own. Official inflation numbers may look modest, but the real cost of living for families compounds in a way that’s much harder to ignore. When expenses rise faster than income, a traditional index portfolio can struggle to keep up after taxes and fees.
          </p>

          <figure className="my-8 overflow-hidden rounded-2xl border border-line bg-base/50 p-2 shadow-2xl">
            <img 
              src={aboutGap} 
              alt="The gap is growing. Inflation is quiet, compounding is loud." 
              className="w-full rounded-xl"
            />
          </figure>

          <p>
            HolyGrail is designed to break that cycle by helping busy parents and early-stage investors learn momentum analysis more quickly. Think of it like weather forecasting for the stock market: human behavior repeats, charts leave footprints, and technical analysis is really about recognizing patterns where the odds are in your favor.
          </p>
          <p>
            Because charts often lead the story, HolyGrail gives you high-conviction indicators to help allocate a small portion of capital toward explosive momentum moves in names like Bitcoin, AMD, or Intel before the broader market fully catches on.
          </p>
          <p>
            Finally, you can backtest all of these indicators to verify their performance for yourself.
          </p>
        </div>

        <div className="pt-4 flex flex-wrap items-center gap-4">
          <Link
            to="/scanner"
            className="inline-flex items-center justify-center rounded-xl bg-ink px-6 py-3 text-sm font-semibold text-base transition hover:opacity-90 active:scale-[0.98]"
          >
            Go to Scanner →
          </Link>
          <Link
            to="/guide"
            onClick={() => window.scrollTo(0, 0)}
            className="inline-flex items-center justify-center rounded-xl bg-white/[0.08] px-6 py-3 text-sm font-semibold text-ink shadow-sm transition hover:bg-white/[0.12] active:scale-[0.98]"
          >
            Learn More
          </Link>
        </div>
      </div>
    </>
  );
}
