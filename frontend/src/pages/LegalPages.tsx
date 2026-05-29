import { Link } from 'react-router-dom';
import {
  Box,
  Button,
  Chip,
  Container,
  Divider,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { overlays } from '../theme';

type LegalFact = {
  label: string;
  value: string;
};

type LegalSection = {
  title: string;
  body?: string[];
  items?: string[];
};

type LegalPageContent = {
  eyebrow: string;
  title: string;
  updated: string;
  intro: string[];
  facts?: LegalFact[];
  sections: LegalSection[];
};

const associationAddress = [
  'AI Club Aachen e.V.',
  'c/o AStA of RWTH Aachen University',
  'Templergraben 55',
  '52062 Aachen',
  'Germany',
];

const contactEmail = 'info@ai-club-aachen.com';

const legalPages: Record<string, LegalPageContent> = {
  imprint: {
    eyebrow: 'Legal Notice',
    title: 'Imprint',
    updated: 'Last updated: May 21, 2026',
    intro: [
      'This legal notice contains the mandatory provider information for the AICA Game Platform.',
      'It applies to this website and the related online services operated by AI Club Aachen e.V.',
    ],
    facts: [
      { label: 'Operator', value: 'AI Club Aachen e.V.' },
      { label: 'Register', value: 'VR 6639, District Court Aachen' },
      { label: 'Contact', value: contactEmail },
    ],
    sections: [
      {
        title: 'Service Provider',
        body: associationAddress,
      },
      {
        title: 'Represented by the Board of Directors',
        items: [
          'Leon Hamm, Chairperson',
          'Denis Baykan, Vice-Chairperson',
          'Moritz Kunisch, Treasurer',
        ],
      },
      {
        title: 'Register',
        body: [
          'Registered in the association register of the District Court (Amtsgericht) Aachen under VR 6639.',
        ],
      },
      {
        title: 'Contact',
        body: [
          'Phone: +49 (0) 15679 744487',
          `Email: ${contactEmail}`,
          'Website: www.ai-club-aachen.com',
        ],
      },
      {
        title: 'Editorial Responsibility',
        body: [
          'Responsible for editorial content in accordance with Section 18(2) MStV:',
          'Leon Hamm',
          ...associationAddress.slice(1),
        ],
      },
      {
        title: 'EU Online Dispute Resolution',
        body: [
          'The European Commission provides a platform for online dispute resolution at https://ec.europa.eu/consumers/odr/. Our email address is listed above.',
        ],
      },
      {
        title: 'Consumer Dispute Resolution',
        body: [
          'We are not willing or obliged to participate in dispute resolution proceedings before a consumer arbitration board.',
        ],
      },
    ],
  },
  privacy: {
    eyebrow: 'Data Protection',
    title: 'Privacy Policy',
    updated: 'Last updated: May 21, 2026',
    intro: [
      'This privacy policy explains how AI Club Aachen e.V. processes personal data when you use the AICA Game Platform.',
      'It covers account registration, authentication, agent submissions, tournament participation, match operations, and the technical operation of the platform.',
    ],
    facts: [
      { label: 'Controller', value: 'AI Club Aachen e.V.' },
      { label: 'Primary contact', value: contactEmail },
      { label: 'Browser storage', value: 'Technically necessary local storage only' },
    ],
    sections: [
      {
        title: 'Controller',
        body: [
          ...associationAddress,
          `Email: ${contactEmail}`,
        ],
      },
      {
        title: 'Data We Process',
        items: [
          'Registration and account data, including username, email address, password hash, role, verification status, and account timestamps.',
          'Authentication and security data, including login state, access credentials, verification or reset tokens, and related security logs.',
          'Platform usage data, including agent records, submissions, selected games, tournament registrations, match results, rankings, and moderation actions.',
          'Uploaded content, including ZIP files, filenames, source code, dependency files, build artefacts, and build or runtime logs.',
          'Technical connection data, including IP address, user agent, requested endpoints, timestamps, and error information where required for secure operation.',
          'Communication data required for transactional emails such as account verification and password reset messages.',
        ],
      },
      {
        title: 'Purposes and Legal Bases',
        items: [
          'To provide user accounts, authentication, submissions, rankings, tournaments, and related platform features under Art. 6(1)(b) GDPR.',
          'To maintain platform security, detect misuse, troubleshoot errors, and ensure stable operation under Art. 6(1)(f) GDPR.',
          'To send service-related emails, including verification and password reset messages, under Art. 6(1)(b) GDPR and, where applicable, Art. 6(1)(f) GDPR.',
          'To comply with statutory obligations and respond to legally required requests under Art. 6(1)(c) GDPR.',
        ],
      },
      {
        title: 'Device Storage and Access',
        body: [
          'The frontend currently stores the `access_token`, `user_id`, and `theme_mode` entries in your browser local storage. These entries are used to maintain your session and remember your display preference.',
          'The platform does not currently use optional analytics, marketing cookies, or third-party tracking scripts in the frontend. If non-essential storage or tracking technologies are added later, they will only be used in accordance with the applicable legal requirements, including Section 25 TDDDG and, where required, your consent.',
        ],
      },
      {
        title: 'Recipients and Processors',
        items: [
          'Authorized administrators may access account data, submissions, logs, and match records where this is necessary for support, moderation, platform security, or tournament operations.',
          'Technical service providers engaged for hosting, infrastructure scaling, storage, and email delivery may process personal data strictly on our behalf and under our instructions.',
          'Leaderboard entries, match results, and tournament information may be visible to other users to the extent required by the platform features you use.',
          'We do not sell personal data.',
        ],
      },
      {
        title: 'Hosting and Infrastructure',
        body: [
          'The platform is currently hosted on a dedicated root server provided by netcup GmbH in Germany.',
          'For periods of increased demand, such as hackathons, individual runner instances may be deployed on Google Cloud infrastructure. Where personal data is processed through such infrastructure, processing is carried out only to the extent necessary for platform operation, match execution, and service stability.',
        ],
      },
      {
        title: 'Retention',
        body: [
          'We retain personal data only for as long as necessary to provide the platform, process submissions, operate tournaments, maintain security, and comply with legal obligations.',
          'Account data, submissions, match records, and tournament data may remain stored for the duration of the user relationship or for as long as required for the respective platform purpose.',
          'Logs and technical records may be retained for a limited period where this is necessary for security, troubleshooting, and abuse prevention.',
        ],
      },
      {
        title: 'Security',
        body: [
          'We use technical and organizational measures intended to protect personal data against unauthorized access, loss, misuse, and unlawful alteration. This includes access controls, authentication mechanisms, and security measures for uploaded submissions and platform operations.',
        ],
      },
      {
        title: 'Your Rights',
        items: [
          'Access to your personal data.',
          'Rectification of inaccurate or incomplete data.',
          'Erasure of your data where legal requirements are met.',
          'Restriction of processing.',
          'Data portability where applicable.',
          'Objection to processing based on legitimate interests.',
          'Withdrawal of consent with future effect where processing is based on consent.',
          'Complaint to a supervisory authority. For North Rhine-Westphalia: Landesbeauftragte fur Datenschutz und Informationsfreiheit Nordrhein-Westfalen, Kavalleriestrasse 2-4, 40213 Dusseldorf, https://www.ldi.nrw.de.',
        ],
      },
      {
        title: 'Contact for Data Protection Requests',
        body: [
          `Email: ${contactEmail}`,
          'Postal address: see Imprint.',
        ],
      },
    ],
  },
  cookies: {
    eyebrow: 'Privacy Controls',
    title: 'Cookie Settings',
    updated: 'Last updated: May 21, 2026',
    intro: [
      'This page explains which cookies and similar browser storage technologies are currently used by the AICA Game Platform.',
      'The current frontend implementation uses only technically necessary local storage entries and does not use optional analytics or marketing cookies.',
    ],
    facts: [
      { label: 'Optional cookies', value: 'Not currently in use' },
      { label: 'Cookie banner', value: 'Not currently required by the frontend' },
      { label: 'Stored locally', value: 'Session and display preferences' },
    ],
    sections: [
      {
        title: 'Current Status',
        body: [
          'No optional cookies or comparable tracking technologies are currently active in the frontend. For that reason, the current implementation does not display a consent banner for optional categories.',
        ],
      },
      {
        title: 'Technically Necessary Storage',
        items: [
          '`access_token`: stored in local storage after login so authenticated API requests can be made.',
          '`user_id`: stored in local storage to restore the current account session.',
          '`theme_mode`: stored in local storage so your selected display theme remains active.',
        ],
      },
      {
        title: 'How to Clear Storage',
        body: [
          'You can remove this data through your browser site settings at any time. Logging out clears the access token and user identifier stored by the application. The saved theme preference can be removed by clearing the site data in your browser.',
        ],
      },
      {
        title: 'If Optional Services Are Added Later',
        body: [
          'If analytics, embedded third-party media, marketing technologies, or other non-essential storage mechanisms are introduced in the future, they will only be activated in accordance with the applicable legal requirements. Where consent is required, it must be obtained before activation and must remain revocable at any time.',
        ],
      },
    ],
  },
  terms: {
    eyebrow: 'Platform Rules',
    title: 'Terms of Use',
    updated: 'Last updated: May 21, 2026',
    intro: [
      'These Terms of Use govern access to and use of the AICA Game Platform, including user accounts, submissions, tournaments, matches, rankings, and related services.',
      'By registering for an account or using the platform, you agree to these terms.',
    ],
    facts: [
      { label: 'Operator', value: 'AI Club Aachen e.V.' },
      { label: 'Scope', value: 'Accounts, submissions, tournaments, and rankings' },
      { label: 'Applicable law', value: 'German law, where legally permitted' },
    ],
    sections: [
      {
        title: 'Operator',
        body: [
          ...associationAddress,
          `Email: ${contactEmail}`,
        ],
      },
      {
        title: 'Accounts',
        items: [
          'You must provide accurate registration information and keep your login credentials confidential.',
          'You are responsible for activity under your account.',
          'We may require email verification and may suspend or delete accounts that violate these terms or endanger the security or integrity of the platform.',
        ],
      },
      {
        title: 'Agent Submissions and Uploaded Code',
        items: [
          'You may upload only code and files that you have the right to submit and run.',
          'By submitting an agent, you grant AI Club Aachen e.V. the rights required to store, inspect, build, execute, benchmark, and evaluate the submission as part of platform operation, tournaments, moderation, and technical support.',
          'You retain ownership of your submitted code unless a separate competition rule says otherwise.',
          'Do not upload secrets, private keys, personal data, malware, copyrighted third-party code without permission, or files unrelated to the competition task.',
        ],
      },
      {
        title: 'Fair Play and Security',
        items: [
          'Do not attempt to escape security restrictions, attack infrastructure, access data belonging to other users, overload the service, scrape non-public endpoints, manipulate rankings, exploit bugs, or interfere with matches.',
          'Do not submit code designed to damage systems, exfiltrate data, mine cryptocurrency, open unauthorized network connections, or bypass resource limits.',
          'Good-faith security research is permitted only where vulnerabilities are reported to us promptly at info@ai-club-aachen.com, no data is retained or disclosed, no service degradation is caused, and no access beyond what is strictly necessary for verification is attempted.',
          'We may inspect submissions, logs, and match behavior where necessary to enforce these rules and protect the platform.',
        ],
      },
      {
        title: 'Tournaments, Rankings, and Availability',
        items: [
          'Tournament rules, scoring, eligibility, deadlines, and prizes, if any, may be defined separately for each tournament.',
          'Rankings and match results may change because of reruns, bug fixes, moderation decisions, or technical failures.',
          'The platform may be changed, interrupted, or discontinued, especially while operated as a club or educational project.',
        ],
      },
      {
        title: 'User Content and Moderation',
        items: [
          'Usernames, agent names, submission names, and other content must not be unlawful, misleading, discriminatory, harassing, or otherwise abusive.',
          'We may remove content, disable agents, disqualify submissions, or restrict accounts where this is necessary to enforce these terms, comply with legal obligations, or protect users and the platform.',
        ],
      },
      {
        title: 'Liability',
        body: [
          'Statutory liability rules apply. To the extent legally permitted, we do not guarantee uninterrupted availability of the platform, the permanence of rankings, or the outcome of individual matches, tournaments, or builds.',
        ],
      },
      {
        title: 'Changes',
        body: [
          'The operator may update these terms for future use of the platform. Material changes should be communicated in an appropriate way before they take effect.',
        ],
      },
      {
        title: 'Governing Law',
        body: [
          'German law applies where legally permitted. Mandatory consumer protection rules remain unaffected.',
        ],
      },
    ],
  },
};

const legalLinks = [
  { label: 'Imprint', to: '/imprint' },
  { label: 'Privacy Policy', to: '/privacy-policy' },
  { label: 'Cookie Settings', to: '/cookie-settings' },
  { label: 'Terms of Use', to: '/terms-of-use' },
];

function renderBody(lines: string[] | undefined) {
  if (!lines) return null;

  return (
    <Stack spacing={1.2}>
      {lines.map((line) => (
        <Typography
          key={line}
          color="text.secondary"
          sx={{ whiteSpace: 'pre-line', lineHeight: 1.75 }}
        >
          {line}
        </Typography>
      ))}
    </Stack>
  );
}

function FactGrid({ facts }: { facts: LegalFact[] | undefined }) {
  if (!facts?.length) return null;

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, minmax(0, 1fr))' },
        gap: 1.5,
      }}
    >
      {facts.map((fact) => (
        <Box
          key={fact.label}
          sx={{
            py: 1,
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.75 }}>
            {fact.label}
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.primary', fontWeight: 600 }}>
            {fact.value}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}

function LegalPage({ content }: { content: LegalPageContent }) {
  return (
    <Box sx={{ minHeight: '100vh', background: overlays.heroGradientSubtle }}>
      <Container maxWidth="md" sx={{ py: { xs: 4, md: 7 } }}>
        <Button
          component={Link}
          to="/"
          startIcon={<ArrowBack />}
          variant="text"
          sx={{ mb: 3, color: 'text.secondary' }}
        >
          Back to platform
        </Button>

        <Paper sx={{ p: { xs: 3, md: 5 }, borderRadius: 4 }}>
          <Stack spacing={4}>
            <Box>
              <Chip
                label={content.eyebrow}
                size="small"
                sx={{
                  mb: 2,
                  backgroundColor: 'background.default',
                  color: 'text.secondary',
                }}
              />
              <Typography
                variant="h1"
                sx={{
                  fontSize: { xs: '2rem', md: '2.6rem' },
                  mb: 1,
                  letterSpacing: '-0.03em',
                }}
              >
                {content.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {content.updated}
              </Typography>
            </Box>

            <Stack spacing={1.5}>
              {content.intro.map((paragraph) => (
                <Typography key={paragraph} color="text.secondary">
                  {paragraph}
                </Typography>
              ))}
            </Stack>

            <FactGrid facts={content.facts} />

            <Divider />

            <Stack spacing={4}>
              {content.sections.map((section, index) => (
                <Box key={section.title}>
                  <Typography variant="h2" sx={{ fontSize: '1.1rem', mb: 1.5 }}>
                    {section.title}
                  </Typography>
                  {renderBody(section.body)}
                  {section.items && (
                    <List dense disablePadding sx={{ mt: section.body ? 1.25 : 0 }}>
                      {section.items.map((item) => (
                        <ListItem
                          key={item}
                          disableGutters
                          sx={{ alignItems: 'flex-start', py: 0.45, pl: 0.25 }}
                        >
                          <ListItemText
                            primary={item}
                            primaryTypographyProps={{ color: 'text.secondary', lineHeight: 1.7 }}
                          />
                        </ListItem>
                      ))}
                    </List>
                  )}
                  {index < content.sections.length - 1 && <Divider sx={{ mt: 3.5 }} />}
                </Box>
              ))}
            </Stack>
          </Stack>
        </Paper>

        <Stack
          component="nav"
          direction={{ xs: 'column', sm: 'row' }}
          spacing={2}
          justifyContent="center"
          sx={{ mt: 3 }}
        >
          {legalLinks.map((link) => (
            <Button key={link.to} component={Link} to={link.to} variant="text">
              {link.label}
            </Button>
          ))}
        </Stack>
      </Container>
    </Box>
  );
}

export function Imprint() {
  return <LegalPage content={legalPages.imprint} />;
}

export function PrivacyPolicy() {
  return <LegalPage content={legalPages.privacy} />;
}

export function CookieSettings() {
  return <LegalPage content={legalPages.cookies} />;
}

export function TermsOfUse() {
  return <LegalPage content={legalPages.terms} />;
}

export { legalLinks };
