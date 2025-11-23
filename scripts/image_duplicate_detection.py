#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像查重/相似图匹配模块（A6）

功能：
- pHash / aHash / dHash 计算
- 重复图检测
- 相似图聚类

支持单文件和批量文件夹处理
"""

import os
import cv2
import numpy as np
import argparse
import glob
import json
import shutil
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, deque
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler


def load_image(image_path: str, target_size: Tuple[int, int] = (32, 32)) -> Optional[np.ndarray]:
    """
    加载并预处理图像
    
    Args:
        image_path: 图像路径
        target_size: 调整后的目标尺寸
    
    Returns:
        预处理后的图像或None
    """
    try:
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            print(f"警告: 无法读取图像 {image_path}")
            return None
        
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 调整大小
        resized = cv2.resize(gray, target_size, interpolation=cv2.INTER_AREA)
        
        return resized
    except Exception as e:
        print(f"处理图像 {image_path} 时出错: {str(e)}")
        return None

def compute_ahash(image: np.ndarray, hash_size: int = 8) -> int:
    """
    计算图像的平均哈希值 (aHash)
    
    Args:
        image: 输入图像 (灰度图)
        hash_size: 哈希大小
    
    Returns:
        哈希值 (整数)
    """
    # 调整大小
    resized = cv2.resize(image, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    
    # 计算差值
    diff = resized[:, 1:] > resized[:, :-1]
    
    # 转换为哈希值
    return sum([2**i for i, v in enumerate(diff.flatten()) if v])

def compute_phash(image: np.ndarray, hash_size: int = 8, highfreq_factor: int = 4) -> int:
    """
    计算图像的感知哈希值 (pHash)
    
    Args:
        image: 输入图像 (灰度图)
        hash_size: 哈希大小
        highfreq_factor: 高频因子
    
    Returns:
        哈希值 (整数)
    """
    import scipy.fftpack
    
    # 计算FFT大小
    img_size = hash_size * highfreq_factor
    
    # 调整大小
    resized = cv2.resize(image, (img_size, img_size), interpolation=cv2.INTER_AREA)
    
    # 计算FFT
    dct = scipy.fftpack.dct(scipy.fftpack.dct(resized, axis=0), axis=1)
    
    # 提取低频部分
    dct_low_freq = dct[:hash_size, :hash_size]
    
    # 计算均值（不包括第一个元素）
    mean_val = np.mean(dct_low_freq[1:, 1:])
    
    # 转换为哈希值
    diff = dct_low_freq > mean_val
    return sum([2**i for i, v in enumerate(diff.flatten()) if v])

def compute_dhash(image: np.ndarray, hash_size: int = 8) -> int:
    """
    计算图像的差异哈希值 (dHash)
    
    Args:
        image: 输入图像 (灰度图)
        hash_size: 哈希大小
    
    Returns:
        哈希值 (整数)
    """
    # 调整大小
    resized = cv2.resize(image, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    
    # 计算行差值
    diff = resized[:, 1:] > resized[:, :-1]
    
    # 转换为哈希值
    return sum([2**i for i, v in enumerate(diff.flatten()) if v])

def hamming_distance(hash1: int, hash2: int) -> int:
    """
    计算两个哈希值之间的汉明距离
    
    Args:
        hash1: 第一个哈希值
        hash2: 第二个哈希值
    
    Returns:
        汉明距离
    """
    return bin(hash1 ^ hash2).count('1')

def hash_to_string(hash_val: int, hash_size: int = 8) -> str:
    """
    将哈希值转换为十六进制字符串
    
    Args:
        hash_val: 哈希值
        hash_size: 哈希大小
    
    Returns:
        十六进制字符串
    """
    return f"{hash_val:x}".zfill(hash_size**2 // 4)

def compute_all_hashes(image_path: str, hash_size: int = 8) -> Dict[str, Any]:
    """
    计算图像的所有类型哈希值
    
    Args:
        image_path: 图像路径
        hash_size: 哈希大小
    
    Returns:
        包含所有哈希值的字典
    """
    # 加载图像
    image = load_image(image_path, (hash_size * 4, hash_size * 4))
    if image is None:
        return None
    
    try:
        # 计算不同类型的哈希值
        ahash_val = compute_ahash(image, hash_size)
        phash_val = compute_phash(image, hash_size)
        dhash_val = compute_dhash(image, hash_size)
        
        return {
            "file_path": image_path,
            "ahash": ahash_val,
            "phash": phash_val,
            "dhash": dhash_val,
            "ahash_str": hash_to_string(ahash_val, hash_size),
            "phash_str": hash_to_string(phash_val, hash_size),
            "dhash_str": hash_to_string(dhash_val, hash_size)
        }
    except Exception as e:
        print(f"计算图像 {image_path} 的哈希值时出错: {str(e)}")
        return None

def find_duplicate_images(
    image_hashes: List[Dict[str, Any]], 
    hash_type: str = "phash",
    threshold: int = 5
) -> List[List[Dict[str, Any]]]:
    """
    查找重复或相似图像
    
    Args:
        image_hashes: 图像哈希值列表
        hash_type: 使用的哈希类型 (ahash/phash/dhash)
        threshold: 汉明距离阈值
    
    Returns:
        重复图像组列表
    """
    # 确保哈希类型有效
    if hash_type not in ["ahash", "phash", "dhash"]:
        raise ValueError("无效的哈希类型，必须是 ahash, phash 或 dhash")
    
    # 初始化重复组
    groups = []
    used_indices = set()
    
    # 对每个图像，查找相似图像
    for i in range(len(image_hashes)):
        if i in used_indices:
            continue
        
        current_group = [image_hashes[i]]
        used_indices.add(i)
        
        # 查找相似图像
        for j in range(i + 1, len(image_hashes)):
            if j in used_indices:
                continue
            
            # 计算汉明距离
            distance = hamming_distance(
                image_hashes[i][hash_type], 
                image_hashes[j][hash_type]
            )
            
            # 如果距离小于阈值，则认为相似
            if distance <= threshold:
                current_group.append(image_hashes[j])
                used_indices.add(j)
        
        # 只有包含多个图像的组才添加
        if len(current_group) > 1:
            groups.append(current_group)
    
    return groups

def cluster_similar_images(
    image_hashes: List[Dict[str, Any]],
    hash_type: str = "phash",
    eps: float = 0.5,
    min_samples: int = 2
) -> List[List[Dict[str, Any]]]:
    """
    使用DBSCAN聚类算法对相似图像进行聚类
    
    Args:
        image_hashes: 图像哈希值列表
        hash_type: 使用的哈希类型 (ahash/phash/dhash)
        eps: DBSCAN的eps参数
        min_samples: DBSCAN的min_samples参数
    
    Returns:
        聚类结果列表
    """
    # 确保哈希类型有效
    if hash_type not in ["ahash", "phash", "dhash"]:
        raise ValueError("无效的哈希类型，必须是 ahash, phash 或 dhash")
    
    if len(image_hashes) < min_samples:
        return []
    
    # 提取哈希值
    hash_values = [img[hash_type] for img in image_hashes]
    
    # 将哈希值转换为特征向量（二进制表示）
    # 对于64位哈希，转换为64维向量
    feature_vectors = []
    for hash_val in hash_values:
        # 将哈希值转换为64位二进制向量
        vector = np.array([int(bit) for bit in bin(hash_val)[2:].zfill(64)])
        feature_vectors.append(vector)
    
    # 标准化特征向量
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(feature_vectors)
    
    # 应用DBSCAN聚类
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
    labels = dbscan.fit_predict(scaled_features)
    
    # 组织聚类结果
    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        # 忽略噪声点（标签为-1）
        if label != -1:
            clusters[label].append(image_hashes[i])
    
    # 转换为列表格式
    return list(clusters.values())

def compute_image_similarity(
    image1_path: str, 
    image2_path: str,
    hash_type: str = "phash"
) -> Dict[str, Any]:
    """
    计算两张图像的相似度
    
    Args:
        image1_path: 第一张图像路径
        image2_path: 第二张图像路径
        hash_type: 使用的哈希类型
    
    Returns:
        相似度信息字典
    """
    # 计算两张图像的哈希值
    hash1 = compute_all_hashes(image1_path)
    hash2 = compute_all_hashes(image2_path)
    
    if hash1 is None or hash2 is None:
        return {"error": "无法计算图像哈希值"}
    
    # 计算所有哈希类型的汉明距离
    results = {
        "image1": image1_path,
        "image2": image2_path,
        "ahash_distance": hamming_distance(hash1["ahash"], hash2["ahash"]),
        "phash_distance": hamming_distance(hash1["phash"], hash2["phash"]),
        "dhash_distance": hamming_distance(hash1["dhash"], hash2["dhash"]),
    }
    
    # 计算指定哈希类型的相似度
    distance = results[f"{hash_type}_distance"]
    # 假设哈希大小为8x8=64位
    max_distance = 64
    similarity = 1.0 - (distance / max_distance)
    
    results.update({
        f"{hash_type}_similarity": similarity,
        "recommended_hash_type": "phash",  # pHash通常效果最好
        "is_duplicate": distance <= 5,  # 小于等于5通常认为是重复
        "is_similar": distance <= 10,  # 小于等于10通常认为是相似
    })
    
    return results

def batch_compute_hashes(
    input_dir: str,
    output_file: str = None,
    hash_size: int = 8,
    recursive: bool = False
) -> List[Dict[str, Any]]:
    """
    批量计算目录中所有图像的哈希值
    
    Args:
        input_dir: 输入目录
        output_file: 输出文件路径
        hash_size: 哈希大小
        recursive: 是否递归处理子目录
    
    Returns:
        图像哈希值列表
    """
    # 获取图像文件列表
    if recursive:
        glob_pattern = os.path.join(input_dir, "**", "*.???")
    else:
        glob_pattern = os.path.join(input_dir, "*.???")
    
    # 常见图像格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_files = [
        f for f in glob.glob(glob_pattern, recursive=recursive)
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in image_extensions
    ]
    
    print(f"找到 {len(image_files)} 个图像文件")
    
    # 计算所有图像的哈希值
    hashes = []
    for i, image_path in enumerate(image_files):
        if (i + 1) % 10 == 0 or i + 1 == len(image_files):
            print(f"处理进度: {i + 1}/{len(image_files)}")
        
        image_hash = compute_all_hashes(image_path, hash_size)
        if image_hash:
            hashes.append(image_hash)
    
    print(f"成功计算 {len(hashes)} 个图像的哈希值")
    
    # 保存结果
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2, ensure_ascii=False)
        print(f"哈希值已保存到: {output_file}")
    
    return hashes

def load_hashes_from_file(hashes_file: str) -> List[Dict[str, Any]]:
    """
    从文件加载哈希值
    
    Args:
        hashes_file: 哈希值文件路径
    
    Returns:
        哈希值列表
    """
    try:
        with open(hashes_file, 'r', encoding='utf-8') as f:
            hashes = json.load(f)
        print(f"成功从 {hashes_file} 加载 {len(hashes)} 个哈希值")
        return hashes
    except Exception as e:
        print(f"加载哈希值文件失败: {str(e)}")
        return []

def save_duplicate_results(
    duplicate_groups: List[List[Dict[str, Any]]],
    output_file: str
) -> bool:
    """
    保存重复图像检测结果
    
    Args:
        duplicate_groups: 重复图像组列表
        output_file: 输出文件路径
    
    Returns:
        是否保存成功
    """
    try:
        # 准备结果数据
        results = {
            "total_groups": len(duplicate_groups),
            "total_duplicates": sum(len(group) for group in duplicate_groups),
            "duplicate_groups": []
        }
        
        for i, group in enumerate(duplicate_groups):
            group_info = {
                "group_id": i + 1,
                "size": len(group),
                "images": [
                    {
                        "file_path": img["file_path"],
                        "phash_str": img["phash_str"]
                    }
                    for img in group
                ]
            }
            results["duplicate_groups"].append(group_info)
        
        # 保存结果
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"重复图像检测结果已保存到: {output_file}")
        return True
    except Exception as e:
        print(f"保存重复图像检测结果失败: {str(e)}")
        return False

def organize_duplicates_by_group(
    duplicate_groups: List[List[Dict[str, Any]]],
    output_dir: str
) -> bool:
    """
    根据重复组组织图像到不同目录
    
    Args:
        duplicate_groups: 重复图像组列表
        output_dir: 输出目录
    
    Returns:
        是否组织成功
    """
    try:
        for i, group in enumerate(duplicate_groups):
            # 创建组目录
            group_dir = os.path.join(output_dir, f"group_{i + 1}")
            os.makedirs(group_dir, exist_ok=True)
            
            # 复制图像到组目录
            for img in group:
                src_path = img["file_path"]
                filename = os.path.basename(src_path)
                dst_path = os.path.join(group_dir, filename)
                
                # 如果文件名重复，添加前缀
                counter = 1
                base_name, ext = os.path.splitext(filename)
                while os.path.exists(dst_path):
                    dst_path = os.path.join(group_dir, f"{base_name}_{counter}{ext}")
                    counter += 1
                
                shutil.copy2(src_path, dst_path)
                print(f"复制 {src_path} -> {dst_path}")
        
        print(f"重复图像已组织到目录: {output_dir}")
        return True
    except Exception as e:
        print(f"组织重复图像失败: {str(e)}")
        return False

def find_and_remove_duplicates(
    image_hashes: List[Dict[str, Any]],
    hash_type: str = "phash",
    threshold: int = 5,
    keep_original: bool = True
) -> Tuple[List[str], List[List[Dict[str, Any]]]]:
    """
    查找并可选地删除重复图像
    
    Args:
        image_hashes: 图像哈希值列表
        hash_type: 使用的哈希类型
        threshold: 汉明距离阈值
        keep_original: 是否保留原始图像（修改时间最早的）
    
    Returns:
        删除的文件路径列表和重复组列表
    """
    # 查找重复组
    duplicate_groups = find_duplicate_images(image_hashes, hash_type, threshold)
    deleted_files = []
    
    for group in duplicate_groups:
        # 按文件修改时间排序
        group_sorted = sorted(group, key=lambda x: os.path.getmtime(x["file_path"]))
        
        # 保留第一个（最早的），删除其余的
        if keep_original:
            to_delete = group_sorted[1:]
        else:
            # 保留一个，删除其余的
            to_delete = group_sorted[:-1]
        
        for img in to_delete:
            try:
                os.remove(img["file_path"])
                deleted_files.append(img["file_path"])
                print(f"已删除重复图像: {img['file_path']}")
            except Exception as e:
                print(f"删除图像 {img['file_path']} 失败: {str(e)}")
    
    return deleted_files, duplicate_groups

def main():
    parser = argparse.ArgumentParser(description="图像查重/相似图匹配工具")
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # compute 命令 - 计算图像哈希值
    compute_parser = subparsers.add_parser("compute", help="计算图像哈希值")
    compute_parser.add_argument("-i", "--input", required=True, help="输入图像或目录路径")
    compute_parser.add_argument("-o", "--output", help="输出哈希值文件路径")
    compute_parser.add_argument("--hash-size", type=int, default=8, help="哈希大小")
    compute_parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    # compare 命令 - 比较两张图像
    compare_parser = subparsers.add_parser("compare", help="比较两张图像的相似度")
    compare_parser.add_argument("-i1", "--input1", required=True, help="第一张图像路径")
    compare_parser.add_argument("-i2", "--input2", required=True, help="第二张图像路径")
    compare_parser.add_argument("--hash-type", choices=["ahash", "phash", "dhash"], default="phash",
                             help="使用的哈希类型")
    
    # find-duplicates 命令 - 查找重复图像
    find_duplicates_parser = subparsers.add_parser("find-duplicates", help="查找重复图像")
    find_duplicates_parser.add_argument("-i", "--input", required=True, help="输入目录路径或哈希值文件路径")
    find_duplicates_parser.add_argument("-o", "--output", help="输出结果文件路径")
    find_duplicates_parser.add_argument("--hash-type", choices=["ahash", "phash", "dhash"], default="phash",
                                     help="使用的哈希类型")
    find_duplicates_parser.add_argument("--threshold", type=int, default=5, help="汉明距离阈值")
    find_duplicates_parser.add_argument("--organize", help="按组组织重复图像的输出目录")
    find_duplicates_parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    # remove-duplicates 命令 - 删除重复图像
    remove_duplicates_parser = subparsers.add_parser("remove-duplicates", help="删除重复图像")
    remove_duplicates_parser.add_argument("-i", "--input", required=True, help="输入目录路径或哈希值文件路径")
    remove_duplicates_parser.add_argument("--hash-type", choices=["ahash", "phash", "dhash"], default="phash",
                                      help="使用的哈希类型")
    remove_duplicates_parser.add_argument("--threshold", type=int, default=5, help="汉明距离阈值")
    remove_duplicates_parser.add_argument("--keep-original", action="store_true",
                                      help="保留修改时间最早的图像")
    remove_duplicates_parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    # cluster 命令 - 聚类相似图像
    cluster_parser = subparsers.add_parser("cluster", help="聚类相似图像")
    cluster_parser.add_argument("-i", "--input", required=True, help="输入目录路径或哈希值文件路径")
    cluster_parser.add_argument("-o", "--output", help="输出聚类结果文件路径")
    cluster_parser.add_argument("--hash-type", choices=["ahash", "phash", "dhash"], default="phash",
                             help="使用的哈希类型")
    cluster_parser.add_argument("--eps", type=float, default=0.5, help="DBSCAN的eps参数")
    cluster_parser.add_argument("--min-samples", type=int, default=2, help="DBSCAN的min_samples参数")
    cluster_parser.add_argument("--organize", help="按聚类组织图像的输出目录")
    cluster_parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行相应的命令
    if args.command == "compute":
        if os.path.isfile(args.input):
            # 单文件处理
            result = compute_all_hashes(args.input, args.hash_size)
            if result:
                if args.output:
                    os.makedirs(os.path.dirname(args.output), exist_ok=True)
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump([result], f, indent=2, ensure_ascii=False)
                    print(f"哈希值已保存到: {args.output}")
                else:
                    print(f"图像: {args.input}")
                    print(f"aHash: {result['ahash_str']}")
                    print(f"pHash: {result['phash_str']}")
                    print(f"dHash: {result['dhash_str']}")
        else:
            # 批量处理
            batch_compute_hashes(args.input, args.output, args.hash_size, args.recursive)
    
    elif args.command == "compare":
        results = compute_image_similarity(args.input1, args.input2, args.hash_type)
        if "error" in results:
            print(results["error"])
        else:
            print(f"图像1: {args.input1}")
            print(f"图像2: {args.input2}")
            print(f"aHash距离: {results['ahash_distance']}")
            print(f"pHash距离: {results['phash_distance']}")
            print(f"dHash距离: {results['dhash_distance']}")
            print(f"{args.hash_type}相似度: {results[f'{args.hash_type}_similarity']:.4f}")
            print(f"是否重复: {'是' if results['is_duplicate'] else '否'}")
            print(f"是否相似: {'是' if results['is_similar'] else '否'}")
    
    elif args.command == "find-duplicates":
        # 加载或计算哈希值
        if args.input.endswith('.json') and os.path.isfile(args.input):
            hashes = load_hashes_from_file(args.input)
        else:
            hashes = batch_compute_hashes(args.input, None, 8, args.recursive)
        
        # 查找重复图像
        duplicate_groups = find_duplicate_images(hashes, args.hash_type, args.threshold)
        
        print(f"\n找到 {len(duplicate_groups)} 组重复图像")
        print(f"总共找到 {sum(len(group) for group in duplicate_groups)} 个重复图像")
        
        # 保存结果
        if args.output:
            save_duplicate_results(duplicate_groups, args.output)
        
        # 组织重复图像
        if args.organize:
            organize_duplicates_by_group(duplicate_groups, args.organize)
    
    elif args.command == "remove-duplicates":
        # 加载或计算哈希值
        if args.input.endswith('.json') and os.path.isfile(args.input):
            hashes = load_hashes_from_file(args.input)
        else:
            hashes = batch_compute_hashes(args.input, None, 8, args.recursive)
        
        # 查找并删除重复图像
        deleted_files, duplicate_groups = find_and_remove_duplicates(
            hashes, args.hash_type, args.threshold, args.keep_original
        )
        
        print(f"\n总共删除了 {len(deleted_files)} 个重复图像")
    
    elif args.command == "cluster":
        # 加载或计算哈希值
        if args.input.endswith('.json') and os.path.isfile(args.input):
            hashes = load_hashes_from_file(args.input)
        else:
            hashes = batch_compute_hashes(args.input, None, 8, args.recursive)
        
        # 聚类相似图像
        clusters = cluster_similar_images(
            hashes, args.hash_type, args.eps, args.min_samples
        )
        
        print(f"\n找到 {len(clusters)} 个相似图像聚类")
        print(f"总共 {sum(len(cluster) for cluster in clusters)} 个图像被聚类")
        
        # 保存结果
        if args.output:
            save_duplicate_results(clusters, args.output)
        
        # 组织聚类图像
        if args.organize:
            organize_duplicates_by_group(clusters, args.organize)


if __name__ == "__main__":
    main()