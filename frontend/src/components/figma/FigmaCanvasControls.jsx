import React from 'react';
import { useReactFlow } from '@xyflow/react';

/**
 * FigmaCanvasControls Component
 * Minimal floating controls in the bottom-left of the canvas:
 * - Zoom In (+)
 * - Zoom Out (-)
 * - Zoom 100% Reset
 * - Fit View
 */
const FigmaCanvasControls = () => {
  const { zoomIn, zoomOut, setViewport, fitView, getZoom } = useReactFlow();

  const handleResetZoom = () => {
    setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 300 });
  };

  const handleFitView = () => {
    fitView({ padding: 0.2, duration: 400 });
  };

  return (
    <div className="canvas-floating-controls">
      <button
        type="button"
        className="canvas-ctrl-btn"
        onClick={() => zoomIn({ duration: 250 })}
        title="Zoom In"
      >
        +
      </button>

      <button
        type="button"
        className="canvas-ctrl-btn"
        onClick={() => zoomOut({ duration: 250 })}
        title="Zoom Out"
      >
        −
      </button>

      <button
        type="button"
        className="canvas-ctrl-btn btn-text"
        onClick={handleResetZoom}
        title="Reset to 100%"
      >
        100%
      </button>

      <button
        type="button"
        className="canvas-ctrl-btn btn-text"
        onClick={handleFitView}
        title="Fit all nodes to view"
      >
        Fit
      </button>
    </div>
  );
};

export default React.memo(FigmaCanvasControls);
