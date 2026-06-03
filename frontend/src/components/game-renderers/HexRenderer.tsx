import { useMemo } from 'react';
import { Box, Typography, useTheme } from '@mui/material';
import type { GameRendererProps } from './index';

// A single pointy-topped hexagon
const hexPoints = (size: number) => {
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle_deg = 60 * i - 30; // Pointy topped
    const angle_rad = (Math.PI / 180) * angle_deg;
    points.push(`${size * Math.cos(angle_rad)},${size * Math.sin(angle_rad)}`);
  }
  return points.join(' ');
};

/**
 * Interpret the game status value
 *  -2 = draw
 *  -1 = ongoing
 *   0 = player 0 wins
 *   1 = player 1 wins
 */
function getStatusText(status: number, name0: string, name1: string): { text: string; color: string } {
  switch (status) {
    case -2:
      return { text: 'Draw', color: 'warning.main' };
    case -1:
      return { text: 'In Progress', color: 'info.main' };
    case 0:
      return { text: `${name0} wins!`, color: '#ef4444' }; // Red
    case 1:
      return { text: `${name1} wins!`, color: '#3b82f6' }; // Blue
    default:
      return { text: 'Unknown', color: 'text.secondary' };
  }
}

export function HexRenderer({ gameState, agentIds, agentMap }: GameRendererProps) {
  const theme = useTheme();
  
  const agentName = (index: number): string => {
    const id = agentIds[index];
    if (!id) return `Player ${index + 1}`;
    return agentMap?.[id] ?? id.slice(0, 8) + '…';
  };

  if (!gameState || !gameState.board || !gameState.board_size) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography color="text.secondary">Waiting for game state...</Typography>
      </Box>
    );
  }

  const { board, board_size, turn, status } = gameState;

  // Render parameters
  const hexRadius = 20;
  const sqrt3 = Math.sqrt(3);
  const hexWidth = sqrt3 * hexRadius;
  const hexHeight = 2 * hexRadius;

  // Calculate grid dimensions
  // x = hexWidth * (c + r / 2)
  // y = hexRadius * 3/2 * r
  const getX = (r: number, c: number) => hexWidth * (c + r / 2);
  const getY = (r: number, _c?: number) => hexRadius * 1.5 * r;

  // Vertex helpers for borders
  const getTop = (r: number, c: number) => `${getX(r,c)},${getY(r,c)-hexRadius}`;
  const getTopRight = (r: number, c: number) => `${getX(r,c)+hexWidth/2},${getY(r,c)-hexRadius/2}`;
  const getBottomRight = (r: number, c: number) => `${getX(r,c)+hexWidth/2},${getY(r,c)+hexRadius/2}`;
  const getBottom = (r: number, c: number) => `${getX(r,c)},${getY(r,c)+hexRadius}`;
  const getBottomLeft = (r: number, c: number) => `${getX(r,c)-hexWidth/2},${getY(r,c)+hexRadius/2}`;
  const getTopLeft = (r: number, c: number) => `${getX(r,c)-hexWidth/2},${getY(r,c)-hexRadius/2}`;

  const minX = -hexWidth;
  const maxX = getX(board_size - 1, board_size - 1) + hexWidth;
  const minY = -hexHeight;
  const maxY = getY(board_size - 1, 0) + hexHeight;

  const width = maxX - minX;
  const height = maxY - minY;

  const hexScale = 0.88;
  const borderStrokeWidth = 4;
  const gapRadius = hexRadius * (1 - hexScale);
  const generalShift = (gapRadius + borderStrokeWidth / 2) / (sqrt3 / 2);

  const padding = generalShift + borderStrokeWidth;
  const viewBoxMinX = minX - padding;
  const viewBoxMinY = minY - padding;
  const viewBoxWidth = width + padding * 2;
  const viewBoxHeight = height + padding * 2;

  const isDark = theme.palette.mode === 'dark';

  const colors = {
    empty: isDark ? theme.palette.action.hover : '#f1f5f9',
    p0: '#ef4444', // Left-Right (Horizontal) Player
    p1: '#3b82f6', // Top-Bottom (Vertical) Player
    stroke: isDark ? theme.palette.divider : '#cbd5e1',
    boardLeftRight: 'rgba(239, 68, 68, 0.3)',
    boardTopBottom: 'rgba(59, 130, 246, 0.3)',
  };

  const statusInfo = getStatusText(status, agentName(0), agentName(1));

  // Determine current turn name
  let turnText = '';
  if (status === -1) {
    turnText = `${agentName(turn)}'s Turn`;
  }

  // Generate paths for the colored borders to accurately map the jagged lines
  const topPathPointsRaw = [getTopLeft(0, 0)];
  for (let c = 0; c < board_size; c++) {
    topPathPointsRaw.push(getTop(0, c));
    topPathPointsRaw.push(getTopRight(0, c));
  }

  const bottomPathPointsRaw = [getBottomRight(board_size - 1, board_size - 1)];
  for (let c = board_size - 1; c >= 0; c--) {
    bottomPathPointsRaw.push(getBottom(board_size - 1, c));
    bottomPathPointsRaw.push(getBottomLeft(board_size - 1, c));
  }

  const leftPathPointsRaw = [getTopLeft(0, 0)];
  for (let r = 0; r < board_size; r++) {
    leftPathPointsRaw.push(getBottomLeft(r, 0));
    if (r < board_size - 1) {
      leftPathPointsRaw.push(getBottom(r, 0));
    }
  }

  const rightPathPointsRaw = [getTopRight(0, board_size - 1)];
  for (let r = 0; r < board_size; r++) {
    rightPathPointsRaw.push(getBottomRight(r, board_size - 1));
    if (r < board_size - 1) {
      rightPathPointsRaw.push(getTopRight(r + 1, board_size - 1));
    }
  }

  const d = generalShift;

  const topPathPoints = topPathPointsRaw.map(p => {
    const [x, y] = p.split(',').map(Number);
    return `${x},${y - d}`;
  });

  const bottomPathPoints = bottomPathPointsRaw.map(p => {
    const [x, y] = p.split(',').map(Number);
    return `${x},${y + d}`;
  });

  const leftPathPoints = leftPathPointsRaw.map(p => {
    const [x, y] = p.split(',').map(Number);
    return `${x - d * sqrt3 / 2},${y + d / 2}`;
  });

  const rightPathPoints = rightPathPointsRaw.map(p => {
    const [x, y] = p.split(',').map(Number);
    return `${x + d * sqrt3 / 2},${y - d / 2}`;
  });

  // Calculate perfect intersection corners
  const tL_x = getX(0,0) - hexWidth/2;
  const tL_y = getY(0,0) - hexRadius/2;
  const cornerTL = `${tL_x - d*sqrt3/2},${tL_y - d/2}`;

  const tR_x = getX(0, board_size-1) + hexWidth/2;
  const tR_y = getY(0, board_size-1) - hexRadius/2;
  const cornerTR = `${tR_x + d*sqrt3/2},${tR_y - d/2}`;
  
  const bL_x = getX(board_size-1, 0) - hexWidth/2;
  const bL_y = getY(board_size-1, 0) + hexRadius/2;
  const cornerBL = `${bL_x - d*sqrt3/2},${bL_y + d/2}`;

  const bR_x = getX(board_size-1, board_size-1) + hexWidth/2;
  const bR_y = getY(board_size-1, board_size-1) + hexRadius/2;
  const cornerBR = `${bR_x + d*sqrt3/2},${bR_y + d/2}`;

  // Prepend and append the exact corners to bridge the gaps
  topPathPoints.unshift(cornerTL);
  topPathPoints.push(cornerTR);

  leftPathPoints.unshift(cornerTL);
  leftPathPoints.push(cornerBL);

  bottomPathPoints.unshift(cornerBR);
  bottomPathPoints.push(cornerBL);

  rightPathPoints.unshift(cornerTR);
  rightPathPoints.push(cornerBR);

  // Pre-calculate poly points string
  const pointsStr = useMemo(() => hexPoints(hexRadius * hexScale), [hexRadius, hexScale]);

  const p0Name = agentName(0);
  const p1Name = agentName(1);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Header Info */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h6" sx={{ color: status === -1 ? 'text.primary' : statusInfo.color }}>
            {status === -1 ? turnText : statusInfo.text}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Size: {board_size}x{board_size}
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="body2" sx={{ color: colors.p0, fontWeight: turn === 0 ? 'bold' : 'normal' }}>
            ■ {p0Name} (Left-Right)
          </Typography>
          <Typography variant="body2" sx={{ color: colors.p1, fontWeight: turn === 1 ? 'bold' : 'normal' }}>
            ■ {p1Name} (Top-Bottom)
          </Typography>
        </Box>
      </Box>

      {/* SVG Board Container */}
      <Box sx={{ display: 'flex', justifyContent: 'center', backgroundColor: 'background.paper', borderRadius: 2, p: 2, boxShadow: 'inset 0 0 10px rgba(0,0,0,0.05)' }}>
        <svg
          viewBox={`${viewBoxMinX} ${viewBoxMinY} ${viewBoxWidth} ${viewBoxHeight}`}
          style={{ width: '100%', maxWidth: '600px', height: 'auto', display: 'block' }}
        >
          {/* Top/Bottom Edges (Player 1) */}
          <polyline
            points={topPathPoints.join(' ')}
            fill="none"
            stroke={colors.p1}
            strokeWidth={borderStrokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <polyline
            points={bottomPathPoints.join(' ')}
            fill="none"
            stroke={colors.p1}
            strokeWidth={borderStrokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Left/Right Edges (Player 0) */}
          <polyline
            points={leftPathPoints.join(' ')}
            fill="none"
            stroke={colors.p0}
            strokeWidth={borderStrokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <polyline
            points={rightPathPoints.join(' ')}
            fill="none"
            stroke={colors.p0}
            strokeWidth={borderStrokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Render Cells */}
          {board.map((row: number[], r: number) =>
            row.map((cell: number, c: number) => {
              let fillStr = colors.empty;
              if (cell === 0) fillStr = colors.p0;
              else if (cell === 1) fillStr = colors.p1;

              const cx = getX(r, c);
              const cy = getY(r, c);

              return (
                <g key={`${r}-${c}`} transform={`translate(${cx}, ${cy})`}>
                  <polygon
                    points={pointsStr}
                    fill={fillStr}
                    stroke={colors.stroke}
                    strokeWidth="1.5"
                    style={{ transition: 'fill 0.3s ease' }}
                  />
                  {/* Optional: coordinate label for debugging or accessibility */}
                  {/* <text x="0" y="4" fontSize="8" textAnchor="middle" fill="#94a3b8" pointerEvents="none">{r},{c}</text> */}
                </g>
              );
            })
          )}
        </svg>
      </Box>
    </Box>
  );
}
