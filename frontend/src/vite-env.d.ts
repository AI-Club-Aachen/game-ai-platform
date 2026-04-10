/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly MAX_TURN_TIME_LIMIT_SECONDS?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
