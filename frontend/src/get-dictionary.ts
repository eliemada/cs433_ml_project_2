import 'server-only';
import type { Locale } from './i18n-config';

export interface Dictionary {
    sidebar: {
        appName: string;
        newChat: string;
        recent: string;
        settings: string;
        logout: string;
        history: {
            patents_sme: string;
            patent_boxes: string;
            maintenance_fees: string;
        };
    };
    input: {
        placeholder: string;
        disclaimer: string;
        starters: string[];
    };
    response: {
        executiveSummary: string;
        analystView: string;
        keyReferences: string;
    };
    chat: {
        headerTitle: string;
        emptyTitle: string;
        emptyDescription: string;
    };
}

// We enumerate all dictionaries here for better type safety
const dictionaries = {
    en: () => import('./dictionaries/en.json').then((module) => module.default as Dictionary),
    fr: () => import('./dictionaries/fr.json').then((module) => module.default as Dictionary),
};

export const getDictionary = async (locale: Locale): Promise<Dictionary> => dictionaries[locale]();
