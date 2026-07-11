import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
} from "lightweight-charts";
import { BandSeries, type BandData } from "../lib/bandSeries";
import type { ScanResponse } from "../lib/types";

interface Props {
  data: ScanResponse;
  showCloud: boolean;
  height?: number;
  type?: "candle" | "line";
}

export function Chart({ data, showCloud, height = 560, type = "candle" }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "rgba(230,234,242,0.6)",
        fontFamily: "Inter, sans-serif",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "rgba(124,92,255,0.4)", labelBackgroundColor: "#7c5cff" },
        horzLine: { color: "rgba(124,92,255,0.4)", labelBackgroundColor: "#7c5cff" },
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      timeScale: { borderColor: "rgba(255,255,255,0.08)", rightOffset: 4 },
    });
    chartRef.current = chart;

    // Cloud behind everything.
    let bandSeries: ISeriesApi<"Custom"> | null = null;
    if (showCloud) {
      bandSeries = chart.addCustomSeries(new BandSeries(), {
        greenFill: "rgba(31,221,151,0.20)",
        redFill: "rgba(255,84,112,0.18)",
        priceLineVisible: false,
        lastValueVisible: false,
      });
      bandSeries.setData(
        data.cloud.map(
          (c): BandData => ({
            time: c.time as Time,
            upper: c.upper,
            lower: c.lower,
            green: c.green,
          }),
        ),
      );
    }

    let mainSeries: ISeriesApi<"Candlestick"> | ISeriesApi<"Line">;
    if (type === "line") {
      mainSeries = chart.addLineSeries({
        color: "#1fdd97",
        lineWidth: 2,
        priceLineVisible: false,
      });
      mainSeries.setData(data.candles.map((c) => ({ time: c.time as Time, value: c.close })));
    } else {
      mainSeries = chart.addCandlestickSeries({
        upColor: "#1fdd97",
        downColor: "#ff5470",
        borderUpColor: "#1fdd97",
        borderDownColor: "#ff5470",
        wickUpColor: "rgba(31,221,151,0.85)",
        wickDownColor: "rgba(255,84,112,0.85)",
        priceLineVisible: false,
      });
      mainSeries.setData(data.candles.map((c) => ({ ...c, time: c.time as Time })));
    }

    if (showCloud) {
      const emaLine = (points: { time: string; value: number }[], color: string) => {
        const s = chart.addLineSeries({
          color,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        s.setData(points.map((p) => ({ time: p.time as Time, value: p.value })));
      };
      emaLine(data.ema21, "rgba(41,98,255,0.65)");
      emaLine(data.ema9, "rgba(0,170,170,0.65)");
      emaLine(data.ema5, "rgba(0,200,120,0.85)");
    }

    const ma = chart.addLineSeries({
      color: "#ff9f0a",
      lineWidth: 3,
      priceLineVisible: false,
      lastValueVisible: false,
      lineStyle: LineStyle.Solid,
      crosshairMarkerVisible: false,
    });
    ma.setData(data.ma50w.map((p) => ({ time: p.time as Time, value: p.value })));

    // Signal markers
    const markers: SeriesMarker<Time>[] = [];
    for (const m of data.markers.fullSetup)
      markers.push({
        time: m.time as Time,
        position: "belowBar",
        color: "#5b6bff",
        shape: "arrowUp",
        text: "HG",
        size: 2,
      });
    for (const m of data.markers.partial)
      markers.push({
        time: m.time as Time,
        position: "belowBar",
        color: "#ffd23f",
        shape: "circle",
        size: 1,
      });
    for (const m of data.markers.hrr)
      markers.push({
        time: m.time as Time,
        position: "belowBar",
        color: "#e879f9",
        shape: "square",
        size: 1,
      });
    markers.sort((a, b) => String(a.time).localeCompare(String(b.time)));
    mainSeries.setMarkers(markers);

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [data, showCloud, type]);

  return <div ref={containerRef} style={{ height }} className="w-full" />;
}
