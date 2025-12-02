export type MessageType = 'user' | 'assistant';

export interface Citation {
    id: string;
    title: string;
    authors: string;
    year: string;
    url?: string;
    snippet?: string;
}

export interface StructuredContent {
    summary: string[]; // Bullet points for executive summary
    details?: {
        title: string;
        content: string;
    }[];
    citations?: Citation[];
}

export interface Message {
    id: string;
    type: MessageType;
    content: string | StructuredContent;
    timestamp: Date;
}
