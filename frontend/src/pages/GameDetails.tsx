import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import {
    Box, Container, Typography, Button, Card, CardContent, Chip,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    LinearProgress, CircularProgress, Alert, Divider,
} from '@mui/material';
import {
    ArrowBack, SportsEsports, EmojiEvents, Close, Circle, Album,
    PanoramaFishEye, Casino, Videocam, History, ArrowForward,
    AddCircleOutline, SmartToy, FiberManualRecord,
} from '@mui/icons-material';
import { fromApiGameType, getGameById } from '../config/games';
import { matchesApi } from '../services/api/matches';
import { leaderboardApi } from '../services/api/leaderboard';
import { agentsApi, Agent } from '../services/api/agents';
import { palette, overlays } from '../theme';

// ─── Types ────────────────────────────────────────────────────────

interface Match {
    id: string;
    game_id: string;
    status: string;
    created_at: string;
    completed_at?: string;
    result?: any;
}

interface LeaderboardEntry {
    rank: number;
    user_id: string;
    username: string;
    score: number;
    wins: number;
    losses: number;
    draws: number;
    total_matches: number;
}

// ─── Icon Map ────────────────────────────────────────────────────

const iconMap: Record<string, React.ReactNode> = {
    chess: '♟',
    tictactoe: (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: 'inherit' }}>
            <Close sx={{ fontSize: 'inherit' }} />
            <PanoramaFishEye sx={{ fontSize: 'inherit' }} />
        </Box>
    ),
    circle: <Circle sx={{ fontSize: 'inherit' }} />,
    album: <Album sx={{ fontSize: 'inherit' }} />,
    casino: <Casino sx={{ fontSize: 'inherit' }} />,
};

// ─── Helpers ─────────────────────────────────────────────────────

const isRunning = (match: Match) =>
    match.status === 'running' || match.status === 'in_progress';

const isCompleted = (match: Match) =>
    match.status === 'completed' || match.status === 'failed' || match.status === 'client_error';

const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
};

const difficultyColor = (d: string) => {
    if (d === 'easy') return palette.success;
    if (d === 'medium') return palette.warning;
    if (d === 'hard') return palette.error;
    return palette.textMuted;
};

const getRankBadge = (rank: number) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
};

const statusColor = (status: string): 'success' | 'error' | 'warning' | 'default' => {
    if (status === 'completed') return 'success';
    if (status === 'failed' || status === 'client_error') return 'error';
    if (isRunning({ status } as Match)) return 'warning';
    return 'default';
};

// ─── Section Header ───────────────────────────────────────────────

function SectionHeader({
    icon,
    title,
    linkTo,
    linkLabel,
}: {
    icon: React.ReactNode;
    title: string;
    linkTo?: string;
    linkLabel?: string;
}) {
    return (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {icon} {title}
            </Typography>
            {linkTo && (
                <Button
                    component={Link}
                    to={linkTo}
                    endIcon={<ArrowForward sx={{ fontSize: 16 }} />}
                    variant="text"
                    size="small"
                    sx={{ color: palette.primary }}
                >
                    {linkLabel}
                </Button>
            )}
        </Box>
    );
}

// ─── Loading / Error helpers ──────────────────────────────────────

function SectionSkeleton() {
    return (
        <Box sx={{ py: 3, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress size={28} />
        </Box>
    );
}

function SectionError({ message }: { message: string }) {
    return <Alert severity="error" sx={{ mb: 2 }}>{message}</Alert>;
}

// ─── Main Component ───────────────────────────────────────────────

export function GameDetails() {
    const { gameId } = useParams<{ gameId: string }>();
    const navigate = useNavigate();
    const goBack = useSmartBack('/games');
    const game = getGameById(gameId ?? '');

    // Data state
    const [matches, setMatches] = useState<Match[]>([]);
    const [matchesLoading, setMatchesLoading] = useState(true);
    const [matchesError, setMatchesError] = useState<string | null>(null);

    const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
    const [lbLoading, setLbLoading] = useState(true);
    const [lbError, setLbError] = useState<string | null>(null);

    const [agents, setAgents] = useState<Agent[]>([]);
    const [agentsLoading, setAgentsLoading] = useState(true);
    const [agentsError, setAgentsError] = useState<string | null>(null);

    useEffect(() => {
        if (!gameId) return;

        // Matches
        matchesApi.getMatches({ game_id: gameId })
            .then(data => setMatches(data))
            .catch(err => setMatchesError(err.message || 'Failed to load matches'))
            .finally(() => setMatchesLoading(false));

        // Leaderboard
        leaderboardApi.getLeaderboard(gameId)
            .then(data => setLeaderboard(data))
            .catch(err => setLbError(err.message || 'Failed to load leaderboard'))
            .finally(() => setLbLoading(false));

        // Agents (filtered client-side by game)
        agentsApi.getAgents()
            .then(data => setAgents(data.filter(agent => fromApiGameType(agent.game_type) === gameId)))
            .catch(err => setAgentsError(err.message || 'Failed to load agents'))
            .finally(() => setAgentsLoading(false));
    }, [gameId]);

    // ── 404 guard ────────────────────────────────────────────────
    if (!game) {
        return (
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Alert severity="error">Game "{gameId}" not found.</Alert>
                <Button
                    startIcon={<ArrowBack />}
                    onClick={goBack}
                    sx={{ mt: 2 }}
                >
                    Back to Games
                </Button>
            </Container>
        );
    }

    const runningMatches = matches.filter(isRunning);
    const recentMatches = matches.filter(isCompleted).slice(0, 5);
    const topLeaderboard = leaderboard.slice(0, 5);

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            {/* ── Back button ─────────────────────────────────── */}
            <Button
                startIcon={<ArrowBack />}
                onClick={goBack}
                variant="text"
                sx={{ mb: 3 }}
            >
                All Games
            </Button>

            {/* ── Hero Card ───────────────────────────────────── */}
            <Card
                sx={{
                    mb: 4,
                    background: overlays.heroGradientSubtle,
                    border: `1px solid ${palette.border}`,
                }}
            >
                <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap' }}>
                        {/* Icon */}
                        <Box
                            sx={{
                                fontSize: 64,
                                color: palette.primary,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                minWidth: 72,
                            }}
                        >
                            {iconMap[game.icon] || <SportsEsports sx={{ fontSize: 64 }} />}
                        </Box>

                        {/* Info */}
                        <Box sx={{ flexGrow: 1 }}>
                            <Typography variant="h3" sx={{ mb: 0.5 }}>
                                {game.name}
                            </Typography>
                            <Typography color="text.secondary" sx={{ mb: 2 }}>
                                {game.description}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                <Chip
                                    label={game.category}
                                    size="small"
                                    sx={{ textTransform: 'capitalize' }}
                                />
                                <Chip
                                    label={game.difficulty}
                                    size="small"
                                    sx={{
                                        backgroundColor: `${difficultyColor(game.difficulty)}18`,
                                        color: difficultyColor(game.difficulty),
                                        textTransform: 'capitalize',
                                    }}
                                />
                                <Chip
                                    label={
                                        game.minPlayers === game.maxPlayers
                                            ? `${game.maxPlayers} players`
                                            : `${game.minPlayers}–${game.maxPlayers} players`
                                    }
                                    size="small"
                                />
                            </Box>
                        </Box>

                        {/* CTA */}
                        <Button
                            variant="contained"
                            size="large"
                            startIcon={<AddCircleOutline />}
                            onClick={() => navigate(`/agents/new?gameId=${gameId}`)}
                        >
                            Create New Agent
                        </Button>
                    </Box>
                </CardContent>
            </Card>

            {/* ── Grid layout for lower sections ──────────────── */}
            <Box
                sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', lg: '3fr 2fr' },
                    gap: 4,
                    alignItems: 'start',
                }}
            >
                {/* ── Left column ───────────────────────────── */}
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>

                    {/* ── Matches section ────────────────────── */}
                    <Box>
                        <SectionHeader
                            icon={<Videocam sx={{ fontSize: 22 }} />}
                            title="Matches"
                            linkTo={`/games/matches?game=${gameId}`}
                            linkLabel="See all matches"
                        />

                        {matchesLoading && <SectionSkeleton />}
                        {matchesError && <SectionError message={matchesError} />}

                        {!matchesLoading && !matchesError && (
                            <>
                                {/* Running matches */}
                                {runningMatches.length > 0 && (
                                    <Box sx={{ mb: 3 }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                                            <FiberManualRecord sx={{
                                                fontSize: 12,
                                                color: palette.error,
                                                animation: 'pulse 2s cubic-bezier(0.4,0,0.6,1) infinite',
                                                '@keyframes pulse': { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.4 } },
                                            }} />
                                            <Typography variant="body2" color="text.secondary">
                                                {runningMatches.length} match{runningMatches.length !== 1 ? 'es' : ''} in progress
                                            </Typography>
                                        </Box>
                                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                            {runningMatches.map(match => (
                                                <Card key={match.id} sx={{ border: `1px solid ${palette.error}30` }}>
                                                    <CardContent sx={{ py: '16px !important' }}>
                                                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
                                                            <Box sx={{ flexGrow: 1 }}>
                                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                                                    <Chip label="LIVE" size="small" color="error" sx={{ height: 20, fontSize: '0.7rem' }} />
                                                                    <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                                                        {match.id.slice(0, 8)}…
                                                                    </Typography>
                                                                </Box>
                                                                <Typography variant="caption" color="text.secondary">
                                                                    Started {formatDate(match.created_at)}
                                                                </Typography>
                                                            </Box>
                                                            <Button
                                                                component={Link}
                                                                to={`/games/live/${match.id}`}
                                                                variant="outlined"
                                                                size="small"
                                                                startIcon={<Videocam sx={{ fontSize: 16 }} />}
                                                                color="error"
                                                            >
                                                                Watch Live
                                                            </Button>
                                                        </Box>
                                                    </CardContent>
                                                </Card>
                                            ))}
                                        </Box>
                                    </Box>
                                )}

                                {/* Recent / past matches */}
                                <Box>
                                    <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1.5 }}>
                                        <History sx={{ fontSize: 16 }} /> Recent Matches
                                    </Typography>

                                    {recentMatches.length === 0 && runningMatches.length === 0 && (
                                        <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
                                            No matches yet for this game.
                                        </Typography>
                                    )}

                                    {recentMatches.length > 0 && (
                                        <Card>
                                            <TableContainer>
                                                <Table size="small">
                                                    <TableHead>
                                                        <TableRow>
                                                            <TableCell>Match ID</TableCell>
                                                            <TableCell>Status</TableCell>
                                                            <TableCell>Date</TableCell>
                                                            <TableCell align="right">Actions</TableCell>
                                                        </TableRow>
                                                    </TableHead>
                                                    <TableBody>
                                                        {recentMatches.map(match => (
                                                            <TableRow key={match.id}>
                                                                <TableCell>
                                                                    <Typography
                                                                        variant="body2"
                                                                        sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                                                                    >
                                                                        {match.id.slice(0, 8)}…
                                                                    </Typography>
                                                                </TableCell>
                                                                <TableCell>
                                                                    <Chip
                                                                        label={match.status}
                                                                        size="small"
                                                                        color={statusColor(match.status)}
                                                                        sx={{ textTransform: 'capitalize', height: 20, fontSize: '0.7rem' }}
                                                                    />
                                                                </TableCell>
                                                                <TableCell>
                                                                    <Typography variant="caption" color="text.secondary">
                                                                        {match.completed_at
                                                                            ? formatDate(match.completed_at)
                                                                            : formatDate(match.created_at)}
                                                                    </Typography>
                                                                </TableCell>
                                                                <TableCell align="right">
                                                                    <Button
                                                                        component={Link}
                                                                        to={`/games/live/${match.id}`}
                                                                        size="small"
                                                                        variant="text"
                                                                    >
                                                                        View
                                                                    </Button>
                                                                </TableCell>
                                                            </TableRow>
                                                        ))}
                                                    </TableBody>
                                                </Table>
                                            </TableContainer>
                                        </Card>
                                    )}
                                </Box>
                            </>
                        )}
                    </Box>

                    {/* ── My Agents section ──────────────────── */}
                    <Box>
                        <SectionHeader
                            icon={<SmartToy sx={{ fontSize: 22 }} />}
                            title="My Agents"
                        />

                        {agentsLoading && <SectionSkeleton />}
                        {agentsError && <SectionError message={agentsError} />}

                        {!agentsLoading && !agentsError && (
                            <>
                                {agents.length === 0 ? (
                                    <Card>
                                        <CardContent sx={{ textAlign: 'center', py: 4 }}>
                                            <SmartToy sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
                                            <Typography color="text.secondary" sx={{ mb: 2 }}>
                                                You haven't created any agents for this game yet.
                                            </Typography>
                                            <Button
                                                variant="contained"
                                                startIcon={<AddCircleOutline />}
                                                onClick={() => navigate(`/agents/new?gameId=${gameId}`)}
                                            >
                                                Create New Agent
                                            </Button>
                                        </CardContent>
                                    </Card>
                                ) : (
                                    <>
                                        <Card sx={{ mb: 2 }}>
                                            <TableContainer>
                                                <Table size="small">
                                                    <TableHead>
                                                        <TableRow>
                                                            <TableCell>Agent ID</TableCell>
                                                            <TableCell>Submission</TableCell>
                                                            <TableCell>Date</TableCell>
                                                            <TableCell align="right">Actions</TableCell>
                                                        </TableRow>
                                                    </TableHead>
                                                    <TableBody>
                                                        {agents.map(agent => (
                                                            <TableRow key={agent.id}>
                                                                <TableCell>
                                                                    <Typography
                                                                        variant="body2"
                                                                        sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                                                                    >
                                                                        {agent.id.slice(0, 8)}…
                                                                    </Typography>
                                                                </TableCell>
                                                                <TableCell>
                                                                    <Typography
                                                                        variant="body2"
                                                                        sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                                                                    >
                                                                        {agent.active_submission_id ? `${agent.active_submission_id.slice(0, 8)}…` : 'None'}
                                                                    </Typography>
                                                                </TableCell>
                                                                <TableCell>
                                                                    <Typography variant="caption" color="text.secondary">
                                                                        {formatDate(agent.created_at)}
                                                                    </Typography>
                                                                </TableCell>
                                                                <TableCell align="right">
                                                                    <Button
                                                                        component={Link}
                                                                        to={`/agents/${agent.id}`}
                                                                        size="small"
                                                                        variant="text"
                                                                    >
                                                                        Details
                                                                    </Button>
                                                                </TableCell>
                                                            </TableRow>
                                                        ))}
                                                    </TableBody>
                                                </Table>
                                            </TableContainer>
                                        </Card>
                                        <Button
                                            variant="outlined"
                                            startIcon={<AddCircleOutline />}
                                            onClick={() => navigate(`/agents/new?gameId=${gameId}`)}
                                            fullWidth
                                        >
                                            Create New Agent
                                        </Button>
                                    </>
                                )}
                            </>
                        )}
                    </Box>
                </Box>

                {/* ── Right column: Leaderboard ─────────────── */}
                <Box>
                    <SectionHeader
                        icon={<EmojiEvents sx={{ fontSize: 22 }} />}
                        title="Leaderboard"
                        linkTo={`/leaderboard?game=${gameId}`}
                        linkLabel="Full leaderboard"
                    />

                    {lbLoading && <SectionSkeleton />}
                    {lbError && <SectionError message={lbError} />}

                    {!lbLoading && !lbError && (
                        <Card>
                            {topLeaderboard.length === 0 ? (
                                <CardContent sx={{ textAlign: 'center', py: 4 }}>
                                    <Typography color="text.secondary">No rankings yet.</Typography>
                                </CardContent>
                            ) : (
                                <>
                                    {topLeaderboard.map((entry, idx) => (
                                        <Box key={entry.user_id}>
                                            {idx > 0 && <Divider />}
                                            <Box
                                                sx={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 2,
                                                    px: 3,
                                                    py: 1.5,
                                                    backgroundColor: entry.rank <= 3
                                                        ? overlays.primaryGlowFaint
                                                        : 'transparent',
                                                }}
                                            >
                                                {/* Rank */}
                                                <Typography
                                                    sx={{
                                                        minWidth: 32,
                                                        fontSize: entry.rank <= 3 ? '1.1rem' : '0.875rem',
                                                        fontWeight: 700,
                                                        textAlign: 'center',
                                                    }}
                                                >
                                                    {getRankBadge(entry.rank)}
                                                </Typography>

                                                {/* User info */}
                                                <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                                                    <Typography variant="body2" fontWeight={600} noWrap>
                                                        {entry.username}
                                                    </Typography>
                                                    <Typography variant="caption" color="text.secondary">
                                                        {entry.wins}W · {entry.losses}L
                                                        {entry.total_matches > 0 && (
                                                            <> · {((entry.wins / entry.total_matches) * 100).toFixed(0)}% WR</>
                                                        )}
                                                    </Typography>
                                                </Box>

                                                {/* Score */}
                                                <Box sx={{ textAlign: 'right' }}>
                                                    <Typography
                                                        variant="body2"
                                                        fontWeight={700}
                                                        color="primary"
                                                    >
                                                        {entry.score}
                                                    </Typography>
                                                    <Typography variant="caption" color="text.secondary">
                                                        pts
                                                    </Typography>
                                                </Box>
                                            </Box>

                                            {/* Win rate bar */}
                                            {entry.total_matches > 0 && (
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={(entry.wins / entry.total_matches) * 100}
                                                    sx={{ height: 2, mx: 3, mb: 0.5 }}
                                                />
                                            )}
                                        </Box>
                                    ))}
                                </>
                            )}
                        </Card>
                    )}
                </Box>
            </Box>
        </Container>
    );
}
