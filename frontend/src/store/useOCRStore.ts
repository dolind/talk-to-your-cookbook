import {create} from 'zustand';

import {
    BookScan,
    ClassificationRecordRead,
    PageScanRecord,
    PageStatus,
    RecordStatus,
    SegmentationSegment,
} from '../lib/model.ts';
import {fetchClassificationRecord, fetchRecordsApi} from "../features/ocr/api/recordsApi.ts";
import {fetchBookImages} from "../features/ocr/api/ocrApi.ts";

export type ViewMode = 'scans' | 'records';

interface OCRState {
    pages: PageScanRecord[];
    bookScans: BookScan[];
    selectedBookId: string | 'all' | 'no-book';

    editingImageId: string | null;
    tempSegments: Record<string, SegmentationSegment[]>;
    manualSegmentation: Record<string, boolean>;
    setManualSegmentation: (imageId: string, value: boolean) => void;
    records: ClassificationRecordRead[];
    editingRecordId: string | null;

    viewMode: ViewMode;

    // Actions
    setSelectedBookId: (id: string | 'all' | 'no-book') => void;
    setImages: (images: PageScanRecord[]) => void;
    setBookScans: (scans: BookScan[]) => void;
    updatePageStatus: (imageId: string, status: PageStatus) => void;
    refetchPages: (bookId: string) => Promise<void>;
    startEditing: (id: string) => void;
    stopEditing: () => void;
    setTempSegments: (id: string, segs: SegmentationSegment[]) => void;

    setRecords: (records: ClassificationRecordRead[]) => void;
    startRecordEditing: (id: string) => void;
    stopRecordEditing: () => void;
    updateRecordStatus: (id: string, status: RecordStatus) => void;

    setViewMode: (mode: ViewMode) => void;
    fetchRecordIfNeeded: (id: string) => Promise<void>;
}

const sortRecords = (records: ClassificationRecordRead[]) => {
    return [...records].sort((a, b) => {
        const aPages = [...(a.text_pages ?? []), ...(a.image_pages ?? [])];
        const bPages = [...(b.text_pages ?? []), ...(b.image_pages ?? [])];

        const aFirst = aPages.length ? aPages[0].page_number ?? Infinity : Infinity;
        const bFirst = bPages.length ? bPages[0].page_number ?? Infinity : Infinity;

        return aFirst - bFirst;
    });
};

const sortPages = (pages: PageScanRecord[]) => {
    return [...pages].sort((a, b) => {
        const aNum = a.page_number ?? Infinity;
        const bNum = b.page_number ?? Infinity;
        return aNum - bNum;
    });
};


export const useOCRStore = create<OCRState>((set, get) => ({
    pages: [],
    bookScans: [],
    selectedBookId: '',
    editingImageId: null,
    tempSegments: {},
    records: [],
    editingRecordId: null,
    viewMode: localStorage.getItem('ocr_viewMode') === 'records' ? 'records' : 'scans',

    setSelectedBookId: (id) => {
        set({
            selectedBookId: id,
            pages: [],
            records: [],
            editingImageId: null,
            editingRecordId: null,
        });
    },
    setImages: (images) => {
        const current = get();

        // Prepare new entries from incoming images
        const newTempSegments: Record<string, SegmentationSegment[]> = {...current.tempSegments};
        const newManualSegmentation: Record<string, boolean> = {...current.manualSegmentation};

        for (const img of images) {
            const hasLocalSegs = newTempSegments[img.id] !== undefined;
            const hasLocalManual = newManualSegmentation[img.id] !== undefined;

            // only overwrite if not already defined
            if (!hasLocalSegs) {
                newTempSegments[img.id] = img.page_segments ?? [];
            }

            if (!hasLocalManual) {
                newManualSegmentation[img.id] = !!img.segmentation_done;
            }
        }

        set({
            pages: sortPages(images),
            tempSegments: newTempSegments,
            manualSegmentation: newManualSegmentation,
        });
    },

    setBookScans: (scans) => set({bookScans: scans}),


    refetchPages: async (bookId: string) => {
        const res = await fetchBookImages(bookId);
        set({pages: res.data});
    },
    updatePageStatus: async (imageId, status) => {
        const {pages, selectedBookId} = get();

        const exists = pages.some((img) => img.id === imageId);
        if (exists) {
            // normal update
            set({
                pages: sortPages(pages.map(img =>
                    img.id === imageId ? {...img, status} : img
                )),
            });
        } else if (selectedBookId && selectedBookId !== 'all') {
            // new page? refetch book pages
            try {
                await get().refetchPages(selectedBookId);
            } catch (e) {
                console.error('Failed to refetch pages', e);
            }
        }
    },


    startEditing: (id) => set({editingImageId: id}),
    stopEditing: () => set({editingImageId: null}),

    setTempSegments: (id, segs) =>
        set((state) => {
            return {
                tempSegments: {...state.tempSegments, [id]: segs},
            };
        }),

    manualSegmentation: {}, // Record<imageId, boolean>
    setManualSegmentation: (imageId: string, value: boolean) =>
        set((state) => ({
            manualSegmentation: {
                ...state.manualSegmentation,
                [imageId]: value,
            },
        })),

    setRecords: (records) => set({records: sortRecords(records)}),
    startRecordEditing: (id) => set({editingRecordId: id}),
    stopRecordEditing: () => set({editingRecordId: null}),

    updateRecordStatus: async (id, status) => {
        const {records, selectedBookId} = get();
        const exists = records.some((r) => r.id === id);

        if (exists) {
            set({
                records: records.map((r) =>
                    r.id === id ? {...r, status} : r
                ),
            });
        } else {
            // unknown record — refetch all
            if (selectedBookId && selectedBookId !== 'all') {
                try {
                    const res = await fetchRecordsApi(selectedBookId);
                    set({records: sortRecords(res.data)});
                } catch (e) {
                    console.error('Failed to refetch records', e);
                }
            }
        }
    },

    fetchRecordIfNeeded: async (id: string) => {
        const existing = get().records.find(r => r.id === id);

        const isComplete = existing &&
            existing.text_pages.length > 0 &&
            existing.image_pages.length > 0 &&
            existing.created_at; // adjust based on what “complete” means to you

        if (isComplete) return;

        try {
            const record = await fetchClassificationRecord(id);
            set((state) => ({
                records: sortRecords([
                    ...state.records.filter(r => r.id !== id),
                    record,
                ]),
            }));
        } catch (err) {
            console.error(`❌ Failed to fetch record ${id}`, err);
        }
    },

    setViewMode: (mode) => {
        localStorage.setItem('ocr_viewMode', mode);
        set({viewMode: mode});
    },
}));
