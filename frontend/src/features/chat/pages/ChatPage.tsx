import {Box, Card, Typography} from '@mui/material';
import {ChatComposer} from '../components/ChatComposer';
import {ChatMessagesPanel} from '../components/ChatMessagesPanel';
import {ChatSessionsSidebar} from '../components/ChatSessionsSidebar';
import {useChatSessions} from '../hooks/useChatSessions';
import {useLocation} from "react-router-dom";
import {useEffect, useRef} from "react";

const ChatPage = () => {
    const location = useLocation();
    const params = new URLSearchParams(location.search);
    const recipeId = params.get("recipeId"); // e.g. "abc123"
    const isRecipeQuestion = params.get("askRecipeQuestion") === "1";
    const initialAssistantText = isRecipeQuestion
        ? "Ask a question about the recipe."
        : "What would you like to eat?";
    const {
        sessions,
        activeSessionId,
        messages,
        loading,
        error,
        sendMessage,
        selectSession,
        createSession,
        deleteSession,
        deleteAllSessions,
        reindex,
        sessionsLoaded
    } = useChatSessions(initialAssistantText);

    const recipeChatCreatedRef = useRef(false);
    useEffect(() => {
        // Wait until the hook finishes loading sessions
        if (!sessionsLoaded || recipeChatCreatedRef.current) return;

        // Only auto-create a session if:
        // - recipe mode is active
        // - no sessions exist
        // - we haven't already created one
        if (isRecipeQuestion) {

            recipeChatCreatedRef.current = true;
            createSession().then((newId) => {
                if (newId) {
                    selectSession(newId);
                }
            });
        }
    }, [sessionsLoaded, isRecipeQuestion, sessions.length, createSession, selectSession]);
    const handleSend = (content: string) => {
        if (isRecipeQuestion && recipeId) {
            return sendMessage(content, recipeId); // ← pass recipeId
        }
        return sendMessage(content); // normal chat
    };
    return (
        <Box sx={{display: 'flex', height: 'calc(100vh - 150px)'}}>
            <ChatSessionsSidebar
                sessions={sessions}
                activeSessionId={activeSessionId}
                onSelect={selectSession}
                onCreate={createSession}
                onDelete={deleteSession}
                onDeleteAll={deleteAllSessions}
                onReindexAll={reindex}
            />

            <Box
                sx={{
                    flexGrow: 1,
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'stretch',
                    p: 3,
                    overflow: 'hidden',
                }}
            >
                <Box
                    sx={{
                        width: '100%',
                        maxWidth: '1000px',
                        display: 'flex',
                        flexDirection: 'column',
                    }}
                >
                    <Typography variant="h4" component="h1" gutterBottom>
                        Meal Planning Assistant
                    </Typography>

                    {error && (
                        <Card sx={{mb: 2, p: 2}} role="alert">
                            <Typography color="error">{error}</Typography>
                        </Card>
                    )}

                    <ChatMessagesPanel messages={messages} loading={loading}/>
                    <ChatComposer onSend={handleSend} disabled={!activeSessionId || loading}/>
                </Box>
            </Box>
        </Box>
    );
};

export default ChatPage;
