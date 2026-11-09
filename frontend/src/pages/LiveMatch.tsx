import { useMemo, useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  CircularProgress,
  Slider,
  IconButton,
  Divider,
  Tooltip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  LinearProgress,
  Snackbar,
} from '@mui/material';
import {
  ArrowBack,
  FiberManualRecord,
  SignalWifiOff,
  CheckCircle,
  HourglassEmpty,
  PlayArrow,
  Pause,
  SkipPrevious,
  SkipNext,
  NavigateBefore,
  NavigateNext,
  EmojiEvents,
  Handshake,
  Warning,
  Flag,
  Person,
} from '@mui/icons-material';
import { useSmartBack } from '../hooks/use-smart-back';
import { useMatchStream } from '../hooks/useMatchStream';
import { getGameRenderer } from '../components/game-renderers';
import { fromApiGameType, getGameById } from '../config/games';
import { agentsApi } from '../services/api/agents';
import { matchesApi } from '../services/api/matches';
import { containersApi } from '../services/api/containers';
import { useAuth } from '../context/AuthContext';

const HUMAN_PLAYER_ID = 'human'; // the human's id in results

// ─── Status Chip ──────────────────────────────────────────────────────────────

function StatusChip({ status }: { status: string | null }) {
  if (!status) return null;

  const config: Record<string, { label: string; color: 'default' | 'success' | 'error' | 'warning' | 'info' }> = {
    queued: { label: 'Queued', color: 'default' },
    running: { label: 'Live', color: 'error' },
    completed: { label: 'Completed', color: 'success' },
    failed: { label: 'Failed', color: 'error' },
    client_error: { label: 'Error', color: 'warning' },
  };

  const { label, color } = config[status] ?? { label: status, color: 'default' as const };

  return (
    <Chip
      icon={status === 'running' ? (
        <FiberManualRecord sx={{
          fontSize: 10,
          animation: 'pulse 1.5s ease-in-out infinite',
          '@keyframes pulse': {
            '0%, 100%': { opacity: 1 },
            '50%': { opacity: 0.3 },
          },
        }} />
      ) : undefined}
      label={label}
      color={color}
      size="small"
      sx={{ fontWeight: 600 }}
    />
  );
}

// ─── Connection Indicator ─────────────────────────────────────────────────────

function ConnectionIndicator({
  isConnected,
  error,
  isTerminal,
}: {
  isConnected: boolean;
  error: string | null;
  isTerminal: boolean;
}) {
  // Hide connection status once the match is over — it's no longer relevant
  if (isTerminal) return null;

  if (error) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <SignalWifiOff sx={{ fontSize: 14, color: 'warning.main' }} />
        <Typography variant="caption" color="warning.main">
          {error}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <FiberManualRecord
        sx={{
          fontSize: 8,
          color: isConnected ? 'success.main' : 'text.disabled',
          ...(isConnected && {
            animation: 'pulse 2s ease-in-out infinite',
            '@keyframes pulse': {
              '0%, 100%': { opacity: 1 },
              '50%': { opacity: 0.4 },
            },
          }),
        }}
      />
      <Typography variant="caption" color="text.secondary">
        {isConnected ? 'Live' : 'Connecting…'}
      </Typography>
    </Box>
  );
}

// ─── Agent Player Card ─────────────────────────────────────────────────────────

const PLAYER_COLORS = ['#6366f1', '#f43f5e'] as const;
const PLAYER_BG = ['rgba(99,102,241,0.08)', 'rgba(244,63,94,0.08)'] as const;

function AgentCard({
  name,
  index,
  isWinner,
  isDraw,
}: {
  name: string;
  index: number;
  isWinner: boolean;
  isDraw: boolean;
}) {
  const color = PLAYER_COLORS[index] ?? '#888';
  const bg = PLAYER_BG[index] ?? 'rgba(128,128,128,0.08)';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 0.5,
        px: 2,
        py: 1.5,
        borderRadius: 2,
        border: `2px solid`,
        borderColor: isWinner ? color : 'divider',
        backgroundColor: isWinner ? bg : 'transparent',
        position: 'relative',
        transition: 'all 0.3s ease',
        minWidth: 120,
      }}
    >
      {(isWinner || isDraw) && (
        <Box sx={{ position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)' }}>
          {isDraw ? (
            <Chip label="Draw" size="small" color="default" sx={{ fontSize: '0.65rem', height: 20 }} />
          ) : (
            <Chip
              icon={<EmojiEvents sx={{ fontSize: 12 }} />}
              label="Winner"
              size="small"
              sx={{
                fontSize: '0.65rem',
                height: 20,
                backgroundColor: color,
                color: '#fff',
                '& .MuiChip-icon': { color: '#fff' },
              }}
            />
          )}
        </Box>
      )}
      <Typography
        variant="body1"
        fontWeight={700}
        sx={{ color, fontSize: '1rem', textAlign: 'center', wordBreak: 'break-word' }}
      >
        {name}
      </Typography>
    </Box>
  );
}

// ─── Match Result Banner ──────────────────────────────────────────────────────

function MatchResultBanner({
  result,
  status,
  agentMap,
  viewerPlayerId,
}: {
  result: any;
  status: string | null;
  agentMap: Record<string, string>;
  viewerPlayerId?: string | null;
}) {
  if (!status || !['completed', 'failed', 'client_error'].includes(status)) return null;

  const isError = status === 'failed' || status === 'client_error';
  const isDraw = result?.winner === 'draw';
  const winnerName = result?.winner && !isDraw
    ? (agentMap[result.winner] || result.winner.slice(0, 8) + '…')
    : null;

  // Banner color and icon based on outcome
  let bgColor: string;
  let borderColor: string;
  let icon: React.ReactNode;
  let headline: string;

  if (isError) {
    bgColor = 'rgba(244,63,94,0.08)';
    borderColor = '#f43f5e';
    icon = <Warning sx={{ fontSize: 28, color: '#f43f5e' }} />;
    headline = status === 'failed' ? 'Match Failed' : 'Match Error';
  } else if (isDraw) {
    bgColor = 'rgba(100,116,139,0.08)';
    borderColor = '#64748b';
    icon = <Handshake sx={{ fontSize: 28, color: '#64748b' }} />;
    headline = 'It\'s a Draw!';
  } else {
    bgColor = 'rgba(34,197,94,0.08)';
    borderColor = '#22c55e';
    icon = <EmojiEvents sx={{ fontSize: 28, color: '#f59e0b' }} />;
    headline = viewerPlayerId && result?.winner === viewerPlayerId
      ? 'You Win!'
      : viewerPlayerId
        ? 'You Lost'
        : `${winnerName} Wins!`;
  }

  return (
    <Box
      sx={{
        mb: 3,
        p: 2.5,
        borderRadius: 2,
        border: `2px solid ${borderColor}`,
        backgroundColor: bgColor,
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        animation: 'fadeIn 0.4s ease',
        '@keyframes fadeIn': { from: { opacity: 0, transform: 'translateY(-8px)' }, to: { opacity: 1, transform: 'none' } },
      }}
    >
      {icon}
      <Box sx={{ flex: 1 }}>
        <Typography variant="h6" fontWeight={700} sx={{ lineHeight: 1.2 }}>
          {headline}
        </Typography>
        {result?.reason && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
            {result.reason}
          </Typography>
        )}
      </Box>
      <CheckCircle sx={{ fontSize: 18, color: isError ? '#f43f5e' : borderColor, opacity: 0.6 }} />
    </Box>
  );
}

// ─── Human Play Panel ─────────────────────────────────────────────────────────

function HumanPlayPanel({
  status,
  isMyTurn,
  pendingMove,
  deadline,
  moveTimeLimit,
  onResign,
}: {
  status: string | null;
  isMyTurn: boolean;
  pendingMove: boolean;
  deadline: number | null;
  moveTimeLimit: number | null;
  onResign: () => void;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!isMyTurn) return;
    setNow(Date.now());
    const t = setInterval(() => setNow(Date.now()), 200);
    return () => clearInterval(t);
  }, [isMyTurn]);

  const counting = isMyTurn && !pendingMove && deadline !== null && moveTimeLimit !== null;
  const remaining = counting ? Math.max(0, (deadline! - now) / 1000) : null;
  const urgent = remaining !== null && remaining <= 10;

  let headline: string;
  if (status === 'queued') headline = 'Waiting for a free match runner…';
  else if (pendingMove) headline = 'Sending your move…';
  else if (isMyTurn) headline = 'Your turn: click a free cell';
  else headline = 'Agent is thinking…';

  return (
    <Box
      sx={{
        mb: 2,
        p: 2,
        borderRadius: 2,
        border: 2,
        borderColor: isMyTurn ? 'primary.main' : 'divider',
        backgroundColor: isMyTurn ? 'action.hover' : 'transparent',
        transition: 'border-color 0.25s ease, background-color 0.25s ease',
      }}
    >
      {/* Everything is always rendered so turns never shift the layout. */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, minHeight: 32 }}>
        <Person color={isMyTurn ? 'primary' : 'disabled'} sx={{ transition: 'color 0.25s ease' }} />
        <Typography
          variant="subtitle1"
          fontWeight={700}
          noWrap
          sx={{ flex: 1, minWidth: 0 }}
          aria-live="polite"
        >
          {headline}
        </Typography>
        <Typography
          variant="subtitle1"
          fontWeight={700}
          aria-hidden={remaining === null}
          sx={{
            width: '4ch',
            textAlign: 'right',
            fontFamily: 'monospace',
            fontVariantNumeric: 'tabular-nums',
            color: urgent ? 'error.main' : 'text.secondary',
            visibility: remaining === null ? 'hidden' : 'visible',
          }}
        >
          {remaining !== null ? `${Math.ceil(remaining)}s` : '00s'}
        </Typography>
        <Button
          size="small"
          color="error"
          variant="outlined"
          startIcon={<Flag />}
          onClick={onResign}
          sx={{ flexShrink: 0, minWidth: 100 }}
        >
          {status === 'queued' ? 'Cancel' : 'Resign'}
        </Button>
      </Box>

      <LinearProgress
        variant={remaining !== null ? 'determinate' : 'indeterminate'}
        value={remaining !== null ? Math.min(100, (remaining / moveTimeLimit!) * 100) : 0}
        color={urgent ? 'error' : remaining !== null ? 'primary' : 'inherit'}
        aria-label={remaining !== null ? 'Time left for your move' : 'Waiting for the agent'}
        sx={{
          mt: 1.5,
          height: 6,
          borderRadius: 3,
          ...(remaining === null && {
            opacity: 0.35,
            '& .MuiLinearProgress-bar': { animationDuration: '3s' },
          }),
          '& .MuiLinearProgress-bar': {
            borderRadius: 3,
            ...(remaining !== null && { transition: 'transform 0.2s linear' }),
          },
        }}
      />
    </Box>
  );
}

// ─── Replay Controls ──────────────────────────────────────────────────────────

function ReplayControls({
  replayIndex,
  historyLength,
  isPlaying,
  onSeek,
  onPlay,
  onPrev,
  onNext,
  onGoStart,
  onGoEnd,
}: {
  replayIndex: number;
  historyLength: number;
  isPlaying: boolean;
  onSeek: (val: number) => void;
  onPlay: () => void;
  onPrev: () => void;
  onNext: () => void;
  onGoStart: () => void;
  onGoEnd: () => void;
}) {
  return (
    <Box
      sx={{
        mt: 3,
        p: 2,
        borderRadius: 2,
        border: 1,
        borderColor: 'divider',
        backgroundColor: 'background.paper',
      }}
    >
      {/* Header row */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Typography variant="subtitle2" color="text.secondary" fontWeight={600}>
          Match Replay
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
          Turn {replayIndex + 1} / {historyLength}
        </Typography>
      </Box>

      {/* Controls row */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        {/* Go to start */}
        <Tooltip title="First turn">
          <span>
            <IconButton size="small" disabled={replayIndex === 0} onClick={onGoStart}>
              <SkipPrevious fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>

        {/* Step back */}
        <Tooltip title="Previous turn">
          <span>
            <IconButton size="small" disabled={replayIndex === 0} onClick={onPrev}>
              <NavigateBefore fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>

        {/* Play / pause */}
        <Tooltip title={isPlaying ? 'Pause' : 'Play'}>
          <IconButton
            color="primary"
            onClick={onPlay}
            sx={{
              backgroundColor: 'primary.main',
              color: '#fff',
              '&:hover': { backgroundColor: 'primary.dark' },
              width: 36,
              height: 36,
            }}
          >
            {isPlaying ? <Pause fontSize="small" /> : <PlayArrow fontSize="small" />}
          </IconButton>
        </Tooltip>

        {/* Step forward */}
        <Tooltip title="Next turn">
          <span>
            <IconButton size="small" disabled={replayIndex >= historyLength - 1} onClick={onNext}>
              <NavigateNext fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>

        {/* Go to end */}
        <Tooltip title="Last turn">
          <span>
            <IconButton size="small" disabled={replayIndex >= historyLength - 1} onClick={onGoEnd}>
              <SkipNext fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>

        {/* Scrubber */}
        <Slider
          value={replayIndex}
          min={0}
          max={historyLength > 0 ? historyLength - 1 : 0}
          step={1}
          onChange={(_, newVal) => {
            onSeek(newVal as number);
          }}
          sx={{ ml: 1.5, flex: 1 }}
        />
      </Box>
    </Box>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function LiveMatch() {
  const { matchId } = useParams<{ matchId: string }>();
  const goBack = useSmartBack('/games/matches');
  const { user } = useAuth();
  const [matchConfig, setMatchConfig] = useState<any>(null);

  // Pre-fetch: load match metadata + all agents before rendering the page content
  const [agentMap, setAgentMap] = useState<Record<string, string>>({});
  const [prefetchDone, setPrefetchDone] = useState(false);
  const [prefetchError, setPrefetchError] = useState<string | null>(null);
  const [containerLogs, setContainerLogs] = useState<Array<{
    id: string;
    container_id: string;
    agent_id: string;
    agent_name: string | null;
    name: string | null;
    status: string;
    logs: string | null;
  }>>([]);
  const [containerLogsError, setContainerLogsError] = useState<string | null>(null);

  useEffect(() => {
    if (!matchId) return;
    const fetchAgents = agentsApi.getAllAgents(true).then(res => {
      const agentsData = Array.isArray(res) ? res : (res as any).data || [];
      const map: Record<string, string> = {};
      agentsData.forEach((a: any) => { map[a.id] = a.name; });
      setAgentMap(map);
    });
    // Fetch match to warm agent IDs / game type before SSE connects
    const fetchMatch = matchesApi.getMatch(matchId)
      .then(m => setMatchConfig(m?.config ?? null))
      .catch(() => null); // non-fatal
    Promise.all([fetchAgents, fetchMatch])
      .then(() => setPrefetchDone(true))
      .catch(err => {
        console.error('Failed to pre-fetch data', err);
        setPrefetchError('Failed to load match data.');
        setPrefetchDone(true); // still proceed
      });
  }, [matchId]);

  const {
    gameState,
    matchStatus,
    gameType,
    agentIds,
    result,
    logs,
    isConnected,
    error,
    humanUserId,
    humanPlayerIndex,
    humanName,
    agentNames,
    humanMoveDeadline,
  } = useMatchStream(matchId);

  const isLoading = matchStatus === null;
  const isTerminal = matchStatus === 'completed' || matchStatus === 'failed' || matchStatus === 'client_error';
  const isError = matchStatus === 'failed' || matchStatus === 'client_error';

  // State to hold the log element for auto-scrolling
  const logEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  useEffect(() => {
    if (!matchId || !isTerminal) return;

    let pollCount = 0;
    const MAX_POLLS = 3;
    let active = true;

    const loadLogs = async () => {
      if (!active || pollCount >= MAX_POLLS) return;
      pollCount++;

      try {
        setContainerLogsError(null);
        const rows = await containersApi.getMatchContainers(matchId);
        if (!active) return;

        setContainerLogs(rows);
        const hasLogs = rows.some(r => r.logs && r.logs.trim().length > 0);

        // Stop if we found logs OR we reached the limit
        if (hasLogs || pollCount >= MAX_POLLS) {
          active = false;
          return;
        }
      } catch (err) {
        if (!active) return;
        const message = err instanceof Error ? err.message : 'Failed to load container logs';
        setContainerLogsError(message);

        if (pollCount >= MAX_POLLS) {
          active = false;
          return;
        }
      }

      // If still active and under limit, schedule next check
      if (active && pollCount < MAX_POLLS) {
        setTimeout(() => {
          void loadLogs();
        }, 5000);
      }
    };

    void loadLogs();
    return () => { active = false; };
  }, [matchId, isTerminal]);

  // Resolve game metadata from config
  const gameInfo = useMemo(() => {
    if (!gameType) return null;
    const frontendId = fromApiGameType(gameType);
    return getGameById(frontendId);
  }, [gameType]);

  // Get the correct renderer component for this game type
  const GameRenderer = useMemo(() => {
    if (!gameType) return null;
    return getGameRenderer(gameType);
  }, [gameType]);

  // ── Replay State ──
  const history: any[] = useMemo(() => result?.history || [], [result?.history]);
  const hasHistory = isTerminal && history.length > 0;

  const [replayIndex, setReplayIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Jump to last state when history first becomes available
  useEffect(() => {
    if (hasHistory) {
      setReplayIndex(history.length - 1);
    }
  }, [hasHistory, history.length]);

  // Auto-play interval
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (isPlaying && hasHistory) {
      timer = setInterval(() => {
        setReplayIndex((prev) => {
          if (prev >= history.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isPlaying, hasHistory, history.length]);

  // State to display: if we have history use selected replay frame, else live frame
  const displayedGameState = hasHistory ? history[replayIndex] : gameState;

  // Determine winner / draw for each agent
  const winnerId = result?.winner;
  const isDraw = winnerId === 'draw';

  // ── Human-vs-agent play ──
  const isHumanMatch = humanPlayerIndex !== null;
  const isMyGame = isHumanMatch && !!user && user.id === humanUserId;
  const playerIds = useMemo(() => {
    if (humanPlayerIndex === null) return agentIds;
    const ids = [...agentIds];
    ids.splice(humanPlayerIndex, 0, HUMAN_PLAYER_ID);
    return ids;
  }, [agentIds, humanPlayerIndex]);
  const playerMap = useMemo(() => {
    // agentNames covers other users' agents.
    const names = { ...agentNames, ...agentMap };
    if (!isHumanMatch) return names;
    const label = isMyGame ? 'You' : `${humanName ?? 'Human'} (human)`;
    return { ...names, [HUMAN_PLAYER_ID]: label };
  }, [agentMap, agentNames, isHumanMatch, isMyGame, humanName]);

  const isMyTurn = isMyGame && matchStatus === 'running' && !hasHistory
    && gameState?.turn === humanPlayerIndex;
  const [pendingMove, setPendingMove] = useState(false);
  const [moveError, setMoveError] = useState<string | null>(null);
  const [resignOpen, setResignOpen] = useState(false);
  const [resigning, setResigning] = useState(false);

  // Any stream event means the runner handled the pending move.
  useEffect(() => { setPendingMove(false); }, [gameState, logs]);

  const handleHumanMove = async (move: Record<string, unknown>) => {
    if (!matchId || pendingMove) return;
    setPendingMove(true);
    setMoveError(null);
    try {
      await matchesApi.submitHumanMove(matchId, move);
    } catch (err) {
      setPendingMove(false);
      setMoveError(err instanceof Error ? err.message : 'Failed to send move');
    }
  };

  const handleResign = async () => {
    if (!matchId) return;
    setResigning(true);
    try {
      await matchesApi.resignHumanMatch(matchId);
      setResignOpen(false);
    } catch (err) {
      setMoveError(err instanceof Error ? err.message : 'Failed to resign');
      setResignOpen(false);
    } finally {
      setResigning(false);
    }
  };

  const logsPanelContainers = useMemo(
    () => containerLogs
      .slice()
      .sort((a, b) => {
        const ai = agentIds.indexOf(a.agent_id);
        const bi = agentIds.indexOf(b.agent_id);
        if (ai === -1 && bi === -1) return 0;
        if (ai === -1) return 1;
        if (bi === -1) return -1;
        return ai - bi;
      })
      .slice(0, 2),
    [containerLogs, agentIds],
  );
  const hasAnyContainerLogs = useMemo(
    () => logsPanelContainers.some((container) => Boolean(container.logs && container.logs.trim().length > 0)),
    [logsPanelContainers],
  );

  // Game icon emoji
  const gameIcon = gameInfo?.icon === 'tictactoe' ? '⭕'
    : gameInfo?.icon === 'chess' ? '♟️'
      : gameInfo?.icon === 'circle' ? '🔵'
        : gameInfo?.icon === 'hexagon' ? '⬡'
          : '🎮';

  // ── Full-page loading / error state while pre-fetching ──
  if (!prefetchDone) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 2 }}>
          <CircularProgress size={44} />
          <Typography color="text.secondary">Loading match…</Typography>
        </Box>
      </Container>
    );
  }

  if (prefetchError) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Button startIcon={<ArrowBack />} onClick={goBack} variant="text" sx={{ mb: 3 }}>Back to Matches</Button>
        <Typography color="error">{prefetchError}</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>

      {/* ── Top bar: back + connection ── */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Button startIcon={<ArrowBack />} onClick={goBack} variant="text">
          Back to Matches
        </Button>
        <ConnectionIndicator isConnected={isConnected} error={error} isTerminal={isTerminal} />
      </Box>

      {/* ── Result banner (prominent, above everything else) ── */}
      {isTerminal && (
        <MatchResultBanner
          result={result}
          status={matchStatus}
          agentMap={playerMap}
          viewerPlayerId={isMyGame ? HUMAN_PLAYER_ID : null}
        />
      )}

      {/* ── Match header card ── */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          {/* Game name + status */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <Typography variant="h5" sx={{ fontSize: '1.5rem' }}>
              {gameIcon}
            </Typography>
            <Typography variant="h5" fontWeight={700} sx={{ flex: 1 }}>
              {gameInfo?.name ?? gameType ?? 'Loading…'}
            </Typography>
            {isHumanMatch && (
              <Chip icon={<Person />} label="Human vs Agent" size="small" variant="outlined" />
            )}
            <StatusChip status={isError ? 'failed' : matchStatus} />
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: playerIds.length > 0 ? 2 : 0, fontFamily: 'monospace', wordBreak: 'break-all' }}>
            {matchId}
          </Typography>

          {/* ── Agent player cards ── */}
          {playerIds.length > 0 && (
            <>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'center' }}>
                {playerIds.length === 2 ? (
                  <>
                    <AgentCard
                      name={playerMap[playerIds[0]] || playerIds[0].slice(0, 8) + '…'}
                      index={0}
                      isWinner={isTerminal && !isDraw && winnerId === playerIds[0]}
                      isDraw={isTerminal && isDraw}
                    />
                    <Typography variant="body2" color="text.secondary" fontWeight={700} sx={{ fontSize: '0.85rem', letterSpacing: 1 }}>
                      VS
                    </Typography>
                    <AgentCard
                      name={playerMap[playerIds[1]] || playerIds[1].slice(0, 8) + '…'}
                      index={1}
                      isWinner={isTerminal && !isDraw && winnerId === playerIds[1]}
                      isDraw={isTerminal && isDraw}
                    />
                  </>
                ) : (
                  playerIds.map((id, i) => {
                    const name = playerMap[id] || id.slice(0, 8) + '…';
                    return (
                      <AgentCard
                        key={id}
                        name={name}
                        index={i}
                        isWinner={isTerminal && !isDraw && winnerId === id}
                        isDraw={isTerminal && isDraw}
                      />
                    );
                  })
                )}
              </Box>
            </>
          )}
        </CardContent>
      </Card>

      {/* ── Game visualization ── */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ boxSizing: 'border-box' }}>
          {isMyGame && !isTerminal && !isLoading && (
            <HumanPlayPanel
              status={matchStatus}
              isMyTurn={isMyTurn}
              pendingMove={pendingMove}
              deadline={humanMoveDeadline}
              moveTimeLimit={typeof matchConfig?.human_turn_time_limit === 'number' ? matchConfig.human_turn_time_limit : null}
              onResign={() => setResignOpen(true)}
            />
          )}
          {isLoading ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 300, gap: 2 }}>
              <CircularProgress size={40} />
              <Typography color="text.secondary">Connecting to match…</Typography>
            </Box>
          ) : matchStatus === 'queued' ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 300, gap: 2 }}>
              <HourglassEmpty sx={{ fontSize: 48, color: 'text.secondary' }} />
              <Typography variant="h6" color="text.secondary">Match is queued</Typography>
              <Typography variant="body2" color="text.secondary">Waiting for the match to start…</Typography>
            </Box>
          ) : GameRenderer ? (
            <Box>
              <GameRenderer
                gameState={displayedGameState}
                gameType={gameType!}
                agentIds={playerIds}
                agentMap={playerMap}
                matchStatus={matchStatus}
                result={result}
                interactive={isMyGame && humanPlayerIndex !== null ? {
                  playerIndex: humanPlayerIndex,
                  enabled: isMyTurn && !pendingMove,
                  onMove: handleHumanMove,
                } : undefined}
              />

              {/* Replay controls */}
              {hasHistory && (
                <ReplayControls
                  replayIndex={replayIndex}
                  historyLength={history.length}
                  isPlaying={isPlaying}
                  onSeek={(val) => {
                    setIsPlaying(false);
                    setReplayIndex(val);
                  }}
                  onPlay={() => {
                    if (isPlaying) {
                      setIsPlaying(false);
                    } else {
                      if (replayIndex >= history.length - 1) setReplayIndex(0);
                      setIsPlaying(true);
                    }
                  }}
                  onPrev={() => {
                    setIsPlaying(false);
                    setReplayIndex((p) => Math.max(0, p - 1));
                  }}
                  onNext={() => {
                    setIsPlaying(false);
                    setReplayIndex((p) => Math.min(history.length - 1, p + 1));
                  }}
                  onGoStart={() => {
                    setIsPlaying(false);
                    setReplayIndex(0);
                  }}
                  onGoEnd={() => {
                    setIsPlaying(false);
                    setReplayIndex(history.length - 1);
                  }}
                />
              )}
            </Box>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography color="text.secondary">
                No renderer available for game type: {gameType}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* ── Match Logs ── */}
      {logs.trim() && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={700} sx={{ mb: 1.5 }}>
              Match Logs
            </Typography>
            <Box
              sx={{
                backgroundColor: 'action.hover',
                borderRadius: 2,
                p: 2,
                minHeight: 120,
                maxHeight: 240,
                overflowY: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                lineHeight: 1.6,
                color: 'text.primary',
                border: 1,
                borderColor: 'divider',
              }}
            >
              {logs.split('\n').map((line, i) => (
                <Box key={i} sx={{ py: 0.1 }}>
                  {line}
                </Box>
              ))}
              <div ref={logEndRef} />
            </Box>
          </CardContent>
        </Card>
      )}

      {/* ── Container logs (visibility filtered by backend) ── */}
      {isTerminal && hasAnyContainerLogs && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6" fontWeight={700}>Container Logs</Typography>
              <Typography variant="caption" color="text.secondary">
                Showing logs for containers you are allowed to view
              </Typography>
            </Box>

            {containerLogsError && (
              <Typography color="error" variant="body2" sx={{ mb: 2 }}>
                {containerLogsError}
              </Typography>
            )}

            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
                gap: 2,
              }}
            >
              {logsPanelContainers.map((container) => {
                const agentName = playerMap[container.agent_id]
                  || container.agent_name
                  || `${container.agent_id.slice(0, 8)}...`;
                const lines = container.logs ? container.logs.split(/\r?\n/) : [];

                return (
                  <Box key={container.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 1.5 }}>
                    <Box sx={{ mb: 1, display: 'flex', justifyContent: 'space-between', gap: 1, alignItems: 'center' }}>
                      <Typography variant="subtitle2" fontWeight={700} sx={{ minWidth: 0 }} noWrap>
                        {agentName}
                      </Typography>
                      <Chip size="small" label={container.status} variant="outlined" />
                    </Box>

                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                      {container.name || container.container_id.slice(0, 12)}
                    </Typography>

                    <Box
                      sx={{
                        backgroundColor: 'action.hover',
                        borderRadius: 1,
                        p: 1,
                        minHeight: 220,
                        maxHeight: 320,
                        overflowY: 'auto',
                        fontFamily: 'monospace',
                        fontSize: '0.78rem',
                        lineHeight: 1.5,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {lines.map((line, i) => (
                        <Box key={i}>{line}</Box>
                      ))}
                    </Box>
                  </Box>
                );
              })}
            </Box>
          </CardContent>
        </Card>
      )
      }

      <Snackbar
        open={!!moveError}
        autoHideDuration={5000}
        onClose={() => setMoveError(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="warning" variant="filled" onClose={() => setMoveError(null)} sx={{ width: '100%' }}>
          {moveError}
        </Alert>
      </Snackbar>

      <Dialog open={resignOpen} onClose={() => !resigning && setResignOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{matchStatus === 'queued' ? 'Cancel this game?' : 'Resign this game?'}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {matchStatus === 'queued'
              ? 'The game has not started yet. It will be removed from the queue.'
              : 'The agent will be declared the winner. Human games never affect agent stats or ELO.'}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResignOpen(false)} disabled={resigning}>Keep playing</Button>
          <Button onClick={handleResign} color="error" variant="contained" disabled={resigning}>
            {matchStatus === 'queued' ? 'Cancel game' : 'Resign'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container >
  );
}
