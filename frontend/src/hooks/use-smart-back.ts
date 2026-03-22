import { useNavigate } from 'react-router-dom';

/**
 * Returns a `goBack()` function that navigates to the previous page in the
 * browser history when possible, or falls back to the provided route when
 * the user landed directly on this page (e.g. via a shared URL).
 */
export function useSmartBack(fallback: string) {
    const navigate = useNavigate();
    return () => {
        if (window.history.length > 1) {
            navigate(-1);
        } else {
            navigate(fallback);
        }
    };
}
