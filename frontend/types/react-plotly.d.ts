declare module "react-plotly.js" {
  import * as React from "react";
  import {
    Layout,
    Data,
    Config,
    PlotMouseEvent,
    PlotRelayoutEvent,
  } from "plotly.js";

  export interface PlotParams {
    data: Data[];
    layout?: Partial<Layout>;
    config?: Partial<Config>;
    style?: React.CSSProperties;
    className?: string;

    onHover?: (event: PlotMouseEvent) => void;
    onUnhover?: (event: PlotMouseEvent) => void;
    onRelayout?: (event: PlotRelayoutEvent) => void;
  }

  const Plot: React.FC<PlotParams>;
  export default Plot;
}
