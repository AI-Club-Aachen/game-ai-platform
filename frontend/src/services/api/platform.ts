import { apiRequest } from './client';

/**
 * Platform-wide admin controls.
 */

export interface SubmissionFreeze {
    enabled: boolean;
    updated_at: string;
    updated_by_user_id: string | null;
}

export type SettingSource = 'override' | 'environment' | 'default';

/** One backend setting; secrets arrive masked as "***". */
export interface PlatformSetting {
    name: string;
    /** Display name; set for the editable settings. */
    label: string | null;
    group: string | null;
    editable: boolean;
    secret: boolean;
    value: unknown;
    base_value: unknown;
    source: SettingSource;
    type: 'bool' | 'int' | 'float' | 'str' | 'choice';
    options: string[] | null;
    option_labels: Record<string, string> | null;
    minimum: number | null;
    maximum: number | null;
    description: string | null;
    updated_at: string | null;
    updated_by_user_id: string | null;
}

export interface PlatformSettings {
    settings: PlatformSetting[];
    warnings: string[];
}

export const platformApi = {
    /**
     * Current submission-freeze state. Readable by any verified user.
     */
    getSubmissionFreeze: async () => {
        return apiRequest<SubmissionFreeze>('/platform/submission-freeze', { method: 'GET' });
    },

    /**
     * Enable or disable the submission freeze. Admin only.
     */
    setSubmissionFreeze: async (enabled: boolean) => {
        return apiRequest<SubmissionFreeze>('/platform/submission-freeze', {
            method: 'PUT',
            body: JSON.stringify({ enabled }),
        });
    },

    /**
     * Effective configuration with value sources. Admin only.
     */
    getSettings: async () => {
        return apiRequest<PlatformSettings>('/platform/settings', { method: 'GET' });
    },

    /**
     * Override editable settings; `null` resets one to its environment/default value. Admin only.
     */
    updateSettings: async (values: Record<string, unknown>) => {
        return apiRequest<PlatformSettings>('/platform/settings', {
            method: 'PUT',
            body: JSON.stringify({ values }),
        });
    },
};
