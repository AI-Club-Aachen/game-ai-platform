/**
 * Generates an avatar URL for a user
 * Uses the custom profile picture if available, otherwise generates a DiceBear avatar
 */
export function getAvatarUrl(username: string, customUrl?: string | null): string {
    if (customUrl) {
        return customUrl;
    }

    // Use DiceBear Adventurer Neutral style
    // See: https://www.dicebear.com/styles/adventurer-neutral/
    return `https://api.dicebear.com/9.x/adventurer-neutral/svg?seed=${encodeURIComponent(username)}`;
}
