import 'server-only';
import type { Locale } from './i18n-config';

// We enumerate all dictionaries here for better type safety
const dictionaries = {
    en: () => import('./dictionaries/en.json').then((module) => module.default),
    fr: () => import('./dictionaries/fr.json').then((module) => module.default),
};

export const getDictionary = async (locale: Locale) => dictionaries[locale]();
