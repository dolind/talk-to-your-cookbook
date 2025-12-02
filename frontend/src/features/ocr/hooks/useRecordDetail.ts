import {useEffect, useState} from 'react';
import {useOCRStore} from '../../../store/useOCRStore';
import {ClassificationRecordRead} from '../../../lib/model';

/** Load a record's validation JSON and keep it in local state. */
export function useRecordDetail(editingRecordId?: string | null) {
    const {fetchRecordIfNeeded} = useOCRStore();
    const [jsonText, setJsonText] = useState('');
    const [originalText, setOriginalText] = useState('');
    const [parseError, setParseError] = useState<string | null>(null);

    useEffect(() => {
        if (!editingRecordId) return;
        (async () => {
            await fetchRecordIfNeeded(editingRecordId);
            const current = useOCRStore.getState().records.find(
                r => r.id === editingRecordId
            ) as ClassificationRecordRead | undefined;
            const json = JSON.stringify(current?.validation_result ?? {}, null, 2);
            setJsonText(json);
            setOriginalText(json);
            setParseError(null);
        })();
    }, [editingRecordId]);

    const handleChange = (value: string) => {
        setJsonText(value);
        try {
            JSON.parse(value);
            setParseError(null);
        } catch (e: any) {
            setParseError(e.message);
        }
    };

    return {jsonText, originalText, parseError, setJsonText, handleChange};
}
