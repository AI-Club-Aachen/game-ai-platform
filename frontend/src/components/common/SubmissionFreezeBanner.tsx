import { Alert } from '@mui/material';

/**
 * Shown to non-admin users while the submission freeze is active, explaining
 * why upload / agent-change controls are disabled.
 */
export function SubmissionFreezeBanner({ sx }: { sx?: object }) {
  return (
    <Alert severity="warning" sx={sx}>
      Submissions are frozen for a tournament. Uploading, deleting, and changing agents are temporarily disabled
      until an admin lifts the freeze.
    </Alert>
  );
}
