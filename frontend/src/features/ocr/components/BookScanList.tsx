import {Box, Button, IconButton, List, ListItemButton, ListItemText, Typography,} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import {useOCRStore} from '../../../store/useOCRStore';
import {useBookScans} from '../hooks/useBookScans';

export const BookScanList = () => {
    const {bookScans, selectedBookId, setSelectedBookId} = useOCRStore();
    const {addNewScan, removeScan} = useBookScans();

    return (
        <>
            <Typography variant="h6">Book Scans</Typography>

            <Button fullWidth variant="outlined" onClick={addNewScan} sx={{mb: 2}}>
                New Scan
            </Button>

            <List>
                {bookScans.map(scan => (
                    <Box
                        key={scan.id}
                        sx={{display: 'flex', alignItems: 'center', mb: 0.5}}
                    >
                        <ListItemButton
                            selected={selectedBookId === scan.id}
                            onClick={() => setSelectedBookId(scan.id)}
                            sx={{flexGrow: 1}}
                        >
                            <ListItemText primary={scan.title}/>
                        </ListItemButton>
                        <IconButton
                            edge="end"
                            size="small"
                            color="error"
                            onClick={() => removeScan(scan.id)}
                        >
                            <DeleteIcon fontSize="small"/>
                        </IconButton>
                    </Box>
                ))}
            </List>
        </>
    );
};
