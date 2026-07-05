import type {
  CustomSeriesPricePlotValues,
  ICustomSeriesPaneRenderer,
  ICustomSeriesPaneView,
  PaneRendererCustomData,
  PriceToCoordinateConverter,
  Time,
  WhitespaceData,
} from "lightweight-charts";
import { customSeriesDefaultOptions } from "lightweight-charts";
import type { CustomSeriesOptions } from "lightweight-charts";

export interface BandData {
  time: Time;
  upper: number;
  lower: number;
  green: boolean;
}

export interface BandSeriesOptions extends CustomSeriesOptions {
  greenFill: string;
  redFill: string;
}

const defaultOptions: BandSeriesOptions = {
  ...customSeriesDefaultOptions,
  greenFill: "rgba(22, 199, 132, 0.20)",
  redFill: "rgba(234, 57, 67, 0.20)",
} as BandSeriesOptions;

interface BarPt {
  x: number;
  upper: number;
  lower: number;
  green: boolean;
}

class BandRenderer implements ICustomSeriesPaneRenderer {
  private _data: PaneRendererCustomData<Time, BandData> | null = null;
  private _options: BandSeriesOptions | null = null;

  update(data: PaneRendererCustomData<Time, BandData>, options: BandSeriesOptions): void {
    this._data = data;
    this._options = options;
  }

  draw(target: Parameters<ICustomSeriesPaneRenderer["draw"]>[0], priceToCoordinate: PriceToCoordinateConverter): void {
    target.useBitmapCoordinateSpace((scope) => {
      const data = this._data;
      const options = this._options;
      if (!data || !options || data.bars.length === 0) return;

      const bars: BarPt[] = data.bars.map((bar) => ({
        x: bar.x * scope.horizontalPixelRatio,
        upper: (priceToCoordinate(bar.originalData.upper) ?? 0) * scope.verticalPixelRatio,
        lower: (priceToCoordinate(bar.originalData.lower) ?? 0) * scope.verticalPixelRatio,
        green: bar.originalData.green,
      }));

      const ctx = scope.context;
      const n = bars.length;
      let start = 0;
      for (let i = 1; i <= n; i++) {
        if (i === n || bars[i].green !== bars[start].green) {
          const end = Math.min(i, n - 1); // bridge into the next run to avoid gaps
          this._fillRun(ctx, bars, start, end, bars[start].green, options);
          start = i;
        }
      }
    });
  }

  private _fillRun(
    ctx: CanvasRenderingContext2D,
    bars: BarPt[],
    a: number,
    b: number,
    green: boolean,
    options: BandSeriesOptions,
  ): void {
    if (b < a) return;
    ctx.beginPath();
    ctx.moveTo(bars[a].x, bars[a].upper);
    for (let i = a + 1; i <= b; i++) ctx.lineTo(bars[i].x, bars[i].upper);
    for (let i = b; i >= a; i--) ctx.lineTo(bars[i].x, bars[i].lower);
    ctx.closePath();
    ctx.fillStyle = green ? options.greenFill : options.redFill;
    ctx.fill();
  }
}

export class BandSeries implements ICustomSeriesPaneView<Time, BandData, BandSeriesOptions> {
  private _renderer = new BandRenderer();

  priceValueBuilder(plotRow: BandData): CustomSeriesPricePlotValues {
    return [plotRow.lower, plotRow.upper];
  }

  isWhitespace(data: BandData | WhitespaceData): data is WhitespaceData {
    return (data as BandData).upper === undefined;
  }

  renderer(): BandRenderer {
    return this._renderer;
  }

  update(data: PaneRendererCustomData<Time, BandData>, options: BandSeriesOptions): void {
    this._renderer.update(data, options);
  }

  defaultOptions(): BandSeriesOptions {
    return defaultOptions;
  }
}
