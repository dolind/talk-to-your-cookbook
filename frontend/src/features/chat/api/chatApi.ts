// src/features/chat/api/chatApi.ts
import api, {authFetch} from '../../../utils/api';
import {ChatMessage, ChatSessionSummary} from '../types';

/**
 * Chat Sessions
 */
export const listChatSessions = () =>
    api.get<{ items: ChatSessionSummary[] }>('/chat/sessions');

export const getChatSessionMessages = (sessionId: string) =>
    api.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`);

export const createChatSession = () =>
    api.post<ChatSessionSummary>('/chat/sessions', {});

export const deleteChatSession = (sessionId: string) =>
    api.delete(`/chat/sessions/${sessionId}`);

/**
 * Embeddings
 */
export const reindexAllEmbeddings = () =>
    api.post('/embeddings/reindex/all');

/**
 * Stream Assistant Message (manual fetch for streaming)
 */
export const streamAssistantMessage = async (
    sessionId: string,
    payload: { content: string, recipe_id: string },
    {
        onChunk,
        onComplete,
    }: {
        onChunk?: (chunk: string) => void;
        onComplete?: () => void;
    } = {},
) => {
    const response = await authFetch(
        `${import.meta.env.VITE_API_BASE_URL}/chat/sessions/${sessionId}/stream`,
        {
            method: 'POST',
            body: JSON.stringify(payload),
        },
    );

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Stream failed: ${response.status} ${text}`);
    }

    if (!response.body) throw new Error('No response body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const {done, value} = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, {stream: true});
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
            if (!part.startsWith('data:')) continue;
            const data = part.slice(5);

            if (data === '[DONE]') {
                onComplete?.();
                return;
            }

            onChunk?.(data);
        }
    }

    onComplete?.();
};
