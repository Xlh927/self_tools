import React, { useState } from 'react';
import TaskController from '../common/TaskController.js';
import ErrorText from '../common/ErrorText.js';
import { extractPairs } from '../../api/tools.js';
import useToolTask from '../../hooks/useToolTask.js';

const e = React.createElement;

export default function PairExtractorTool() {
    const [sourceDir, setSourceDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [dryRun, setDryRun] = useState(true);
    const [splitByRatio, setSplitByRatio] = useState(false);
    const inferredOutput = sourceDir.trim().replace(/\/+$/, '') + '_ok';
    const task = useToolTask({
        toolName: 'pair-extractor',
        startTask: () => extractPairs({ source_dir: sourceDir.trim(),
            output_dir: outputDir.trim() || inferredOutput, dry_run: dryRun, split_by_ratio: splitByRatio }),
    });
    const result = task.result;
    const field = (label, value, onChange, placeholder) => e('label', { className: 'input-group' },
        e('span', { className: 'input-label' }, label),
        e('input', { className: 'input-field', value, placeholder,
            onChange: (event) => onChange(event.target.value) }));
    const details = (title, items) => items?.length > 0 && e('details', {},
        e('summary', {}, `${title}（${items.length}）`),
        e('div', { style: { maxHeight: '240px', overflow: 'auto', overflowWrap: 'anywhere' } },
            items.map((item, index) => e('p', { key: index }, typeof item === 'string' ? item : `${item.path}: ${item.error}`))));
    return e('div', { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },
        field('源数据根目录（必填）', sourceDir, setSourceDir, '/path/to/广州局'),
        field('输出目录（留空使用源目录名 + _ok）', outputDir, setOutputDir,
            sourceDir.trim() ? inferredOutput : '/path/to/广州局_ok'),
        e('p', { style: { color: 'var(--text-secondary)', fontSize: '0.85rem' } },
            '递归查找 image 或 images 与 xml 子目录（目录名不区分大小写），以及同目录图片/XML，按同名配对复制到输出目录。长名称自动缩短，图片和 XML 共用名称；已有一致配对自动跳过。源文件保持不变。'),
        e('label', {}, e('input', { type: 'checkbox', checked: dryRun,
            onChange: (event) => setDryRun(event.target.checked) }), ' 空跑测试 (Dry Run) — 仅预览，不创建输出文件'),
        e('label', {}, e('input', { type: 'checkbox', checked: splitByRatio,
            onChange: (event) => setSplitByRatio(event.target.checked) }), ' 按长图/小图分别提取（可选）'),
        splitByRatio && e('p', { style: { color: 'var(--text-secondary)', fontSize: '0.85rem' } },
            '按图片实际像素宽高判断：0.5 ≤ 宽 ÷ 高 ≤ 2 为小图（包含 1:2 和 2:1），其余为长图。分别输出到“小图/images、xml”和“长图/images、xml”，XML 随图片分组。无法读取尺寸的图片会跳过并报告错误。'),
        e(TaskController, { ...task.taskControllerProps, canStart: !!sourceDir.trim() }),
        result && e('div', { className: `result-box ${result.success ? 'success' : 'error'}` },
            e('h3', {}, result.success ? (result.dry_run ? '预览完成' : '提取完成') : '提取未完成'),
            result.matched_pairs != null && e('div', {},
                e('p', {}, `匹配配对：${result.matched_pairs}；${result.dry_run ? '预计新增或补全' : '新增或补全'}：${result.copied_pairs}；已有一致配对：${result.existing_pairs}`),
                e('p', {}, `未配对文件：${result.unmatched_count}；配对歧义文件：${result.ambiguous_count}；失败配对：${result.error_count}`),
                e('p', { style: { overflowWrap: 'anywhere' } }, `输出目录：${result.output_dir}`),
                result.manifest_path && e('p', { style: { overflowWrap: 'anywhere' } }, `来源映射清单：${result.manifest_path}`)),
            result.split_by_ratio && result.size_groups && e('div', {},
                ...[['small', '小图'], ['long', '长图']].map(([key, label]) => {
                    const counts = result.size_groups[key];
                    return e('p', { key }, `${label}：匹配 ${counts.matched_pairs} 对，${result.dry_run ? '预计新增或补全' : '新增或补全'} ${counts.copied_pairs} 对，已有一致 ${counts.existing_pairs} 对`);
                })),
            details('未配对文件', result.unmatched_files),
            details('配对歧义文件（同一名称对应多个文件，已跳过）', result.ambiguous_files),
            details('复制失败', result.errors),
            e(ErrorText, { error: result.error, errorCode: result.error_code })));
}
