import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import { useAuth } from '../context/AuthContext';
import {
    Box, Container, Typography, Button, Card, CardContent,
    Dialog, DialogTitle, DialogContent, DialogActions, TextField,
    FormControlLabel, Checkbox, CircularProgress, Alert, InputAdornment, IconButton,
    FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import {
    ArrowBack, SportsEsports, Close, Circle, Album,
    PanoramaFishEye, Casino, AddCircleOutline, Hexagon,
    Lock, LockOpen, Visibility, VisibilityOff
} from '@mui/icons-material';
import { toApiGameType, getGameById } from '../config/games';
import { arenasApi, ArenaRead } from '../services/api/arenas';
import { palette, overlays } from '../theme';

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

export function GameDetails() {
    const { gameId } = useParams<{ gameId: string }>();
    const goBack = useSmartBack('/games');
    const { isAdmin } = useAuth();
    const game = getGameById(gameId ?? '');

    const [arenas, setArenas] = useState<ArenaRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Dialog state
    const [openCreate, setOpenCreate] = useState(false);
    const [arenaName, setArenaName] = useState('');
    const [arenaDesc, setArenaDesc] = useState('');
    const [boardSize, setBoardSize] = useState('11');
    const [packages, setPackages] = useState<'numpy' | 'torch'>('numpy');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [isActive, setIsActive] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);

    const loadArenas = () => {
        if (!gameId) return;
        setLoading(true);
        arenasApi.getArenas()
            .then(data => {
                const apiGameType = toApiGameType(gameId);
                setArenas(data.filter(arena => arena.game_type === apiGameType));
                setError(null);
            })
            .catch(err => {
                setError(err.message || 'Failed to load arenas');
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadArenas();
    }, [gameId]);

    if (!game) {
        return (
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Alert severity="error">Game "{gameId}" not found.</Alert>
                <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mt: 2 }}>
                    Back to Games
                </Button>
            </Container>
        );
    }

    const handleCreateArena = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!arenaName.trim() || !gameId) return;

        setSubmitting(true);
        setSubmitError(null);

        const config: Record<string, any> = {};
        if (boardSize.trim()) {
            config.board_size = parseInt(boardSize, 10);
        }

        try {
            await arenasApi.createArena({
                name: arenaName,
                description: arenaDesc,
                game_type: toApiGameType(gameId),
                config,
                packages,
                password: password.trim() ? password : undefined,
                is_active: isActive,
            });
            // Clear form
            setArenaName('');
            setArenaDesc('');
            setBoardSize(gameId === 'hex' ? '11' : '');
            setPackages('numpy');
            setPassword('');
            setIsActive(true);
            setOpenCreate(false);
            // Refresh
            loadArenas();
        } catch (err: any) {
            setSubmitError(err.message || 'Failed to create arena');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            {/* Back button */}
            <Button
                startIcon={<ArrowBack />}
                onClick={goBack}
                variant="text"
                sx={{ mb: 3 }}
            >
                All Games
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
                        </Box>

                        {/* Admin Action: Create Arena */}
                        {isAdmin && (
                            <Button
                                variant="contained"
                                startIcon={<AddCircleOutline />}
                                onClick={() => {
                                    setBoardSize(gameId === 'hex' ? '11' : '');
                                    setOpenCreate(true);
                                }}
                            >
                                Create Arena
                            </Button>
                        )}
                    </Box>
                </CardContent>
            </Card>

            <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
                Arenas
            </Typography>

            {loading && (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
                    <CircularProgress />
                </Box>
            )}

            {error && <Alert severity="error" sx={{ mb: 4 }}>{error}</Alert>}

            {!loading && !error && (
                <>
                    {arenas.length === 0 ? (
                        <Card sx={{ borderStyle: 'dashed', borderWidth: 2, borderColor: palette.border }}>
                            <CardContent sx={{ py: 6, textPosition: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                <Typography color="text.secondary" sx={{ mb: 2 }}>
                                    No arenas have been created for this game yet.
                                </Typography>
                                {isAdmin && (
                                    <Button
                                        variant="outlined"
                                        startIcon={<AddCircleOutline />}
                                        onClick={() => setOpenCreate(true)}
                                    >
                                        Create the First Arena
                                    </Button>
                                )}
                            </CardContent>
                        </Card>
                    ) : (
                        <Box sx={{
                            display: 'grid',
                            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
                            gap: 3,
                        }}>
                            {arenas.map(arena => (
                                <Card
                                    key={arena.id}
                                    component={Link}
                                    to={`/arenas/${arena.id}`}
                                    sx={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        textDecoration: 'none',
                                        cursor: 'pointer',
                                        '&:hover': {
                                            borderColor: palette.primary,
                                            transform: 'translateY(-2px)',
                                        },
                                        transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                                    }}
                                >
                                    <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                                            <Typography variant="h6">
                                                {arena.name}
                                            </Typography>
                                            {arena.has_password ? (
                                                <Lock sx={{ color: 'warning.main', fontSize: 18 }} />
                                            ) : (
                                                <LockOpen sx={{ color: 'success.main', fontSize: 18 }} />
                                            )}
                                        </Box>
                                        
                                        <Typography color="text.secondary" sx={{ mb: 3, flexGrow: 1, fontSize: '0.875rem' }}>
                                            {arena.description || 'Custom configured arena'}
                                        </Typography>

                                        <Box sx={{ borderTop: `1px solid ${palette.border}`, pt: 1.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <Typography variant="body2" color="text.secondary">Board Size</Typography>
                                                <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                                    {arena.config.board_size ? `${arena.config.board_size}x${arena.config.board_size}` : 'Standard'}
                                                </Typography>
                                            </Box>
                                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <Typography variant="body2" color="text.secondary">Packages</Typography>
                                                <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                                    {arena.packages || 'numpy'}
                                                </Typography>
                                            </Box>
                                        </Box>
                                    </CardContent>
                                </Card>
                            ))}
                        </Box>
                    )}
                </>
            )}

            {/* Create Arena Dialog */}
            <Dialog open={openCreate} onClose={() => setOpenCreate(false)} fullWidth maxWidth="sm">
                <form onSubmit={handleCreateArena}>
                    <DialogTitle>Create New Arena</DialogTitle>
                    <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
                        {submitError && <Alert severity="error">{submitError}</Alert>}

                        <TextField
                            label="Arena Name"
                            value={arenaName}
                            onChange={(e) => setArenaName(e.target.value)}
                            required
                            fullWidth
                        />

                        <TextField
                            label="Description"
                            value={arenaDesc}
                            onChange={(e) => setArenaDesc(e.target.value)}
                            multiline
                            rows={3}
                            fullWidth
                        />

                        <FormControl fullWidth>
                            <InputLabel id="packages-select-label">Available Packages</InputLabel>
                            <Select
                                labelId="packages-select-label"
                                id="packages-select"
                                value={packages}
                                label="Available Packages"
                                onChange={(e) => setPackages(e.target.value as 'numpy' | 'torch')}
                            >
                                <MenuItem value="numpy">numpy (standard)</MenuItem>
                                <MenuItem value="torch">torch (PyTorch support)</MenuItem>
                            </Select>
                        </FormControl>

                        {gameId === 'hex' && (
                            <TextField
                                label="Board Size"
                                value={boardSize}
                                onChange={(e) => setBoardSize(e.target.value)}
                                type="number"
                                helperText="Hex board size (e.g. 5 for 5x5, 11 for 11x11)"
                                fullWidth
                            />
                        )}

                        <TextField
                            label="Arena Password (Optional)"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            type={showPassword ? 'text' : 'password'}
                            helperText="Simple password protection if you want to restrict submission entry."
                            InputProps={{
                                endAdornment: (
                                    <InputAdornment position="end">
                                        <IconButton onClick={() => setShowPassword(!showPassword)} edge="end">
                                            {showPassword ? <VisibilityOff /> : <Visibility />}
                                        </IconButton>
                                    </InputAdornment>
                                )
                            }}
                            fullWidth
                        />

                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={isActive}
                                    onChange={(e) => setIsActive(e.target.checked)}
                                    color="primary"
                                />
                            }
                            label="Active (visible and accepting submissions)"
                        />
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={() => setOpenCreate(false)}>Cancel</Button>
                        <Button
                            type="submit"
                            variant="contained"
                            disabled={submitting || !arenaName.trim()}
                        >
                            {submitting ? 'Creating...' : 'Create'}
                        </Button>
                    </DialogActions>
                </form>
            </Dialog>
        </Container>
    );
}
