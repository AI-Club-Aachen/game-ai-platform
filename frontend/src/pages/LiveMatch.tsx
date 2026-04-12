import { useMemo, useState, useEffect } from 'react';
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
} from '@mui/icons-material';
import { useSmartBack } from '../hooks/use-smart-back';
import { useMatchStream } from '../hooks/useMatchStream';
import { getGameRenderer } from '../components/game-renderers';
import { fromApiGameType, getGameById } from '../config/games';
import { agentsApi } from '../services/api/agents';
import { matchesApi } from '../services/api/matches';
import { containersApi } from '../services/api/containers';

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
}: {
  result: any;
  status: string | null;
  agentMap: Record<string, string>;
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
    headline = `${winnerName} Wins!`;
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
    const fetchAgents = agentsApi.getAgents(0, 1000, true).then(res => {
      const agentsData = Array.isArray(res) ? res : (res as any).data || [];
      const map: Record<string, string> = {};
      agentsData.forEach((a: any) => { map[a.id] = a.name; });
      setAgentMap(map);
    });
    // Fetch match to warm agent IDs / game type before SSE connects
    const fetchMatch = matchesApi.getMatch(matchId).catch(() => null); // non-fatal
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
    isConnected,
    error,
  } = useMatchStream(matchId);

  const isLoading = matchStatus === null;
  const isTerminal = matchStatus === 'completed' || matchStatus === 'failed' || matchStatus === 'client_error';
  const isError = matchStatus === 'failed' || matchStatus === 'client_error';

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
          agentMap={agentMap}
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
            <StatusChip status={isError ? 'failed' : matchStatus} />
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: agentIds.length > 0 ? 2 : 0, fontFamily: 'monospace', wordBreak: 'break-all' }}>
            {matchId}
          </Typography>

          {/* ── Agent player cards ── */}
          {agentIds.length > 0 && (
            <>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'center' }}>
                {agentIds.length === 2 ? (
                  <>
                    <AgentCard
                      name={agentMap[agentIds[0]] || agentIds[0].slice(0, 8) + '…'}
                      index={0}
                      isWinner={isTerminal && !isDraw && winnerId === agentIds[0]}
                      isDraw={isTerminal && isDraw}
                    />
                    <Typography variant="body2" color="text.secondary" fontWeight={700} sx={{ fontSize: '0.85rem', letterSpacing: 1 }}>
                      VS
                    </Typography>
                    <AgentCard
                      name={agentMap[agentIds[1]] || agentIds[1].slice(0, 8) + '…'}
                      index={1}
                      isWinner={isTerminal && !isDraw && winnerId === agentIds[1]}
                      isDraw={isTerminal && isDraw}
                    />
                  </>
                ) : (
                  agentIds.map((id, i) => {
                    const name = agentMap[id] || id.slice(0, 8) + '…';
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
                agentIds={agentIds}
                agentMap={agentMap}
                matchStatus={matchStatus}
                result={result}
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
                const agentName = agentMap[container.agent_id]
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
    </Container >
  );
}
