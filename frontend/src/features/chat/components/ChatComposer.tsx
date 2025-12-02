import {FC, FormEvent, useState} from 'react';
import {Box, Button, TextField} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

interface ChatComposerProps {
    onSend: (content: string) => Promise<void> | void;
    disabled?: boolean;
}

export const ChatComposer: FC<ChatComposerProps> = ({onSend, disabled}) => {
    const [input, setInput] = useState('');

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const value = input.trim();
        if (!value) return;
        await onSend(value);
        setInput('');
    };

    return (
        <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{
                p: 2,
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                borderTop: '1px solid #eee',
            }}
        >
            <TextField
                fullWidth
                placeholder="Ask about recipes or request a meal plan..."
                value={input}
                onChange={(event) => setInput(event.target.value)}
                variant="outlined"
                disabled={disabled}
            />
            <Button
                type="submit"
                variant="contained"
                color="primary"
                disabled={!input.trim() || disabled}
                endIcon={<SendIcon/>}
            >
                Send
            </Button>
        </Box>
    );
};
