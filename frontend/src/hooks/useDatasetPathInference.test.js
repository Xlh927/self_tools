import { act, renderHook, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import useDatasetPathInference from './useDatasetPathInference.js';

function renderPathInferenceHook(initialState = {}) {
    return renderHook(() => {
        const [imagesDir, setImagesDir] = useState(initialState.imagesDir || '');
        const [annotationsDir, setAnnotationsDir] = useState(initialState.annotationsDir || '');
        const [outputDir, setOutputDir] = useState(initialState.outputDir || '');

        useDatasetPathInference({
            imagesDir,
            setImagesDir,
            annotationsDir,
            setAnnotationsDir,
            outputDir,
            setOutputDir,
            outputFolderName: initialState.outputFolderName || 'split_dataset',
            outputFromAnnotationsMode: initialState.outputFromAnnotationsMode || 'always',
        });

        return {
            imagesDir,
            setImagesDir,
            annotationsDir,
            setAnnotationsDir,
            outputDir,
            setOutputDir,
        };
    });
}

describe('useDatasetPathInference', () => {
    it('infers annotations and output from images dir', async () => {
        const { result } = renderPathInferenceHook();

        act(() => {
            result.current.setImagesDir('/data/images');
        });

        await waitFor(() => {
            expect(result.current.annotationsDir).toBe('/data/annotations');
            expect(result.current.outputDir).toBe('/data/split_dataset');
        });
    });

    it('infers images and output from annotations dir', async () => {
        const { result } = renderPathInferenceHook({
            outputFolderName: 'visualized',
        });

        act(() => {
            result.current.setAnnotationsDir('/data/annotations');
        });

        await waitFor(() => {
            expect(result.current.imagesDir).toBe('/data/images');
            expect(result.current.outputDir).toBe('/data/visualized');
        });
    });

    it('does not override manually specified output dir', async () => {
        const { result } = renderPathInferenceHook({
            outputDir: '/tmp/custom-output',
        });

        act(() => {
            result.current.setImagesDir('/data/images');
        });

        await waitFor(() => {
            expect(result.current.outputDir).toBe('/tmp/custom-output');
        });
    });
});

