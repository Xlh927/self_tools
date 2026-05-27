import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { describe, expect, it } from 'vitest';
import SlurmGeneratorTool, { inferDataYamlRunFields } from './SlurmGeneratorTool.js';

describe('inferDataYamlRunFields', () => {
    it('infers project and name from a dataset path', () => {
        expect(inferDataYamlRunFields('/mnt/usrhome/sk/ndata/TFDS/dataset/baseline.yaml', 'train')).toEqual({
            project: '/mnt/usrhome/sk/ndata/TFDS/runs/train',
            name: 'baseline',
        });
    });

    it('infers project and name from a datasets path', () => {
        expect(inferDataYamlRunFields('/mnt/usrhome/sk/ndata/TFDS/datasets/baseline.yml', 'train')).toEqual({
            project: '/mnt/usrhome/sk/ndata/TFDS/runs/train',
            name: 'baseline',
        });
    });

    it('uses the mode-specific runs folder when provided', () => {
        expect(inferDataYamlRunFields('/data/datasets/exp.yaml', 'val')).toEqual({
            project: '/data/runs/val',
            name: 'exp',
        });
    });

    it('does not infer fields from non-dataset paths', () => {
        expect(inferDataYamlRunFields('/data/configs/exp.yaml', 'train')).toBe(null);
    });

    it('uses disk as the default cache mode in the generated train command', async () => {
        render(React.createElement(SlurmGeneratorTool));

        await waitFor(() => {
            expect(screen.getByText(/cache=disk/)).toBeTruthy();
        });
    });
});
