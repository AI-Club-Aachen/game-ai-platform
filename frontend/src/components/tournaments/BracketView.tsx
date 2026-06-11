import { Fragment } from 'react';
import { Link } from 'react-router-dom';
import { Box, Chip, Paper, Tooltip, Typography } from '@mui/material';
import { EmojiEvents, ReportProblemOutlined } from '@mui/icons-material';
import { TournamentMatchup, TournamentGame, MatchupStatus } from '../../services/api/tournaments';

interface BracketViewProps {
  matchups: TournamentMatchup[];
  agentNames: Record<string, string>;
  seeds: Record<string, number>;
}

interface ColumnSpec {
  label: string;
  matchups: TournamentMatchup[];
}

const winsFor = (matchup: TournamentMatchup, agentId: string | null) => {
  if (!agentId) return 0;
  return matchup.games.filter((game) => game.winner_agent_id === agentId).length;
};

const isBye = (matchup: TournamentMatchup) =>
  matchup.status === 'completed' && (matchup.agent1_id === null || matchup.agent2_id === null);

const resolutionLabel: Record<string, string> = {
  played: 'Played',
  draw_coin_flip: 'Draw — resolved by coin flip',
  forfeit_client_error: 'Forfeit (agent error)',
  admin_resolved: 'Resolved by admin',
};

function GameChips({ matchup, agentNames }: { matchup: TournamentMatchup; agentNames: Record<string, string> }) {
  if (matchup.games.length === 0) return null;
  return (
    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
      {matchup.games.map((game: TournamentGame) => {
        const winnerName = game.winner_agent_id ? agentNames[game.winner_agent_id] ?? 'unknown' : null;
        const tooltip = winnerName
          ? `Game ${game.game_index + 1}: ${winnerName} won (${resolutionLabel[game.resolution ?? 'played'] ?? game.resolution})`
          : `Game ${game.game_index + 1}: in progress`;
        const chip = (
          <Chip
            label={`G${game.game_index + 1}`}
            size="small"
            variant="outlined"
            color={game.winner_agent_id ? 'default' : 'info'}
            clickable={!!game.match_id}
            sx={{ height: 18, fontSize: '0.65rem' }}
          />
        );
        return (
          <Tooltip key={game.id} title={tooltip}>
            {game.match_id ? (
              <Link to={`/games/live/${game.match_id}`} style={{ textDecoration: 'none' }}>
                {chip}
              </Link>
            ) : (
              chip
            )}
          </Tooltip>
        );
      })}
    </Box>
  );
}

function SlotRow({
  agentId,
  matchup,
  agentNames,
  seeds,
}: {
  agentId: string | null;
  matchup: TournamentMatchup;
  agentNames: Record<string, string>;
  seeds: Record<string, number>;
}) {
  const decided = matchup.status === 'completed';
  const isWinner = decided && agentId !== null && matchup.winner_agent_id === agentId;
  const name = agentId ? agentNames[agentId] ?? `${agentId.slice(0, 8)}…` : isBye(matchup) ? 'Bye' : 'TBD';
  const seed = agentId ? seeds[agentId] : undefined;

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, minWidth: 0 }}>
      <Typography
        variant="body2"
        noWrap
        title={name}
        sx={{
          fontWeight: isWinner ? 700 : 400,
          color: agentId ? (decided && !isWinner ? 'text.disabled' : 'text.primary') : 'text.disabled',
          fontStyle: agentId ? 'normal' : 'italic',
          minWidth: 0,
        }}
      >
        {seed !== undefined && (
          <Typography component="span" variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
            {seed}
          </Typography>
        )}
        {name}
        {isWinner && <EmojiEvents sx={{ fontSize: 14, ml: 0.5, verticalAlign: 'text-top', color: 'warning.main' }} />}
      </Typography>
      {agentId && matchup.games.length > 0 && (
        <Typography variant="body2" sx={{ fontWeight: isWinner ? 700 : 400 }}>
          {winsFor(matchup, agentId)}
        </Typography>
      )}
    </Box>
  );
}

const matchupBorderColor = (status: MatchupStatus) => {
  if (status === 'needs_attention') return 'warning.main';
  if (status === 'in_progress') return 'info.main';
  return 'divider';
};

function MatchupCard({
  matchup,
  agentNames,
  seeds,
}: {
  matchup: TournamentMatchup;
  agentNames: Record<string, string>;
  seeds: Record<string, number>;
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1,
        width: 210,
        borderColor: matchupBorderColor(matchup.status),
        opacity: matchup.status === 'cancelled' || (isBye(matchup) && matchup.winner_agent_id === null) ? 0.5 : 1,
      }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        <SlotRow agentId={matchup.agent1_id} matchup={matchup} agentNames={agentNames} seeds={seeds} />
        <SlotRow agentId={matchup.agent2_id} matchup={matchup} agentNames={agentNames} seeds={seeds} />
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 0.5 }}>
          <GameChips matchup={matchup} agentNames={agentNames} />
          {matchup.status === 'needs_attention' && (
            <Tooltip title="This matchup needs admin attention">
              <ReportProblemOutlined sx={{ fontSize: 16, color: 'warning.main' }} />
            </Tooltip>
          )}
        </Box>
      </Box>
    </Paper>
  );
}

function BracketColumns({
  columns,
  agentNames,
  seeds,
}: {
  columns: ColumnSpec[];
  agentNames: Record<string, string>;
  seeds: Record<string, number>;
}) {
  return (
    <Box sx={{ display: 'flex', overflowX: 'auto', pb: 1 }}>
      {columns.map((column, columnIndex) => (
        <Fragment key={column.label}>
          <Box sx={{ display: 'flex', flexDirection: 'column', minWidth: 226 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, fontWeight: 600 }}>
              {column.label}
            </Typography>
            <Box
              sx={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-around',
                gap: 1.5,
              }}
            >
              {column.matchups.map((matchup) => (
                <Box key={matchup.id} sx={{ display: 'flex', alignItems: 'center' }}>
                  {columnIndex > 0 && (
                    <Box sx={{ width: 14, borderTop: '2px solid', borderColor: 'divider' }} />
                  )}
                  <MatchupCard matchup={matchup} agentNames={agentNames} seeds={seeds} />
                  {columnIndex < columns.length - 1 && (
                    <Box sx={{ width: 14, borderTop: '2px solid', borderColor: 'divider' }} />
                  )}
                </Box>
              ))}
            </Box>
          </Box>
        </Fragment>
      ))}
    </Box>
  );
}

const roundColumns = (matchups: TournamentMatchup[]): ColumnSpec[] => {
  const rounds = new Map<number, TournamentMatchup[]>();
  for (const matchup of matchups) {
    const list = rounds.get(matchup.round) ?? [];
    list.push(matchup);
    rounds.set(matchup.round, list);
  }
  return [...rounds.entries()]
    .sort(([a], [b]) => a - b)
    .map(([round, roundMatchups]) => ({
      label: `Round ${round}`,
      matchups: roundMatchups.sort((a, b) => a.position - b.position),
    }));
};

export function BracketView({ matchups, agentNames, seeds }: BracketViewProps) {
  const winners = matchups.filter((m) => m.bracket === 'winners');
  const losers = matchups.filter((m) => m.bracket === 'losers');
  const grandFinal = matchups.find((m) => m.bracket === 'grand_final');
  const reset = matchups.find((m) => m.bracket === 'grand_final_reset');

  const winnersColumns = roundColumns(winners);
  if (grandFinal) {
    winnersColumns.push({ label: 'Grand Final', matchups: [grandFinal] });
  }
  // The reset matchup only exists visually when the losers-bracket champion
  // forced it by winning the grand final.
  if (reset && reset.status !== 'cancelled') {
    winnersColumns.push({ label: 'Bracket Reset', matchups: [reset] });
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Winners Bracket
        </Typography>
        <BracketColumns columns={winnersColumns} agentNames={agentNames} seeds={seeds} />
      </Box>
      {losers.length > 0 && (
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Losers Bracket
          </Typography>
          <BracketColumns columns={roundColumns(losers)} agentNames={agentNames} seeds={seeds} />
        </Box>
      )}
    </Box>
  );
}
