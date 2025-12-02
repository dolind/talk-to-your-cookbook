import api from '../../../utils/api';
import {ClassificationRecordRead} from "../../../lib/model.ts";

export const approveRecord = (id: string, phase: 'group' | 'recipe' | 'taxonomy', payload?: any) => {
    const url = `/recipescanner/approve_classification/${id}`;

    if (phase === 'group') {
        return api.post(url, {
            phase,
            approved: true,
            recipe: payload ?? null, // this matches GroupApproval schema (list[Page])
        });
    }
    if (phase === 'recipe') {
        return api.post(url, {phase, approved: true, recipe: payload ?? null});
    }
    if (phase === 'taxonomy') {
        return api.post(url, {
            phase,
            approved: true,
            categories: payload?.categories ?? null,
            tags: payload?.tags ?? null,
            source: payload?.source ?? null,
        });
    }
    throw new Error(`Unsupported approval phase: ${phase}`);
};


export const addPageToRecord = (recordId: string, pageId: string) =>
    api.post(`/recipescanner/classification_records/${recordId}/pages/${pageId}`);

export const removePageFromRecord = (recordId: string, pageId: string) =>
    api.delete(`/recipescanner/classification_records/${recordId}/pages/${pageId}`);

export const redoRecord = (id: string) => api.post(`/recipescanner/trigger_classification/${id}`);
export const classifyRecipes = (bookId: string) => api.post(`/recipescanner/classify_book_scan/${bookId}`);
export const fetchRecordsApi = (bookId: string) =>
    api.get(`/recipescanner/book_scans/${bookId}/classification_records`);
export const deleteRecord = (id: string) =>
    api.delete(`/recipescanner/classification_records/${id}`);

export async function fetchClassificationRecord(id: string): Promise<ClassificationRecordRead> {
    const res = await api.get<ClassificationRecordRead>(`/recipescanner/classification_records/${id}`);
    return res.data;
}
