import AugmentorTool from '../components/tools/AugmentorTool.js';
import CleanerTool from '../components/tools/CleanerTool.js';
import ConverterTool from '../components/tools/ConverterTool.js';
import CropperTool from '../components/tools/CropperTool.js';
import DeduplicatorTool from '../components/tools/DeduplicatorTool.js';
import GeneratorTool from '../components/tools/GeneratorTool.js';
import GridGeneratorTool from '../components/tools/GridGeneratorTool.js';
import LabelModifierTool from '../components/tools/LabelModifierTool.js';
import MatcherTool from '../components/tools/MatcherTool.js';
import SlurmGeneratorTool from '../components/tools/SlurmGeneratorTool.js';
import SplitterTool from '../components/tools/SplitterTool.js';
import VisualizerTool from '../components/tools/VisualizerTool.js';

export const TOOL_COMPONENTS = {
    converter: ConverterTool,
    cropper: CropperTool,
    generator: GeneratorTool,
    splitter: SplitterTool,
    deduplicator: DeduplicatorTool,
    matcher: MatcherTool,
    visualizer: VisualizerTool,
    'label-modifier': LabelModifierTool,
    augmentor: AugmentorTool,
    'grid-generator': GridGeneratorTool,
    'slurm-generator': SlurmGeneratorTool,
    cleaner: CleanerTool,
};

export function getToolComponentById(toolId) {
    return TOOL_COMPONENTS[toolId] || null;
}
