import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormLabel,
  InputLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  Typography,
} from '@mui/material';
import { SportsEsports } from '@mui/icons-material';
import { matchesApi, HumanOpponent } from '../services/api/matches';

interface PlayVsAgentDialogProps {
  open: boolean;
  onClose: () => void;
  arenaId: string;
  initialAgentId?: string;
}

export function PlayVsAgentDialog({ open, onClose, arenaId, initialAgentId }: PlayVsAgentDialogProps) {
  const navigate = useNavigate();
  const [opponents, setOpponents] = useState<HumanOpponent[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [agentId, setAgentId] = useState('');
  const [seat, setSeat] = useState<0 | 1>(0);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setLoadError(null);
    setStartError(null);
    matchesApi.getHumanOpponents(arenaId)
      .then((list) => {
        setOpponents(list);
        const preselect = list.find((o) => o.id === initialAgentId) ?? list[0];
        setAgentId(preselect?.id ?? '');
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : 'Failed to load agents'))
      .finally(() => setLoading(false));
  }, [open, arenaId, initialAgentId]);

  const handleStart = async () => {
    if (!agentId) return;
    setStarting(true);
    setStartError(null);
    try {
      const match = await matchesApi.createHumanMatch({
        arena_id: arenaId,
        agent_id: agentId,
        human_player_index: seat,
      });
      onClose();
      navigate(`/games/live/${match.id}`);
    } catch (err) {
      setStartError(err instanceof Error ? err.message : 'Failed to start the game');
    } finally {
      setStarting(false);
    }
  };

  return (
    <Dialog open={open} onClose={() => !starting && onClose()} maxWidth="xs" fullWidth>
      <DialogTitle>Play vs Agent</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Play by hand against any agent in this arena. These games don't affect agent stats or ELO.
          </Typography>

          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={28} />
            </Box>
          )}
          {loadError && <Alert severity="error">{loadError}</Alert>}
          {!loading && !loadError && opponents.length === 0 && (
            <Alert severity="info">No agent in this arena has a successful build yet.</Alert>
          )}

          {!loading && opponents.length > 0 && (
            <>
              <FormControl fullWidth>
                <InputLabel id="play-vs-agent-opponent">Opponent</InputLabel>
                <Select
                  labelId="play-vs-agent-opponent"
                  value={agentId}
                  label="Opponent"
                  onChange={(e) => setAgentId(e.target.value)}
                >
                  {opponents.map((o) => (
                    <MenuItem key={o.id} value={o.id}>
                      {o.agent_name}
                      <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                        {o.is_mine ? '(yours)' : `by ${o.username}`}
                        {o.elo !== null ? ` · ELO ${o.elo}` : ''}
                      </Typography>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel id="play-vs-agent-seat">Who moves first?</FormLabel>
                <RadioGroup
                  aria-labelledby="play-vs-agent-seat"
                  value={String(seat)}
                  onChange={(e) => setSeat(e.target.value === '1' ? 1 : 0)}
                >
                  <FormControlLabel value="0" control={<Radio />} label="I move first" />
                  <FormControlLabel value="1" control={<Radio />} label="The agent moves first" />
                </RadioGroup>
              </FormControl>
            </>
          )}

          {startError && <Alert severity="error">{startError}</Alert>}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={starting}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleStart}
          disabled={!agentId || starting || loading}
          startIcon={starting ? <CircularProgress size={18} /> : <SportsEsports />}
        >
          Start game
        </Button>
      </DialogActions>
    </Dialog>
  );
}
