import {useEffect} from 'react';
import {useOCRStore} from '../../../store/useOCRStore';
import {createBookScan, deleteBookScan, getBookScans} from '../api/bookScanApi';
import {useSnackbar} from 'notistack';
import {BookScan} from '../../../lib/model';

/** Encapsulates loading, creating and deleting book scans. */
export function useBookScans() {
    const {bookScans, setBookScans, setSelectedBookId} = useOCRStore();
    const {enqueueSnackbar} = useSnackbar();

    const refreshBookScans = async () => {
        try {
            const res = await getBookScans();
            setBookScans(res.data);
        } catch {
            enqueueSnackbar('Failed to load book scans', {variant: 'error'});
        }
    };

    const addNewScan = async () => {
        const title = prompt('Enter a title for the new book scan:');
        if (!title) return;
        try {
            const res = await createBookScan(title);
            const created: BookScan = res.data;
            setBookScans([...bookScans, created]);
            setSelectedBookId(created.id);
            enqueueSnackbar('New scan created', {variant: 'success'});
        } catch {
            enqueueSnackbar('Failed to create book scan', {variant: 'error'});
        }
    };

    const removeScan = async (scanId: string) => {
        try {
            await deleteBookScan(scanId);
            enqueueSnackbar('Scan deleted', {variant: 'info'});
            refreshBookScans();
        } catch {
            enqueueSnackbar('Failed to delete scan', {variant: 'error'});
        }
    };

    useEffect(() => {
        refreshBookScans();
    }, []);

    return {refreshBookScans, addNewScan, removeScan};
}
