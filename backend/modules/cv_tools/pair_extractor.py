"""Flatten TEDS image/XML pairs without modifying source data."""
import csv
import filecmp
import hashlib
import os
import shutil
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from PIL import Image

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
_EXTRACTION_LOCK = threading.Lock()


def validate_paths(source_dir, output_dir):
    source = Path(source_dir).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    if not source.is_dir():
        raise ValueError('源目录不存在或不是目录')
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('源目录与输出目录必须相互独立，不能相同或互相包含')
    if output.exists() and not output.is_dir():
        raise ValueError('输出路径不是目录')
    return source, output


def _scan(source, progress):
    pairs, unmatched, ambiguous = [], [], []
    seen = set()
    handled_files = set()

    def collect(images, xmls, parent):
        handled_files.update(images)
        handled_files.update(xmls)
        image_map, xml_map = defaultdict(list), defaultdict(list)
        for p in images:
            image_map[p.stem].append(p)
        for p in xmls:
            xml_map[p.stem].append(p)
        for stem in sorted(image_map.keys() | xml_map.keys()):
            ims, xs = image_map[stem], xml_map[stem]
            if len(ims) > 1 or len(xs) > 1:
                ambiguous.extend(str(p) for p in ims + xs)
            elif ims and xs:
                identity = (str(ims[0]), str(xs[0]))
                if identity not in seen:
                    seen.add(identity)
                    pairs.append((ims[0], xs[0], parent))
            else:
                unmatched.extend(str(p) for p in ims + xs)

    for current, dirs, names in os.walk(source, onerror=lambda exc: (_ for _ in ()).throw(exc)):
        dirs.sort()
        parent = Path(current)
        progress(0, 0, f'扫描目录: {parent}')
        image_dirs = [parent / name for name in dirs if name.casefold() in ('image', 'images')]
        xml_dirs = [parent / name for name in dirs if name.casefold() == 'xml']
        if image_dirs and xml_dirs:
            # Merge aliases before matching so duplicate candidates remain ambiguous.
            images = sorted(p for directory in image_dirs for p in directory.iterdir()
                            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
            xmls = sorted(p for directory in xml_dirs for p in directory.iterdir()
                          if p.is_file() and p.suffix.lower() == '.xml')
            collect(images, xmls, parent)
        # Do not report sibling-folder files again; still visit nested datasets
        # and collect co-located files that were not handled above.
        files = [parent / name for name in sorted(names)
                 if parent / name not in handled_files and (parent / name).is_file()]
        collect([p for p in files if p.suffix.lower() in IMAGE_SUFFIXES],
                [p for p in files if p.suffix.lower() == '.xml'], parent)
    return pairs, unmatched, ambiguous


def _short_stem(source, image, parent, limit):
    prefix = '_'.join(parent.relative_to(source).parts)
    stem = f'{prefix}_{image.stem}' if prefix else image.stem
    budget = limit - max(len(image.suffix.encode()), 4) - 24
    if len(stem.encode('utf-8')) > budget:
        digest = hashlib.sha256(image.relative_to(source).as_posix().encode('utf-8')).hexdigest()[:20]
        stem = stem.encode('utf-8')[:budget - 22].decode('utf-8', errors='ignore') + '__' + digest
    return stem


def extract_pairs(source_dir, output_dir, dry_run=True, progress_callback=None, split_by_ratio=False):
    source, output = validate_paths(source_dir, output_dir)
    progress = progress_callback or (lambda *_: None)
    # Avoid two queued extraction jobs choosing the same destination names.
    with _EXTRACTION_LOCK:
        pairs, unmatched, ambiguous = _scan(source, progress)
        result = {'success': True, 'dry_run': dry_run, 'output_dir': str(output),
                  'matched_pairs': len(pairs), 'copied_pairs': 0, 'existing_pairs': 0,
                  'unmatched_count': len(unmatched), 'ambiguous_count': len(ambiguous),
                  'unmatched_files': unmatched, 'ambiguous_files': ambiguous, 'errors': [],
                  'manifest_path': None, 'split_by_ratio': split_by_ratio,
                  'size_groups': {key: {'matched_pairs': 0, 'copied_pairs': 0, 'existing_pairs': 0}
                                  for key in ('small', 'long')} if split_by_ratio else {}}
        destinations = {'small': output / '小图', 'long': output / '长图'} if split_by_ratio else {'': output}
        if not dry_run:
            for destination in destinations.values():
                (destination / 'images').mkdir(parents=True, exist_ok=True)
                (destination / 'xml').mkdir(parents=True, exist_ok=True)
        ancestor = output
        while not ancestor.exists():
            ancestor = ancestor.parent
        limit = min(os.pathconf(ancestor, 'PC_NAME_MAX'), 255)
        reserved, records = {}, []
        for index, (image, xml, parent) in enumerate(pairs):
            progress(index, len(pairs), f'处理配对: {image.name}')
            try:
                group, width, height = '', '', ''
                if split_by_ratio:
                    with Image.open(image) as opened:
                        width, height = opened.size
                    if width <= 0 or height <= 0:
                        raise ValueError('图片宽高必须大于零')
                    # Small images include both orientations and the 1:2 / 2:1 boundaries.
                    group = 'small' if max(width, height) <= 2 * min(width, height) else 'long'
                    result['size_groups'][group]['matched_pairs'] += 1
                destination = destinations[group]
                base = _short_stem(source, image, parent, limit)
                duplicate = 0
                while True:
                    stem = base if not duplicate else f'{base}__dup{duplicate}'
                    image_dst = destination / 'images' / (stem + image.suffix)
                    xml_dst = destination / 'xml' / (stem + xml.suffix)
                    if max(len(image_dst.name.encode()), len(xml_dst.name.encode())) > limit:
                        raise ValueError('目标重名数量超过文件名长度限制')
                    # Reserve the stem across extensions, including Dry Run plans.
                    previous = reserved.get((group, stem))
                    if previous:
                        same = (filecmp.cmp(image, previous[0], shallow=False) and
                                filecmp.cmp(xml, previous[1], shallow=False))
                        if same:
                            status = 'existing'
                            image_dst, xml_dst = previous[2], previous[3]
                            break
                        duplicate += 1
                        continue
                    other_images = [p for p in (destination / 'images').iterdir() if p.stem == stem] if (destination / 'images').exists() else []
                    other_xmls = [p for p in (destination / 'xml').iterdir() if p.stem == stem] if (destination / 'xml').exists() else []
                    conflicts = any(p != image_dst for p in other_images) or any(p != xml_dst for p in other_xmls)
                    ie, xe = image_dst.exists(), xml_dst.exists()
                    isame = ie and filecmp.cmp(image, image_dst, shallow=False)
                    xsame = xe and filecmp.cmp(xml, xml_dst, shallow=False)
                    if not conflicts and (not ie or isame) and (not xe or xsame):
                        status = 'existing' if isame and xsame else ('planned' if dry_run else 'copied')
                        if not dry_run:
                            if not ie:
                                shutil.copy2(image, image_dst)
                            if not xe:
                                shutil.copy2(xml, xml_dst)
                        reserved[(group, stem)] = (image, xml, image_dst, xml_dst)
                        break
                    duplicate += 1
                result['existing_pairs' if status == 'existing' else 'copied_pairs'] += 1
                if split_by_ratio:
                    result['size_groups'][group]['existing_pairs' if status == 'existing' else 'copied_pairs'] += 1
                records.append([str(image), str(xml), str(image_dst), str(xml_dst), status, group, width, height])
            except (OSError, ValueError) as exc:
                result['errors'].append({'path': str(image), 'error': str(exc)})
        progress(len(pairs), len(pairs), '提取完成')
        if not dry_run:
            manifest = output / ('extract_manifest_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.csv')
            with manifest.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['source_image', 'source_xml', 'target_image', 'target_xml', 'status', 'size_group', 'width', 'height'])
                writer.writerows(records)
            result['manifest_path'] = str(manifest)
        result['error_count'] = len(result['errors'])
        result['success'] = not result['errors']
        if result['errors']:
            result['error'] = f"{len(result['errors'])} 对复制失败，可修复问题后重新运行"
        return result
