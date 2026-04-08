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
  Alert,
  Slider,
  IconButton,
} from '@mui/material';
import {
  ArrowBack,
  FiberManualRecord,
  SignalWifiOff,
  CheckCircle,
  Error as ErrorIcon,
  HourglassEmpty,
  PlayArrow,
  Pause,
  SkipPrevious,
  SkipNext,
} from '@mui/icons-material';
import { useSmartBack } from '../hooks/use-smart-back';
import { useMatchStream } from '../hooks/useMatchStream';
import { getGameRenderer } from '../components/game-renderers';
import { fromApiGameType, getGameById } from '../config/games';
import { agentsApi } from '../services/api/agents';

/** Map match status to a user-friendly chip */
function StatusChip({ status }: { status: string | null }) {
  if (!status) return null;

  const config: Record<string, { label: string; color: 'default' | 'success' | 'error' | 'warning' | 'info' }> = {
    queued: { label: 'Queued', color: 'default' },
    running: { label: 'Live', color: 'error' },
    completed: { label: 'Completed', color: 'success' },
    failed: { label: 'Failed', color: 'error' },
    client_error: { label: 'Client Error', color: 'warning' },
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

/** Connection status indicator */
function ConnectionIndicator({ isConnected, error }: { isConnected: boolean; error: string | null }) {
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
        }}
      />
      <Typography variant="caption" color="text.secondary">
        {isConnected ? 'Connected' : 'Connecting...'}
      </Typography>
    </Box>
  );
}

/** Result summary for completed/failed matches */
function MatchResult({ result, status }: { result: any; status: string | null }) {
  if (!result || !status) return null;

  const isError = status === 'failed' || status === 'client_error';

  if (isError) {
    return (
      <Alert severity="error" icon={<ErrorIcon />} sx={{ mt: 2 }}>
        <Typography variant="body2" fontWeight={600}>
          Match {status === 'failed' ? 'Failed' : 'Client Error'}
        </Typography>
        {result.reason && (
          <Typography variant="body2" color="text.secondary">
            {result.reason}
          </Typography>
        )}
      </Alert>
    );
  }

  if (status === 'completed') {
    return (
      <Alert severity="success" icon={<CheckCircle />} sx={{ mt: 2 }}>
        <Typography variant="body2" fontWeight={600}>
          Match Complete
        </Typography>
        {result.winner && (
          <Typography variant="body2" color="text.secondary">
            Winner: {result.winner === 'draw' ? 'Draw' : result.winner.slice(0, 8) + '…'}
          </Typography>
        )}
        {result.reason && (
          <Typography variant="body2" color="text.secondary">
            {result.reason}
          </Typography>
        )}
      </Alert>
    );
  }

  return null;
}

export function LiveMatch() {
  const { matchId } = useParams<{ matchId: string }>();
  const goBack = useSmartBack('/games/matches');

  const [agentMap, setAgentMap] = useState<Record<string, string>>({});

  useEffect(() => {
    agentsApi.getAgents(0, 1000, true)
      .then(res => {
        const agentsData = Array.isArray(res) ? res : (res as any).data || [];
        const map: Record<string, string> = {};
        agentsData.forEach((a: any) => { map[a.id] = a.name; });
        setAgentMap(map);
      })
      .catch(err => console.error("Failed to load agents", err));
  }, []);

  const {
    gameState,
    matchStatus,
    gameType,
    agentIds,
    result,
    isConnected,
    error,
  } = useMatchStream(matchId);

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

  const isLoading = matchStatus === null;
  const isTerminal = matchStatus === 'completed' || matchStatus === 'failed' || matchStatus === 'client_error';

  // --- Replay State Logic ---
  const history: any[] = useMemo(() => result?.history || [], [result?.history]);
  const hasHistory = isTerminal && history.length > 0;
  
  const [replayIndex, setReplayIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Set replay index to end when history first becomes available
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
      }, 1000); // 1 state per second playback
    }
    return () => clearInterval(timer);
  }, [isPlaying, hasHistory, history.length]);

  // The state to render: if we have history, use the selected replay frame, else use the live frame
  const displayedGameState = hasHistory ? history[replayIndex] : gameState;

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      {/* Back button + connection status */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Button startIcon={<ArrowBack />} onClick={goBack} variant="text">
          Back to Matches
        </Button>
        <ConnectionIndicator isConnected={isConnected} error={error} />
      </Box>

      {/* Match header */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
                {gameInfo && (
                  <Typography variant="h5" sx={{ fontSize: '1.5rem' }}>
                    {gameInfo.icon === 'tictactoe' ? '⭕' : gameInfo.icon === 'chess' ? '♟️' : '🎮'}
                  </Typography>
                )}
                <Typography variant="h5" fontWeight={700}>
                  {gameInfo?.name ?? gameType ?? 'Loading...'}
                </Typography>
                <StatusChip status={matchStatus} />
              </Box>
              <Typography variant="body2" color="text.secondary">
                Match {matchId?.slice(0, 8)}…
              </Typography>
            </Box>

            {/* Agents */}
            {agentIds.length > 0 && (
              <Box sx={{ display: 'flex', gap: 2 }}>
                {agentIds.map((id, i) => (
                  <Chip
                    key={id}
                    variant="outlined"
                    size="small"
                    label={`${agentMap[id] || id.slice(0, 8) + '...'}`}
                    sx={{
                      borderColor: i === 0 ? '#6366f1' : '#f43f5e',
                      color: i === 0 ? '#6366f1' : '#f43f5e',
                      fontWeight: 500,
                      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                      fontSize: '0.75rem',
                    }}
                  />
                ))}
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Game visualization */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ minHeight: 360, boxSizing: 'border-box' }}>
          {isLoading ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 300, gap: 2 }}>
              <CircularProgress size={40} />
              <Typography color="text.secondary">
                Connecting to match…
              </Typography>
            </Box>
          ) : matchStatus === 'queued' ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 300, gap: 2 }}>
              <HourglassEmpty sx={{ fontSize: 48, color: 'text.secondary' }} />
              <Typography variant="h6" color="text.secondary">
                Match is queued
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Waiting for the match to start…
              </Typography>
            </Box>
          ) : GameRenderer ? (
            <Box>
              <GameRenderer
                gameState={displayedGameState}
                gameType={gameType!}
                agentIds={agentIds}
              />
              
              {/* Replay Controls (Only shown if history is available) */}
              {hasHistory && (
                <Box sx={{ mt: 4, px: 2, bg: 'background.paper', borderRadius: 2, p: 2, border: 1, borderColor: 'divider' }}>
                  <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Match Replay</span>
                    <span>Turn {replayIndex} / {history.length - 1}</span>
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <IconButton 
                      size="small" 
                      disabled={replayIndex === 0}
                      onClick={() => setReplayIndex(0)}
                    >
                      <SkipPrevious />
                    </IconButton>
                    <IconButton
                      color="primary"
                      onClick={() => {
                        if (isPlaying) {
                          setIsPlaying(false);
                        } else {
                          if (replayIndex >= history.length - 1) {
                            setReplayIndex(0); // Restart if at end
                          }
                          setIsPlaying(true);
                        }
                      }}
                    >
                      {isPlaying ? <Pause /> : <PlayArrow />}
                    </IconButton>
                    <IconButton 
                      size="small" 
                      disabled={replayIndex >= history.length - 1}
                      onClick={() => setReplayIndex(history.length - 1)}
                    >
                      <SkipNext />
                    </IconButton>
                    <Slider
                      value={replayIndex}
                      min={0}
                      max={history.length > 0 ? history.length - 1 : 0}
                      step={1}
                      onChange={(_, newVal) => {
                        setIsPlaying(false); // Pause when seeking
                        setReplayIndex(newVal as number);
                      }}
                      sx={{ ml: 2, flex: 1 }}
                    />
                  </Box>
                </Box>
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

      {/* Match result (shown for terminal states) */}
      {isTerminal && <MatchResult result={result} status={matchStatus} />}
    </Container>
  );
}
