import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import {
    Box, Container, Typography, Button, Card, CardContent, Chip,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    CircularProgress, Alert,
} from '@mui/material';
import {
    ArrowBack, SportsEsports, EmojiEvents, Close, Circle, Album,
    PanoramaFishEye, Casino, Videocam, History, ArrowForward,
    AddCircleOutline, SmartToy, FiberManualRecord, Hexagon, Lock, LockOpen
} from '@mui/icons-material';
import { fromApiGameType, getGameById } from '../config/games';
import { matchesApi } from '../services/api/matches';
import { agentsApi, Agent } from '../services/api/agents';
import { submissionsApi, Submission } from '../services/api/submissions';
import { arenasApi, ArenaRead } from '../services/api/arenas';
import { tournamentsApi, Tournament } from '../services/api/tournaments';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { PrimarySecondaryCell } from '../components/common/TableCells';
import { palette, overlays } from '../theme';

interface Match {
    id: string;
    game_type: string;
    status: string;
    created_at: string;
    completed_at?: string;
    result?: any;
}

interface LeaderboardEntry {
    id: string;
    rank: number;
    user_id: string;
    username: string;
    elo: number;
    wins: number;
    losses: number;
    draws: number;
    matches_played: number;
    agent_name: string;
}

const iconMap: Record<string, React.ReactNode> = {
    chess: '♟',
    tictactoe: (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: 'inherit' }}>
            <Close sx={{ fontSize: 'inherit' }} />
            <PanoramaFishEye sx={{ fontSize: 'inherit' }} />
        </Box>
    ),
    hexagon: <Hexagon sx={{ fontSize: 'inherit' }} />,
    circle: <Circle sx={{ fontSize: 'inherit' }} />,
    album: <Album sx={{ fontSize: 'inherit' }} />,
    casino: <Casino sx={{ fontSize: 'inherit' }} />,
};

const isRunning = (match: Match) =>
    match.status === 'running' || match.status === 'in_progress';

const isCompleted = (match: Match) =>
    match.status === 'completed' || match.status === 'failed' || match.status === 'client_error';

const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
};

const getRankBadge = (rank: number) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
};

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

export function ArenaDetails() {
    const { arenaId } = useParams<{ arenaId: string }>();
    const navigate = useNavigate();
    
    const [arena, setArena] = useState<ArenaRead | null>(null);
    const [arenaLoading, setArenaLoading] = useState(true);
    const [arenaError, setArenaError] = useState<string | null>(null);

    const [matches, setMatches] = useState<Match[]>([]);
    const [matchesLoading, setMatchesLoading] = useState(true);
    const [matchesError, setMatchesError] = useState<string | null>(null);

    const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
    const [lbLoading, setLbLoading] = useState(true);
    const [lbError, setLbError] = useState<string | null>(null);

    const [agents, setAgents] = useState<Agent[]>([]);
    const [submissions, setSubmissions] = useState<Submission[]>([]);
    const [agentsLoading, setAgentsLoading] = useState(true);
    const [agentsError, setAgentsError] = useState<string | null>(null);

    const [tournaments, setTournaments] = useState<Tournament[]>([]);
    const [tournamentsLoading, setTournamentsLoading] = useState(true);

    const goBack = useSmartBack(arena ? `/games/${fromApiGameType(arena.game_type)}` : '/games');

    useEffect(() => {
        if (!arenaId) return;

        // Fetch Arena
        arenasApi.getArena(arenaId)
            .then(data => {
                setArena(data);
                setArenaLoading(false);
                
                // Load tournaments
                tournamentsApi.getTournaments({ arena_id: arenaId, limit: 5 })
                    .then(tourneys => setTournaments(tourneys))
                    .catch(err => console.error("Failed to load tournaments", err))
                    .finally(() => setTournamentsLoading(false));
            })
            .catch(err => {
                setArenaError(err.message || 'Failed to load arena details');
                setArenaLoading(false);
            });

        // Matches
        matchesApi.getMatches({
            arena_id: arenaId,
            status: ['running', 'completed', 'failed', 'client_error'],
            limit: 50
        })
            .then(data => setMatches(data))
            .catch(err => setMatchesError(err.message || 'Failed to load matches'))
            .finally(() => setMatchesLoading(false));

        // Leaderboard
        agentsApi.getLeaderboardByArena(arenaId)
            .then(data => {
                // Map ranks to the entries
                const ranked = data.map((entry, idx) => ({
                    ...entry,
                    rank: idx + 1
                }));
                setLeaderboard(ranked);
            })
            .catch(err => setLbError(err.message || 'Failed to load leaderboard'))
            .finally(() => setLbLoading(false));

        // Agents (filtered client-side by arena)
        agentsApi.getAllAgents()
            .then(data => setAgents(data.filter(agent => agent.arena_id === arenaId)))
            .catch(err => setAgentsError(err.message || 'Failed to load agents'))
            .finally(() => setAgentsLoading(false));

        submissionsApi.getSubmissions(0, 100)
            .then(data => setSubmissions(data))
            .catch(err => console.error("Failed to load submissions", err));
    }, [arenaId]);

    if (arenaLoading) {
        return (
            <Container maxWidth="lg" sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
            </Container>
        );
    }

    if (arenaError || !arena) {
        return (
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Alert severity="error">{arenaError || 'Arena not found'}</Alert>
                <Button startIcon={<ArrowBack />} onClick={() => navigate('/games')} sx={{ mt: 2 }}>
                    Back to Games
                </Button>
            </Container>
        );
    }

    const game = getGameById(fromApiGameType(arena.game_type));
    const runningMatches = matches.filter(isRunning);
    const recentMatches = matches.filter(isCompleted).slice(0, 5);
    const topLeaderboard = leaderboard.slice(0, 5);

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            {/* Back button */}
            <Button
                startIcon={<ArrowBack />}
                onClick={goBack}
                variant="text"
                sx={{ mb: 3 }}
            >
                Back to {game?.name || 'Game'} Arenas
            </Button>

            {/* Hero Card */}
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
                            {game && iconMap[game.icon] || <SportsEsports sx={{ fontSize: 64 }} />}
                        </Box>

                        {/* Info */}
                        <Box sx={{ flexGrow: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
                                <Typography variant="h3">
                                    {arena.name}
                                </Typography>
                                {arena.has_password ? (
                                    <Chip
                                        icon={<Lock sx={{ fontSize: '14px !important' }} />}
                                        label="Protected"
                                        size="small"
                                        color="warning"
                                        variant="outlined"
                                    />
                                ) : (
                                    <Chip
                                        icon={<LockOpen sx={{ fontSize: '14px !important' }} />}
                                        label="Public"
                                        size="small"
                                        color="success"
                                        variant="outlined"
                                    />
                                )}
                            </Box>
                            <Typography color="text.secondary" sx={{ mb: 2 }}>
                                {arena.description || `Arena for ${game?.name || arena.game_type}`}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                <Chip
                                    label={`Game: ${game?.name || arena.game_type}`}
                                    size="small"
                                />
                                <Chip
                                    label={`Packages: ${arena.packages || 'numpy'}`}
                                    size="small"
                                    color="info"
                                    variant="outlined"
                                />
                                {arena.config.board_size && (
                                    <Chip
                                        label={`Board Size: ${arena.config.board_size}x${arena.config.board_size}`}
                                        size="small"
                                        color="primary"
                                        variant="outlined"
                                    />
                                )}
                                {arena.config.turn_time_limit && (
                                    <Chip
                                        label={`Time Limit: ${arena.config.turn_time_limit}s / turn`}
                                        size="small"
                                    />
                                )}
                            </Box>
                        </Box>

                        {/* CTA */}
                        <Button
                            variant="contained"
                            size="large"
                            startIcon={<AddCircleOutline />}
                            onClick={() => navigate(`/agents/new?arenaId=${arena.id}&gameId=${fromApiGameType(arena.game_type)}`)}
                        >
                            Submit Agent
                        </Button>
                    </Box>
                </CardContent>
            </Card>

            {/* Grid layout for lower sections */}
            <Box
                sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', lg: '3fr 2fr' },
                    gap: 4,
                    alignItems: 'start',
                }}
            >
                {/* Left column */}
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>

                    {/* Matches section */}
                    <Box>
                        <SectionHeader
                            icon={<Videocam sx={{ fontSize: 22 }} />}
                            title="Matches"
                            linkTo={`/games/matches?arena_id=${arena.id}`}
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
                                            No matches yet for this arena.
                                        </Typography>
                                    )}

                                    {recentMatches.length > 0 && (
                                        <Card>
                                            <TableContainer>
                                                <Table size="small">
                                                    <TableHead>
                                                        <TableRow>
                                                            <TableCell>Match</TableCell>
                                                            <TableCell>Status</TableCell>
                                                            <TableCell>Finished</TableCell>
                                                            <TableCell align="right">Actions</TableCell>
                                                        </TableRow>
                                                    </TableHead>
                                                    <TableBody>
                                                        {recentMatches.map(match => (
                                                            <TableRow key={match.id}>
                                                                <TableCell>
                                                                    <PrimarySecondaryCell
                                                                        primary={`${match.id.slice(0, 8)}…`}
                                                                        title={match.id}
                                                                    />
                                                                </TableCell>
                                                                <TableCell>
                                                                    <StatusIndicator status={match.status} />
                                                                </TableCell>
                                                                <TableCell>
                                                                    <Typography variant="body2" color="text.secondary">
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

                    {/* My Agents section */}
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
                                        <CardContent sx={{ py: 3, textAlign: 'center' }}>
                                            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                                You haven't submitted any agents for this arena yet.
                                            </Typography>
                                            <Button
                                                variant="outlined"
                                                size="small"
                                                startIcon={<AddCircleOutline />}
                                                onClick={() => navigate(`/agents/new?arenaId=${arena.id}&gameId=${fromApiGameType(arena.game_type)}`)}
                                            >
                                                Create First Agent
                                            </Button>
                                        </CardContent>
                                    </Card>
                                ) : (
                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                        {agents.map(agent => {
                                            const sub = submissions.find(s => s.id === agent.active_submission_id);
                                            return (
                                                <Card key={agent.id}>
                                                    <CardContent>
                                                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
                                                            <Box>
                                                                <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                                    {agent.name}
                                                                </Typography>
                                                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                                                                    Active build: {sub ? sub.name : 'None (No builds)'}
                                                                </Typography>
                                                                <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
                                                                    <Chip label={`ELO: ${agent.elo ?? 1200}`} size="small" color="primary" />
                                                                    <Chip label={`Record: ${agent.wins}W - ${agent.losses}L - ${agent.draws}D`} size="small" variant="outlined" />
                                                                </Box>
                                                            </Box>
                                                            <Button
                                                                component={Link}
                                                                to={`/agents/${agent.id}`}
                                                                variant="outlined"
                                                                size="small"
                                                            >
                                                                Manage Agent
                                                            </Button>
                                                        </Box>
                                                    </CardContent>
                                                </Card>
                                            );
                                        })}
                                    </Box>
                                )}
                            </>
                        )}
                    </Box>
                </Box>

                {/* Right column */}
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    
                    {/* Leaderboard section */}
                    <Box>
                        <SectionHeader
                            icon={<EmojiEvents sx={{ fontSize: 22 }} />}
                            title="Leaderboard"
                            linkTo={`/leaderboard?arena=${arena.id}`}
                            linkLabel="Full leaderboard"
                        />

                        {lbLoading && <SectionSkeleton />}
                        {lbError && <SectionError message={lbError} />}

                        {!lbLoading && !lbError && (
                            <Card>
                                {topLeaderboard.length === 0 ? (
                                    <CardContent sx={{ py: 3, textAlign: 'center' }}>
                                        <Typography variant="body2" color="text.secondary">
                                            No ranked agents in this arena yet.
                                        </Typography>
                                    </CardContent>
                                ) : (
                                    <TableContainer>
                                        <Table size="small">
                                            <TableHead>
                                                <TableRow>
                                                    <TableCell sx={{ width: 60 }}>Rank</TableCell>
                                                    <TableCell>Agent / User</TableCell>
                                                    <TableCell align="right">ELO</TableCell>
                                                </TableRow>
                                            </TableHead>
                                            <TableBody>
                                                {topLeaderboard.map((entry) => (
                                                    <TableRow key={entry.id}>
                                                        <TableCell>
                                                            <Typography variant="body2" sx={{ fontWeight: entry.rank <= 3 ? 'bold' : 'normal' }}>
                                                                {getRankBadge(entry.rank)}
                                                            </Typography>
                                                        </TableCell>
                                                        <TableCell>
                                                            <PrimarySecondaryCell
                                                                primary={entry.agent_name}
                                                                secondary={`by ${entry.username}`}
                                                            />
                                                        </TableCell>
                                                        <TableCell align="right">
                                                            <Typography sx={{ fontWeight: 'medium' }}>
                                                                {entry.elo}
                                                            </Typography>
                                                        </TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </TableContainer>
                                )}
                            </Card>
                        )}
                    </Box>

                    {/* Active Tournaments section */}
                    <Box>
                        <SectionHeader
                            icon={<EmojiEvents sx={{ fontSize: 22, color: 'gold' }} />}
                            title="Recent Tournaments"
                            linkTo="/tournaments"
                            linkLabel="All tournaments"
                        />

                        {tournamentsLoading && <SectionSkeleton />}

                        {!tournamentsLoading && (
                            <Card>
                                {tournaments.length === 0 ? (
                                    <CardContent sx={{ py: 3, textAlign: 'center' }}>
                                        <Typography variant="body2" color="text.secondary">
                                            No tournaments hosted in this arena yet.
                                        </Typography>
                                    </CardContent>
                                ) : (
                                    <TableContainer>
                                        <Table size="small">
                                            <TableHead>
                                                <TableRow>
                                                    <TableCell>Name</TableCell>
                                                    <TableCell>Status</TableCell>
                                                    <TableCell align="right">Link</TableCell>
                                                </TableRow>
                                            </TableHead>
                                            <TableBody>
                                                {tournaments.map((tourney) => (
                                                    <TableRow key={tourney.id}>
                                                        <TableCell>
                                                            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                                                {tourney.name}
                                                            </Typography>
                                                        </TableCell>
                                                        <TableCell>
                                                            <StatusIndicator status={tourney.status} />
                                                        </TableCell>
                                                        <TableCell align="right">
                                                            <Button
                                                                component={Link}
                                                                to={`/tournaments/${tourney.id}`}
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
                                )}
                            </Card>
                        )}
                    </Box>
                </Box>
            </Box>
        </Container>
    );
}
