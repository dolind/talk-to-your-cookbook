import {useEffect} from 'react';
import {useOCRStore} from '../../../store/useOCRStore';
import {useSnackbar} from 'notistack';
import {fetchRecordsApi} from '../api/recordsApi';
import {ClassificationRecordRead} from '../../../lib/model';

export function useRecords() {
    const {selectedBookId, setRecords} = useOCRStore();
    const {enqueueSnackbar} = useSnackbar();

    const fetchRecords = async () => {
        if (!selectedBookId) return;
        try {
            const res = await fetchRecordsApi(selectedBookId);
            setRecords(res.data as ClassificationRecordRead[]);
        } catch {
            enqueueSnackbar('Failed to load records', {variant: 'error'});
        }
    };

    useEffect(() => {
        fetchRecords();
    }, [selectedBookId]);

    return {fetchRecords};
}
