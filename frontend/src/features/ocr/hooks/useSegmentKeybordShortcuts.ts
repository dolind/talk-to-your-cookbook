import {useEffect} from 'react';
import {SegmentationSegment} from '../../../lib/model';

interface UseSegmentKeyboardShortcutsProps {
    selectedId: { segId: number; boxIdx: number } | null;
    segments: SegmentationSegment[];
    setSelectedId: (sel: { segId: number; boxIdx: number } | null) => void;
    setTempSegments: (imageId: string, segs: SegmentationSegment[]) => void;
    imageId: string;
}

export function useSegmentKeyboardShortcuts({
                                                selectedId,
                                                segments,
                                                setSelectedId,
                                                setTempSegments,
                                                imageId,
                                            }: UseSegmentKeyboardShortcutsProps) {
    useEffect(() => {
        const onKey = (ev: KeyboardEvent) => {
            if ((ev.key === 'Delete' || ev.key === 'Backspace') && selectedId) {
                // delete entire segment (or adapt to delete only the selected box if you want)
                const updated = segments.filter(s => s.id !== selectedId.segId);
                setTempSegments(imageId, updated);
                setSelectedId(null);
            }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [selectedId, segments, imageId, setTempSegments, setSelectedId]);
}
