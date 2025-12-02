import {FC} from 'react';
import {Box, Button, IconButton, Typography} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import {ChatSessionSummary} from '../types';

interface ChatSessionsSidebarProps {
    sessions: ChatSessionSummary[];
    activeSessionId: string | null;
    onSelect: (sessionId: string) => void;
    onCreate: () => Promise<string | null> | void;
    onDelete: (sessionId: string) => void | Promise<void>;
    onDeleteAll: () => void | Promise<void>;
    onReindexAll: () => void | Promise<void>;
}

export const ChatSessionsSidebar: FC<ChatSessionsSidebarProps> = ({
                                                                      sessions,
                                                                      activeSessionId,
                                                                      onSelect,
                                                                      onCreate,
                                                                      onDelete,
                                                                      onDeleteAll,
                                                                      onReindexAll,
                                                                  }) => {
    const formatDate = (iso: string) => {
        const date = new Date(iso);
        const day = date.getDate();
        const month = date.getMonth() + 1;
        const year = date.getFullYear();
        const hours = date.getHours();
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${day}.${month}.${year} ${hours}:${minutes}`;
    };

    return (
        <Box
            sx={{
                width: '25%',
                minWidth: '220px',
                maxWidth: '300px',
                overflowY: 'auto',
                p: 2,
                borderRight: '1px solid #ccc',
            }}
        >
            <Typography variant="h6" gutterBottom>
                Past Chats
            </Typography>

            {sessions.map(session => (
                <Box key={session.id} sx={{display: 'flex', alignItems: 'center', mb: 1}}>
                    <Button
                        fullWidth
                        variant={session.id === activeSessionId ? 'contained' : 'outlined'}
                        onClick={() => onSelect(session.id)}
                        sx={{textTransform: 'none', mr: 1}}
                    >
                        {session.title || formatDate(session.created_at)}
                    </Button>
                    <IconButton
                        size="small"
                        color="error"
                        onClick={() => onDelete(session.id)}
                    >
                        <DeleteIcon fontSize="small"/>
                    </IconButton>
                </Box>
            ))}

            <Button fullWidth variant="outlined" onClick={onCreate} sx={{mt: 1}}>
                New Chat
            </Button>
            <Button
                fullWidth
                variant="outlined"
                color="error"
                sx={{mt: 2}}
                onClick={onDeleteAll}
            >
                Delete All Chats
            </Button>
            <Button
                fullWidth
                variant="outlined"
                color="warning"
                sx={{mt: 2}}
                onClick={onReindexAll}
            >
                Reindex All Embeddings
            </Button>
        </Box>
    );
};
