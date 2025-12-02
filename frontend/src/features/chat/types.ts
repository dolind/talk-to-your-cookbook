export type ChatSender = 'user' | 'assistant';

export interface ChatMessage {
    id: string;
    content: string;
    sender: ChatSender;
    timestamp: Date;
}

export interface ChatSessionSummary {
    id: string;
    created_at: string;
    title?: string | null;
}
