import {useCallback, useEffect, useRef, useState} from 'react';
import {
    createChatSession,
    deleteChatSession,
    getChatSessionMessages,
    listChatSessions,
    reindexAllEmbeddings,
    streamAssistantMessage,
} from '../api/chatApi';
import {ChatMessage, ChatSessionSummary} from '../types';

const createInitialAssistantMessage = (text: string): ChatMessage => ({
    id: `init-${Date.now()}`,
    content: text,
    sender: 'assistant',
    timestamp: new Date(),
});

export const useChatSessions = (
    initialAssistantText: string = 'Hi! What would you like to talk about?',
) => {
    const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bootstrappedRef = useRef(false);
    const [sessionsLoaded, setSessionsLoaded] = useState(false);

    const loadSessionMessages = useCallback(async (sessionId: string) => {
        try {
            const {data} = await getChatSessionMessages(sessionId);
            const loaded = data.map((msg: any) => ({
                id: msg.id,
                content: msg.content,
                sender: msg.role,
                timestamp: new Date(msg.created_at),
            })) as ChatMessage[];
            if (loaded.length === 0) {
                loaded.push(createInitialAssistantMessage(initialAssistantText));
            }

            setMessages(loaded);
            setActiveSessionId(sessionId);
            setError(null);
        } catch (err) {
            console.error('Failed to load session', err);
            setError('Failed to load session');
        }
    }, []);

    const createSession = useCallback(async () => {
        try {
            const {data} = await createChatSession();
            setSessions((prev) => [...prev, data]);
            setActiveSessionId(data.id);
            setMessages([createInitialAssistantMessage(initialAssistantText)]);
            setError(null);
            return data.id;
        } catch (err) {
            console.error('Failed to create session', err);
            setError('Failed to create session');
            return null;
        }
    }, [initialAssistantText]);

    const loadInitialSession = useCallback(async () => {
        try {
            const {data} = await listChatSessions();
            const items: ChatSessionSummary[] = data.items ?? [];
            setSessions(items);
            setSessionsLoaded(true);
            setError(null);


            const latest = [...items].sort(
                (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
            )[items.length - 1];


            if (latest) await loadSessionMessages(latest.id);
        } catch (err) {
            console.error('Failed to load sessions', err);
            setError('Failed to load sessions');
        }
    }, [createSession, loadSessionMessages]);

    useEffect(() => {
        if (bootstrappedRef.current) return;
        bootstrappedRef.current = true;
        void loadInitialSession();
    }, [loadInitialSession]);

    const sendMessage = useCallback(
        async (content: string, recipeId?: string) => {
            if (!activeSessionId || !content.trim()) return;

            const userMessage: ChatMessage = {
                id: Date.now().toString(),
                content,
                sender: 'user',
                timestamp: new Date(),
            };

            const assistantId = `assistant-${Date.now()}`;
            setMessages((prev) => [
                ...prev,
                userMessage,
                {id: assistantId, content: '', sender: 'assistant', timestamp: new Date()},
            ]);

            setLoading(true);
            setError(null);

            try {
                await streamAssistantMessage(activeSessionId, {content, recipe_id: recipeId}, {
                    onChunk: (chunk) =>
                        setMessages((prev) =>
                            prev.map((m) =>
                                m.id === assistantId
                                    ? {...m, content: m.content + chunk}
                                    : m,
                            ),
                        ),
                    onComplete: () => setLoading(false),
                });
            } catch (err) {
                console.error('Streaming error', err);
                setLoading(false);
                setError('Failed to send message');
            }
        },
        [activeSessionId],
    );

    const deleteSession = useCallback(async (sessionId: string) => {
        try {
            await deleteChatSession(sessionId);
            setSessions((prev) => prev.filter((s) => s.id !== sessionId));
            if (activeSessionId === sessionId) {
                setActiveSessionId(null);
                setMessages([]);
            }
            setError(null);
        } catch (err) {
            console.error('Failed to delete session', err);
            setError('Failed to delete session');
        }
    }, [activeSessionId]);

    const deleteAllSessions = useCallback(async () => {
        try {
            await Promise.all(sessions.map((s) => deleteChatSession(s.id)));
            setSessions([]);
            setActiveSessionId(null);
            setMessages([createInitialAssistantMessage(initialAssistantText)]);
            setError(null);
        } catch (err) {
            console.error('Failed to delete all sessions', err);
            setError('Failed to delete all sessions');
        }
    }, [sessions]);

    const reindex = useCallback(async () => {
        try {
            await reindexAllEmbeddings();
        } catch (err) {
            console.error('Failed to trigger reindexing', err);
            setError('Failed to trigger reindexing');
        }
    }, []);

    return {
        sessions,
        activeSessionId,
        messages,
        loading,
        error,
        sessionsLoaded,
        sendMessage,
        createSession,
        deleteSession,
        deleteAllSessions,
        reindex,
        selectSession: loadSessionMessages,
    };
};
