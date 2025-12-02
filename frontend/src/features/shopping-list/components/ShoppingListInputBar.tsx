import {FC, FormEvent} from 'react';
import {Box, Button, TextField} from '@mui/material';

interface ShoppingListInputBarProps {
    value: string;
    onChange: (value: string) => void;
    onSubmit: () => void;
}

export const ShoppingListInputBar: FC<ShoppingListInputBarProps> = ({value, onChange, onSubmit}) => {
    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        onSubmit();
    };

    return (
        <Box component="form" onSubmit={handleSubmit} sx={{display: 'flex', gap: 2, mb: 3}}>
            <TextField
                size="small"
                placeholder="Add ingredient..."
                value={value}
                onChange={event => onChange(event.target.value)}
                sx={{flexGrow: 1, minWidth: 300}}
            />
            <Button type="submit" variant="contained">
                Add
            </Button>
        </Box>
    );
};
