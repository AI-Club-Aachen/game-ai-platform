import { useCallback, useLayoutEffect, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Chip, Paper, Tooltip, Typography } from '@mui/material';
import { ReportProblemOutlined } from '@mui/icons-material';
import { TournamentMatchup, TournamentGame, MatchupStatus } from '../../services/api/tournaments';

interface BracketViewProps {
  matchups: TournamentMatchup[];
  agentNames: Record<string, string>;
  section: 'winners' | 'losers';
}

interface ColumnSpec {
  label: string;
  caption?: string;
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
}: {
  agentId: string | null;
  matchup: TournamentMatchup;
  agentNames: Record<string, string>;
}) {
  const decided = matchup.status === 'completed';
  const isWinner = decided && agentId !== null && matchup.winner_agent_id === agentId;
  const name = agentId ? agentNames[agentId] ?? `${agentId.slice(0, 8)}…` : isBye(matchup) ? 'Bye' : 'TBD';

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
        {name}
      </Typography>
      {agentId && matchup.games.length > 0 && (
        <Typography
          variant="body2"
          sx={{ fontWeight: isWinner ? 700 : 400, color: isWinner ? 'success.main' : 'text.secondary' }}
        >
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

// Fixed height so every card (including byes, which have no game chips) is the
// same size; this keeps vertical centers — and therefore connector lines —
// aligned across columns.
const CARD_HEIGHT = 84;
const COLUMN_MAX_WIDTH = 240;

function MatchupCard({
  matchup,
  agentNames,
}: {
  matchup: TournamentMatchup;
  agentNames: Record<string, string>;
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1,
        width: '100%',
        height: CARD_HEIGHT,
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        gap: 0.5,
        borderColor: matchupBorderColor(matchup.status),
        opacity: matchup.status === 'cancelled' || (isBye(matchup) && matchup.winner_agent_id === null) ? 0.5 : 1,
      }}
    >
      <SlotRow agentId={matchup.agent1_id} matchup={matchup} agentNames={agentNames} />
      <SlotRow agentId={matchup.agent2_id} matchup={matchup} agentNames={agentNames} />
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 0.5, minHeight: 18 }}>
        <GameChips matchup={matchup} agentNames={agentNames} />
        {matchup.status === 'needs_attention' && (
          <Tooltip title="This matchup needs admin attention">
            <ReportProblemOutlined sx={{ fontSize: 16, color: 'warning.main' }} />
          </Tooltip>
        )}
      </Box>
    </Paper>
  );
}

interface ConnectorLine {
  key: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

function BracketColumns({
  columns,
  agentNames,
}: {
  columns: ColumnSpec[];
  agentNames: Record<string, string>;
}) {
  const contentRef = useRef<HTMLDivElement | null>(null);
  const cardRefs = useRef(new Map<string, HTMLDivElement>());
  const [lines, setLines] = useState<ConnectorLine[]>([]);

  // Winner-advancement edges between matchups rendered in this section.
  const edges = useMemo(() => {
    const visible = new Set(columns.flatMap((column) => column.matchups.map((m) => m.id)));
    const result: { from: string; to: string }[] = [];
    for (const column of columns) {
      for (const matchup of column.matchups) {
        const sources = [
          [matchup.slot1_source_matchup_id, matchup.slot1_source_role],
          [matchup.slot2_source_matchup_id, matchup.slot2_source_role],
        ] as const;
        for (const [sourceId, role] of sources) {
          if (role === 'winner' && sourceId && visible.has(sourceId)) {
            result.push({ from: sourceId, to: matchup.id });
          }
        }
      }
    }
    return result;
  }, [columns]);

  const measure = useCallback(() => {
    const content = contentRef.current;
    if (!content) return;
    const contentRect = content.getBoundingClientRect();

    const next: ConnectorLine[] = [];
    for (const edge of edges) {
      const fromEl = cardRefs.current.get(edge.from);
      const toEl = cardRefs.current.get(edge.to);
      if (!fromEl || !toEl) continue;
      const from = fromEl.getBoundingClientRect();
      const to = toEl.getBoundingClientRect();
      next.push({
        key: `${edge.from}-${edge.to}`,
        x1: from.right - contentRect.left,
        y1: from.top + from.height / 2 - contentRect.top,
        x2: to.left - contentRect.left,
        y2: to.top + to.height / 2 - contentRect.top,
      });
    }
    // Keep the previous array when nothing moved so observer callbacks
    // cannot trigger render loops.
    setLines((previous) => {
      const unchanged =
        previous.length === next.length &&
        previous.every((line, i) => {
          const candidate = next[i];
          return (
            line.key === candidate.key &&
            line.x1 === candidate.x1 &&
            line.y1 === candidate.y1 &&
            line.x2 === candidate.x2 &&
            line.y2 === candidate.y2
          );
        });
      return unchanged ? previous : next;
    });
  }, [edges]);

  const measureCallbackRef = useRef(measure);
  useLayoutEffect(() => {
    measureCallbackRef.current = measure;
    measure();
  }, [measure, agentNames]);

  // One observer for the container AND every card: cards change height when
  // game chips appear (byes never get them), which shifts centers without
  // resizing the container itself.
  const observerRef = useRef<ResizeObserver | null>(null);
  if (observerRef.current === null && typeof ResizeObserver !== 'undefined') {
    observerRef.current = new ResizeObserver(() => measureCallbackRef.current());
  }

  useEffect(() => {
    const observer = observerRef.current;
    const content = contentRef.current;
    if (observer && content) observer.observe(content);
    return () => observer?.disconnect();
  }, []);

  const registerCard = (matchupId: string) => (el: HTMLDivElement | null) => {
    if (el) {
      cardRefs.current.set(matchupId, el);
      observerRef.current?.observe(el);
    } else {
      const previous = cardRefs.current.get(matchupId);
      if (previous) observerRef.current?.unobserve(previous);
      cardRefs.current.delete(matchupId);
    }
  };

  return (
    <Box sx={{ overflowX: 'auto', pb: 1 }}>
      {/* Columns flex to share the available width so even large brackets fit
          on the page; the parent still scrolls if the viewport is too narrow. */}
      <Box ref={contentRef} sx={{ position: 'relative', display: 'flex', gap: 2.5, width: '100%', minWidth: 'min-content' }}>
        <Box
          component="svg"
          sx={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            color: 'divider',
          }}
        >
          {lines.map((line) => (
            <path
              key={line.key}
              d={`M ${line.x1} ${line.y1} H ${(line.x1 + line.x2) / 2} V ${line.y2} H ${line.x2}`}
              fill="none"
              stroke="var(--color-border-hover)"
              strokeWidth={1.5}
            />
          ))}
        </Box>
        {columns.map((column) => (
          <Box
            key={column.label}
            sx={{ display: 'flex', flexDirection: 'column', flex: '1 1 0', minWidth: 120, maxWidth: COLUMN_MAX_WIDTH }}
          >
            <Box sx={{ mb: 1, minHeight: 32, textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, display: 'block' }}>
                {column.label}
              </Typography>
              {column.caption && (
                <Typography variant="caption" color="text.disabled" sx={{ display: 'block', lineHeight: 1.2 }}>
                  {column.caption}
                </Typography>
              )}
            </Box>
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
                <Box key={matchup.id} ref={registerCard(matchup.id)} sx={{ display: 'flex' }}>
                  <MatchupCard matchup={matchup} agentNames={agentNames} />
                </Box>
              ))}
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

type RoundLabeler = (roundIndex: number, totalRounds: number) => { label: string; caption?: string };

// The tab already names the bracket, so labels stay unprefixed.
const labelWinnersRound: RoundLabeler = (roundIndex, totalRounds) => {
  const fromEnd = totalRounds - roundIndex; // 0 = the last (deciding) round
  if (fromEnd === 0) return { label: 'Final', caption: 'Winner goes to the Grand Final' };
  if (fromEnd === 1) return { label: 'Semifinals' };
  if (fromEnd === 2) return { label: 'Quarterfinals' };
  return { label: `Round ${roundIndex}` };
};

// Losers-bracket rounds; the last two decide 3rd/4th place.
const labelLosersRound: RoundLabeler = (roundIndex, totalRounds) => {
  const fromEnd = totalRounds - roundIndex;
  if (fromEnd === 0) return { label: 'Final', caption: 'Winner to Grand Final · loser places 3rd' };
  if (fromEnd === 1) return { label: 'Semifinal', caption: 'Loser places 4th' };
  return { label: `Round ${roundIndex}` };
};

const buildRoundColumns = (matchups: TournamentMatchup[], labeler: RoundLabeler): ColumnSpec[] => {
  const byRound = new Map<number, TournamentMatchup[]>();
  for (const matchup of matchups) {
    const list = byRound.get(matchup.round) ?? [];
    list.push(matchup);
    byRound.set(matchup.round, list);
  }
  const rounds = [...byRound.keys()].sort((a, b) => a - b);
  return rounds.map((round, index) => {
    const { label, caption } = labeler(index + 1, rounds.length);
    return { label, caption, matchups: byRound.get(round)!.sort((a, b) => a.position - b.position) };
  });
};

export function BracketView({ matchups, agentNames, section }: BracketViewProps) {
  if (section === 'losers') {
    const columns = buildRoundColumns(
      matchups.filter((m) => m.bracket === 'losers'),
      labelLosersRound,
    );
    return <BracketColumns columns={columns} agentNames={agentNames} />;
  }

  const columns = buildRoundColumns(
    matchups.filter((m) => m.bracket === 'winners'),
    labelWinnersRound,
  );
  const grandFinal = matchups.find((m) => m.bracket === 'grand_final');
  const reset = matchups.find((m) => m.bracket === 'grand_final_reset');
  if (grandFinal) {
    columns.push({ label: 'Grand Final', caption: 'Championship match', matchups: [grandFinal] });
  }
  // The reset matchup only matters once the losers-bracket champion forced it
  // by winning the grand final.
  if (reset && reset.status !== 'cancelled') {
    columns.push({ label: 'Grand Final — Reset', caption: 'Decider for the title', matchups: [reset] });
  }
  return <BracketColumns columns={columns} agentNames={agentNames} />;
}
